from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from contributions.models import Category, ContributionType, SubmittedContribution
from partners.models import Partner
from validators.models import Validator

from notifications import services
from notifications.models import Notification, NotificationReceipt

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
