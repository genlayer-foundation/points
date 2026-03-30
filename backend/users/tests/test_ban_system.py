from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from users.models import BanAppeal

User = get_user_model()


class BanModelTest(TestCase):
    """Test ban fields on the User model and BanAppeal model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email='user@test.com',
            address='0x1234567890123456789012345678901234567890',
            password='testpass123',
        )
        self.admin = User.objects.create_superuser(
            email='admin@test.com',
            address='0x0987654321098765432109876543210987654321',
            password='testpass123',
        )

    def test_user_not_banned_by_default(self):
        self.assertFalse(self.user.is_banned)
        self.assertEqual(self.user.ban_reason, '')
        self.assertIsNone(self.user.banned_at)
        self.assertIsNone(self.user.banned_by)

    def test_ban_user(self):
        self.user.is_banned = True
        self.user.ban_reason = 'Repeated spam submissions'
        self.user.banned_at = timezone.now()
        self.user.banned_by = self.admin
        self.user.save()

        self.user.refresh_from_db()
        self.assertTrue(self.user.is_banned)
        self.assertEqual(self.user.ban_reason, 'Repeated spam submissions')
        self.assertIsNotNone(self.user.banned_at)
        self.assertEqual(self.user.banned_by, self.admin)

    def test_unban_user(self):
        self.user.is_banned = True
        self.user.ban_reason = 'Spam'
        self.user.banned_at = timezone.now()
        self.user.banned_by = self.admin
        self.user.save()

        self.user.is_banned = False
        self.user.ban_reason = ''
        self.user.banned_at = None
        self.user.banned_by = None
        self.user.save()

        self.user.refresh_from_db()
        self.assertFalse(self.user.is_banned)
        self.assertEqual(self.user.ban_reason, '')

    def test_create_ban_appeal(self):
        self.user.is_banned = True
        self.user.save()

        appeal = BanAppeal.objects.create(
            user=self.user,
            appeal_text='I promise to submit quality content.',
        )
        self.assertEqual(appeal.status, 'pending')
        self.assertIsNone(appeal.reviewed_by)
        self.assertIsNone(appeal.reviewed_at)
        self.assertEqual(str(appeal), f'Appeal by {self.user.email} (pending)')

    def test_approve_appeal(self):
        self.user.is_banned = True
        self.user.save()

        appeal = BanAppeal.objects.create(
            user=self.user,
            appeal_text='Please reconsider.',
        )
        appeal.status = 'approved'
        appeal.reviewed_by = self.admin
        appeal.reviewed_at = timezone.now()
        appeal.review_notes = 'User seems genuine.'
        appeal.save()

        appeal.refresh_from_db()
        self.assertEqual(appeal.status, 'approved')
        self.assertEqual(appeal.reviewed_by, self.admin)
        self.assertIsNotNone(appeal.reviewed_at)

    def test_deny_appeal(self):
        self.user.is_banned = True
        self.user.save()

        appeal = BanAppeal.objects.create(
            user=self.user,
            appeal_text='It was a mistake.',
        )
        appeal.status = 'denied'
        appeal.reviewed_by = self.admin
        appeal.reviewed_at = timezone.now()
        appeal.save()

        appeal.refresh_from_db()
        self.assertEqual(appeal.status, 'denied')


class BanAppealAPITest(TestCase):
    """Test the ban appeal API endpoints for users."""

    def setUp(self):
        self.user = User.objects.create_user(
            email='user@test.com',
            address='0x1234567890123456789012345678901234567890',
            password='testpass123',
        )
        self.client = APIClient()

    def test_get_appeal_not_banned(self):
        """Non-banned user sees no appeal and can_appeal=False."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/v1/users/me/appeal/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data['appeal'])
        self.assertFalse(response.data['can_appeal'])

    def test_get_appeal_banned_no_appeal_yet(self):
        """Banned user sees can_appeal=True when no appeal exists."""
        self.user.is_banned = True
        self.user.ban_reason = 'Spam'
        self.user.save()

        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/v1/users/me/appeal/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data['appeal'])
        self.assertTrue(response.data['can_appeal'])

    def test_submit_appeal(self):
        """Banned user can submit an appeal."""
        self.user.is_banned = True
        self.user.ban_reason = 'Spam'
        self.user.save()

        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/v1/users/me/appeal/', {
            'appeal_text': 'I will submit quality content from now on.',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'pending')
        self.assertEqual(BanAppeal.objects.filter(user=self.user).count(), 1)

    def test_cannot_submit_appeal_twice(self):
        """Banned user cannot submit more than one appeal."""
        self.user.is_banned = True
        self.user.save()

        BanAppeal.objects.create(user=self.user, appeal_text='First appeal')

        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/v1/users/me/appeal/', {
            'appeal_text': 'Second attempt',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(BanAppeal.objects.filter(user=self.user).count(), 1)

    def test_cannot_appeal_if_not_banned(self):
        """Non-banned user cannot submit an appeal."""
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/v1/users/me/appeal/', {
            'appeal_text': 'Not banned but trying to appeal.',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_appeal_empty_text(self):
        """Appeal requires non-empty text."""
        self.user.is_banned = True
        self.user.save()

        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/v1/users/me/appeal/', {
            'appeal_text': '',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_appeal_after_submission(self):
        """After submitting, GET returns the appeal and can_appeal=False."""
        self.user.is_banned = True
        self.user.save()

        BanAppeal.objects.create(user=self.user, appeal_text='My appeal')

        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/v1/users/me/appeal/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data['appeal'])
        self.assertFalse(response.data['can_appeal'])
        self.assertEqual(response.data['appeal']['status'], 'pending')

    def test_unauthenticated_cannot_access_appeal(self):
        """Unauthenticated users cannot access appeal endpoint."""
        response = self.client.get('/api/v1/users/me/appeal/')
        self.assertIn(response.status_code, [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ])

    def test_ban_fields_in_user_serializer(self):
        """is_banned and ban_reason are included in /users/me/ response."""
        self.user.is_banned = True
        self.user.ban_reason = 'Too much spam'
        self.user.save()

        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/v1/users/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_banned'])
        self.assertEqual(response.data['ban_reason'], 'Too much spam')


class BanAppealStewardReviewTest(TestCase):
    """Test steward ban appeal review endpoints."""

    def setUp(self):
        self.banned_user = User.objects.create_user(
            email='banned@test.com',
            address='0x1234567890123456789012345678901234567890',
            password='testpass123',
            is_banned=True,
            ban_reason='Auto-banned: 10 rejections',
        )
        self.steward_user = User.objects.create_user(
            email='steward@test.com',
            address='0x0987654321098765432109876543210987654321',
            password='testpass123',
        )
        from stewards.models import Steward
        Steward.objects.create(user=self.steward_user)

        self.regular_user = User.objects.create_user(
            email='regular@test.com',
            address='0x1111111111111111111111111111111111111111',
            password='testpass123',
        )

        self.appeal = BanAppeal.objects.create(
            user=self.banned_user,
            appeal_text='I have learned my lesson.',
        )
        self.client = APIClient()

    def test_steward_can_list_appeals(self):
        self.client.force_authenticate(user=self.steward_user)
        response = self.client.get('/api/v1/steward-submissions/ban-appeals/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['status'], 'pending')

    def test_steward_can_filter_appeals_by_status(self):
        self.client.force_authenticate(user=self.steward_user)
        response = self.client.get('/api/v1/steward-submissions/ban-appeals/?status=pending')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        response = self.client.get('/api/v1/steward-submissions/ban-appeals/?status=approved')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_steward_can_approve_appeal(self):
        self.client.force_authenticate(user=self.steward_user)
        response = self.client.post(
            f'/api/v1/steward-submissions/ban-appeals/{self.appeal.id}/review/',
            {'action': 'approve', 'review_notes': 'Seems genuine'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'approved')

        # Verify user is unbanned
        self.banned_user.refresh_from_db()
        self.assertFalse(self.banned_user.is_banned)
        self.assertEqual(self.banned_user.ban_reason, '')
        self.assertIsNone(self.banned_user.banned_at)

    def test_steward_can_deny_appeal(self):
        self.client.force_authenticate(user=self.steward_user)
        response = self.client.post(
            f'/api/v1/steward-submissions/ban-appeals/{self.appeal.id}/review/',
            {'action': 'deny', 'review_notes': 'Persistent spammer'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'denied')

        # Verify user stays banned
        self.banned_user.refresh_from_db()
        self.assertTrue(self.banned_user.is_banned)

    def test_cannot_review_already_reviewed_appeal(self):
        self.appeal.status = 'denied'
        self.appeal.save()

        self.client.force_authenticate(user=self.steward_user)
        response = self.client.post(
            f'/api/v1/steward-submissions/ban-appeals/{self.appeal.id}/review/',
            {'action': 'approve'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_regular_user_cannot_list_appeals(self):
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get('/api/v1/steward-submissions/ban-appeals/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_regular_user_cannot_review_appeal(self):
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.post(
            f'/api/v1/steward-submissions/ban-appeals/{self.appeal.id}/review/',
            {'action': 'approve'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_list_appeals(self):
        response = self.client.get('/api/v1/steward-submissions/ban-appeals/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
