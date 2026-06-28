"""Tests for required_evidence_url_type_groups (AND across groups, OR within)."""

from unittest.mock import MagicMock

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers as drf_serializers

from contributions.models import Category, ContributionType, EvidenceURLType
from contributions.serializers import SubmittedContributionSerializer
from leaderboard.models import GlobalLeaderboardMultiplier

User = get_user_model()

ADDR = '0x' + '0' * 40
EXPLORER_URL = f'https://explorer-asimov.genlayer.com/address/{ADDR}'
STUDIO_URL = f'https://studio.genlayer.com/contracts?import-contract={ADDR}'
GITHUB_URL = 'https://github.com/foo/bar'


class RequiredEvidenceURLTypeGroupsTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Test', slug='test')
        self.ctype = ContributionType.objects.create(
            name='Intelligent Contracts', slug='intelligent-contracts',
            category=self.category, min_points=1, max_points=100,
        )
        GlobalLeaderboardMultiplier.objects.create(
            contribution_type=self.ctype, multiplier_value=1,
            valid_from=timezone.now(),
        )
        self.user = User.objects.create_user(
            email='user@test.com',
            address='0x1234567890123456789012345678901234567890',
            password='testpass123',
        )
        # update_or_create by slug: migrations 0050/0075 already seed these
        # rows in the test DB, so plain create() collides on the unique name.
        EvidenceURLType.objects.update_or_create(slug='github-repo', defaults=dict(
            name='GitHub Repository',
            url_patterns=[r'^https?://github\.com/[^/]+/[^/]+/?$'],
            is_generic=False, order=1, ownership_social_account='',
        ))
        EvidenceURLType.objects.update_or_create(slug='studio-contract', defaults=dict(
            name='GenLayer Studio Contract',
            url_patterns=[r'^https?://studio\.genlayer\.com/contracts\?(?:[^#]*&)?import-contract=0x[0-9a-fA-F]{40}\b'],
            is_generic=False, order=2,
        ))
        EvidenceURLType.objects.update_or_create(slug='genlayer-explorer-contract', defaults=dict(
            name='GenLayer Explorer Contract',
            url_patterns=[r'^https?://explorer[.-][a-z0-9.-]+\.genlayer\.com/address/0x[0-9a-fA-F]{40}\b'],
            is_generic=False, order=3,
        ))
        EvidenceURLType.objects.update_or_create(slug='other', defaults=dict(
            name='Other', url_patterns=[], is_generic=True, order=99,
        ))

        self.ctype.required_evidence_url_type_groups = [
            ['studio-contract', 'github-repo'],
            ['genlayer-explorer-contract'],
        ]
        self.ctype.save()

        request = MagicMock()
        request.user = self.user
        self.serializer = SubmittedContributionSerializer(
            context={'request': request}
        )

    def _validate(self, items):
        return self.serializer._validate_evidence_items(
            items, require_at_least_one=True,
            contribution_type=self.ctype, user=self.user,
        )

    def test_code_link_without_explorer_rejected(self):
        with self.assertRaises(drf_serializers.ValidationError) as cm:
            self._validate([{'url': GITHUB_URL, 'description': 'Repo'}])
        self.assertIn('genlayer-explorer-contract', str(cm.exception.detail))

    def test_explorer_without_code_link_rejected(self):
        with self.assertRaises(drf_serializers.ValidationError) as cm:
            self._validate([{'url': EXPLORER_URL, 'description': 'Deployed'}])
        self.assertIn('studio-contract', str(cm.exception.detail))

    def test_studio_plus_explorer_accepted(self):
        result = self._validate([
            {'url': STUDIO_URL, 'description': 'Code'},
            {'url': EXPLORER_URL, 'description': 'Deployed'},
        ])
        self.assertEqual(len(result), 2)

    def test_github_plus_explorer_accepted(self):
        result = self._validate([
            {'url': GITHUB_URL, 'description': 'Code'},
            {'url': EXPLORER_URL, 'description': 'Deployed'},
        ])
        self.assertEqual(len(result), 2)

    def test_no_groups_means_no_group_check(self):
        self.ctype.required_evidence_url_type_groups = []
        self.ctype.save()
        result = self._validate([{'url': GITHUB_URL, 'description': 'Repo'}])
        self.assertEqual(len(result), 1)

    def test_grouped_types_implicitly_accepted_with_whitelist(self):
        """A non-empty accepted whitelist must not reject grouped URLs that
        aren't explicitly listed in it."""
        other = EvidenceURLType.objects.get(slug='other')
        self.ctype.accepted_evidence_url_types.set([other])  # whitelist excludes group types
        result = self._validate([
            {'url': GITHUB_URL, 'description': 'Code'},
            {'url': EXPLORER_URL, 'description': 'Deployed'},
        ])
        self.assertEqual(len(result), 2)
