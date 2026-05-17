import tempfile
import zipfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import IntegrityError, connection, transaction
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from poaps.models import PoapClaim, PoapDistribution, PoapDrop
from poaps.services import generate_mint_links, hash_secret

User = get_user_model()


class PoapAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='user@example.com',
            password='pass123',
            address='0x1111111111111111111111111111111111111111',
        )
        self.other_user = User.objects.create_user(
            email='other@example.com',
            password='pass123',
            address='0x2222222222222222222222222222222222222222',
        )
        self.staff = User.objects.create_user(
            email='staff@example.com',
            password='pass123',
            address='0x3333333333333333333333333333333333333333',
            is_staff=True,
        )
        self.drop = PoapDrop.objects.create(
            title='AMA Session',
            slug='ama-session',
            description='Participation badge',
            artwork_url='https://example.com/poap.png',
            event_start_at=timezone.now(),
            status=PoapDrop.STATUS_ACTIVE,
        )

    def _secret_distribution(self, secret='friend-scientist-natural', **kwargs):
        defaults = {
            'drop': self.drop,
            'method': PoapDistribution.METHOD_SECRET,
            'active': True,
            'secret_hash': hash_secret(secret),
        }
        defaults.update(kwargs)
        return PoapDistribution.objects.create(**defaults)

    def test_unique_claim_per_user_and_drop(self):
        PoapClaim.objects.create(
            drop=self.drop,
            user=self.user,
            claim_method=PoapClaim.CLAIM_SECRET,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PoapClaim.objects.create(
                    drop=self.drop,
                    user=self.user,
                    claim_method=PoapClaim.CLAIM_SECRET,
                )

    def test_secret_claim_success(self):
        distribution = self._secret_distribution()
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            '/api/v1/poaps/ama-session/claim-secret/',
            {'secret': ' Friend-Scientist-Natural '},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(PoapClaim.objects.filter(drop=self.drop, user=self.user).exists())
        distribution.refresh_from_db()
        self.assertEqual(distribution.claimed_count, 1)

    def test_secret_claim_rejects_invalid_secret(self):
        self._secret_distribution()
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            '/api/v1/poaps/ama-session/claim-secret/',
            {'secret': 'wrong'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(PoapClaim.objects.exists())

    def test_secret_claim_enforces_duplicate(self):
        self._secret_distribution()
        self.client.force_authenticate(user=self.user)
        self.client.post('/api/v1/poaps/ama-session/claim-secret/', {'secret': 'friend-scientist-natural'}, format='json')

        response = self.client.post(
            '/api/v1/poaps/ama-session/claim-secret/',
            {'secret': 'friend-scientist-natural'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_secret_claim_enforces_window_and_capacity(self):
        self._secret_distribution(
            starts_at=timezone.now() + timezone.timedelta(hours=1),
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            '/api/v1/poaps/ama-session/claim-secret/',
            {'secret': 'friend-scientist-natural'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_mint_link_single_use(self):
        distribution = PoapDistribution.objects.create(
            drop=self.drop,
            method=PoapDistribution.METHOD_MINT_LINK,
            active=True,
            max_claims=1,
        )
        [(link, token)] = generate_mint_links(distribution=distribution, count=1)

        self.client.force_authenticate(user=self.user)
        response = self.client.post(f'/api/v1/poaps/claim-link/{token}/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.client.force_authenticate(user=self.other_user)
        response = self.client.post(f'/api/v1/poaps/claim-link/{token}/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        link.refresh_from_db()
        distribution.refresh_from_db()
        self.assertEqual(link.used_count, 1)
        self.assertEqual(distribution.claimed_count, 1)

    def test_list_and_profile_poaps_are_query_bounded(self):
        for index in range(15):
            drop = PoapDrop.objects.create(
                title=f'Drop {index}',
                event_start_at=timezone.now() - timezone.timedelta(days=index),
                status=PoapDrop.STATUS_ACTIVE,
            )
            PoapClaim.objects.create(
                drop=drop,
                user=self.user,
                claim_method=PoapClaim.CLAIM_LEGACY,
            )

        self.client.force_authenticate(user=self.user)
        with CaptureQueriesContext(connection) as list_queries:
            response = self.client.get('/api/v1/poaps/?page_size=10')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(list_queries), 6)

        with CaptureQueriesContext(connection) as profile_queries:
            response = self.client.get(f'/api/v1/users/by-address/{self.user.address}/poaps/?page_size=10')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(profile_queries), 6)

    def test_list_reports_claimability_from_distribution_and_capacity(self):
        live_drop = PoapDrop.objects.create(
            title='Live Drop',
            slug='live-drop',
            event_start_at=timezone.now(),
            status=PoapDrop.STATUS_ACTIVE,
        )
        PoapDistribution.objects.create(
            drop=live_drop,
            method=PoapDistribution.METHOD_SECRET,
            active=True,
            secret_hash=hash_secret('live'),
        )
        full_drop = PoapDrop.objects.create(
            title='Full Drop',
            slug='full-drop',
            event_start_at=timezone.now(),
            status=PoapDrop.STATUS_ACTIVE,
            max_claims=1,
        )
        PoapDistribution.objects.create(
            drop=full_drop,
            method=PoapDistribution.METHOD_SECRET,
            active=True,
            secret_hash=hash_secret('full'),
        )
        PoapClaim.objects.create(
            drop=full_drop,
            user=self.other_user,
            claim_method=PoapClaim.CLAIM_SECRET,
        )

        response = self.client.get('/api/v1/poaps/?page_size=20')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        by_slug = {item['slug']: item for item in response.data['results']}

        self.assertTrue(by_slug['live-drop']['can_claim'])
        self.assertEqual(by_slug['live-drop']['claim_state'], 'live')
        self.assertFalse(by_slug['full-drop']['can_claim'])
        self.assertEqual(by_slug['full-drop']['claim_state'], 'full')
        self.assertFalse(by_slug['ama-session']['can_claim'])
        self.assertEqual(by_slug['ama-session']['claim_state'], 'unavailable')

    def test_public_claims_do_not_expose_legacy_private_fields(self):
        PoapClaim.objects.create(
            drop=self.drop,
            user=self.user,
            claim_method=PoapClaim.CLAIM_LEGACY,
            source=PoapClaim.SOURCE_LEGACY_IMPORT,
            legacy_wallet_address=self.user.address,
            legacy_email='legacy-private@example.com',
            legacy_external_id='external-123',
            legacy_metadata={'ens': 'private.eth'},
        )

        response = self.client.get('/api/v1/poaps/ama-session/claims/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        claim = response.data['results'][0]
        self.assertIn('user_details', claim)
        self.assertNotIn('user', claim)
        self.assertNotIn('source', claim)
        self.assertNotIn('legacy_wallet_address', claim)
        self.assertNotIn('legacy_email', claim)
        self.assertNotIn('legacy_external_id', claim)
        self.assertNotIn('legacy_ens', claim)

    def test_staff_permissions_and_generation(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            '/api/v1/poaps/',
            {
                'title': 'Private',
                'event_start_at': timezone.now().isoformat(),
                'status': PoapDrop.STATUS_ACTIVE,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.staff)
        response = self.client.post(
            '/api/v1/poaps/ama-session/distributions/secret/',
            {'secret': 'secret-code'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.client.post(
            '/api/v1/poaps/ama-session/mint-links/generate/',
            {'count': 2},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['created'], 2)

    def test_staff_distribution_generation_rejects_archived_and_over_capacity_drops(self):
        archived_drop = PoapDrop.objects.create(
            title='Archived',
            slug='archived',
            event_start_at=timezone.now(),
            status=PoapDrop.STATUS_ARCHIVED,
        )
        full_drop = PoapDrop.objects.create(
            title='Full',
            slug='full',
            event_start_at=timezone.now(),
            status=PoapDrop.STATUS_ACTIVE,
            max_claims=1,
        )
        PoapClaim.objects.create(
            drop=full_drop,
            user=self.user,
            claim_method=PoapClaim.CLAIM_LEGACY,
        )

        self.client.force_authenticate(user=self.staff)
        response = self.client.post(
            '/api/v1/poaps/archived/mint-links/generate/',
            {'count': 1},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.post(
            '/api/v1/poaps/full/distributions/secret/',
            {'secret': 'closed'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_lower_drop_max_claims_below_current_claims(self):
        PoapClaim.objects.create(
            drop=self.drop,
            user=self.user,
            claim_method=PoapClaim.CLAIM_LEGACY,
        )
        PoapClaim.objects.create(
            drop=self.drop,
            user=self.other_user,
            claim_method=PoapClaim.CLAIM_LEGACY,
        )

        self.client.force_authenticate(user=self.staff)
        response = self.client.patch(
            '/api/v1/poaps/ama-session/',
            {'max_claims': 1},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('max_claims', response.data)

    def test_legacy_unmatched_claim_attaches_when_user_matches_wallet(self):
        claim = PoapClaim.objects.create(
            drop=self.drop,
            claim_method=PoapClaim.CLAIM_LEGACY,
            source=PoapClaim.SOURCE_LEGACY_IMPORT,
            legacy_wallet_address='0x4444444444444444444444444444444444444444',
        )

        user = User.objects.create_user(
            email='new@example.com',
            password='pass123',
            address='0x4444444444444444444444444444444444444444',
        )

        claim.refresh_from_db()
        self.assertEqual(claim.user, user)

    def test_legacy_unmatched_claim_does_not_attach_by_email(self):
        claim = PoapClaim.objects.create(
            drop=self.drop,
            claim_method=PoapClaim.CLAIM_LEGACY,
            source=PoapClaim.SOURCE_LEGACY_IMPORT,
            legacy_email='new-email@example.com',
        )

        user = User.objects.create_user(
            email='new-email@example.com',
            password='pass123',
            address='0x5555555555555555555555555555555555555555',
            is_email_verified=True,
        )
        user.save()

        claim.refresh_from_db()
        self.assertIsNone(claim.user)

    @patch('users.cloudinary_service.CloudinaryService.upload_image')
    def test_poap_archive_import_matches_wallet_only_and_requires_images(self, upload_image):
        upload_image.return_value = {
            'url': 'https://res.cloudinary.com/demo/image/upload/tally/poaps/poap-123.webp',
            'public_id': 'tally/poaps/poap_123',
        }
        wallet = '0x6666666666666666666666666666666666666666'
        matched_user = User.objects.create_user(
            email='wallet-match@example.com',
            password='pass123',
            address=wallet,
        )
        csv_data = (
            'ens,email_address,ethereum_address\n'
            f'wallet.eth,,{wallet}\n'
            ',email-only@example.com,\n'
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            archive_path = f'{temp_dir}/poaps.zip'
            with zipfile.ZipFile(archive_path, 'w') as archive:
                archive.writestr(
                    'poap.data/POAP_drop_123_collectors_2026-03-25 - Test Drop.csv',
                    csv_data,
                )
                archive.writestr(
                    'poap.data/poap_images/ID 123_Test Drop.webp',
                    b'fake-webp',
                )

            call_command(
                'import_poap_archive',
                archive_path,
                '--upload-artwork',
                verbosity=0,
            )
            call_command(
                'import_poap_archive',
                archive_path,
                '--upload-artwork',
                verbosity=0,
            )

        drop = PoapDrop.objects.get(legacy_poap_id='123')
        self.assertEqual(drop.title, 'Test Drop')
        self.assertEqual(drop.max_claims, 2)
        self.assertEqual(
            drop.artwork_url,
            'https://res.cloudinary.com/demo/image/upload/tally/poaps/poap-123.webp',
        )
        self.assertEqual(drop.artwork_public_id, 'tally/poaps/poap_123')
        self.assertTrue(PoapClaim.objects.filter(drop=drop, user=matched_user).exists())
        self.assertTrue(PoapClaim.objects.filter(
            drop=drop,
            user__isnull=True,
            legacy_email='email-only@example.com',
        ).exists())
        upload_image.assert_called_once()
        self.assertEqual(PoapClaim.objects.filter(drop=drop).count(), 2)
