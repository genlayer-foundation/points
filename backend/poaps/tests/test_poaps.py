import tempfile
import zipfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, connection, transaction
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from eth_account import Account
from eth_account.messages import encode_defunct
from rest_framework import status
from rest_framework.test import APIClient

from ethereum_auth.models import Nonce
from poaps.admin import PoapDistributionAdminForm, PoapDropAdminForm
from poaps.models import PoapClaim, PoapDistribution, PoapDrop, PoapImportBatch
from poaps.services import generate_mint_links, hash_secret
from social_connections.models import DiscordConnection

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
        self._link_discord(self.user, 'discord-user')
        self._link_discord(self.other_user, 'discord-other')

    def _link_discord(self, user, platform_user_id):
        return DiscordConnection.objects.create(
            user=user,
            platform_user_id=platform_user_id,
            platform_username=platform_user_id,
            linked_at=timezone.now(),
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

    def _recovery_payload(self, account, portal_user=None, nonce_value='recover-nonce'):
        portal_user = portal_user or self.user
        Nonce.objects.create(
            value=nonce_value,
            expires_at=timezone.now() + timezone.timedelta(minutes=5),
        )
        message = (
            f'localhost wants you to verify a wallet for GenLayer POAP recovery:\n'
            f'{account.address}\n\n'
            'This signature only proves ownership of this wallet for attaching legacy POAPs '
            'to your current portal account. It will not sign you into the portal or change your account.\n\n'
            f'Portal Account: {portal_user.address}\n'
            'URI: http://localhost:5173\n'
            'Version: 1\n'
            'Chain ID: 1\n'
            f'Nonce: {nonce_value}\n'
            f'Issued At: {timezone.now().isoformat()}'
        )
        signed = Account.sign_message(encode_defunct(text=message), private_key=account.key)
        return {
            'address': account.address,
            'message': message,
            'signature': signed.signature.hex(),
        }

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

    def test_secret_claim_requires_discord_connection(self):
        distribution = self._secret_distribution()
        DiscordConnection.objects.filter(user=self.user).delete()
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            '/api/v1/poaps/ama-session/claim-secret/',
            {'secret': 'friend-scientist-natural'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('link your Discord', response.data['error'])
        self.assertFalse(PoapClaim.objects.filter(drop=self.drop, user=self.user).exists())
        distribution.refresh_from_db()
        self.assertEqual(distribution.claimed_count, 0)

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

    def test_mint_link_claim_reports_missing_token(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post('/api/v1/poaps/claim-link/not-a-real-token/')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data['error'],
            'Mint link token was not found. Check that the full Claim URL was copied from the admin.',
        )

    def test_mint_link_claim_requires_discord_connection(self):
        distribution = PoapDistribution.objects.create(
            drop=self.drop,
            method=PoapDistribution.METHOD_MINT_LINK,
            active=True,
        )
        [(link, token)] = generate_mint_links(distribution=distribution, count=1)
        DiscordConnection.objects.filter(user=self.user).delete()
        self.client.force_authenticate(user=self.user)

        response = self.client.post(f'/api/v1/poaps/claim-link/{token}/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('link your Discord', response.data['error'])
        self.assertFalse(PoapClaim.objects.filter(drop=self.drop, user=self.user).exists())
        link.refresh_from_db()
        distribution.refresh_from_db()
        self.assertEqual(link.used_count, 0)
        self.assertEqual(distribution.claimed_count, 0)

    def test_mint_link_claim_reports_inactive_distribution(self):
        distribution = PoapDistribution.objects.create(
            drop=self.drop,
            method=PoapDistribution.METHOD_MINT_LINK,
            active=False,
        )
        [(_link, token)] = generate_mint_links(distribution=distribution, count=1)
        self.client.force_authenticate(user=self.user)

        response = self.client.post(f'/api/v1/poaps/claim-link/{token}/')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'This mint-link distribution is inactive.')

    def test_mint_link_claim_reports_expired_link(self):
        distribution = PoapDistribution.objects.create(
            drop=self.drop,
            method=PoapDistribution.METHOD_MINT_LINK,
            active=True,
        )
        [(_link, token)] = generate_mint_links(
            distribution=distribution,
            count=1,
            expires_at=timezone.now() - timezone.timedelta(minutes=1),
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.post(f'/api/v1/poaps/claim-link/{token}/')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'This mint link has expired.')

    def test_mint_link_claim_reports_used_link(self):
        distribution = PoapDistribution.objects.create(
            drop=self.drop,
            method=PoapDistribution.METHOD_MINT_LINK,
            active=True,
        )
        [(link, token)] = generate_mint_links(distribution=distribution, count=1)
        link.used_count = 1
        link.save(update_fields=['used_count', 'updated_at'])
        self.client.force_authenticate(user=self.user)

        response = self.client.post(f'/api/v1/poaps/claim-link/{token}/')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'This mint link has already been used.')

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

    def test_poap_management_api_is_not_exposed(self):
        self.client.force_authenticate(user=self.staff)

        response = self.client.post(
            '/api/v1/poaps/',
            {
                'title': 'Admin Only',
                'event_start_at': timezone.now().isoformat(),
                'status': PoapDrop.STATUS_ACTIVE,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        response = self.client.patch(
            '/api/v1/poaps/ama-session/',
            {'max_claims': 10},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        response = self.client.post(
            '/api/v1/poaps/ama-session/distributions/secret/',
            {'secret': 'secret-code'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        response = self.client.post(
            '/api/v1/poaps/ama-session/mint-links/generate/',
            {'count': 2},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        response = self.client.get('/api/v1/poaps/ama-session/mint-links/download/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        response = self.client.get('/api/v1/poaps/permissions/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_verify_wallet_attaches_unmatched_legacy_claims_without_changing_session(self):
        account = Account.create()
        claim = PoapClaim.objects.create(
            drop=self.drop,
            claim_method=PoapClaim.CLAIM_LEGACY,
            source=PoapClaim.SOURCE_LEGACY_IMPORT,
            legacy_wallet_address=account.address,
        )
        session = self.client.session
        session['ethereum_address'] = self.user.address
        session['authenticated'] = True
        session.save()
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            '/api/v1/poaps/verify-wallet/',
            self._recovery_payload(account),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['attached_count'], 1)
        self.assertEqual(response.data['attached_poaps'][0]['drop']['slug'], self.drop.slug)
        claim.refresh_from_db()
        self.assertEqual(claim.user, self.user)
        self.assertEqual(self.client.session['ethereum_address'], self.user.address)

    def test_verify_wallet_rejects_invalid_signature(self):
        account = Account.create()
        signer = Account.create()
        payload = self._recovery_payload(account)
        payload['signature'] = Account.sign_message(
            encode_defunct(text=payload['message']),
            private_key=signer.key,
        ).signature.hex()
        self.client.force_authenticate(user=self.user)

        response = self.client.post('/api/v1/poaps/verify-wallet/', payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_wallet_rejects_expired_nonce(self):
        account = Account.create()
        nonce_value = 'expired-recovery-nonce'
        Nonce.objects.create(
            value=nonce_value,
            expires_at=timezone.now() - timezone.timedelta(minutes=1),
        )
        message = (
            f'localhost wants you to verify a wallet for GenLayer POAP recovery:\n'
            f'{account.address}\n\n'
            'This signature only proves ownership of this wallet for attaching legacy POAPs '
            'to your current portal account. It will not sign you into the portal or change your account.\n\n'
            f'Portal Account: {self.user.address}\n'
            'URI: http://localhost:5173\n'
            'Version: 1\n'
            'Chain ID: 1\n'
            f'Nonce: {nonce_value}\n'
            f'Issued At: {timezone.now().isoformat()}'
        )
        payload = {
            'address': account.address,
            'message': message,
            'signature': Account.sign_message(encode_defunct(text=message), private_key=account.key).signature.hex(),
        }
        self.client.force_authenticate(user=self.user)

        response = self.client.post('/api/v1/poaps/verify-wallet/', payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_wallet_blocks_another_users_primary_wallet(self):
        account = Account.create()
        self.other_user.address = account.address
        self.other_user.save(update_fields=['address', 'updated_at'])
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            '/api/v1/poaps/verify-wallet/',
            self._recovery_payload(account),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_verify_wallet_blocks_legacy_claims_attached_to_another_user(self):
        account = Account.create()
        PoapClaim.objects.create(
            drop=self.drop,
            user=self.other_user,
            claim_method=PoapClaim.CLAIM_LEGACY,
            source=PoapClaim.SOURCE_LEGACY_IMPORT,
            legacy_wallet_address=account.address,
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            '/api/v1/poaps/verify-wallet/',
            self._recovery_payload(account),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_verify_wallet_skips_drops_user_already_has(self):
        account = Account.create()
        second_drop = PoapDrop.objects.create(
            title='Second Drop',
            slug='second-drop',
            description='Another badge',
            artwork_url='https://example.com/poap-2.png',
            event_start_at=timezone.now(),
            status=PoapDrop.STATUS_ACTIVE,
        )
        PoapClaim.objects.create(
            drop=self.drop,
            user=self.user,
            claim_method=PoapClaim.CLAIM_SECRET,
        )
        duplicate_claim = PoapClaim.objects.create(
            drop=self.drop,
            claim_method=PoapClaim.CLAIM_LEGACY,
            source=PoapClaim.SOURCE_LEGACY_IMPORT,
            legacy_wallet_address=account.address,
        )
        attachable_claim = PoapClaim.objects.create(
            drop=second_drop,
            claim_method=PoapClaim.CLAIM_LEGACY,
            source=PoapClaim.SOURCE_LEGACY_IMPORT,
            legacy_wallet_address=account.address,
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            '/api/v1/poaps/verify-wallet/',
            self._recovery_payload(account),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['attached_count'], 1)
        self.assertEqual(response.data['skipped_existing_drop_count'], 1)
        duplicate_claim.refresh_from_db()
        attachable_claim.refresh_from_db()
        self.assertIsNone(duplicate_claim.user)
        self.assertEqual(attachable_claim.user, self.user)

    def test_poap_drop_admin_form_rejects_lower_max_claims_below_current_claims(self):
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

        form = PoapDropAdminForm(
            data={
                'title': self.drop.title,
                'slug': self.drop.slug,
                'description': self.drop.description,
                'artwork_url': self.drop.artwork_url,
                'event_start_at': self.drop.event_start_at.isoformat(),
                'event_end_at': '',
                'status': self.drop.status,
                'max_claims': 1,
                'created_by': '',
                'legacy_poap_id': self.drop.legacy_poap_id,
                'discord_role_id': self.drop.discord_role_id,
            },
            instance=self.drop,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('max_claims', form.errors)

    def test_poap_distribution_admin_form_counts_existing_unused_links_against_distribution_capacity(self):
        distribution = PoapDistribution.objects.create(
            drop=self.drop,
            method=PoapDistribution.METHOD_MINT_LINK,
            active=True,
            max_claims=10,
        )
        generate_mint_links(distribution=distribution, count=10)

        form = PoapDistributionAdminForm(
            data={
                'drop': self.drop.pk,
                'method': PoapDistribution.METHOD_MINT_LINK,
                'active': 'on',
                'starts_at': '',
                'ends_at': '',
                'max_claims': 10,
                'claimed_count': distribution.claimed_count,
                'secret_hash': '',
                'secret_phrase': '',
                'mint_link_count': 1,
                'mint_link_max_uses': 1,
                'mint_link_expires_at': '',
            },
            instance=distribution,
        )

        self.assertFalse(form.is_valid())
        self.assertIn('mint_link_count', form.errors)

    def test_poap_distribution_admin_form_hides_discord_voice_for_new_distributions(self):
        form = PoapDistributionAdminForm()

        method_choices = [value for value, _label in form.fields['method'].choices]

        self.assertEqual(
            method_choices,
            [
                PoapDistribution.METHOD_SECRET,
                PoapDistribution.METHOD_MINT_LINK,
            ],
        )

    def test_poap_distribution_admin_form_keeps_existing_discord_voice_distribution_editable(self):
        distribution = PoapDistribution.objects.create(
            drop=self.drop,
            method=PoapDistribution.METHOD_DISCORD_VOICE,
            active=True,
        )
        form = PoapDistributionAdminForm(instance=distribution)

        method_choices = [value for value, _label in form.fields['method'].choices]

        self.assertIn(PoapDistribution.METHOD_DISCORD_VOICE, method_choices)

    def test_poap_distribution_admin_form_counts_existing_unused_links_against_drop_capacity(self):
        self.drop.max_claims = 10
        self.drop.save(update_fields=['max_claims', 'updated_at'])
        existing_distribution = PoapDistribution.objects.create(
            drop=self.drop,
            method=PoapDistribution.METHOD_MINT_LINK,
            active=True,
            max_claims=10,
        )
        generate_mint_links(distribution=existing_distribution, count=10)

        form = PoapDistributionAdminForm(
            data={
                'drop': self.drop.pk,
                'method': PoapDistribution.METHOD_MINT_LINK,
                'active': 'on',
                'starts_at': '',
                'ends_at': '',
                'max_claims': 1,
                'claimed_count': 0,
                'secret_hash': '',
                'secret_phrase': '',
                'mint_link_count': 1,
                'mint_link_max_uses': 1,
                'mint_link_expires_at': '',
            },
        )

        self.assertFalse(form.is_valid())
        self.assertIn('mint_link_count', form.errors)

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

    @patch('users.cloudinary_service.CloudinaryService.upload_image')
    def test_poap_archive_import_keeps_shared_email_wallet_claims(self, upload_image):
        upload_image.return_value = {
            'url': 'https://res.cloudinary.com/demo/image/upload/tally/poaps/poap-456.webp',
            'public_id': 'tally/poaps/poap_456',
        }
        first_wallet = '0x7777777777777777777777777777777777777777'
        second_wallet = '0x8888888888888888888888888888888888888888'
        csv_data = (
            'email_address,ethereum_address\n'
            f'shared@example.com,{first_wallet}\n'
            f'shared@example.com,{second_wallet}\n'
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            archive_path = f'{temp_dir}/poaps.zip'
            with zipfile.ZipFile(archive_path, 'w') as archive:
                archive.writestr(
                    'poap.data/POAP_drop_456_collectors_2026-03-25 - Shared Email.csv',
                    csv_data,
                )
                archive.writestr(
                    'poap.data/poap_images/ID 456_Shared Email.webp',
                    b'fake-webp',
                )

            call_command(
                'import_poap_archive',
                archive_path,
                '--upload-artwork',
                verbosity=0,
            )

        drop = PoapDrop.objects.get(legacy_poap_id='456')
        self.assertEqual(PoapClaim.objects.filter(drop=drop).count(), 2)
        self.assertTrue(PoapClaim.objects.filter(drop=drop, legacy_wallet_address=first_wallet).exists())
        self.assertTrue(PoapClaim.objects.filter(drop=drop, legacy_wallet_address=second_wallet).exists())

    def test_poap_archive_import_accepts_claim_only_zip_for_existing_artwork(self):
        existing_drop = PoapDrop.objects.create(
            title='Existing Legacy Drop',
            slug='existing-legacy-drop',
            artwork_url='https://example.com/existing-poap.png',
            event_start_at=timezone.now(),
            status=PoapDrop.STATUS_ARCHIVED,
            legacy_poap_id='654',
        )
        wallet = '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
        matched_user = User.objects.create_user(
            email='claim-only@example.com',
            password='pass123',
            address=wallet,
        )
        csv_data = (
            'ens,email_address,ethereum_address\n'
            f'claim.eth,,{wallet}\n'
            ',email-only@example.com,\n'
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            archive_path = f'{temp_dir}/poaps.zip'
            with zipfile.ZipFile(archive_path, 'w') as archive:
                archive.writestr(
                    'poap.data/POAP_drop_654_collectors_2026-03-25_Existing Legacy Drop.csv',
                    csv_data,
                )

            call_command('import_poap_archive', archive_path, verbosity=0)
            call_command('import_poap_archive', archive_path, verbosity=0)

        existing_drop.refresh_from_db()
        self.assertEqual(existing_drop.artwork_url, 'https://example.com/existing-poap.png')
        self.assertTrue(PoapClaim.objects.filter(drop=existing_drop, user=matched_user).exists())
        self.assertTrue(PoapClaim.objects.filter(
            drop=existing_drop,
            user__isnull=True,
            legacy_email='email-only@example.com',
        ).exists())
        self.assertEqual(PoapClaim.objects.filter(drop=existing_drop).count(), 2)

    @patch('users.cloudinary_service.CloudinaryService.upload_image')
    def test_poap_archive_import_links_rows_for_previously_recovered_wallet(self, upload_image):
        upload_image.return_value = {
            'url': 'https://res.cloudinary.com/demo/image/upload/tally/poaps/poap-655.webp',
            'public_id': 'tally/poaps/poap_655',
        }
        recovered_wallet = '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'
        PoapClaim.objects.create(
            drop=self.drop,
            user=self.user,
            claim_method=PoapClaim.CLAIM_LEGACY,
            source=PoapClaim.SOURCE_LEGACY_IMPORT,
            legacy_wallet_address=recovered_wallet,
        )
        csv_data = (
            'ens,email_address,ethereum_address\n'
            f'recovered.eth,,{recovered_wallet}\n'
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            archive_path = f'{temp_dir}/poaps.zip'
            with zipfile.ZipFile(archive_path, 'w') as archive:
                archive.writestr(
                    'poap.data/POAP_drop_655_collectors_2026-03-25_Recovered Wallet Drop.csv',
                    csv_data,
                )
                archive.writestr(
                    'poap.data/poap_images/ID 655_Recovered Wallet Drop.webp',
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

        drop = PoapDrop.objects.get(legacy_poap_id='655')
        self.assertTrue(PoapClaim.objects.filter(
            drop=drop,
            user=self.user,
            legacy_wallet_address=recovered_wallet,
        ).exists())
        self.assertEqual(PoapClaim.objects.filter(drop=drop).count(), 1)

    def test_poap_archive_import_rejects_claim_only_zip_for_new_drop(self):
        csv_data = (
            'ens,email_address,ethereum_address\n'
            ',email-only@example.com,\n'
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            archive_path = f'{temp_dir}/poaps.zip'
            with zipfile.ZipFile(archive_path, 'w') as archive:
                archive.writestr(
                    'poap.data/POAP_drop_987_collectors_2026-03-25_New Drop.csv',
                    csv_data,
                )

            with self.assertRaisesMessage(
                CommandError,
                'POAP 987 has no image in the archive and no existing artwork.',
            ):
                call_command('import_poap_archive', archive_path, '--dry-run', verbosity=0)

    def test_poap_archive_import_requires_upload_artwork_for_new_drop_before_batch(self):
        csv_data = (
            'ens,email_address,ethereum_address\n'
            ',email-only@example.com,\n'
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            archive_path = f'{temp_dir}/poaps.zip'
            with zipfile.ZipFile(archive_path, 'w') as archive:
                archive.writestr(
                    'poap.data/POAP_drop_988_collectors_2026-03-25_New Drop With Image.csv',
                    csv_data,
                )
                archive.writestr(
                    'poap.data/poap_images/ID 988_New Drop With Image.webp',
                    b'fake-webp',
                )

            with self.assertRaisesMessage(
                CommandError,
                'Images are mandatory for new POAP drops. Pass --upload-artwork to upload badge images to Cloudinary.',
            ):
                call_command('import_poap_archive', archive_path, verbosity=0)

        self.assertFalse(PoapImportBatch.objects.exists())
        self.assertFalse(PoapDrop.objects.filter(legacy_poap_id='988').exists())

    @patch('users.cloudinary_service.CloudinaryService.upload_image')
    def test_poap_archive_import_skips_bad_rows_without_rolling_back_drop(self, upload_image):
        upload_image.return_value = {
            'url': 'https://res.cloudinary.com/demo/image/upload/tally/poaps/poap-789.webp',
            'public_id': 'tally/poaps/poap_789',
        }
        valid_wallet = '0x9999999999999999999999999999999999999999'
        overlong_wallet = '0x' + ('a' * 120)
        csv_data = (
            'email_address,ethereum_address\n'
            f'valid@example.com,{valid_wallet}\n'
            f'invalid@example.com,{overlong_wallet}\n'
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            archive_path = f'{temp_dir}/poaps.zip'
            with zipfile.ZipFile(archive_path, 'w') as archive:
                archive.writestr(
                    'poap.data/POAP_drop_789_collectors_2026-03-25 - Bad Row.csv',
                    csv_data,
                )
                archive.writestr(
                    'poap.data/poap_images/ID 789_Bad Row.webp',
                    b'fake-webp',
                )

            call_command(
                'import_poap_archive',
                archive_path,
                '--upload-artwork',
                verbosity=0,
            )

        drop = PoapDrop.objects.get(legacy_poap_id='789')
        batch = PoapImportBatch.objects.get(file_name=archive_path)
        self.assertEqual(PoapClaim.objects.filter(drop=drop).count(), 1)
        self.assertTrue(PoapClaim.objects.filter(drop=drop, legacy_wallet_address=valid_wallet).exists())
        self.assertEqual(batch.total_rows, 2)
        self.assertEqual(batch.imported_count, 1)
        self.assertEqual(batch.unmatched_count, 1)
        self.assertEqual(batch.error_count, 1)
