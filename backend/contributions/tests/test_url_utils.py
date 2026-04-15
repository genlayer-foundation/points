from django.test import TestCase

from contributions.models import EvidenceURLType
from contributions.url_utils import (
    normalize_url,
    detect_url_type,
    extract_handle,
    validate_handle_ownership,
    check_duplicate_url,
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


class DetectUrlTypeTests(TestCase):
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


class ExtractHandleTests(TestCase):
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
        url_type = EvidenceURLType.objects.get(slug='youtube-video')
        handle = extract_handle('https://youtube.com/watch?v=abc', url_type)
        self.assertIsNone(handle)

    def test_github_file_handle(self):
        url_type = EvidenceURLType.objects.get(slug='github-file')
        handle = extract_handle(
            'https://github.com/JohnDoe/project/blob/main/src/app.py',
            url_type,
        )
        self.assertEqual(handle, 'johndoe')


class ValidateHandleOwnershipTests(TestCase):
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


class CheckDuplicateUrlTests(TestCase):
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
