from django.test import TestCase

from contributions.models import EvidenceURLType
from contributions.url_utils import (
    normalize_url,
    detect_url_type,
    extract_handle,
    validate_handle_ownership,
    check_duplicate_url,
)


EVIDENCE_URL_TYPES = [
    {
        'name': 'X Post',
        'slug': 'x-post',
        'description': 'A post on X (formerly Twitter)',
        'url_patterns': [
            r'^https?://(www\.)?x\.com/[^/]+/status/\d+',
            r'^https?://(www\.)?twitter\.com/[^/]+/status/\d+',
        ],
        'is_generic': False,
        'order': 1,
        'handle_extract_pattern': r'(?:x|twitter)\.com/(?P<handle>[^/]+)/status/',
        'ownership_social_account': 'twitter',
    },
    {
        'name': 'GitHub Repository',
        'slug': 'github-repo',
        'description': 'A GitHub repository',
        'url_patterns': [
            r'^https?://github\.com/[^/]+/[^/]+/?$',
            r'^https?://github\.com/[^/]+/[^/]+/?#',
        ],
        'is_generic': False,
        'order': 2,
        'handle_extract_pattern': r'github\.com/(?P<handle>[^/]+)/',
        'ownership_social_account': 'github',
    },
    {
        'name': 'GitHub File',
        'slug': 'github-file',
        'description': 'A file in a GitHub repository',
        'url_patterns': [r'^https?://github\.com/[^/]+/[^/]+/blob/.+'],
        'is_generic': False,
        'order': 3,
        'handle_extract_pattern': r'github\.com/(?P<handle>[^/]+)/',
        'ownership_social_account': 'github',
    },
    {
        'name': 'GitHub Pull Request',
        'slug': 'github-pr',
        'description': 'A pull request on GitHub',
        'url_patterns': [r'^https?://github\.com/[^/]+/[^/]+/pull/\d+'],
        'is_generic': False,
        'order': 4,
        'handle_extract_pattern': '',
        'ownership_social_account': '',
    },
    {
        'name': 'GitHub Issue',
        'slug': 'github-issue',
        'description': 'An issue on GitHub',
        'url_patterns': [r'^https?://github\.com/[^/]+/[^/]+/issues/\d+'],
        'is_generic': False,
        'order': 5,
        'handle_extract_pattern': '',
        'ownership_social_account': '',
    },
    {
        'name': 'GenLayer Studio Contract',
        'slug': 'studio-contract',
        'description': 'A smart contract deployed on GenLayer Studio',
        'url_patterns': [
            r'^https?://studio\.genlayer\.com/contracts\?.*import-contract=0x[0-9a-fA-F]{40}',
        ],
        'is_generic': False,
        'order': 6,
        'handle_extract_pattern': '',
        'ownership_social_account': '',
    },
    {
        'name': 'Other',
        'slug': 'other',
        'description': 'Any URL that does not match a specific evidence type',
        'url_patterns': [],
        'is_generic': True,
        'order': 100,
        'handle_extract_pattern': '',
        'ownership_social_account': '',
    },
]


class EvidenceURLTypeSeededTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        for data in EVIDENCE_URL_TYPES:
            EvidenceURLType.objects.update_or_create(
                slug=data['slug'],
                defaults=data,
            )


class NormalizeUrlTests(TestCase):
    """Tests for URL normalization."""

    def test_strips_trailing_slash(self):
        self.assertEqual(
            normalize_url('https://github.com/user/repo/'),
            'https://github.com/user/repo',
        )

    def test_strips_fragment(self):
        self.assertEqual(
            normalize_url('https://github.com/user/repo#readme'),
            'https://github.com/user/repo',
        )

    def test_strips_tracking_params(self):
        self.assertEqual(
            normalize_url('https://example.com/post?utm_source=twitter&utm_medium=social'),
            'https://example.com/post',
        )

    def test_preserves_youtube_v_param(self):
        result = normalize_url('https://youtube.com/watch?v=abc123&utm_source=share')
        self.assertIn('v=abc123', result)
        self.assertNotIn('utm_source', result)

    def test_preserves_studio_import_contract(self):
        url = 'https://studio.genlayer.com/contracts?import-contract=0x1234'
        result = normalize_url(url)
        self.assertIn('import-contract=0x1234', result)

    def test_lowercases_import_contract_hex(self):
        """EVM addresses are case-insensitive (EIP-55 is just a checksum),
        so differently-cased contract addresses must collapse to the same
        normalized URL."""
        a = normalize_url(
            'https://studio.genlayer.com/contracts?import-contract=0xAbC123dEf456'
        )
        b = normalize_url(
            'https://studio.genlayer.com/contracts?import-contract=0xabc123def456'
        )
        self.assertEqual(a, b)
        self.assertIn('import-contract=0xabc123def456', a)

    def test_lowercases_host(self):
        result = normalize_url('https://GitHub.COM/User/Repo')
        self.assertTrue(result.startswith('https://github.com/'))

    def test_empty_url(self):
        self.assertEqual(normalize_url(''), '')

    def test_strips_ref_param(self):
        self.assertEqual(
            normalize_url('https://example.com/post?ref=homepage'),
            'https://example.com/post',
        )

    def test_lowercases_x_handle(self):
        """X/Twitter handles are case-insensitive; normalization should
        collapse differently-cased variants of the same post."""
        self.assertEqual(
            normalize_url('https://x.com/GenLayer/status/123'),
            normalize_url('https://x.com/genlayer/status/123'),
        )
        self.assertEqual(
            normalize_url('https://twitter.com/GenLayer/status/456'),
            'https://twitter.com/genlayer/status/456',
        )

    def test_lowercases_github_owner_repo(self):
        """GitHub owner/repo are case-insensitive; different casings of
        the same repo must collapse. Branch/path segments after the
        repo stay untouched."""
        self.assertEqual(
            normalize_url('https://github.com/GenLayer/Studio'),
            'https://github.com/genlayer/studio',
        )
        # Case-sensitive downstream segments (branches, blob SHAs, file
        # paths) must be preserved.
        self.assertEqual(
            normalize_url(
                'https://github.com/GenLayer/Studio/blob/AbC123/README.md'
            ),
            'https://github.com/genlayer/studio/blob/AbC123/README.md',
        )

    def test_preserves_youtube_v_param_case(self):
        """YouTube v= values are case-sensitive IDs; path-case
        normalization must not touch them."""
        result = normalize_url('https://www.youtube.com/watch?v=dQw4w9WgXcQ')
        self.assertIn('v=dQw4w9WgXcQ', result)


class DetectUrlTypeTests(EvidenceURLTypeSeededTestCase):
    """Tests for URL type auto-detection using seeded EvidenceURLType records."""

    def test_x_post_detected(self):
        result = detect_url_type('https://x.com/genlayer/status/123456789')
        self.assertIsNotNone(result)
        self.assertEqual(result.slug, 'x-post')

    def test_twitter_post_detected(self):
        result = detect_url_type('https://twitter.com/user/status/999')
        self.assertIsNotNone(result)
        self.assertEqual(result.slug, 'x-post')

    def test_medium_article_falls_through_to_generic(self):
        result = detect_url_type('https://medium.com/@user/my-article-abc123')
        self.assertIsNotNone(result)
        self.assertTrue(result.is_generic)

    def test_blog_falls_through_to_generic(self):
        result = detect_url_type('https://myblog.substack.com/p/my-post')
        self.assertIsNotNone(result)
        self.assertTrue(result.is_generic)

    def test_youtube_falls_through_to_generic(self):
        result = detect_url_type('https://www.youtube.com/watch?v=dQw4w9WgXcQ')
        self.assertIsNotNone(result)
        self.assertTrue(result.is_generic)

    def test_github_repo_detected(self):
        result = detect_url_type('https://github.com/genlayer/studio')
        self.assertIsNotNone(result)
        self.assertEqual(result.slug, 'github-repo')

    def test_github_file_detected(self):
        result = detect_url_type('https://github.com/user/repo/blob/main/README.md')
        self.assertIsNotNone(result)
        self.assertEqual(result.slug, 'github-file')

    def test_github_pr_detected(self):
        result = detect_url_type('https://github.com/genlayer/studio/pull/42')
        self.assertIsNotNone(result)
        self.assertEqual(result.slug, 'github-pr')

    def test_github_issue_detected(self):
        result = detect_url_type('https://github.com/genlayer/studio/issues/99')
        self.assertIsNotNone(result)
        self.assertEqual(result.slug, 'github-issue')

    def test_studio_contract_detected(self):
        url = 'https://studio.genlayer.com/contracts?import-contract=0x1234567890abcdef1234567890abcdef12345678'
        result = detect_url_type(url)
        self.assertIsNotNone(result)
        self.assertEqual(result.slug, 'studio-contract')

    def test_studio_contract_invalid_address_falls_through(self):
        url = 'https://studio.genlayer.com/contracts?import-contract=0xinvalid'
        result = detect_url_type(url)
        self.assertIsNotNone(result)
        self.assertTrue(result.is_generic)

    def test_unknown_url_returns_generic(self):
        result = detect_url_type('https://random-site.com/some-page')
        self.assertIsNotNone(result)
        self.assertTrue(result.is_generic)
        self.assertEqual(result.slug, 'other')


class ExtractHandleTests(EvidenceURLTypeSeededTestCase):
    """Tests for handle extraction from URLs."""

    def test_x_handle_extracted(self):
        url_type = EvidenceURLType.objects.get(slug='x-post')
        handle = extract_handle('https://x.com/genlayer/status/123', url_type)
        self.assertEqual(handle, 'genlayer')

    def test_github_handle_extracted(self):
        url_type = EvidenceURLType.objects.get(slug='github-repo')
        handle = extract_handle('https://github.com/MyUser/my-repo', url_type)
        self.assertEqual(handle, 'myuser')  # lowercased

    def test_no_pattern_returns_none(self):
        # github-pr is seeded without a handle_extract_pattern, so
        # extract_handle must short-circuit to None.
        url_type = EvidenceURLType.objects.get(slug='github-pr')
        handle = extract_handle(
            'https://github.com/user/repo/pull/42', url_type,
        )
        self.assertIsNone(handle)

    def test_github_file_handle(self):
        url_type = EvidenceURLType.objects.get(slug='github-file')
        handle = extract_handle(
            'https://github.com/JohnDoe/project/blob/main/src/app.py',
            url_type,
        )
        self.assertEqual(handle, 'johndoe')

    def test_x_intent_url_returns_none(self):
        """X 'intent' URLs (e.g. /i/status/...) use 'i' as a reserved
        segment rather than a real handle. extract_handle must return
        None so ownership validation is skipped."""
        url_type = EvidenceURLType.objects.get(slug='x-post')
        handle = extract_handle(
            'https://x.com/i/status/2020874480562659811', url_type,
        )
        self.assertIsNone(handle)


class ValidateHandleOwnershipTests(EvidenceURLTypeSeededTestCase):
    """Tests for handle ownership validation."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.user = User.objects.create_user(
            email='test@test.com',
            address='0x1234567890123456789012345678901234567890',
            password='testpass',
        )

    def test_no_social_account_configured_passes(self):
        url_type = EvidenceURLType.objects.get(slug='github-pr')
        result = validate_handle_ownership(
            'https://github.com/genlayer/studio/pull/42', url_type, self.user,
        )
        self.assertIsNone(result)

    def test_user_without_linked_account_fails(self):
        url_type = EvidenceURLType.objects.get(slug='x-post')
        result = validate_handle_ownership(
            'https://x.com/someone/status/123', url_type, self.user,
        )
        self.assertIsNotNone(result)
        self.assertIn('link your', result.lower())

    def test_matching_handle_passes(self):
        from social_connections.models import TwitterConnection
        TwitterConnection.objects.create(
            user=self.user,
            platform_user_id='12345',
            platform_username='myhandle',
            linked_at='2025-01-01T00:00:00Z',
        )
        url_type = EvidenceURLType.objects.get(slug='x-post')
        result = validate_handle_ownership(
            'https://x.com/myhandle/status/123', url_type, self.user,
        )
        self.assertIsNone(result)

    def test_mismatched_handle_fails(self):
        from social_connections.models import TwitterConnection
        TwitterConnection.objects.create(
            user=self.user,
            platform_user_id='12345',
            platform_username='myhandle',
            linked_at='2025-01-01T00:00:00Z',
        )
        url_type = EvidenceURLType.objects.get(slug='x-post')
        result = validate_handle_ownership(
            'https://x.com/someone_else/status/123', url_type, self.user,
        )
        self.assertIsNotNone(result)
        self.assertIn('someone_else', result)
        self.assertIn('myhandle', result)

    def test_github_matching_handle_passes(self):
        from social_connections.models import GitHubConnection
        GitHubConnection.objects.create(
            user=self.user,
            platform_user_id='99',
            platform_username='myghuser',
            linked_at='2025-01-01T00:00:00Z',
        )
        url_type = EvidenceURLType.objects.get(slug='github-repo')
        result = validate_handle_ownership(
            'https://github.com/myghuser/my-repo', url_type, self.user,
        )
        self.assertIsNone(result)

    def test_github_mismatched_handle_fails(self):
        from social_connections.models import GitHubConnection
        GitHubConnection.objects.create(
            user=self.user,
            platform_user_id='99',
            platform_username='myghuser',
            linked_at='2025-01-01T00:00:00Z',
        )
        url_type = EvidenceURLType.objects.get(slug='github-repo')
        result = validate_handle_ownership(
            'https://github.com/otheruser/their-repo', url_type, self.user,
        )
        self.assertIsNotNone(result)
        self.assertIn('otheruser', result)

    def test_x_intent_url_bypasses_ownership_check(self):
        """X intent URLs (/i/status/...) do not contain a real handle; the
        user should be allowed to submit them even when their linked X
        handle is different."""
        from social_connections.models import TwitterConnection
        TwitterConnection.objects.create(
            user=self.user,
            platform_user_id='12345',
            platform_username='myhandle',
            linked_at='2025-01-01T00:00:00Z',
        )
        url_type = EvidenceURLType.objects.get(slug='x-post')
        result = validate_handle_ownership(
            'https://x.com/i/status/2020874480562659811', url_type, self.user,
        )
        self.assertIsNone(result)


class CheckDuplicateUrlTests(EvidenceURLTypeSeededTestCase):
    """Tests for duplicate URL checking."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        from contributions.models import (
            Category, ContributionType, SubmittedContribution, Evidence,
        )
        from leaderboard.models import GlobalLeaderboardMultiplier
        from django.utils import timezone

        User = get_user_model()
        self.category = Category.objects.create(
            name='Test', slug='test', description='Test',
        )
        self.ctype = ContributionType.objects.create(
            name='Test', slug='test-type',
            category=self.category, min_points=1, max_points=100,
        )
        GlobalLeaderboardMultiplier.objects.create(
            contribution_type=self.ctype,
            multiplier_value=1,
            valid_from=timezone.now(),
        )
        self.user = User.objects.create_user(
            email='dup@test.com',
            address='0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
            password='testpass',
        )
        # Create a pending submission with a URL
        self.sub = SubmittedContribution.objects.create(
            user=self.user,
            contribution_type=self.ctype,
            contribution_date=timezone.now(),
            notes='test',
        )
        Evidence.objects.create(
            submitted_contribution=self.sub,
            url='https://github.com/user/repo',
            description='test evidence',
        )

    def test_duplicate_detected(self):
        result = check_duplicate_url('https://github.com/user/repo')
        self.assertIsNotNone(result)
        self.assertIn('already been submitted', result)

    def test_duplicate_with_tracking_params(self):
        result = check_duplicate_url('https://github.com/user/repo?utm_source=share')
        self.assertIsNotNone(result)

    def test_unique_url_passes(self):
        result = check_duplicate_url('https://github.com/other/different-repo')
        self.assertIsNone(result)

    def test_exclude_own_submission(self):
        result = check_duplicate_url(
            'https://github.com/user/repo',
            exclude_submission_id=self.sub.id,
        )
        self.assertIsNone(result)


class CheckDuplicateUrlAllowDuplicateTests(EvidenceURLTypeSeededTestCase):
    """Tests for the ``allow_duplicate`` exemption in ``check_duplicate_url``.

    The flag is admin-configurable (no data migration ships it on by default).
    Each test opts the relevant URL type into the exemption explicitly so
    the suite documents the behavior independently of admin state.
    """

    def setUp(self):
        from django.contrib.auth import get_user_model
        from contributions.models import (
            Category, ContributionType, SubmittedContribution, Evidence,
        )
        from leaderboard.models import GlobalLeaderboardMultiplier
        from django.utils import timezone

        User = get_user_model()
        self.category = Category.objects.create(
            name='Test', slug='test', description='Test',
        )
        self.ctype = ContributionType.objects.create(
            name='Test', slug='test-type',
            category=self.category, min_points=1, max_points=100,
        )
        GlobalLeaderboardMultiplier.objects.create(
            contribution_type=self.ctype,
            multiplier_value=1,
            valid_from=timezone.now(),
        )
        self.user = User.objects.create_user(
            email='allow-dup@test.com',
            address='0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
            password='testpass',
        )
        self.repo_url = 'https://github.com/genlayer/studio'
        # Opt the github-repo URL type into the duplicate-allowed flag.
        EvidenceURLType.objects.filter(slug='github-repo').update(
            allow_duplicate=True,
        )
        # Stored evidence on a pending submission for the same github repo.
        self.sub = SubmittedContribution.objects.create(
            user=self.user,
            contribution_type=self.ctype,
            contribution_date=timezone.now(),
            notes='test',
        )
        # Evidence.save() auto-detects url_type → github-repo.
        Evidence.objects.create(
            submitted_contribution=self.sub,
            url=self.repo_url,
            description='first repo submission',
        )

    def test_permissive_type_allows_duplicate_submission(self):
        """When the URL type is flagged permissive, a second submission of
        the same URL must NOT be flagged as duplicate."""
        result = check_duplicate_url(self.repo_url)
        self.assertIsNone(result)

    def test_non_permissive_type_still_strict(self):
        """github-pr is left strict in this test — the same PR URL twice
        must still reject, proving the exemption is per-type."""
        from contributions.models import Evidence
        pr_url = 'https://github.com/genlayer/studio/pull/42'
        Evidence.objects.create(
            submitted_contribution=self.sub,
            url=pr_url,
            description='pr evidence',
        )
        result = check_duplicate_url(pr_url)
        self.assertIsNotNone(result)

    def test_disabling_flag_re_enables_check(self):
        """Flipping ``allow_duplicate`` off restores strict duplicate
        detection — both for the incoming URL and stored evidence."""
        EvidenceURLType.objects.filter(slug='github-repo').update(
            allow_duplicate=False,
        )
        result = check_duplicate_url(self.repo_url)
        self.assertIsNotNone(result)
        self.assertIn('already been submitted', result)

    def test_stored_permissive_evidence_does_not_block_other_url(self):
        """Sanity check: a different repo URL still passes when a permissive
        URL is already stored (no spurious cross-URL blocking)."""
        result = check_duplicate_url('https://github.com/other/different')
        self.assertIsNone(result)

    def test_accepted_contribution_with_permissive_url_does_not_block(self):
        """An accepted contribution holding a permissive-type URL must not
        trigger duplicate rejection on a fresh submission of the same URL."""
        from contributions.models import Contribution, Evidence
        contribution = Contribution.objects.create(
            user=self.user,
            contribution_type=self.ctype,
            points=10,
            multiplier_at_creation=1,
            frozen_global_points=10,
        )
        Evidence.objects.create(
            contribution=contribution,
            url=self.repo_url,
            description='accepted repo evidence',
        )
        result = check_duplicate_url(self.repo_url)
        self.assertIsNone(result)


class CheckDuplicateUrlNullUrlTypeTests(EvidenceURLTypeSeededTestCase):
    """Legacy/null ``url_type`` rows must be handled correctly.

    Some historical evidence rows have ``url_type=None`` (e.g. before the
    type FK existed, or via paths that bypassed Evidence.save()). The
    duplicate check must still recognise their URL via ``detect_url_type``.
    """

    def setUp(self):
        from django.contrib.auth import get_user_model
        from contributions.models import (
            Category, ContributionType, SubmittedContribution, Evidence,
        )
        from leaderboard.models import GlobalLeaderboardMultiplier
        from django.utils import timezone

        User = get_user_model()
        self.category = Category.objects.create(
            name='T', slug='t-null', description='',
        )
        self.ctype = ContributionType.objects.create(
            name='T', slug='t-null-type',
            category=self.category, min_points=1, max_points=100,
        )
        GlobalLeaderboardMultiplier.objects.create(
            contribution_type=self.ctype,
            multiplier_value=1,
            valid_from=timezone.now(),
        )
        self.user = User.objects.create_user(
            email='null-type@test.com',
            address='0xcccccccccccccccccccccccccccccccccccccccc',
            password='testpass',
        )
        self.sub = SubmittedContribution.objects.create(
            user=self.user,
            contribution_type=self.ctype,
            contribution_date=timezone.now(),
            notes='legacy',
        )
        # Legacy-style evidence: url_type forcibly null after save().
        ev = Evidence.objects.create(
            submitted_contribution=self.sub,
            url='https://x.com/legacy/status/111',
            description='legacy evidence',
        )
        Evidence.objects.filter(pk=ev.pk).update(url_type=None)

    def test_null_typed_non_permissive_evidence_still_blocks_duplicate(self):
        """An X post URL stored with url_type=None must still trigger a
        duplicate rejection on the new submission side (the exclude filter
        keeps null-typed rows in the comparison set)."""
        result = check_duplicate_url('https://x.com/legacy/status/111')
        self.assertIsNotNone(result)
