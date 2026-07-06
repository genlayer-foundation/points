"""
Tests for the synthetic `status='missing'` rows on the public Grafana roster
endpoint (/validators/wallets/grafana/): graduated portal validators with no
wallet linked on a network must still get one row per network, so the Wall of
Shame dashboard can surface them.
"""

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from users.models import User
from users.utils import truncate_address
from validators.models import Validator, ValidatorWallet


class GrafanaRosterMissingValidatorTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.alice = User.objects.create_user(
            email='alice@example.com',
            password='pass',
            address='0xAAAAaaaaAAAAaaaaAAAAaaaaAAAAaaaaAAAAaaaa',
            name='Alice',
            visible=True,
        )
        self.alice_operator = Validator.objects.create(user=self.alice)

    def _rows(self, network=None):
        url = '/api/v1/validators/wallets/grafana/'
        if network:
            url += f'?network={network}'
        cache.clear()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        return response.data

    def _missing_accounts(self, rows):
        return {row['account'] for row in rows if row['status'] == 'missing'}

    def _truncated(self, user):
        return truncate_address(user.address.lower())

    def test_graduated_without_wallet_gets_missing_row(self):
        rows = self._rows('bradbury')
        missing = [row for row in rows if row['status'] == 'missing']
        self.assertEqual(len(missing), 1)
        row = missing[0]
        # Account addresses are truncated on public surfaces; the join key is
        # a synthetic user-<id> value that matches no metric series.
        self.assertEqual(row['account'], truncate_address(self.alice.address.lower()))
        self.assertEqual(row['node'], f'user-{self.alice.id}')
        self.assertEqual(row['name'], 'Alice')
        self.assertEqual(row['account_name'], 'Alice')
        self.assertIsNone(row['operator'])
        self.assertEqual(row['network'], 'bradbury-phase1')

    def test_linked_wallet_suppresses_missing_row_on_that_network_only(self):
        ValidatorWallet.objects.create(
            address='0x1111111111111111111111111111111111111111',
            network='asimov',
            operator=self.alice_operator,
            operator_address='0x2222222222222222222222222222222222222222',
            status='active',
        )
        self.assertNotIn(
            self._truncated(self.alice),
            self._missing_accounts(self._rows('asimov')),
        )
        self.assertIn(
            self._truncated(self.alice),
            self._missing_accounts(self._rows('bradbury')),
        )

    def test_inactive_wallet_still_counts_as_present(self):
        # A fully-inactive operator already shows as an `inactive` roster row;
        # adding a `missing` row too would double-represent the same account.
        ValidatorWallet.objects.create(
            address='0x1111111111111111111111111111111111111111',
            network='asimov',
            operator=self.alice_operator,
            operator_address='0x2222222222222222222222222222222222222222',
            status='inactive',
        )
        self.assertNotIn(
            self._truncated(self.alice),
            self._missing_accounts(self._rows('asimov')),
        )

    def test_unlinked_wallet_does_not_count_as_present(self):
        # A wallet with no operator link can't be attributed to Alice — she is
        # still `missing` (outreach: link the wallet or spin up a node).
        ValidatorWallet.objects.create(
            address='0x1111111111111111111111111111111111111111',
            network='asimov',
            operator=None,
            operator_address='0x2222222222222222222222222222222222222222',
            status='active',
        )
        self.assertIn(
            self._truncated(self.alice),
            self._missing_accounts(self._rows('asimov')),
        )

    def test_non_visible_graduated_user_is_skipped(self):
        bob = User.objects.create_user(
            email='bob@example.com',
            password='pass',
            address='0xBBBBbbbbBBBBbbbbBBBBbbbbBBBBbbbbBBBBbbbb',
            name='Bob',
            visible=False,
        )
        Validator.objects.create(user=bob)
        self.assertNotIn(
            self._truncated(bob),
            self._missing_accounts(self._rows('asimov')),
        )

    def test_unfiltered_response_carries_missing_rows_for_every_network(self):
        rows = self._rows()
        networks = {
            row['network'] for row in rows
            if row['status'] == 'missing'
            and row['account'] == self._truncated(self.alice)
        }
        self.assertEqual(networks, {'asimov-phase5', 'bradbury-phase1'})
