from datetime import timedelta
from unittest.mock import patch

from django.test import override_settings
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from django.utils import timezone
from validators.genlayer_validators_service import GenLayerValidatorsService
from validators.models import SyncLock, Validator, ValidatorOperatorWallet, ValidatorWallet
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

    def test_patch_validator_profile_is_not_allowed(self):
        """/me is read-only: node versions come from Grafana, not the portal."""
        response = self.client.patch('/api/v1/validators/me/', {
            'node_version_asimov': '1.2.3'
        })
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertFalse(Validator.objects.filter(user=self.user).exists())

    def test_regular_user_cannot_mutate_arbitrary_validator_profile(self):
        """Ordinary users cannot mutate validator profiles through object routes."""
        other_user = User.objects.create_user(
            email='other@example.com',
            password='testpass123',
        )
        validator = Validator.objects.create(user=other_user)

        response = self.client.patch(
            f'/api/v1/validators/{validator.id}/',
            {'node_version_asimov': '9.9.9'},
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        validator.refresh_from_db()
        self.assertNotEqual(validator.node_version_asimov, '9.9.9')

    def test_regular_user_cannot_create_validator_profile(self):
        response = self.client.post('/api/v1/validators/', {
            'node_version_asimov': '1.2.3',
        })

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Validator.objects.filter(user=self.user).exists())

    def test_patch_does_not_change_node_version(self):
        """A PATCH to /me cannot overwrite the Grafana-sourced node version."""
        Validator.objects.create(user=self.user, node_version_asimov='1.0.0')

        response = self.client.patch('/api/v1/validators/me/', {
            'node_version_asimov': '2.0.0'
        })
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        validator = Validator.objects.get(user=self.user)
        self.assertEqual(validator.node_version_asimov, '1.0.0')

    def test_get_validator_profile_exists(self):
        """Test getting existing validator profile"""
        Validator.objects.create(user=self.user, node_version_asimov='1.2.3')

        response = self.client.get('/api/v1/validators/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('node_version_asimov', response.data)
        self.assertEqual(response.data['node_version_asimov'], '1.2.3')


class ValidatorOperatorWalletLinkTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='validator@example.com',
            password='testpass123',
            address='0x1111111111111111111111111111111111111111',
            name='Validator',
        )
        self.validator = Validator.objects.create(user=self.user)
        self.client.force_authenticate(user=self.user)

    def _claim_operator(self, address):
        return self.client.post('/api/v1/validators/link-by-operator/', {
            'operator_address': address,
        }, format='json')

    def test_operator_wallet_claim_links_matching_wallets_across_networks(self):
        operator_address = '0x2222222222222222222222222222222222222222'
        asimov_wallet = ValidatorWallet.objects.create(
            address='0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
            network='asimov',
            operator_address=operator_address,
            status='active',
        )
        bradbury_wallet = ValidatorWallet.objects.create(
            address='0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
            network='bradbury',
            operator_address=operator_address,
            status='active',
        )

        response = self._claim_operator(operator_address)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['wallets_linked'], 2)
        link = ValidatorOperatorWallet.objects.get(address=operator_address)
        self.assertEqual(link.validator, self.validator)
        asimov_wallet.refresh_from_db()
        bradbury_wallet.refresh_from_db()
        self.assertEqual(asimov_wallet.operator, self.validator)
        self.assertEqual(bradbury_wallet.operator, self.validator)

    def test_validator_can_claim_multiple_operator_wallets(self):
        first = '0x2222222222222222222222222222222222222222'
        second = '0x3333333333333333333333333333333333333333'
        ValidatorWallet.objects.create(
            address='0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
            network='asimov',
            operator_address=first,
            status='active',
        )
        ValidatorWallet.objects.create(
            address='0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
            network='bradbury',
            operator_address=second,
            status='active',
        )

        first_response = self._claim_operator(first)
        second_response = self._claim_operator(second)

        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            set(self.validator.operator_wallets.values_list('address', flat=True)),
            {first, second},
        )

    def test_operator_wallet_claim_is_first_come_first_served(self):
        operator_address = '0x2222222222222222222222222222222222222222'
        other_user = User.objects.create_user(
            email='other-validator@example.com',
            password='testpass123',
            address='0x4444444444444444444444444444444444444444',
        )
        other_validator = Validator.objects.create(user=other_user)
        ValidatorOperatorWallet.objects.create(
            validator=other_validator,
            address=operator_address,
        )
        ValidatorWallet.objects.create(
            address='0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
            network='asimov',
            operator_address=operator_address,
            status='active',
        )

        response = self._claim_operator(operator_address)

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_operator_wallet_claim_requires_existing_synced_wallet(self):
        response = self._claim_operator('0x2222222222222222222222222222222222222222')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_sync_uses_claimed_operator_wallet_link(self):
        link = ValidatorOperatorWallet.objects.create(
            validator=self.validator,
            address='0x2222222222222222222222222222222222222222',
        )
        service = GenLayerValidatorsService.__new__(GenLayerValidatorsService)
        service.network_key = 'bradbury'
        stats = {'rpc_time_operator': 0.0, 'rpc_time_identity': 0.0, 'rpc_time_view': 0.0, 'created': 0, 'updated': 0}

        with patch.object(service, 'fetch_operator_for_wallet', return_value=link.address), \
                patch.object(service, 'fetch_validator_identity', return_value={'moniker': 'Bradbury One'}), \
                patch.object(service, 'fetch_validator_view', return_value={'v_stake': '1', 'd_stake': '2'}):
            service._process_validator(
                address='0xcccccccccccccccccccccccccccccccccccccccc',
                is_active=True,
                banned_info=None,
                stats=stats,
            )

        wallet = ValidatorWallet.objects.get(address='0xcccccccccccccccccccccccccccccccccccccccc')
        self.assertEqual(wallet.network, 'bradbury')
        self.assertEqual(wallet.operator, self.validator)

    def test_sync_preserves_existing_link_when_operator_unchanged_and_claim_missing(self):
        operator_address = '0x2222222222222222222222222222222222222222'
        wallet = ValidatorWallet.objects.create(
            address='0xdddddddddddddddddddddddddddddddddddddddd',
            network='bradbury',
            operator=self.validator,
            operator_address=operator_address,
            status='active',
        )
        service = GenLayerValidatorsService.__new__(GenLayerValidatorsService)
        service.network_key = 'bradbury'
        stats = {'rpc_time_operator': 0.0, 'rpc_time_identity': 0.0, 'rpc_time_view': 0.0, 'created': 0, 'updated': 0}

        with patch.object(service, 'fetch_operator_for_wallet', return_value=operator_address), \
                patch.object(service, 'fetch_validator_identity', return_value=None), \
                patch.object(service, 'fetch_validator_view', return_value=None):
            service._process_validator(
                address=wallet.address,
                is_active=True,
                banned_info=None,
                stats=stats,
            )

        wallet.refresh_from_db()
        self.assertEqual(wallet.operator, self.validator)
        self.assertTrue(
            ValidatorOperatorWallet.objects.filter(
                validator=self.validator,
                address=operator_address,
            ).exists()
        )

    def test_sync_clears_stale_operator_link_when_chain_operator_changes(self):
        old_operator = self.user.address.lower()
        wallet = ValidatorWallet.objects.create(
            address='0xdddddddddddddddddddddddddddddddddddddddd',
            network='bradbury',
            operator=self.validator,
            operator_address=old_operator,
            status='active',
        )
        service = GenLayerValidatorsService.__new__(GenLayerValidatorsService)
        service.network_key = 'bradbury'
        stats = {'rpc_time_operator': 0.0, 'rpc_time_identity': 0.0, 'rpc_time_view': 0.0, 'created': 0, 'updated': 0}

        with patch.object(service, 'fetch_operator_for_wallet', return_value='0x3333333333333333333333333333333333333333'), \
                patch.object(service, 'fetch_validator_identity', return_value=None), \
                patch.object(service, 'fetch_validator_view', return_value=None):
            service._process_validator(
                address=wallet.address,
                is_active=True,
                banned_info=None,
                stats=stats,
            )

        wallet.refresh_from_db()
        self.assertEqual(wallet.operator_address, '0x3333333333333333333333333333333333333333')
        self.assertIsNone(wallet.operator)


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
