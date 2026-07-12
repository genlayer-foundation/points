from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from contributions.models import Category, ContributionType, SubmittedContribution
from partners.models import Partner
from validators.models import Validator

from notifications import campaigns, services
from notifications.models import (
    CustomNotification,
    Notification,
    NotificationReceipt,
    WhatsNewAnnouncement,
    WhatsNewAnnouncementSeen,
)

User = get_user_model()


def make_user(email, address):
    return User.objects.create_user(email=email, address=address, password='testpass123')


class SubmissionReviewNotificationTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Test', slug='test', description='Test')
        self.contribution_type = ContributionType.objects.create(
            name='Test Type',
            slug='test-type',
            description='Test type',
            category=self.category,
            min_points=1,
            max_points=10,
        )
        self.user = make_user('user@test.com', '0x1234567890123456789012345678901234567890')

    def test_repeated_same_state_review_creates_unread_notification(self):
        first_reviewed_at = timezone.now()
        submission = SubmittedContribution.objects.create(
            user=self.user,
            contribution_type=self.contribution_type,
            contribution_date=timezone.now(),
            notes='Test submission',
            state='rejected',
            staff_reply='First rejection',
            reviewed_at=first_reviewed_at,
        )

        first_notification = services.notify_submission_review(submission)
        first_notification.mark_read()

        submission.state = 'rejected'
        submission.staff_reply = 'Second rejection'
        submission.reviewed_at = first_reviewed_at + timedelta(days=1)
        submission.save()

        second_notification = services.notify_submission_review(submission)

        self.assertNotEqual(first_notification.id, second_notification.id)
        self.assertIsNone(second_notification.read_at)
        self.assertEqual(
            Notification.objects.filter(
                recipient=self.user,
                event_type='submission.rejected',
            ).count(),
            2,
        )

    def test_same_dedupe_key_never_reassigns_across_users(self):
        other_user = make_user('other-dedupe@test.com', '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa')

        first = services.notify(
            'referral.joined',
            recipient=self.user,
            title='First user notification',
            dedupe_key='shared-key',
        )
        second = services.notify(
            'referral.joined',
            recipient=other_user,
            title='Second user notification',
            dedupe_key='shared-key',
        )

        self.assertNotEqual(first.id, second.id)
        first.refresh_from_db()
        self.assertEqual(first.recipient, self.user)
        self.assertEqual(first.title, 'First user notification')
        self.assertEqual(second.recipient, other_user)

    def test_duplicate_review_call_dedupes(self):
        submission = SubmittedContribution.objects.create(
            user=self.user,
            contribution_type=self.contribution_type,
            contribution_date=timezone.now(),
            notes='Test submission',
            state='accepted',
            reviewed_at=timezone.now(),
        )

        first = services.notify_submission_review(submission)
        second = services.notify_submission_review(submission)

        self.assertEqual(first.id, second.id)
        self.assertEqual(Notification.objects.count(), 1)

    def test_review_link_targets_my_submissions(self):
        submission = SubmittedContribution.objects.create(
            user=self.user,
            contribution_type=self.contribution_type,
            contribution_date=timezone.now(),
            notes='Test submission',
            state='more_info_needed',
            reviewed_at=timezone.now(),
        )

        notification = services.notify_submission_review(submission)
        self.assertIn('/my-submissions?', notification.link_url)
        self.assertIn('state=more_info_needed', notification.link_url)
        self.assertIn(f'submission={submission.id}', notification.link_url)


class BroadcastNotificationTests(TestCase):
    def setUp(self):
        self.member = make_user('member@test.com', '0x1111111111111111111111111111111111111111')
        self.partner = Partner.objects.create(
            name='Test Partner',
            slug='test-partner-notif',
            description='A partner',
            is_active=True,
        )

    def test_broadcast_creates_single_row(self):
        make_user('other@test.com', '0x2222222222222222222222222222222222222222')

        services.broadcast_partner(self.partner)

        self.assertEqual(Notification.objects.count(), 1)
        notification = Notification.objects.get()
        self.assertIsNone(notification.recipient)
        self.assertEqual(notification.audience, Notification.AUDIENCE_ALL)
        self.assertTrue(notification.is_broadcast)

    def test_rebroadcast_refreshes_instead_of_duplicating(self):
        first = services.broadcast_partner(self.partner)
        NotificationReceipt.objects.create(
            notification=first, user=self.member, read_at=timezone.now()
        )
        old_created_at = first.created_at

        second = services.broadcast_partner(self.partner, message='Updated copy')

        self.assertEqual(first.id, second.id)
        self.assertEqual(Notification.objects.count(), 1)
        self.assertEqual(second.body, 'Updated copy')
        # Resurfaces as new and unread for everyone.
        self.assertGreaterEqual(second.created_at, old_created_at)
        self.assertEqual(NotificationReceipt.objects.count(), 0)

    def test_recall_broadcast_removes_row_and_receipts(self):
        notification = services.broadcast_partner(self.partner)
        NotificationReceipt.objects.create(
            notification=notification, user=self.member, read_at=timezone.now()
        )

        deleted = services.recall_broadcast('partner.published', self.partner)

        self.assertEqual(deleted, 1)
        self.assertEqual(Notification.objects.count(), 0)
        self.assertEqual(NotificationReceipt.objects.count(), 0)

    def test_broadcast_hidden_from_users_joined_after(self):
        # Member joined well before the broadcast; newcomer joins after it.
        User.objects.filter(pk=self.member.pk).update(
            date_joined=timezone.now() - timedelta(days=10)
        )
        self.member.refresh_from_db()

        notification = services.broadcast_partner(self.partner)
        Notification.objects.filter(pk=notification.pk).update(
            created_at=timezone.now() - timedelta(days=2)
        )

        newcomer = make_user('new@test.com', '0x3333333333333333333333333333333333333333')

        self.assertIn(notification.pk, [n.pk for n in services.feed_for(self.member)])
        self.assertNotIn(notification.pk, [n.pk for n in services.feed_for(newcomer)])

    def test_validator_audience_scoping(self):
        validator_user = make_user('validator@test.com', '0x4444444444444444444444444444444444444444')
        Validator.objects.create(user=validator_user)

        notification = services.broadcast(
            'node_version.published',
            title='Node upgrade available: 1.2.3',
            source=self.partner,  # any source object works for dedupe
        )

        self.assertEqual(notification.audience, Notification.AUDIENCE_VALIDATORS)
        self.assertIn(notification.pk, [n.pk for n in services.feed_for(validator_user)])
        self.assertNotIn(notification.pk, [n.pk for n in services.feed_for(self.member)])


class ReadStateTests(TestCase):
    def setUp(self):
        self.user = make_user('reader@test.com', '0x5555555555555555555555555555555555555555')
        self.partner = Partner.objects.create(
            name='Read Partner',
            slug='read-partner-notif',
            description='A partner',
            is_active=True,
        )

    def unread_count(self, user):
        return (
            services.annotate_read_state(services.feed_for(user), user)
            .filter(services.UNREAD_Q)
            .count()
        )

    def test_broadcast_read_uses_receipts(self):
        notification = services.broadcast_partner(self.partner)
        self.assertEqual(self.unread_count(self.user), 1)

        services.mark_notification_read(notification, self.user)

        self.assertEqual(self.unread_count(self.user), 0)
        self.assertEqual(
            NotificationReceipt.objects.filter(
                notification=notification, user=self.user, read_at__isnull=False
            ).count(),
            1,
        )
        # Idempotent.
        services.mark_notification_read(notification, self.user)
        self.assertEqual(NotificationReceipt.objects.count(), 1)

    def test_mark_all_read_covers_personal_and_broadcast(self):
        services.broadcast_partner(self.partner)
        services.notify(
            'referral.joined',
            recipient=self.user,
            title='Your referral joined the portal',
        )
        self.assertEqual(self.unread_count(self.user), 2)

        updated = services.mark_all_read(self.user)

        self.assertEqual(updated, 2)
        self.assertEqual(self.unread_count(self.user), 0)


class NotificationAPITests(TestCase):
    def setUp(self):
        self.user = make_user('api@test.com', '0x6666666666666666666666666666666666666666')
        # Joined before the broadcasts these tests backdate.
        User.objects.filter(pk=self.user.pk).update(
            date_joined=timezone.now() - timedelta(days=1)
        )
        self.user.refresh_from_db()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.partner = Partner.objects.create(
            name='API Partner',
            slug='api-partner-notif',
            description='A partner',
            is_active=True,
        )

    def test_feed_lists_personal_and_broadcast_chronologically(self):
        broadcast = services.broadcast_partner(self.partner)
        Notification.objects.filter(pk=broadcast.pk).update(
            created_at=timezone.now() - timedelta(minutes=5)
        )
        services.notify(
            'referral.joined',
            recipient=self.user,
            title='Your referral joined the portal',
        )

        response = self.client.get('/api/v1/notifications/')
        self.assertEqual(response.status_code, 200)
        results = response.data['results']
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['event_type'], 'referral.joined')
        self.assertEqual(results[1]['event_type'], 'partner.published')
        self.assertFalse(results[1]['is_read'])

    def test_mark_read_and_unread_count(self):
        broadcast = services.broadcast_partner(self.partner)

        response = self.client.get('/api/v1/notifications/unread-count/')
        self.assertEqual(response.data['count'], 1)

        response = self.client.post(f'/api/v1/notifications/{broadcast.pk}/mark-read/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['is_read'])

        response = self.client.get('/api/v1/notifications/unread-count/')
        self.assertEqual(response.data['count'], 0)

    def test_unread_filter(self):
        services.broadcast_partner(self.partner)
        personal = services.notify(
            'referral.joined',
            recipient=self.user,
            title='Your referral joined the portal',
        )
        personal.mark_read()

        response = self.client.get('/api/v1/notifications/', {'unread': 'true'})
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['event_type'], 'partner.published')

    def test_requires_authentication(self):
        client = APIClient()
        response = client.get('/api/v1/notifications/')
        self.assertIn(response.status_code, (401, 403))

    def test_category_filter(self):
        services.broadcast_partner(self.partner)  # category: content
        services.notify(
            'referral.joined',  # category: community
            recipient=self.user,
            title='Your referral joined the portal',
        )

        response = self.client.get('/api/v1/notifications/', {'category': 'community'})
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['category'], 'community')

    def test_pagination(self):
        for i in range(5):
            services.notify(
                'referral.joined',
                recipient=self.user,
                title=f'Referral {i} joined',
            )

        response = self.client.get('/api/v1/notifications/', {'page_size': 2})
        self.assertEqual(response.data['count'], 5)
        self.assertEqual(len(response.data['results']), 2)
        self.assertIsNotNone(response.data['next'])
        self.assertIsNone(response.data['previous'])

        response = self.client.get('/api/v1/notifications/', {'page_size': 2, 'page': 3})
        self.assertEqual(len(response.data['results']), 1)
        self.assertIsNone(response.data['next'])

    def test_user_cannot_see_other_users_personal_notifications(self):
        other_user = make_user('other-iso@test.com', '0x7777777777777777777777777777777777777777')
        foreign = services.notify(
            'referral.joined',
            recipient=other_user,
            title='Other user referral joined',
        )

        response = self.client.get('/api/v1/notifications/')
        self.assertNotIn(foreign.pk, [item['id'] for item in response.data['results']])

    def test_user_cannot_mark_other_users_notification_read(self):
        other_user = make_user('other-iso@test.com', '0x7777777777777777777777777777777777777777')
        foreign = services.notify(
            'referral.joined',
            recipient=other_user,
            title='Other user referral joined',
        )

        response = self.client.post(f'/api/v1/notifications/{foreign.pk}/mark-read/')
        self.assertEqual(response.status_code, 404)
        foreign.refresh_from_db()
        self.assertIsNone(foreign.read_at)


class StewardReviewEndpointNotificationTests(TestCase):
    """The main steward review endpoint must notify the submitter."""

    def setUp(self):
        from stewards.models import Steward, StewardPermission

        self.category = Category.objects.create(name='Review', slug='review-notif', description='x')
        self.contribution_type = ContributionType.objects.create(
            name='Review Type',
            slug='review-type-notif',
            description='x',
            category=self.category,
            min_points=1,
            max_points=10,
        )
        self.submitter = make_user('submitter@test.com', '0x8888888888888888888888888888888888888888')
        self.steward_user = make_user('steward@test.com', '0x9999999999999999999999999999999999999999')
        steward = Steward.objects.create(user=self.steward_user)
        StewardPermission.objects.create(
            steward=steward,
            contribution_type=self.contribution_type,
            action='reject',
        )
        self.submission = SubmittedContribution.objects.create(
            user=self.submitter,
            contribution_type=self.contribution_type,
            contribution_date=timezone.now(),
            notes='Review me',
            state='pending',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.steward_user)

    def test_review_action_notifies_submitter(self):
        response = self.client.post(
            f'/api/v1/steward-submissions/{self.submission.id}/review/',
            {'action': 'reject', 'staff_reply': 'Missing evidence'},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)

        notification = Notification.objects.get(recipient=self.submitter)
        self.assertEqual(notification.event_type, 'submission.rejected')
        self.assertEqual(notification.actor, self.steward_user)
        self.assertIn(str(self.submission.id), notification.link_url)


class SubmissionReturnNotificationTests(TestCase):
    """Submitter appeals/resubmits should notify the assigned steward."""

    def setUp(self):
        from stewards.models import Steward

        self.category = Category.objects.create(name='Return', slug='return-notif', description='x')
        self.contribution_type = ContributionType.objects.create(
            name='Return Type',
            slug='return-type-notif',
            description='x',
            category=self.category,
            min_points=1,
            max_points=10,
        )
        self.submitter = make_user('return-submit@test.com', '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa')
        self.steward_user = make_user('return-steward@test.com', '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb')
        Steward.objects.create(user=self.steward_user)
        self.client = APIClient()

    def test_appeal_notifies_assigned_steward(self):
        submission = SubmittedContribution.objects.create(
            user=self.submitter,
            contribution_type=self.contribution_type,
            contribution_date=timezone.now(),
            notes='Review me again',
            state='rejected',
            staff_reply='Rejected first time',
            reviewed_at=timezone.now(),
            assigned_to=self.steward_user,
            gate_reviewed=True,
        )
        self.client.force_authenticate(user=self.submitter)

        response = self.client.post(
            f'/api/v1/submissions/{submission.id}/appeal/',
            {'reason': 'I added context in the original evidence.'},
            format='json',
        )

        self.assertEqual(response.status_code, 200, response.data)
        submission.refresh_from_db()
        self.assertFalse(submission.gate_reviewed)
        notification = Notification.objects.get(recipient=self.steward_user)
        self.assertEqual(notification.event_type, 'submission.appealed')
        self.assertEqual(notification.actor, self.submitter)
        self.assertEqual(notification.payload['submission_id'], str(submission.id))
        self.assertIn('/stewards/submissions?', notification.link_url)
        self.assertIn(str(submission.id), notification.link_url)

    def test_more_info_resubmission_notifies_assigned_steward(self):
        reviewed_at = timezone.now() - timedelta(hours=1)
        submission = SubmittedContribution.objects.create(
            user=self.submitter,
            contribution_type=self.contribution_type,
            contribution_date=timezone.now(),
            notes='Needs edits',
            state='more_info_needed',
            staff_reply='Please add evidence.',
            reviewed_by=self.steward_user,
            reviewed_at=reviewed_at,
            assigned_to=self.steward_user,
            gate_reviewed=True,
        )
        self.client.force_authenticate(user=self.submitter)

        response = self.client.patch(
            f'/api/v1/submissions/{submission.id}/',
            {'notes': 'Added the requested evidence.'},
            format='json',
        )

        self.assertEqual(response.status_code, 200, response.data)
        submission.refresh_from_db()
        self.assertEqual(submission.state, 'pending')
        self.assertFalse(submission.gate_reviewed)
        self.assertIsNone(submission.reviewed_by)
        self.assertIsNone(submission.reviewed_at)
        self.assertGreater(submission.last_edited_at, reviewed_at)
        notification = Notification.objects.get(recipient=self.steward_user)
        self.assertEqual(notification.event_type, 'submission.more_info_resubmitted')
        self.assertEqual(notification.actor, self.submitter)
        self.assertEqual(notification.payload['submission_id'], str(submission.id))
        self.assertIn(str(submission.id), notification.link_url)


class BroadcastAdminMixinTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            email='admin@test.com',
            password='adminpass123',
        )
        self.partner = Partner.objects.create(
            name='Admin Partner',
            slug='admin-partner-notif',
            description='A partner',
            is_active=True,
        )

    def test_admin_change_form_renders_with_broadcast_fields(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(f'/admin/partners/partner/{self.partner.pk}/change/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'broadcast_notification')
        self.assertContains(response, 'recall_broadcast_notification')
        self.assertContains(response, 'Broadcast notification now')

    def test_admin_save_without_checkbox_stays_silent(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(
            f'/admin/partners/partner/{self.partner.pk}/change/',
            {
                'name': self.partner.name,
                'slug': self.partner.slug,
                'description': self.partner.description,
                'is_active': 'on',
                'logo_url': '',
                'website_url': 'https://example.com',
                'url': '',
                'display_order': 0,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Notification.objects.count(), 0)

    def test_admin_save_with_checkbox_broadcasts(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(
            f'/admin/partners/partner/{self.partner.pk}/change/',
            {
                'name': self.partner.name,
                'slug': self.partner.slug,
                'description': self.partner.description,
                'is_active': 'on',
                'logo_url': '',
                'website_url': 'https://example.com',
                'url': '',
                'display_order': 0,
                'broadcast_notification': 'on',
                'notification_message': 'Say hello to our new partner',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Notification.objects.count(), 1)
        notification = Notification.objects.get()
        self.assertIsNone(notification.recipient)
        self.assertEqual(notification.event_type, 'partner.published')
        self.assertEqual(notification.body, 'Say hello to our new partner')
        self.assertEqual(notification.actor, self.admin_user)

    def test_admin_recall_checkbox_removes_broadcast(self):
        services.broadcast_partner(self.partner)
        self.assertEqual(Notification.objects.count(), 1)

        self.client.force_login(self.admin_user)
        response = self.client.post(
            f'/admin/partners/partner/{self.partner.pk}/change/',
            {
                'name': self.partner.name,
                'slug': self.partner.slug,
                'description': self.partner.description,
                'is_active': 'on',
                'logo_url': '',
                'website_url': 'https://example.com',
                'url': '',
                'display_order': 0,
                'recall_broadcast_notification': 'on',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Notification.objects.count(), 0)

    def test_admin_bulk_recall_removes_broadcast(self):
        services.broadcast_partner(self.partner)
        self.client.force_login(self.admin_user)

        response = self.client.post(
            '/admin/partners/partner/',
            {
                'action': 'recall_selected_notifications',
                '_selected_action': [str(self.partner.pk)],
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Notification.objects.count(), 0)


class CampaignRecipientResolutionTests(TestCase):
    def setUp(self):
        self.alice = make_user('alice@test.com', '0x1010101010101010101010101010101010101010')
        self.bob = make_user('bob@test.com', '0x2020202020202020202020202020202020202020')
        self.carol = make_user('carol@test.com', '0x3030303030303030303030303030303030303030')

    def make_campaign(self, **kwargs):
        defaults = {'title': 'Hello', 'target_mode': CustomNotification.TARGET_EVERYONE}
        defaults.update(kwargs)
        target_users = defaults.pop('target_users', None)
        campaign = CustomNotification.objects.create(**defaults)
        if target_users:
            campaign.target_users.set(target_users)
        return campaign

    def test_everyone_excludes_inactive_users(self):
        User.objects.filter(pk=self.carol.pk).update(is_active=False)
        campaign = self.make_campaign()

        audience = campaigns.resolve_recipients(campaign)

        self.assertIn(self.alice, audience.users)
        self.assertNotIn(self.carol, audience.users)

    def test_roles_union_dedupes_dual_role_users(self):
        from stewards.models import Steward
        Validator.objects.create(user=self.alice)
        Steward.objects.create(user=self.alice)
        Steward.objects.create(user=self.bob)
        campaign = self.make_campaign(
            target_mode=CustomNotification.TARGET_ROLES,
            target_roles=['validators', 'stewards'],
        )

        audience = campaigns.resolve_recipients(campaign)

        recipients = list(audience.users)
        self.assertEqual(recipients.count(self.alice), 1)
        self.assertIn(self.bob, recipients)
        self.assertNotIn(self.carol, recipients)

    def test_users_mode_excludes_inactive_picks(self):
        User.objects.filter(pk=self.bob.pk).update(is_active=False)
        campaign = self.make_campaign(
            target_mode=CustomNotification.TARGET_USERS,
            target_users=[self.alice, self.bob],
        )

        audience = campaigns.resolve_recipients(campaign)

        self.assertIn(self.alice, audience.users)
        self.assertNotIn(self.bob, audience.users)

    def test_wallets_match_case_insensitively_and_report_unmatched(self):
        User.objects.filter(pk=self.alice.pk).update(
            address='0xAbCd010101010101010101010101010101010101'
        )
        campaign = self.make_campaign(
            target_mode=CustomNotification.TARGET_WALLETS,
            target_wallets=(
                '0xabcd010101010101010101010101010101010101\n'
                '0x9999999999999999999999999999999999999999\n'
                'not-an-address\n'
            ),
        )

        audience = campaigns.resolve_recipients(campaign)

        self.assertEqual(list(audience.users), [User.objects.get(pk=self.alice.pk)])
        self.assertIn('not-an-address', audience.unmatched_wallets)
        self.assertIn('0x9999999999999999999999999999999999999999', audience.unmatched_wallets)

    def test_parse_wallet_lines_handles_commas_and_duplicates(self):
        addresses, invalid = campaigns.parse_wallet_lines(
            '0x1010101010101010101010101010101010101010, '
            '0X1010101010101010101010101010101010101010\n\n'
            'garbage'
        )

        self.assertEqual(len(addresses), 1)
        self.assertEqual(invalid, ['garbage'])


class CampaignSendTests(TestCase):
    def setUp(self):
        self.admin = make_user('sender@test.com', '0x4040404040404040404040404040404040404040')
        self.alice = make_user('alice-send@test.com', '0x5050505050505050505050505050505050505050')
        self.bob = make_user('bob-send@test.com', '0x6060606060606060606060606060606060606060')

    def make_users_campaign(self, users, **kwargs):
        defaults = {
            'title': 'Campaign title',
            'body': 'Campaign body',
            'target_mode': CustomNotification.TARGET_USERS,
            'priority': Notification.PRIORITY_HIGH,
        }
        defaults.update(kwargs)
        campaign = CustomNotification.objects.create(**defaults)
        campaign.target_users.set(users)
        return campaign

    def test_send_fans_out_personal_rows_only(self):
        campaign = self.make_users_campaign([self.alice, self.bob], link_url='/missions')

        result = campaigns.send_campaign(campaign, actor=self.admin)

        self.assertEqual(result.total, 2)
        self.assertEqual(result.created, 2)
        rows = Notification.objects.filter(event_type='custom.announcement')
        self.assertEqual(rows.count(), 2)
        # Privacy guard: campaigns must never create broadcast rows.
        self.assertFalse(rows.filter(recipient__isnull=True).exists())
        row = rows.get(recipient=self.alice)
        self.assertEqual(row.dedupe_key, f'custom.announcement:{campaign.pk}')
        self.assertEqual(row.priority, Notification.PRIORITY_HIGH)
        self.assertEqual(row.category, 'announcement')
        self.assertEqual(row.link_url, '/missions')
        self.assertEqual(row.payload, {'campaign_id': campaign.pk})

        campaign.refresh_from_db()
        self.assertEqual(campaign.status, CustomNotification.STATUS_SENT)
        self.assertEqual(campaign.sent_by, self.admin)
        self.assertEqual(campaign.sent_count, 2)

    def test_zero_recipients_raises_and_stays_draft(self):
        campaign = CustomNotification.objects.create(
            title='Nobody',
            target_mode=CustomNotification.TARGET_WALLETS,
            target_wallets='0x7777777777777777777777777777777777777777',
        )

        with self.assertRaises(campaigns.CampaignSendError):
            campaigns.send_campaign(campaign, actor=self.admin)

        campaign.refresh_from_db()
        self.assertEqual(campaign.status, CustomNotification.STATUS_DRAFT)
        self.assertEqual(Notification.objects.count(), 0)

    def test_double_send_never_duplicates(self):
        campaign = self.make_users_campaign([self.alice])

        campaigns.send_campaign(campaign, actor=self.admin)
        result = campaigns.send_campaign(campaign, actor=self.admin)

        self.assertEqual(Notification.objects.filter(recipient=self.alice).count(), 1)
        self.assertEqual(result.refreshed, 1)
        self.assertEqual(result.created, 0)

    def test_resend_resurfaces_unread_for_current_audience_only(self):
        campaign = self.make_users_campaign([self.alice, self.bob])
        campaigns.send_campaign(campaign, actor=self.admin)

        alice_row = Notification.objects.get(recipient=self.alice)
        bob_row = Notification.objects.get(recipient=self.bob)
        alice_row.mark_read()
        bob_row.mark_read()
        old_bob_created_at = bob_row.created_at

        # Narrow targeting to alice only, then resend with fresh copy.
        campaign.target_users.set([self.alice])
        campaign.title = 'Updated title'
        campaign.save()
        campaigns.send_campaign(campaign, actor=self.admin)

        alice_row.refresh_from_db()
        self.assertIsNone(alice_row.read_at)
        self.assertEqual(alice_row.title, 'Updated title')

        bob_row.refresh_from_db()
        self.assertIsNotNone(bob_row.read_at)
        self.assertEqual(bob_row.created_at, old_bob_created_at)
        self.assertEqual(Notification.objects.count(), 2)

    def test_resend_reaches_newly_matching_users(self):
        campaign = self.make_users_campaign([self.alice])
        campaigns.send_campaign(campaign, actor=self.admin)

        campaign.target_users.add(self.bob)
        result = campaigns.send_campaign(campaign, actor=self.admin)

        self.assertEqual(result.total, 2)
        self.assertTrue(Notification.objects.filter(recipient=self.bob).exists())


class CampaignFeedVisibilityTests(TestCase):
    def setUp(self):
        self.recipient = make_user('target@test.com', '0x8080808080808080808080808080808080808080')
        self.outsider = make_user('outsider@test.com', '0x9090909090909090909090909090909090909090')
        campaign = CustomNotification.objects.create(
            title='Private announcement',
            body='Only for you.',
            target_mode=CustomNotification.TARGET_USERS,
        )
        campaign.target_users.set([self.recipient])
        campaigns.send_campaign(campaign, actor=None)

    def feed_client(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    def test_only_recipient_sees_the_campaign(self):
        response = self.feed_client(self.recipient).get('/api/v1/notifications/')
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], 'Private announcement')

        response = self.feed_client(self.outsider).get('/api/v1/notifications/')
        self.assertEqual(response.data['count'], 0)

    def test_unread_count_and_mark_all_read(self):
        client = self.feed_client(self.recipient)
        self.assertEqual(client.get('/api/v1/notifications/unread-count/').data['count'], 1)

        client.post('/api/v1/notifications/mark-all-read/')
        self.assertEqual(client.get('/api/v1/notifications/unread-count/').data['count'], 0)


class CustomNotificationAdminTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            email='campaign-admin@test.com',
            password='adminpass123',
        )
        self.alice = make_user('alice-admin@test.com', '0xa0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0')
        self.client.force_login(self.admin_user)

    def post_change_form(self, campaign=None, **overrides):
        data = {
            'title': 'Admin campaign',
            'body': 'Body text',
            'link_url': '',
            'link_label': '',
            'priority': Notification.PRIORITY_NORMAL,
            'target_mode': CustomNotification.TARGET_USERS,
            'target_users': [str(self.alice.pk)],
            'target_wallets': '',
        }
        data.update(overrides)
        if campaign is None:
            return self.client.post('/admin/notifications/customnotification/add/', data)
        return self.client.post(
            f'/admin/notifications/customnotification/{campaign.pk}/change/', data
        )

    def test_change_form_renders(self):
        response = self.client.get('/admin/notifications/customnotification/add/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'target_mode')
        self.assertContains(response, 'Send now')

    def test_save_without_send_now_stays_draft(self):
        response = self.post_change_form()
        self.assertEqual(response.status_code, 302)
        campaign = CustomNotification.objects.get()
        self.assertEqual(campaign.status, CustomNotification.STATUS_DRAFT)
        self.assertEqual(Notification.objects.count(), 0)

    def test_save_with_send_now_fans_out_via_save_related(self):
        # Hand-picked users are an M2M saved after save_model; this proves
        # the send runs in save_related with the committed M2M state.
        response = self.post_change_form(send_now='on')
        self.assertEqual(response.status_code, 302)
        campaign = CustomNotification.objects.get()
        self.assertEqual(campaign.status, CustomNotification.STATUS_SENT)
        row = Notification.objects.get(recipient=self.alice)
        self.assertEqual(row.event_type, 'custom.announcement')
        self.assertEqual(row.actor, self.admin_user)

    def test_wallets_mode_send_stores_unmatched(self):
        response = self.post_change_form(
            send_now='on',
            target_mode=CustomNotification.TARGET_WALLETS,
            target_users=[],
            target_wallets=(
                f'{self.alice.address}\n0xdead00000000000000000000000000000000beef'
            ),
        )
        self.assertEqual(response.status_code, 302)
        campaign = CustomNotification.objects.get()
        self.assertEqual(campaign.status, CustomNotification.STATUS_SENT)
        self.assertEqual(campaign.sent_count, 1)
        self.assertEqual(
            campaign.unmatched_wallets,
            ['0xdead00000000000000000000000000000000beef'],
        )

    def test_bulk_actions_respect_status(self):
        draft = CustomNotification.objects.create(
            title='Draft one', target_mode=CustomNotification.TARGET_USERS
        )
        draft.target_users.set([self.alice])

        response = self.client.post(
            '/admin/notifications/customnotification/',
            {'action': 'resend_selected', '_selected_action': [str(draft.pk)]},
        )
        self.assertEqual(response.status_code, 302)
        draft.refresh_from_db()
        self.assertEqual(draft.status, CustomNotification.STATUS_DRAFT)

        response = self.client.post(
            '/admin/notifications/customnotification/',
            {'action': 'send_selected', '_selected_action': [str(draft.pk)]},
        )
        self.assertEqual(response.status_code, 302)
        draft.refresh_from_db()
        self.assertEqual(draft.status, CustomNotification.STATUS_SENT)

    def test_recall_checkbox_deletes_delivered_campaign_rows(self):
        campaign = CustomNotification.objects.create(
            title='Recall me',
            body='Wrong copy',
            target_mode=CustomNotification.TARGET_USERS,
            status=CustomNotification.STATUS_SENT,
        )
        campaign.target_users.set([self.alice])
        campaigns.send_campaign(campaign, actor=self.admin_user)
        self.assertEqual(Notification.objects.filter(event_type='custom.announcement').count(), 1)

        response = self.post_change_form(campaign=campaign, recall_now='on')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Notification.objects.filter(event_type='custom.announcement').count(), 0)
        campaign.refresh_from_db()
        self.assertEqual(campaign.status, CustomNotification.STATUS_SENT)

    def test_bulk_recall_deletes_delivered_campaign_rows(self):
        campaign = CustomNotification.objects.create(
            title='Recall selected',
            target_mode=CustomNotification.TARGET_USERS,
        )
        campaign.target_users.set([self.alice])
        campaigns.send_campaign(campaign, actor=self.admin_user)

        response = self.client.post(
            '/admin/notifications/customnotification/',
            {'action': 'recall_selected', '_selected_action': [str(campaign.pk)]},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Notification.objects.filter(event_type='custom.announcement').count(), 0)


class SocialTaskBroadcastTests(TestCase):
    def setUp(self):
        from contributions.models import Category
        from social_tasks.models import SocialTask

        self.builder_user = make_user('builder-task@test.com', '0xb1b1b1b1b1b1b1b1b1b1b1b1b1b1b1b1b1b1b1b1')
        self.community_user = make_user('creator-task@test.com', '0xc1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1')
        self.plain_user = make_user('plain-task@test.com', '0xd1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1')

        from builders.models import Builder
        from creators.models import Creator
        Builder.objects.create(user=self.builder_user)
        Creator.objects.create(user=self.community_user)

        self.builder_category, _ = Category.objects.get_or_create(
            slug='builder', defaults={'name': 'Builder', 'description': 'x'}
        )
        self.community_category, _ = Category.objects.get_or_create(
            slug='community', defaults={'name': 'Community', 'description': 'x'}
        )
        self.task = SocialTask.objects.create(
            name='Follow GenLayer',
            slug='follow-genlayer-notif',
            category=self.builder_category,
            points=10,
            verification_type='twitter_follow',
            target_handle='genlayer',
        )

    def test_new_audiences_resolve_by_role(self):
        self.assertIn(Notification.AUDIENCE_BUILDERS, services.audiences_for(self.builder_user))
        self.assertIn(Notification.AUDIENCE_COMMUNITY, services.audiences_for(self.community_user))
        self.assertNotIn(Notification.AUDIENCE_BUILDERS, services.audiences_for(self.plain_user))
        self.assertNotIn(Notification.AUDIENCE_COMMUNITY, services.audiences_for(self.plain_user))

    def test_builder_task_broadcast_targets_builders_only(self):
        notification = services.broadcast_social_task(self.task)

        self.assertEqual(notification.audience, Notification.AUDIENCE_BUILDERS)
        self.assertEqual(notification.event_type, 'social_task.published')
        self.assertEqual(notification.link_url, '/builders/tasks')
        self.assertEqual(notification.payload['points'], 10)

        self.assertIn(notification.pk, [n.pk for n in services.feed_for(self.builder_user)])
        self.assertNotIn(notification.pk, [n.pk for n in services.feed_for(self.plain_user)])
        self.assertNotIn(notification.pk, [n.pk for n in services.feed_for(self.community_user)])

    def test_community_task_broadcast_targets_community(self):
        self.task.category = self.community_category
        self.task.save()

        notification = services.broadcast_social_task(self.task, message='Join us!')

        self.assertEqual(notification.audience, Notification.AUDIENCE_COMMUNITY)
        self.assertEqual(notification.body, 'Join us!')
        self.assertEqual(notification.link_url, '/community/tasks')
        self.assertIn(notification.pk, [n.pk for n in services.feed_for(self.community_user)])
        self.assertNotIn(notification.pk, [n.pk for n in services.feed_for(self.builder_user)])

    def test_rebroadcast_same_task_updates_single_row(self):
        first = services.broadcast_social_task(self.task)
        second = services.broadcast_social_task(self.task, message='Reminder')

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(
            Notification.objects.filter(event_type='social_task.published').count(), 1
        )

    def test_admin_save_with_checkbox_broadcasts(self):
        admin_user = User.objects.create_superuser(
            email='task-admin@test.com', password='adminpass123'
        )
        self.client.force_login(admin_user)
        response = self.client.post(
            f'/admin/social_tasks/socialtask/{self.task.pk}/change/',
            {
                'name': self.task.name,
                'slug': self.task.slug,
                'description': '',
                'category': str(self.builder_category.pk),
                'points': 10,
                'order': 0,
                'action_url': self.task.action_url,
                'cta_text': 'Complete',
                'verification_type': 'twitter_follow',
                'target_handle': 'genlayer',
                'target_guild_id': '',
                'target_repo': '',
                'is_active': 'on',
                'starts_at_0': '', 'starts_at_1': '',
                'ends_at_0': '', 'ends_at_1': '',
                'broadcast_notification': 'on',
            },
        )
        self.assertEqual(response.status_code, 302)
        notification = Notification.objects.get(event_type='social_task.published')
        self.assertEqual(notification.audience, Notification.AUDIENCE_BUILDERS)
        self.assertEqual(notification.actor, admin_user)

    def test_admin_recall_checkbox_removes_social_task_broadcast(self):
        services.broadcast_social_task(self.task)
        self.assertEqual(Notification.objects.filter(event_type='social_task.published').count(), 1)

        admin_user = User.objects.create_superuser(
            email='task-recall-admin@test.com', password='adminpass123'
        )
        self.client.force_login(admin_user)
        response = self.client.post(
            f'/admin/social_tasks/socialtask/{self.task.pk}/change/',
            {
                'name': self.task.name,
                'slug': self.task.slug,
                'description': '',
                'category': str(self.builder_category.pk),
                'points': 10,
                'order': 0,
                'action_url': self.task.action_url,
                'cta_text': 'Complete',
                'verification_type': 'twitter_follow',
                'target_handle': 'genlayer',
                'target_guild_id': '',
                'target_repo': '',
                'is_active': 'on',
                'starts_at_0': '', 'starts_at_1': '',
                'ends_at_0': '', 'ends_at_1': '',
                'recall_broadcast_notification': 'on',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Notification.objects.filter(event_type='social_task.published').count(), 0)


class WhatsNewAnnouncementAPITests(TestCase):
    def setUp(self):
        self.user = make_user('whatsnew@test.com', '0xe1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1')
        self.validator_user = make_user('whatsnew-validator@test.com', '0xe2e2e2e2e2e2e2e2e2e2e2e2e2e2e2e2e2e2e2e2')
        Validator.objects.create(user=self.validator_user)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def make_announcement(self, **kwargs):
        defaults = {
            'title': 'New portal section',
            'body': 'A focused product update.',
            'status': WhatsNewAnnouncement.STATUS_PUBLISHED,
            'audience': Notification.AUDIENCE_ALL,
            'published_at': timezone.now() - timedelta(minutes=5),
        }
        defaults.update(kwargs)
        return WhatsNewAnnouncement.objects.create(**defaults)

    def results(self, response):
        if isinstance(response.data, dict):
            return response.data.get('results', response.data)
        return response.data

    def test_requires_authentication(self):
        client = APIClient()
        response = client.get('/api/v1/whats-new/')
        self.assertIn(response.status_code, (401, 403))

        response = client.get('/api/v1/whats-new/unseen-count/')
        self.assertIn(response.status_code, (401, 403))

    def test_published_announcement_requires_published_at(self):
        announcement = WhatsNewAnnouncement(
            title='Hidden by missing publish time',
            status=WhatsNewAnnouncement.STATUS_PUBLISHED,
        )

        with self.assertRaises(ValidationError) as context:
            announcement.full_clean()

        self.assertIn('published_at', context.exception.message_dict)

    def test_lists_only_active_unseen_announcements(self):
        visible = self.make_announcement(title='Visible')
        self.make_announcement(title='Draft', status=WhatsNewAnnouncement.STATUS_DRAFT)
        self.make_announcement(title='Archived', status=WhatsNewAnnouncement.STATUS_ARCHIVED)
        self.make_announcement(title='Expired', expires_at=timezone.now() - timedelta(minutes=1))
        self.make_announcement(title='Future', published_at=timezone.now() + timedelta(minutes=5))
        seen = self.make_announcement(title='Already seen')
        WhatsNewAnnouncementSeen.objects.create(
            announcement=seen,
            user=self.user,
            version=seen.version,
        )

        response = self.client.get('/api/v1/whats-new/')

        self.assertEqual(response.status_code, 200)
        results = self.results(response)
        self.assertEqual([item['id'] for item in results], [visible.id])
        self.assertEqual(results[0]['title'], 'Visible')

    def test_role_audience_filtering(self):
        validator_announcement = self.make_announcement(
            title='Validator only',
            audience=Notification.AUDIENCE_VALIDATORS,
        )

        response = self.client.get('/api/v1/whats-new/')
        self.assertEqual(self.results(response), [])

        validator_client = APIClient()
        validator_client.force_authenticate(user=self.validator_user)
        response = validator_client.get('/api/v1/whats-new/')

        self.assertEqual([item['id'] for item in self.results(response)], [validator_announcement.id])

    def test_new_users_can_see_currently_published_announcements(self):
        announcement = self.make_announcement()
        User.objects.filter(pk=self.user.pk).update(date_joined=timezone.now())
        self.user.refresh_from_db()

        response = self.client.get('/api/v1/whats-new/')

        self.assertEqual([item['id'] for item in self.results(response)], [announcement.id])

    def test_mark_seen_excludes_current_version_from_list_and_count(self):
        announcement = self.make_announcement()

        response = self.client.get('/api/v1/whats-new/unseen-count/')
        self.assertEqual(response.data['count'], 1)

        response = self.client.post(
            '/api/v1/whats-new/mark-seen/',
            {'ids': [announcement.id], 'action': WhatsNewAnnouncementSeen.ACTION_SKIPPED},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(
            WhatsNewAnnouncementSeen.objects.get(
                announcement=announcement,
                user=self.user,
            ).action,
            WhatsNewAnnouncementSeen.ACTION_SKIPPED,
        )
        self.assertEqual(self.results(self.client.get('/api/v1/whats-new/')), [])

    def test_preview_includes_published_announcements_already_seen(self):
        announcement = self.make_announcement(title='Seen preview')
        expired = self.make_announcement(
            title='Expired seen preview',
            published_at=timezone.now() - timedelta(days=2),
            expires_at=timezone.now() - timedelta(days=1),
        )
        WhatsNewAnnouncementSeen.objects.create(
            announcement=announcement,
            user=self.user,
            version=announcement.version,
        )
        WhatsNewAnnouncementSeen.objects.create(
            announcement=expired,
            user=self.user,
            version=expired.version,
        )

        response = self.client.get('/api/v1/whats-new/')
        self.assertEqual(self.results(response), [])

        response = self.client.get('/api/v1/whats-new/', {'preview': 'true'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['id'] for item in self.results(response)], [announcement.id, expired.id])

    def test_preview_excludes_unseen_announcements(self):
        seen = self.make_announcement(title='Seen preview')
        self.make_announcement(title='Unseen preview')
        WhatsNewAnnouncementSeen.objects.create(
            announcement=seen,
            user=self.user,
            version=seen.version,
        )

        response = self.client.get('/api/v1/whats-new/', {'preview': 'true'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['id'] for item in self.results(response)], [seen.id])

    def test_version_bump_resurfaces_seen_announcement(self):
        announcement = self.make_announcement()
        WhatsNewAnnouncementSeen.objects.create(
            announcement=announcement,
            user=self.user,
            version=1,
        )
        self.assertEqual(self.results(self.client.get('/api/v1/whats-new/')), [])

        announcement.version = 2
        announcement.save(update_fields=['version', 'updated_at'])

        response = self.client.get('/api/v1/whats-new/')
        self.assertEqual([item['id'] for item in self.results(response)], [announcement.id])
        self.assertEqual(self.results(response)[0]['version'], 2)

    def test_regular_notifications_never_become_whats_new_items(self):
        services.notify(
            'referral.joined',
            recipient=self.user,
            title='Regular notification',
        )

        response = self.client.get('/api/v1/whats-new/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.results(response), [])


class EmailVerificationReminderTests(TestCase):
    def setUp(self):
        self.unverified = make_user('unverified@test.com', '0x1111111111111111111111111111111111111111')
        self.verified = make_user('verified@test.com', '0x2222222222222222222222222222222222222222')
        self.verified.is_email_verified = True
        self.verified.save(update_fields=['is_email_verified'])

    def run_command(self, *args):
        from django.core.management import call_command
        call_command('send_email_verification_reminders', *args)

    def test_command_notifies_only_unverified_users(self):
        self.run_command()

        self.assertEqual(Notification.objects.filter(recipient=self.verified).count(), 0)
        notification = Notification.objects.get(recipient=self.unverified)
        self.assertEqual(notification.event_type, 'email.verify_reminder')
        self.assertEqual(notification.link_url, '/verify-email')

    def test_command_is_idempotent_and_keeps_read_state(self):
        self.run_command()
        Notification.objects.get(recipient=self.unverified).mark_read()

        self.run_command()

        notification = Notification.objects.get(recipient=self.unverified)
        self.assertIsNotNone(notification.read_at)

    def test_dry_run_sends_nothing(self):
        self.run_command('--dry-run')
        self.assertEqual(Notification.objects.count(), 0)

    def test_clear_removes_reminder_after_verification(self):
        services.notify_email_verification_reminder(self.unverified)

        services.clear_email_verification_reminder(self.unverified)

        self.assertEqual(Notification.objects.filter(recipient=self.unverified).count(), 0)


class TelegramEnqueueTests(TestCase):
    """notify()/broadcast() enqueue Telegram outbox rows for telegram-channel events."""

    def setUp(self):
        from social_connections.models import TelegramConnection
        self.linked = make_user('linked@test.com', '0x1111111111111111111111111111111111111111')
        self.unlinked = make_user('unlinked@test.com', '0x2222222222222222222222222222222222222222')
        self.connection = TelegramConnection.objects.create(
            user=self.linked,
            platform_user_id='111',
            platform_username='linked',
            linked_at=timezone.now(),
        )

    def outbox(self):
        from social_connections.models import TelegramMessage
        return TelegramMessage.objects.filter(
            direction=TelegramMessage.DIRECTION_OUT,
            status=TelegramMessage.STATUS_PENDING,
        )

    def test_personal_telegram_event_enqueues_for_linked_recipient(self):
        notification = services.notify(
            'submission.accepted',
            recipient=self.linked,
            title='Submission accepted <script>',
            body='Nice work',
            link_url='/my-submissions',
        )
        row = self.outbox().get()
        self.assertEqual(row.connection, self.connection)
        # Card layout: emoji + bold title, italic byline, body in blockquote.
        self.assertIn('✅ <b>Submission accepted &lt;script&gt;</b>', row.text)
        self.assertIn('<i>Submission · GenLayer Portal</i>', row.text)
        self.assertIn('<blockquote>Nice work</blockquote>', row.text)
        # The link travels as an inline button, not inside the text.
        self.assertNotIn('/my-submissions', row.text)
        from notifications.telegram import notification_link_button
        button = notification_link_button(notification)
        button_spec = button['inline_keyboard'][0][0]
        self.assertTrue(button_spec['url'].startswith('http'))
        self.assertTrue(button_spec['url'].endswith('/my-submissions'))

    def test_portal_only_event_enqueues_nothing(self):
        services.notify(
            'referral.joined',
            recipient=self.linked,
            title='Referral joined',
        )
        self.assertEqual(self.outbox().count(), 0)

    def test_unlinked_muted_and_blocked_recipients_skip(self):
        services.notify('submission.accepted', recipient=self.unlinked, title='A')
        self.assertEqual(self.outbox().count(), 0)

        self.connection.notifications_enabled = False
        self.connection.save(update_fields=['notifications_enabled'])
        services.notify('submission.accepted', recipient=self.linked, title='B')
        self.assertEqual(self.outbox().count(), 0)

        self.connection.notifications_enabled = True
        self.connection.blocked_at = timezone.now()
        self.connection.save(update_fields=['notifications_enabled', 'blocked_at'])
        services.notify('submission.accepted', recipient=self.linked, title='C')
        self.assertEqual(self.outbox().count(), 0)

    def test_deduped_notify_enqueues_once(self):
        for _ in range(2):
            services.notify(
                'submission.accepted',
                recipient=self.linked,
                title='Same event',
                dedupe_key='same-key',
            )
        self.assertEqual(self.outbox().count(), 1)

    def test_broadcast_respects_audience(self):
        Validator.objects.create(user=self.linked)
        other_linked = make_user('other@test.com', '0x3333333333333333333333333333333333333333')
        from social_connections.models import TelegramConnection
        TelegramConnection.objects.create(
            user=other_linked,
            platform_user_id='222',
            platform_username='other',
            linked_at=timezone.now(),
        )

        services.broadcast(
            'node_version.published',
            title='New node version',
        )
        rows = self.outbox()
        self.assertEqual(rows.count(), 1)
        self.assertEqual(rows.get().connection, self.connection)

    def test_rebroadcast_only_reaches_newly_linked_users(self):
        from contributions.models import Category, ContributionType, Mission
        from social_connections.models import TelegramConnection, TelegramMessage
        category = Category.objects.create(name='T', slug='t', description='t')
        contribution_type = ContributionType.objects.create(
            name='Type', slug='type', description='d', category=category,
            min_points=1, max_points=10,
        )
        mission = Mission.objects.create(
            name='Mission', description='d', contribution_type=contribution_type,
        )

        services.broadcast_mission(mission)
        self.assertEqual(self.outbox().count(), 1)

        late_linker = make_user('late@test.com', '0x4444444444444444444444444444444444444444')
        TelegramConnection.objects.create(
            user=late_linker,
            platform_user_id='333',
            platform_username='late',
            linked_at=timezone.now(),
        )
        services.broadcast_mission(mission)

        all_out = TelegramMessage.objects.filter(direction=TelegramMessage.DIRECTION_OUT)
        self.assertEqual(all_out.count(), 2)
        self.assertEqual(all_out.filter(connection__user=self.linked).count(), 1)
        self.assertEqual(all_out.filter(connection__user=late_linker).count(), 1)

    def test_users_for_audience_matches_estimate(self):
        Validator.objects.create(user=self.linked)
        for audience in (
            Notification.AUDIENCE_ALL,
            Notification.AUDIENCE_VALIDATORS,
            Notification.AUDIENCE_STEWARDS,
        ):
            self.assertEqual(
                services.users_for_audience(audience).count(),
                services.estimate_broadcast_reach(audience),
            )
        self.assertIn(self.linked, services.users_for_audience(Notification.AUDIENCE_VALIDATORS))
        self.assertNotIn(self.unlinked, services.users_for_audience(Notification.AUDIENCE_VALIDATORS))


class TelegramCampaignTests(TestCase):
    def setUp(self):
        from social_connections.models import TelegramConnection
        self.linked = make_user('linked@test.com', '0x1111111111111111111111111111111111111111')
        self.unlinked = make_user('unlinked@test.com', '0x2222222222222222222222222222222222222222')
        self.connection = TelegramConnection.objects.create(
            user=self.linked,
            platform_user_id='111',
            platform_username='linked',
            linked_at=timezone.now(),
        )

    def outbox(self):
        from social_connections.models import TelegramMessage
        return TelegramMessage.objects.filter(direction=TelegramMessage.DIRECTION_OUT)

    def make_campaign(self, channels):
        return CustomNotification.objects.create(
            title='Announcement',
            body='Body',
            target_mode=CustomNotification.TARGET_EVERYONE,
            channels=channels,
        )

    def test_telegram_channel_enqueues_for_linked_recipients_only(self):
        campaign = self.make_campaign(['portal', 'telegram'])
        campaigns.send_campaign(campaign)

        rows = self.outbox()
        self.assertEqual(rows.count(), 1)
        self.assertEqual(rows.get().connection, self.connection)

    def test_portal_only_campaign_enqueues_nothing(self):
        campaign = self.make_campaign(['portal'])
        campaigns.send_campaign(campaign)
        self.assertEqual(self.outbox().count(), 0)

    def test_resend_does_not_duplicate_telegram_sends(self):
        campaign = self.make_campaign(['portal', 'telegram'])
        campaigns.send_campaign(campaign)
        campaigns.send_campaign(campaign)
        self.assertEqual(self.outbox().count(), 1)

    def test_recall_cancels_pending_and_keeps_sent(self):
        from social_connections.models import TelegramMessage
        campaign = self.make_campaign(['portal', 'telegram'])
        campaigns.send_campaign(campaign)

        # Simulate one already-delivered message plus the pending one.
        sent_row = TelegramMessage.objects.create(
            direction=TelegramMessage.DIRECTION_OUT,
            connection=self.connection,
            chat_id='111',
            text='delivered',
            status=TelegramMessage.STATUS_SENT,
            sent_at=timezone.now(),
        )

        deleted, cancelled = campaigns.recall_campaign(campaign)

        # TARGET_EVERYONE includes users seeded by data migrations, so assert
        # presence rather than an exact portal-row count.
        self.assertGreaterEqual(deleted, 1)
        self.assertEqual(cancelled, 1)
        self.assertFalse(
            TelegramMessage.objects.filter(status=TelegramMessage.STATUS_PENDING).exists()
        )
        self.assertTrue(TelegramMessage.objects.filter(pk=sent_row.pk).exists())


class TelegramDeliverEndpointTests(TestCase):
    URL = '/api/v1/notifications/telegram/deliver/'

    def setUp(self):
        from social_connections.models import TelegramConnection
        self.client = APIClient()
        self.user = make_user('linked@test.com', '0x1111111111111111111111111111111111111111')
        self.connection = TelegramConnection.objects.create(
            user=self.user,
            platform_user_id='111',
            platform_username='linked',
            linked_at=timezone.now(),
        )

    def enqueue(self):
        return services.notify(
            'submission.accepted',
            recipient=self.user,
            title='Accepted',
            link_url='/my-submissions',
            link_label='Open My Submissions',
        )

    def drain(self, send_result=(True, None, '')):
        from unittest.mock import patch
        from django.test import override_settings
        with override_settings(CRON_SYNC_TOKEN='cron-token'), \
                patch('notifications.telegram.send_telegram_message', return_value=send_result) as send_mock, \
                patch('notifications.telegram.time.sleep'):
            response = self.client.post(self.URL, HTTP_X_CRON_TOKEN='cron-token')
        return response, send_mock

    def test_requires_cron_token(self):
        from django.test import override_settings
        with override_settings(CRON_SYNC_TOKEN='cron-token'):
            self.assertEqual(self.client.post(self.URL).status_code, 403)
            self.assertEqual(
                self.client.post(self.URL, HTTP_X_CRON_TOKEN='wrong').status_code, 403
            )

    def test_drains_pending_messages(self):
        from social_connections.models import TelegramMessage
        self.enqueue()
        response, send_mock = self.drain()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['sent'], 1)
        self.assertEqual(response.data['remaining'], 0)
        send_mock.assert_called_once()
        # Sends to the connection's live chat id.
        self.assertEqual(send_mock.call_args[0][0], '111')
        # The notification link is delivered as an inline URL button.
        reply_markup = send_mock.call_args.kwargs['reply_markup']
        button_spec = reply_markup['inline_keyboard'][0][0]
        self.assertEqual(button_spec['text'], 'Open My Submissions')
        self.assertTrue(button_spec['url'].endswith('/my-submissions'))
        row = TelegramMessage.objects.get(direction=TelegramMessage.DIRECTION_OUT)
        self.assertEqual(row.status, TelegramMessage.STATUS_SENT)
        self.assertIsNotNone(row.sent_at)

    def test_transient_failure_retries_then_fails(self):
        from social_connections.models import TelegramMessage
        self.enqueue()

        for expected_attempts in (1, 2):
            response, _ = self.drain(send_result=(False, None, 'boom'))
            row = TelegramMessage.objects.get(direction=TelegramMessage.DIRECTION_OUT)
            self.assertEqual(row.status, TelegramMessage.STATUS_PENDING)
            self.assertEqual(row.attempts, expected_attempts)

        response, _ = self.drain(send_result=(False, None, 'boom'))
        row = TelegramMessage.objects.get(direction=TelegramMessage.DIRECTION_OUT)
        self.assertEqual(row.status, TelegramMessage.STATUS_FAILED)
        self.assertEqual(response.data['failed'], 1)

    def test_deleted_connection_fails_with_connection_gone(self):
        from social_connections.models import TelegramMessage
        self.enqueue()
        self.connection.delete()

        response, send_mock = self.drain()

        send_mock.assert_not_called()
        row = TelegramMessage.objects.get(direction=TelegramMessage.DIRECTION_OUT)
        self.assertEqual(row.status, TelegramMessage.STATUS_FAILED)
        self.assertEqual(row.error, 'connection_gone')

    def test_rate_limit_stops_run_and_unclaims(self):
        from social_connections.models import TelegramMessage
        self.enqueue()
        response, _ = self.drain(send_result=(False, 30, 'rate_limited'))

        self.assertEqual(response.status_code, 200)
        row = TelegramMessage.objects.get(direction=TelegramMessage.DIRECTION_OUT)
        self.assertEqual(row.status, TelegramMessage.STATUS_PENDING)
        self.assertEqual(row.attempts, 0)
        self.assertEqual(response.data['remaining'], 1)


class TelegramRecallBroadcastTests(TestCase):
    """Recalling a broadcast must cancel its queued Telegram deliveries
    BEFORE the notification row is deleted (the FK is SET_NULL)."""

    def setUp(self):
        from social_connections.models import TelegramConnection
        self.user = make_user('linked@test.com', '0x1111111111111111111111111111111111111111')
        self.connection = TelegramConnection.objects.create(
            user=self.user,
            platform_user_id='111',
            platform_username='linked',
            linked_at=timezone.now(),
        )
        category = Category.objects.create(name='T', slug='t', description='t')
        contribution_type = ContributionType.objects.create(
            name='Type', slug='type', description='d', category=category,
            min_points=1, max_points=10,
        )
        from contributions.models import Mission
        self.mission = Mission.objects.create(
            name='Mission', description='d', contribution_type=contribution_type,
        )

    def test_recall_broadcast_cancels_pending_telegram_rows(self):
        from social_connections.models import TelegramMessage
        services.broadcast_mission(self.mission)
        self.assertEqual(
            TelegramMessage.objects.filter(status=TelegramMessage.STATUS_PENDING).count(), 1
        )

        deleted = services.recall_broadcast('mission.published', self.mission)

        self.assertEqual(deleted, 1)
        self.assertEqual(TelegramMessage.objects.count(), 0)

    def test_drain_never_sends_rows_whose_notification_was_deleted(self):
        """Belt and braces: any other deletion path (e.g. admin) that orphans
        a pending row must not deliver the recalled content."""
        from unittest.mock import patch
        from social_connections.models import TelegramMessage
        services.broadcast_mission(self.mission)
        # Simulate a deletion path that bypasses the cancel helper.
        Notification.objects.all().delete()
        row = TelegramMessage.objects.get()
        self.assertIsNone(row.notification_id)
        self.assertEqual(row.status, TelegramMessage.STATUS_PENDING)

        from notifications.telegram import deliver_pending
        with patch('notifications.telegram.send_telegram_message') as send_mock, \
                patch('notifications.telegram.time.sleep'):
            stats = deliver_pending()

        send_mock.assert_not_called()
        row.refresh_from_db()
        self.assertEqual(row.status, TelegramMessage.STATUS_FAILED)
        self.assertEqual(row.error, 'notification_recalled')
        self.assertEqual(stats['failed'], 1)


class TelegramReviewFixTests(TestCase):
    """Regression tests for the second review round."""

    def setUp(self):
        from social_connections.models import TelegramConnection
        self.user = make_user('linked@test.com', '0x1111111111111111111111111111111111111111')
        self.connection = TelegramConnection.objects.create(
            user=self.user,
            platform_user_id='111',
            platform_username='linked',
            linked_at=timezone.now(),
        )

    def pending(self):
        from social_connections.models import TelegramMessage
        return TelegramMessage.objects.filter(
            direction=TelegramMessage.DIRECTION_OUT,
            status=TelegramMessage.STATUS_PENDING,
        )

    def test_dedupe_refresh_updates_pending_outbox_text(self):
        """An edit before the cron runs must deliver the refreshed copy."""
        for body in ('Original body', 'Corrected body'):
            services.notify(
                'submission.accepted',
                recipient=self.user,
                title='Accepted',
                body=body,
                dedupe_key='same-key',
            )
        row = self.pending().get()
        self.assertIn('Corrected body', row.text)
        self.assertNotIn('Original body', row.text)

    def test_escaping_heavy_body_stays_within_limit_with_intact_html(self):
        import re
        from notifications.telegram import render_notification_text
        notification = Notification(
            event_type='alert.published',
            category='system',
            title='Big alert',
            body='&' * 3000,
        )
        text = render_notification_text(notification)
        self.assertLessEqual(len(text), 4096)
        self.assertTrue(text.endswith('</blockquote>'))
        # The cut never lands inside an entity.
        self.assertIsNone(re.search(r'&[a-zA-Z]{0,4}…', text))

    def test_final_attempt_crash_row_is_swept_to_failed(self):
        from unittest.mock import patch
        from social_connections.models import TelegramMessage
        from notifications.telegram import MAX_ATTEMPTS, deliver_pending
        notification = services.notify(
            'submission.accepted', recipient=self.user, title='Accepted'
        )
        TelegramMessage.objects.filter(notification=notification).update(
            status=TelegramMessage.STATUS_SENDING,
            attempts=MAX_ATTEMPTS,
            updated_at=timezone.now() - timedelta(hours=1),
        )

        with patch('notifications.telegram.send_telegram_message') as send_mock, \
                patch('notifications.telegram.time.sleep'):
            deliver_pending()

        send_mock.assert_not_called()
        row = TelegramMessage.objects.get(notification=notification)
        self.assertEqual(row.status, TelegramMessage.STATUS_FAILED)
        self.assertEqual(row.error, 'max_attempts_exceeded')

    def test_recall_during_send_does_not_abort_the_drain(self):
        """A recall can delete a claimed row while its send is in flight;
        finishing that row must be a no-op, not an exception."""
        from unittest.mock import patch
        from social_connections.models import TelegramMessage
        from notifications.telegram import deliver_pending
        first = services.notify(
            'submission.accepted', recipient=self.user, title='First', dedupe_key='k1'
        )

        def send_and_recall(chat_id, text, **kwargs):
            # Simulate the recall landing while the worker is mid-send.
            TelegramMessage.objects.filter(notification=first).delete()
            return True, None, ''

        with patch('notifications.telegram.send_telegram_message', side_effect=send_and_recall), \
                patch('notifications.telegram.time.sleep'):
            stats = deliver_pending()

        # No crash; the deleted row is simply gone.
        self.assertEqual(TelegramMessage.objects.count(), 0)
        self.assertEqual(stats['remaining'], 0)
