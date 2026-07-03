"""
Tests for the public Grafana roster endpoint (/validators/wallets/grafana/),
focused on the `identity_missing` setup flag consumed by the Wall of Shame
dashboard's Identity column.
"""

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from users.models import User
from validators.models import Validator, ValidatorWallet


class GrafanaRosterIdentityMissingTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='alice@example.com',
            password='pass',
            address='0xAAAAaaaaAAAAaaaaAAAAaaaaAAAAaaaaAAAAaaaa',
            name='Alice',
            visible=True,
        )
        self.operator = Validator.objects.create(user=self.user)

    def _get_rows(self):
        response = self.client.get('/api/v1/validators/wallets/grafana/?network=asimov')
        self.assertEqual(response.status_code, 200)
        return {row['node']: row for row in response.data}

    def test_complete_identity_yields_empty_string(self):
        ValidatorWallet.objects.create(
            address='0x1111111111111111111111111111111111111111',
            network='asimov',
            operator=self.operator,
            operator_address='0x2222222222222222222222222222222222222222',
            status='active',
            moniker='alice-node',
            logo_uri='https://example.com/logo.png',
            description='A well set up validator.',
        )
        rows = self._get_rows()
        row = rows['0x1111111111111111111111111111111111111111']
        self.assertEqual(row['identity_missing'], '')

    def test_missing_pieces_are_listed(self):
        ValidatorWallet.objects.create(
            address='0x3333333333333333333333333333333333333333',
            network='asimov',
            operator=self.operator,
            operator_address='0x2222222222222222222222222222222222222222',
            status='active',
            moniker='alice-node-2',
            logo_uri='',
            description='',
        )
        rows = self._get_rows()
        row = rows['0x3333333333333333333333333333333333333333']
        self.assertEqual(row['identity_missing'], 'logo,description')

    def test_unlinked_wallet_flags_portal(self):
        ValidatorWallet.objects.create(
            address='0x4444444444444444444444444444444444444444',
            network='asimov',
            operator=None,
            operator_address='0x5555555555555555555555555555555555555555',
            status='active',
        )
        rows = self._get_rows()
        row = rows['0x4444444444444444444444444444444444444444']
        self.assertEqual(row['identity_missing'], 'moniker,logo,description,portal')

    def test_linked_but_invisible_operator_does_not_flag_portal(self):
        # Non-visible operators hide account/account_name, but the wallet IS
        # linked — identity_missing must not report a missing portal link.
        invisible_user = User.objects.create_user(
            email='bob@example.com',
            password='pass',
            address='0xBBBBbbbbBBBBbbbbBBBBbbbbBBBBbbbbBBBBbbbb',
            name='Bob',
            visible=False,
        )
        invisible_operator = Validator.objects.create(user=invisible_user)
        ValidatorWallet.objects.create(
            address='0x6666666666666666666666666666666666666666',
            network='asimov',
            operator=invisible_operator,
            operator_address='0x7777777777777777777777777777777777777777',
            status='active',
            moniker='bob-node',
            logo_uri='https://example.com/bob.png',
            description='Runs on both testnets.',
        )
        rows = self._get_rows()
        row = rows['0x6666666666666666666666666666666666666666']
        self.assertIsNone(row['account'])
        self.assertEqual(row['identity_missing'], '')
