from datetime import timedelta

from django.test import override_settings
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from django.utils import timezone
from validators.models import SyncLock, Validator
from validators.views import ValidatorWalletViewSet
from contributions.models import Category

User = get_user_model()


class ValidatorAPITestCase(APITestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            name='Test User'
        )

        # Get or create validator category (migration may have created it)
        self.category, _ = Category.objects.get_or_create(
            slug='validator',
            defaults={
                'name': 'Validator',
                'description': 'Test validator category',
                'profile_model': 'validators.Validator'
            }
        )

        # Authenticate
        self.client.force_authenticate(user=self.user)

    def test_get_validator_profile_not_exists(self):
        """Test getting validator profile when it doesn't exist"""
        response = self.client.get('/api/v1/validators/me/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_validator_profile(self):
        """Test creating validator profile via PATCH"""
        response = self.client.patch('/api/v1/validators/me/', {
            'node_version_asimov': '1.2.3'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify profile was created
        self.assertTrue(Validator.objects.filter(user=self.user).exists())
        validator = Validator.objects.get(user=self.user)
        self.assertEqual(validator.node_version_asimov, '1.2.3')

    def test_update_validator_profile(self):
        """Test updating existing validator profile"""
        # Create profile first
        Validator.objects.create(user=self.user, node_version_asimov='1.0.0')

        # Update it
        response = self.client.patch('/api/v1/validators/me/', {
            'node_version_asimov': '2.0.0'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify update
        validator = Validator.objects.get(user=self.user)
        self.assertEqual(validator.node_version_asimov, '2.0.0')

    def test_get_validator_profile_exists(self):
        """Test getting existing validator profile"""
        Validator.objects.create(user=self.user, node_version_asimov='1.2.3')

        response = self.client.get('/api/v1/validators/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('node_version_asimov', response.data)
        self.assertEqual(response.data['node_version_asimov'], '1.2.3')

    def test_update_bradbury_version(self):
        """Test updating bradbury version"""
        Validator.objects.create(user=self.user, node_version_asimov='1.0.0')

        response = self.client.patch('/api/v1/validators/me/', {
            'node_version_bradbury': '2.0.0'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        validator = Validator.objects.get(user=self.user)
        self.assertEqual(validator.node_version_bradbury, '2.0.0')
        self.assertEqual(validator.node_version_asimov, '1.0.0')


@override_settings(CRON_SYNC_TOKEN='test-cron-token')
class ValidatorSyncLockTestCase(APITestCase):
    def test_sync_returns_409_while_non_stale_lock_is_held(self):
        SyncLock.objects.create(
            name=ValidatorWalletViewSet.SYNC_LOCK_NAME,
            owner_token='active-owner',
            acquired_at=timezone.now(),
            heartbeat_at=timezone.now(),
            released_at=None,
        )

        response = self.client.post(
            '/api/v1/validators/wallets/sync/',
            HTTP_X_CRON_TOKEN='test-cron-token',
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn('already in progress', response.data['message'])

    def test_old_owner_cannot_release_reclaimed_stale_lock(self):
        SyncLock.objects.create(
            name=ValidatorWalletViewSet.SYNC_LOCK_NAME,
            owner_token='old-owner',
            acquired_at=timezone.now() - timedelta(seconds=ValidatorWalletViewSet.SYNC_LOCK_STALE_AFTER_SECONDS + 1),
            heartbeat_at=timezone.now() - timedelta(seconds=ValidatorWalletViewSet.SYNC_LOCK_STALE_AFTER_SECONDS + 1),
            released_at=None,
        )

        new_owner_token, elapsed_seconds = ValidatorWalletViewSet._acquire_sync_lock()

        self.assertIsNotNone(new_owner_token)
        self.assertIsNone(elapsed_seconds)

        ValidatorWalletViewSet._release_sync_lock('old-owner')

        lock_row = SyncLock.objects.get(name=ValidatorWalletViewSet.SYNC_LOCK_NAME)
        self.assertEqual(lock_row.owner_token, new_owner_token)
        self.assertIsNone(lock_row.released_at)

        ValidatorWalletViewSet._release_sync_lock(new_owner_token)

        lock_row.refresh_from_db()
        self.assertIsNone(lock_row.owner_token)
        self.assertIsNotNone(lock_row.released_at)
