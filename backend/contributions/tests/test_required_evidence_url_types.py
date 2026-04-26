"""Tests for required_evidence_url_types enforcement during submission."""

from unittest.mock import MagicMock

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers as drf_serializers

from contributions.models import (
    Category, ContributionType, EvidenceURLType,
)
from contributions.serializers import SubmittedContributionSerializer
from leaderboard.models import GlobalLeaderboardMultiplier

User = get_user_model()


class RequiredEvidenceURLTypesTest(TestCase):
    """Exercise _validate_evidence_items with required_evidence_url_types set."""

    def setUp(self):
        self.category = Category.objects.create(
            name='Test', slug='test', description='Test',
        )
        self.ctype = ContributionType.objects.create(
            name='Projecting Milestone',
            slug='projecting-milestone',
            description='Test',
            category=self.category,
            min_points=1,
            max_points=100,
        )
        GlobalLeaderboardMultiplier.objects.create(
            contribution_type=self.ctype,
            multiplier_value=1,
            valid_from=timezone.now(),
        )
        self.user = User.objects.create_user(
            email='user@test.com',
            address='0x1234567890123456789012345678901234567890',
            password='testpass123',
        )

        self.github_repo_type = EvidenceURLType.objects.create(
            name='GitHub Repository',
            slug='github-repo',
            url_patterns=[r'^https?://github\.com/[^/]+/[^/]+/?$'],
            is_generic=False,
            order=1,
        )
        self.studio_type = EvidenceURLType.objects.create(
            name='Studio Contract',
            slug='studio-contract',
            url_patterns=[r'^https?://studio\.genlayer\.com/'],
            is_generic=False,
            order=2,
        )
        self.other_type = EvidenceURLType.objects.create(
            name='Other',
            slug='other',
            url_patterns=[],
            is_generic=True,
            order=99,
        )

        self.ctype.required_evidence_url_types.set(
            [self.github_repo_type, self.studio_type]
        )

        # Build a serializer instance with a minimal request context
        request = MagicMock()
        request.user = self.user
        self.serializer = SubmittedContributionSerializer(
            context={'request': request}
        )

    def _validate(self, items):
        return self.serializer._validate_evidence_items(
            items,
            require_at_least_one=True,
            contribution_type=self.ctype,
            user=self.user,
        )

    def test_rejects_submission_missing_required_type(self):
        """A submission with only a generic/unrelated URL is rejected."""
        with self.assertRaises(drf_serializers.ValidationError) as cm:
            self._validate([
                {'url': 'https://example.com/blog/post', 'description': 'Blog'},
            ])
        msg = str(cm.exception.detail)
        self.assertIn('GitHub Repository', msg)
        self.assertIn('Studio Contract', msg)

    def test_accepts_submission_with_one_required_type(self):
        """A single URL matching any required type satisfies the requirement."""
        result = self._validate([
            {'url': 'https://github.com/foo/bar', 'description': 'Repo'},
        ])
        self.assertEqual(len(result), 1)

    def test_required_types_are_implicitly_accepted(self):
        """Required types pass the type-mismatch check even when
        accepted_evidence_url_types is also set to a different list."""
        extra_type = EvidenceURLType.objects.create(
            name='Blog', slug='blog', url_patterns=[], is_generic=False,
            order=3,
        )
        self.ctype.accepted_evidence_url_types.set([extra_type])

        # Required type URL should still pass even though not in the accepted list
        result = self._validate([
            {'url': 'https://github.com/foo/bar', 'description': 'Repo'},
        ])
        self.assertEqual(len(result), 1)

    def test_extra_urls_allowed_on_top_of_required(self):
        """Additional non-required URLs are accepted when one required URL is present."""
        result = self._validate([
            {'url': 'https://github.com/foo/bar', 'description': 'Repo'},
            {
                'url': 'https://studio.genlayer.com/contract/abc',
                'description': 'Deployed contract',
            },
        ])
        self.assertEqual(len(result), 2)

    def test_no_required_types_means_no_extra_check(self):
        """When no required types are configured, submissions with any URL pass."""
        self.ctype.required_evidence_url_types.clear()
        result = self._validate([
            {'url': 'https://example.com/some/link', 'description': 'Other'},
        ])
        self.assertEqual(len(result), 1)

    def test_generic_url_rejected_when_accepted_list_set(self):
        """When accepted_evidence_url_types is an explicit whitelist,
        URLs that detect as the generic 'Other' type must not bypass it;
        otherwise any unrecognized URL would slip through."""
        self.ctype.required_evidence_url_types.clear()
        self.ctype.accepted_evidence_url_types.set([self.github_repo_type])
        with self.assertRaises(drf_serializers.ValidationError):
            self._validate([
                {'url': 'https://random-blog.com/post', 'description': 'Blog'},
            ])

    def test_generic_url_allowed_when_other_in_accepted_list(self):
        """Admins can opt in to generic URLs by adding the 'Other' type
        to accepted_evidence_url_types."""
        self.ctype.required_evidence_url_types.clear()
        self.ctype.accepted_evidence_url_types.set(
            [self.github_repo_type, self.other_type]
        )
        result = self._validate([
            {'url': 'https://random-blog.com/post', 'description': 'Blog'},
        ])
        self.assertEqual(len(result), 1)

    def test_required_without_accepted_leaves_extras_unrestricted(self):
        """Empty accepted_evidence_url_types must keep meaning 'all types
        accepted' even when required_evidence_url_types is set. Adding a
        required type should not retroactively restrict which other URL
        types a user can attach."""
        self.ctype.accepted_evidence_url_types.clear()
        # required set retained from setUp: github-repo + studio-contract

        # Arbitrary extra URL type alongside a required match should pass.
        result = self._validate([
            {'url': 'https://github.com/foo/bar', 'description': 'Repo'},
            {'url': 'https://example.com/my-blog', 'description': 'Blog'},
        ])
        self.assertEqual(len(result), 2)

        # But the at-least-one-required rule still fires.
        with self.assertRaises(drf_serializers.ValidationError):
            self._validate([
                {'url': 'https://example.com/my-blog', 'description': 'Blog'},
            ])
