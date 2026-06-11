from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from contributions.models import Category, ContributionType, SubmittedContribution
from partners.models import Partner
from validators.models import Validator

from notifications import campaigns, services
from notifications.models import CustomNotification, Notification, NotificationReceipt

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
        self.assertIn('#/my-submissions?', notification.link_url)
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
        self.assertEqual(row.link_url, '#/missions')
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
