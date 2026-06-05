from collections import defaultdict
from io import StringIO

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone
from rest_framework import serializers as drf_serializers

from contributions.models import (
    Category, Contribution, ContributionType, Evidence,
    SubmittedContribution,
)
from contributions.management.commands.review_submissions import (
    _normalize_url,
    rule_no_evidence_url,
    rule_blocklisted_url,
    rule_duplicate_evidence_url,
)
from contributions.serializers import SubmittedContributionSerializer
from leaderboard.models import GlobalLeaderboardMultiplier
from stewards.models import ReviewTemplate

User = get_user_model()


class Tier1RuleTestBase(TestCase):
    """Base class with shared setup for Tier 1 rule tests."""

    def setUp(self):
        self.category = Category.objects.create(
            name='Test', slug='test', description='Test',
        )
        self.ctype = ContributionType.objects.create(
            name='Test Type', slug='test-type',
            description='Test', category=self.category,
            min_points=1, max_points=100,
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
        self.other_user = User.objects.create_user(
            email='other@test.com',
            address='0x0987654321098765432109876543210987654321',
            password='testpass123',
        )

    def _create_submission(self, user=None, notes='', state='pending',
                           created_at=None):
        sub = SubmittedContribution.objects.create(
            user=user or self.user,
            contribution_type=self.ctype,
            contribution_date=timezone.now(),
            notes=notes,
            state=state,
        )
        if created_at:
            SubmittedContribution.objects.filter(id=sub.id).update(
                created_at=created_at,
            )
            sub.refresh_from_db()
        return sub

    def _add_evidence(self, submission, url='', description=''):
        return Evidence.objects.create(
            submitted_contribution=submission,
            url=url,
            description=description,
        )


class RuleNoEvidenceUrlTest(Tier1RuleTestBase):
    """Test rule_no_evidence_url."""

    def test_rejects_no_evidence(self):
        sub = self._create_submission(notes='Some notes')
        result = rule_no_evidence_url(sub, [])
        self.assertIsNotNone(result)
        self.assertEqual(result[0], 'Reject: No Evidence')

    def test_rejects_evidence_with_empty_url(self):
        sub = self._create_submission(notes='Some notes')
        ev = self._add_evidence(sub, url='', description='A description')
        result = rule_no_evidence_url(sub, [ev])
        self.assertIsNotNone(result)
        self.assertEqual(result[0], 'Reject: No Evidence')

    def test_passes_with_url(self):
        sub = self._create_submission(notes='My project')
        ev = self._add_evidence(sub, url='https://github.com/test/repo')
        result = rule_no_evidence_url(sub, [ev])
        self.assertIsNone(result)

    def test_passes_with_one_valid_url_among_empty(self):
        sub = self._create_submission(notes='My project')
        ev1 = self._add_evidence(sub, url='')
        ev2 = self._add_evidence(sub, url='https://example.com/work')
        result = rule_no_evidence_url(sub, [ev1, ev2])
        self.assertIsNone(result)


class RuleBlocklistedUrlTest(Tier1RuleTestBase):
    """Test rule_blocklisted_url."""

    BLOCKLIST = [
        'https://points.genlayer.foundation',
        'https://www.genlayer.com',
        'https://genlayer.com',
    ]

    def test_catches_points_url(self):
        sub = self._create_submission(notes='My work')
        ev = self._add_evidence(
            sub, url='https://points.genlayer.foundation/#/submit',
        )
        result = rule_blocklisted_url(sub, [ev], self.BLOCKLIST)
        self.assertIsNotNone(result)
        self.assertEqual(result[0], 'Reject: Invalid Evidence URL')

    def test_catches_genlayer_com(self):
        sub = self._create_submission(notes='My work')
        ev = self._add_evidence(sub, url='https://genlayer.com')
        result = rule_blocklisted_url(sub, [ev], self.BLOCKLIST)
        self.assertIsNotNone(result)

    def test_allows_studio_url(self):
        """studio.genlayer.com is a valid evidence URL."""
        sub = self._create_submission(notes='My work')
        ev = self._add_evidence(
            sub, url='https://studio.genlayer.com/run-debug',
        )
        result = rule_blocklisted_url(sub, [ev], self.BLOCKLIST)
        self.assertIsNone(result)

    def test_passes_real_evidence(self):
        sub = self._create_submission(notes='My work')
        ev = self._add_evidence(
            sub, url='https://github.com/user/genlayer-project',
        )
        result = rule_blocklisted_url(sub, [ev], self.BLOCKLIST)
        self.assertIsNone(result)

    def test_passes_if_mixed_evidence(self):
        """If one URL is blocklisted but another is real, don't reject."""
        sub = self._create_submission(notes='My work')
        ev1 = self._add_evidence(
            sub, url='https://points.genlayer.foundation/#/submit',
        )
        ev2 = self._add_evidence(
            sub, url='https://github.com/user/real-project',
        )
        result = rule_blocklisted_url(sub, [ev1, ev2], self.BLOCKLIST)
        self.assertIsNone(result)

    def test_no_url_evidence_returns_none(self):
        """No URLs means handled by rule_no_evidence_url, not this rule."""
        sub = self._create_submission(notes='My work')
        ev = self._add_evidence(sub, url='', description='text only')
        result = rule_blocklisted_url(sub, [ev], self.BLOCKLIST)
        self.assertIsNone(result)


class RuleDuplicateEvidenceUrlTest(Tier1RuleTestBase):
    """Test rule_duplicate_evidence_url."""

    def _build_lookup(self):
        """Build the URL lookup from current DB state (with normalization)."""
        submitted = (
            Evidence.objects
            .filter(
                submitted_contribution__state__in=['pending', 'accepted'],
                url__gt='',
            )
            .values_list('url', 'submitted_contribution_id')
        )
        url_to_sub_ids = defaultdict(set)
        for url, sub_id in submitted:
            url_to_sub_ids[_normalize_url(url)].add(sub_id)

        accepted_urls = set(
            _normalize_url(url) for url in
            Evidence.objects
            .filter(contribution__isnull=False, url__gt='')
            .values_list('url', flat=True)
        )
        return url_to_sub_ids, accepted_urls

    def test_catches_url_in_another_pending_submission(self):
        """URL already used in another user's pending submission."""
        other_sub = self._create_submission(
            user=self.other_user, notes='Their work',
        )
        self._add_evidence(other_sub, url='https://example.com/post')

        my_sub = self._create_submission(notes='My work')
        ev = self._add_evidence(my_sub, url='https://example.com/post')

        url_lookup, accepted_urls = self._build_lookup()
        result = rule_duplicate_evidence_url(
            my_sub, [ev], url_lookup, accepted_urls,
        )
        self.assertIsNotNone(result)
        self.assertEqual(result[0], 'Reject: Duplicate Submission')

    def test_catches_url_in_accepted_contribution(self):
        """URL exists in a converted/accepted contribution."""
        contribution = Contribution.objects.create(
            user=self.other_user,
            contribution_type=self.ctype,
            points=5,
        )
        Evidence.objects.create(
            contribution=contribution,
            url='https://example.com/accepted-work',
        )

        my_sub = self._create_submission(notes='My work')
        ev = self._add_evidence(my_sub, url='https://example.com/accepted-work')

        url_lookup, accepted_urls = self._build_lookup()
        result = rule_duplicate_evidence_url(
            my_sub, [ev], url_lookup, accepted_urls,
        )
        self.assertIsNotNone(result)
        self.assertIn('accepted contribution', result[1])

    def test_self_exclusion(self):
        """Submission's own URL should not trigger duplicate detection."""
        sub = self._create_submission(notes='My unique work')
        ev = self._add_evidence(sub, url='https://example.com/unique')

        url_lookup, accepted_urls = self._build_lookup()
        result = rule_duplicate_evidence_url(
            sub, [ev], url_lookup, accepted_urls,
        )
        self.assertIsNone(result)

    def test_passes_unique_url(self):
        """URL not used anywhere else passes."""
        other_sub = self._create_submission(
            user=self.other_user, notes='Their work',
        )
        self._add_evidence(other_sub, url='https://example.com/their-post')

        my_sub = self._create_submission(notes='My work')
        ev = self._add_evidence(my_sub, url='https://example.com/my-post')

        url_lookup, accepted_urls = self._build_lookup()
        result = rule_duplicate_evidence_url(
            my_sub, [ev], url_lookup, accepted_urls,
        )
        self.assertIsNone(result)

    def test_catches_same_user_duplicate_url(self):
        """Same user submitting same URL in two pending submissions."""
        older = self._create_submission(notes='First submission')
        self._add_evidence(older, url='https://example.com/my-repo')

        newer = self._create_submission(notes='Second submission')
        ev = self._add_evidence(newer, url='https://example.com/my-repo')

        url_lookup, accepted_urls = self._build_lookup()
        result = rule_duplicate_evidence_url(
            newer, [ev], url_lookup, accepted_urls,
        )
        self.assertIsNotNone(result)
        self.assertEqual(result[0], 'Reject: Duplicate Submission')

    def test_passes_if_at_least_one_url_unique(self):
        """Submission with one duplicate and one unique URL should pass."""
        other_sub = self._create_submission(
            user=self.other_user, notes='Their work',
        )
        self._add_evidence(other_sub, url='https://example.com/shared')

        my_sub = self._create_submission(notes='My work')
        ev1 = self._add_evidence(my_sub, url='https://example.com/shared')
        ev2 = self._add_evidence(my_sub, url='https://example.com/unique')

        url_lookup, accepted_urls = self._build_lookup()
        result = rule_duplicate_evidence_url(
            my_sub, [ev1, ev2], url_lookup, accepted_urls,
        )
        self.assertIsNone(result)

    def test_rejects_when_all_urls_are_duplicates(self):
        """Submission where ALL URLs are duplicates should be rejected."""
        other_sub = self._create_submission(
            user=self.other_user, notes='Their work',
        )
        self._add_evidence(other_sub, url='https://example.com/post-a')
        self._add_evidence(other_sub, url='https://example.com/post-b')

        my_sub = self._create_submission(notes='My work')
        ev1 = self._add_evidence(my_sub, url='https://example.com/post-a')
        ev2 = self._add_evidence(my_sub, url='https://example.com/post-b')

        url_lookup, accepted_urls = self._build_lookup()
        result = rule_duplicate_evidence_url(
            my_sub, [ev1, ev2], url_lookup, accepted_urls,
        )
        self.assertIsNotNone(result)
        self.assertEqual(result[0], 'Reject: Duplicate Submission')

    def test_no_evidence_passes(self):
        """Submission with no evidence is not checked."""
        sub = self._create_submission(notes='No evidence')
        url_lookup, accepted_urls = self._build_lookup()
        result = rule_duplicate_evidence_url(
            sub, [], url_lookup, accepted_urls,
        )
        self.assertIsNone(result)

    def test_rejected_submissions_not_in_lookup(self):
        """URLs from rejected submissions should not count as duplicates."""
        rejected_sub = self._create_submission(
            user=self.other_user, notes='Rejected', state='rejected',
        )
        self._add_evidence(rejected_sub, url='https://example.com/post')

        my_sub = self._create_submission(notes='My work')
        ev = self._add_evidence(my_sub, url='https://example.com/post')

        url_lookup, accepted_urls = self._build_lookup()
        result = rule_duplicate_evidence_url(
            my_sub, [ev], url_lookup, accepted_urls,
        )
        self.assertIsNone(result)

    def test_skip_pending_still_catches_accepted(self):
        """skip_pending=True skips pending lookup but still catches accepted."""
        contribution = Contribution.objects.create(
            user=self.other_user,
            contribution_type=self.ctype,
            points=5,
        )
        Evidence.objects.create(
            contribution=contribution,
            url='https://example.com/accepted-work',
        )

        my_sub = self._create_submission(notes='My work')
        ev = self._add_evidence(my_sub, url='https://example.com/accepted-work')

        url_lookup, accepted_urls = self._build_lookup()
        result = rule_duplicate_evidence_url(
            my_sub, [ev], url_lookup, accepted_urls, skip_pending=True,
        )
        self.assertIsNotNone(result)
        self.assertIn('accepted contribution', result[1])

    def test_skip_pending_rejects_when_older_duplicate_exists(self):
        """Targeted runs should still reject against an older duplicate."""
        older_sub = self._create_submission(notes='Older submission')
        self._add_evidence(older_sub, url='https://example.com/post')

        newer_sub = self._create_submission(
            user=self.other_user, notes='Newer submission',
        )
        ev = self._add_evidence(newer_sub, url='https://example.com/post')

        url_lookup, accepted_urls = self._build_lookup()
        created_at_lookup = {
            older_sub.id: older_sub.created_at,
            newer_sub.id: newer_sub.created_at,
        }
        result = rule_duplicate_evidence_url(
            newer_sub, [ev], url_lookup, accepted_urls, skip_pending=True,
            submitted_created_at=created_at_lookup,
        )
        self.assertIsNotNone(result)
        self.assertIn('older submission', result[1])

    def test_skip_pending_allows_oldest_submission(self):
        """Targeted runs should keep the oldest submission as the survivor."""
        oldest_sub = self._create_submission(notes='Oldest submission')
        ev = self._add_evidence(oldest_sub, url='https://example.com/post')

        newer_sub = self._create_submission(
            user=self.other_user, notes='Newer submission',
        )
        self._add_evidence(newer_sub, url='https://example.com/post')

        url_lookup, accepted_urls = self._build_lookup()
        created_at_lookup = {
            oldest_sub.id: oldest_sub.created_at,
            newer_sub.id: newer_sub.created_at,
        }
        result = rule_duplicate_evidence_url(
            oldest_sub, [ev], url_lookup, accepted_urls, skip_pending=True,
            submitted_created_at=created_at_lookup,
        )
        self.assertIsNone(result)

    def test_newer_duplicate_plus_unique_url_does_not_reject_older_original(self):
        """A newer duplicate must not cause the older original to fail."""
        original = self._create_submission(notes='Original submission')
        original_shared = self._add_evidence(
            original,
            url='https://example.com/shared',
        )
        original_unique = self._add_evidence(
            original,
            url='https://example.com/original-unique',
        )

        newer = self._create_submission(
            user=self.other_user,
            notes='Newer duplicate',
        )
        newer_shared = self._add_evidence(newer, url='https://example.com/shared')

        url_lookup, accepted_urls = self._build_lookup()

        original_result = rule_duplicate_evidence_url(
            original,
            [original_shared, original_unique],
            url_lookup,
            accepted_urls,
        )
        newer_result = rule_duplicate_evidence_url(
            newer,
            [newer_shared],
            url_lookup,
            accepted_urls,
        )

        self.assertIsNone(original_result)
        self.assertIsNotNone(newer_result)


class RuleDuplicateUrlNormalizationTest(Tier1RuleTestBase):
    """Test that URL normalization catches cosmetic variants."""

    def test_trailing_slash_detected(self):
        """URL with trailing slash matches one without."""
        other_sub = self._create_submission(
            user=self.other_user, notes='Their work',
        )
        self._add_evidence(other_sub, url='https://example.com/post')

        my_sub = self._create_submission(notes='My work')
        ev = self._add_evidence(my_sub, url='https://example.com/post/')

        url_lookup, accepted_urls = RuleDuplicateEvidenceUrlTest._build_lookup(
            self,
        )
        result = rule_duplicate_evidence_url(
            my_sub, [ev], url_lookup, accepted_urls,
        )
        self.assertIsNotNone(result)
        self.assertEqual(result[0], 'Reject: Duplicate Submission')

    def test_query_params_detected(self):
        """URL with query params matches one without."""
        other_sub = self._create_submission(
            user=self.other_user, notes='Their work',
        )
        self._add_evidence(other_sub, url='https://example.com/post')

        my_sub = self._create_submission(notes='My work')
        ev = self._add_evidence(
            my_sub, url='https://example.com/post?utm_source=twitter',
        )

        url_lookup, accepted_urls = RuleDuplicateEvidenceUrlTest._build_lookup(
            self,
        )
        result = rule_duplicate_evidence_url(
            my_sub, [ev], url_lookup, accepted_urls,
        )
        self.assertIsNotNone(result)

    def test_fragment_detected(self):
        """URL with fragment matches one without."""
        other_sub = self._create_submission(
            user=self.other_user, notes='Their work',
        )
        self._add_evidence(other_sub, url='https://example.com/post')

        my_sub = self._create_submission(notes='My work')
        ev = self._add_evidence(
            my_sub, url='https://example.com/post#section-2',
        )

        url_lookup, accepted_urls = RuleDuplicateEvidenceUrlTest._build_lookup(
            self,
        )
        result = rule_duplicate_evidence_url(
            my_sub, [ev], url_lookup, accepted_urls,
        )
        self.assertIsNotNone(result)

    def test_normalize_url_helper(self):
        """_normalize_url strips query, fragment, and trailing slash."""
        self.assertEqual(
            _normalize_url('https://example.com/post?utm_source=x'),
            'https://example.com/post',
        )
        self.assertEqual(
            _normalize_url('https://example.com/post#sec'),
            'https://example.com/post',
        )
        self.assertEqual(
            _normalize_url('https://example.com/post/'),
            'https://example.com/post',
        )
        self.assertEqual(
            _normalize_url('https://example.com/post/?utm_source=x#sec'),
            'https://example.com/post',
        )


class AutoBanTest(TestCase):
    """Test the auto-ban functionality in the review_submissions command."""

    def setUp(self):
        self.category = Category.objects.create(
            name='Test', slug='test', description='Test',
        )
        self.ctype = ContributionType.objects.create(
            name='Test Type', slug='test-type',
            description='Test', category=self.category,
            min_points=1, max_points=100,
        )
        # Create a user with many rejections
        self.spammer = User.objects.create_user(
            email='spammer@test.com',
            address='0x1234567890123456789012345678901234567890',
            password='testpass123',
        )
        for i in range(6):
            SubmittedContribution.objects.create(
                user=self.spammer,
                contribution_type=self.ctype,
                contribution_date=timezone.now(),
                notes=f'Spam submission {i}',
                state='rejected',
            )

        # Create a legitimate user with some rejections but also acceptances
        self.legit_user = User.objects.create_user(
            email='legit@test.com',
            address='0x0987654321098765432109876543210987654321',
            password='testpass123',
        )
        for i in range(3):
            SubmittedContribution.objects.create(
                user=self.legit_user,
                contribution_type=self.ctype,
                contribution_date=timezone.now(),
                notes=f'Rejected {i}',
                state='rejected',
            )
        SubmittedContribution.objects.create(
            user=self.legit_user,
            contribution_type=self.ctype,
            contribution_date=timezone.now(),
            notes='Accepted one',
            state='accepted',
        )

        # Create a user with exactly 4 rejections (below threshold)
        self.borderline_user = User.objects.create_user(
            email='borderline@test.com',
            address='0x1111111111111111111111111111111111111111',
            password='testpass123',
        )
        for i in range(4):
            SubmittedContribution.objects.create(
                user=self.borderline_user,
                contribution_type=self.ctype,
                contribution_date=timezone.now(),
                notes=f'Rejected {i}',
                state='rejected',
            )

        # Create review templates so the command doesn't exit early
        ReviewTemplate.objects.create(
            label='Reject: No Evidence',
            text='No evidence URL provided.',
            action='reject',
        )
        ReviewTemplate.objects.create(
            label='Reject: Duplicate Submission',
            text='Duplicate evidence URL.',
            action='reject',
        )
        ReviewTemplate.objects.create(
            label='Reject: Invalid Evidence URL',
            text='Invalid evidence URL.',
            action='reject',
        )

    def test_auto_ban_spammer(self):
        """User with 5+ rejections and 0 acceptances gets auto-banned."""
        out = StringIO()
        call_command('review_submissions', '--batch-size', '0', stdout=out)
        self.spammer.refresh_from_db()
        self.assertTrue(self.spammer.is_banned)
        self.assertIn('6', self.spammer.ban_reason)
        self.assertIsNotNone(self.spammer.banned_at)

    def test_no_ban_legit_user(self):
        """User with acceptances is not auto-banned."""
        out = StringIO()
        call_command('review_submissions', '--batch-size', '0', stdout=out)
        self.legit_user.refresh_from_db()
        self.assertFalse(self.legit_user.is_banned)

    def test_no_ban_below_threshold(self):
        """User with <5 rejections is not auto-banned."""
        out = StringIO()
        call_command('review_submissions', '--batch-size', '0', stdout=out)
        self.borderline_user.refresh_from_db()
        self.assertFalse(self.borderline_user.is_banned)

    def test_dry_run_no_ban(self):
        """Dry run does not actually ban users."""
        out = StringIO()
        call_command(
            'review_submissions', '--dry-run', '--batch-size', '0',
            stdout=out,
        )
        self.spammer.refresh_from_db()
        self.assertFalse(self.spammer.is_banned)
        self.assertIn('auto-ban', out.getvalue().lower())

    def test_already_banned_not_rebanned(self):
        """Already-banned user is not processed again."""
        self.spammer.is_banned = True
        self.spammer.ban_reason = 'Already banned'
        self.spammer.save()

        out = StringIO()
        call_command('review_submissions', '--batch-size', '0', stdout=out)
        self.spammer.refresh_from_db()
        self.assertEqual(self.spammer.ban_reason, 'Already banned')


class ActiveProposalSkipTest(TestCase):
    """Tier 1 should not overwrite active proposal state."""

    def setUp(self):
        self.category = Category.objects.create(
            name='Test', slug='test', description='Test',
        )
        self.ctype = ContributionType.objects.create(
            name='Test Type', slug='test-type',
            description='Test', category=self.category,
            min_points=1, max_points=100,
        )
        self.user = User.objects.create_user(
            email='user@test.com',
            address='0x1234567890123456789012345678901234567890',
            password='testpass123',
        )
        self.proposer = User.objects.create_user(
            email='proposer@test.com',
            address='0x0987654321098765432109876543210987654321',
            password='testpass123',
        )
        self.submission = SubmittedContribution.objects.create(
            user=self.user,
            contribution_type=self.ctype,
            contribution_date=timezone.now(),
            notes='Missing evidence but already proposed',
            state='pending',
            proposed_action='reject',
            proposed_staff_reply='Existing proposal',
            proposed_by=self.proposer,
            proposed_at=timezone.now(),
        )
        ReviewTemplate.objects.create(
            label='Reject: No Evidence',
            text='No evidence URL provided.',
            action='reject',
        )
        ReviewTemplate.objects.create(
            label='Reject: Duplicate Submission',
            text='Duplicate evidence URL.',
            action='reject',
        )
        ReviewTemplate.objects.create(
            label='Reject: Invalid Evidence URL',
            text='Invalid evidence URL.',
            action='reject',
        )

    def test_command_skips_submission_with_active_proposal(self):
        out = StringIO()
        call_command('review_submissions', '--batch-size', '0', stdout=out)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.state, 'pending')
        self.assertEqual(self.submission.proposed_action, 'reject')
        self.assertEqual(self.submission.proposed_by, self.proposer)


class SubmissionIdDuplicateDeterminismTest(Tier1RuleTestBase):
    """Targeted review runs should keep duplicate handling deterministic."""

    def setUp(self):
        super().setUp()
        ReviewTemplate.objects.create(
            label='Reject: No Evidence',
            text='No evidence URL provided.',
            action='reject',
        )
        ReviewTemplate.objects.create(
            label='Reject: Duplicate Submission',
            text='Duplicate evidence URL.',
            action='reject',
        )
        ReviewTemplate.objects.create(
            label='Reject: Invalid Evidence URL',
            text='Invalid evidence URL.',
            action='reject',
        )

    def test_submission_id_rejects_newer_duplicate(self):
        older_sub = self._create_submission(notes='Older submission')
        self._add_evidence(older_sub, url='https://example.com/post')

        newer_sub = self._create_submission(
            user=self.other_user, notes='Newer submission',
        )
        self._add_evidence(newer_sub, url='https://example.com/post')

        out = StringIO()
        call_command(
            'review_submissions',
            '--submission-id', str(newer_sub.id),
            '--batch-size', '0',
            stdout=out,
        )

        newer_sub.refresh_from_db()
        self.assertEqual(newer_sub.state, 'rejected')

    def test_submission_id_keeps_oldest_duplicate(self):
        oldest_sub = self._create_submission(notes='Oldest submission')
        self._add_evidence(oldest_sub, url='https://example.com/post')

        newer_sub = self._create_submission(
            user=self.other_user, notes='Newer submission',
        )
        self._add_evidence(newer_sub, url='https://example.com/post')

        out = StringIO()
        call_command(
            'review_submissions',
            '--submission-id', str(oldest_sub.id),
            '--batch-size', '0',
            stdout=out,
        )

        oldest_sub.refresh_from_db()
        self.assertEqual(oldest_sub.state, 'pending')
        self.assertEqual(newer_sub.state, 'pending')


class SubmittedContributionSerializerUpdateTest(TestCase):
    """Update flow should validate evidence before persisting changes."""

    def setUp(self):
        self.category = Category.objects.create(
            name='Test', slug='test', description='Test',
        )
        self.ctype = ContributionType.objects.create(
            name='Test Type', slug='test-type',
            description='Test', category=self.category,
            min_points=1, max_points=100,
        )
        self.user = User.objects.create_user(
            email='user@test.com',
            address='0x1234567890123456789012345678901234567890',
            password='testpass123',
        )
        self.submission = SubmittedContribution.objects.create(
            user=self.user,
            contribution_type=self.ctype,
            contribution_date=timezone.now(),
            notes='Original notes',
            state='pending',
        )
        self.evidence = Evidence.objects.create(
            submitted_contribution=self.submission,
            description='Original evidence',
            url='https://example.com/work',
        )

    def test_update_rejects_empty_evidence_list_without_saving_changes(self):
        serializer = SubmittedContributionSerializer(
            self.submission,
            data={
                'notes': 'Changed notes',
                'evidence_items': [],
            },
            partial=True,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

        with self.assertRaises(drf_serializers.ValidationError):
            serializer.save()

        self.submission.refresh_from_db()
        self.assertEqual(self.submission.notes, 'Original notes')
        self.assertEqual(self.submission.evidence_items.count(), 1)

    def test_update_requires_at_least_one_evidence_item(self):
        serializer = SubmittedContributionSerializer(
            self.submission,
            data={
                'evidence_items': [],
            },
            partial=True,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

        with self.assertRaises(drf_serializers.ValidationError) as ctx:
            serializer.save()

        self.assertIn('evidence_items', ctx.exception.detail)

    def test_update_rejects_unknown_evidence_id_without_saving_changes(self):
        serializer = SubmittedContributionSerializer(
            self.submission,
            data={
                'notes': 'Changed notes',
                'evidence_items': [
                    {
                        'id': self.evidence.id + 999,
                        'description': 'Replacement evidence',
                        'url': 'https://example.com/replacement',
                    },
                ],
            },
            partial=True,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

        with self.assertRaises(drf_serializers.ValidationError):
            serializer.save()

        self.submission.refresh_from_db()
        self.assertEqual(self.submission.notes, 'Original notes')
        self.assertEqual(self.submission.evidence_items.count(), 1)


class RuleDuplicateUrlAllowDuplicateTest(Tier1RuleTestBase):
    """Tests for ``allow_duplicate`` exemption in ``rule_duplicate_evidence_url``.

    The flag is admin-configurable (no data migration). ``setUp`` flips
    github-repo into permissive mode so the exemption can be exercised.
    Covers (a) lookup-time exclusion of permissive evidence,
    (b) per-URL short-circuit when the new evidence's url_type is permissive,
    (c) fallback to ``detect_url_type`` when ``url_type`` is null on the new
    evidence, and (d) that other URL types still get rejected normally.
    """

    REPO_URL = 'https://github.com/genlayer/studio'
    PR_URL = 'https://github.com/genlayer/studio/pull/42'

    def setUp(self):
        super().setUp()
        from contributions.models import EvidenceURLType
        EvidenceURLType.objects.update_or_create(
            slug='github-repo',
            defaults={
                'name': 'GitHub Repository',
                'description': 'A GitHub repository',
                'url_patterns': [
                    r'^https?://github\.com/[^/]+/[^/]+/?$',
                    r'^https?://github\.com/[^/]+/[^/]+/?#',
                ],
                'is_generic': False,
                'order': 2,
                'handle_extract_pattern': r'github\.com/(?P<handle>[^/]+)/',
                'ownership_social_account': 'github',
                'allow_duplicate': True,
            },
        )
        EvidenceURLType.objects.update_or_create(
            slug='github-pr',
            defaults={
                'name': 'GitHub Pull Request',
                'description': 'A pull request on GitHub',
                'url_patterns': [
                    r'^https?://github\.com/[^/]+/[^/]+/pull/\d+',
                ],
                'is_generic': False,
                'order': 4,
                'handle_extract_pattern': '',
                'ownership_social_account': '',
                'allow_duplicate': False,
            },
        )

    def _build_lookup(self):
        from contributions.management.commands.review_submissions import Command
        return Command()._build_url_lookup()

    def test_permissive_evidence_excluded_from_lookup(self):
        """Stored evidence with ``url_type.allow_duplicate=True`` must be
        absent from ``url_to_sub_ids`` so subsequent submissions of the
        same URL do not even see a candidate match."""
        sub = self._create_submission()
        self._add_evidence(sub, url=self.REPO_URL)
        url_to_sub_ids, accepted_urls, _ = self._build_lookup()
        self.assertNotIn(_normalize_url(self.REPO_URL), url_to_sub_ids)
        self.assertNotIn(_normalize_url(self.REPO_URL), accepted_urls)

    def test_non_permissive_evidence_still_in_lookup(self):
        """A github-pr URL is not duplicate-allowed and must still appear
        in the lookup (control case)."""
        sub = self._create_submission()
        self._add_evidence(sub, url=self.PR_URL)
        url_to_sub_ids, _, _ = self._build_lookup()
        self.assertIn(_normalize_url(self.PR_URL), url_to_sub_ids)

    def test_duplicate_repo_url_passes_review(self):
        """Two pending submissions of the same github-repo URL must both
        pass the duplicate rule (because the URL type allows duplicates)."""
        first = self._create_submission(
            created_at=timezone.now() - timezone.timedelta(hours=2),
        )
        self._add_evidence(first, url=self.REPO_URL)
        second = self._create_submission(user=self.other_user)
        ev2 = self._add_evidence(second, url=self.REPO_URL)
        url_to_sub_ids, accepted_urls, created_at = self._build_lookup()
        result = rule_duplicate_evidence_url(
            second, [ev2], url_to_sub_ids, accepted_urls,
            submitted_created_at=created_at,
        )
        self.assertIsNone(result)

    def test_duplicate_pr_url_still_rejects(self):
        """github-pr is not permissive — duplicate must still reject so
        that the exemption is truly per-type, not blanket-github."""
        first = self._create_submission(
            created_at=timezone.now() - timezone.timedelta(hours=2),
        )
        self._add_evidence(first, url=self.PR_URL)
        second = self._create_submission(user=self.other_user)
        ev2 = self._add_evidence(second, url=self.PR_URL)
        url_to_sub_ids, accepted_urls, created_at = self._build_lookup()
        result = rule_duplicate_evidence_url(
            second, [ev2], url_to_sub_ids, accepted_urls,
            submitted_created_at=created_at,
        )
        self.assertIsNotNone(result)

    def test_null_url_type_falls_back_to_detect(self):
        """When the new submission's evidence has ``url_type=None`` (legacy
        or bulk-created without it), the rule must fall back to
        ``detect_url_type(evidence.url)`` and recognise permissive URLs."""
        # Existing pending repo evidence (correctly excluded from lookup
        # because its detected url_type is permissive).
        first = self._create_submission(
            created_at=timezone.now() - timezone.timedelta(hours=2),
        )
        self._add_evidence(first, url=self.REPO_URL)

        # New submission whose evidence row has no url_type FK.
        second = self._create_submission(user=self.other_user)
        ev2 = self._add_evidence(second, url=self.REPO_URL)
        Evidence.objects.filter(pk=ev2.pk).update(url_type=None)
        ev2.refresh_from_db()

        url_to_sub_ids, accepted_urls, created_at = self._build_lookup()
        result = rule_duplicate_evidence_url(
            second, [ev2], url_to_sub_ids, accepted_urls,
            submitted_created_at=created_at,
        )
        self.assertIsNone(result)

    def test_accepted_contribution_evidence_preserves_url_type(self):
        """When a submission is accepted, copied Evidence rows on the
        Contribution must carry both ``url_type`` and ``normalized_url``
        — bulk_create skips Evidence.save(), so the view must populate
        them explicitly. Without this, accepted evidence with a permissive
        type would silently degrade to null and bypass the lookup-time
        exclusion."""
        from contributions.url_utils import normalize_url
        sub = self._create_submission()
        ev = self._add_evidence(sub, url=self.REPO_URL)
        # Sanity: source evidence has detected url_type and normalized_url.
        self.assertIsNotNone(ev.url_type_id)
        self.assertEqual(ev.normalized_url, normalize_url(self.REPO_URL))

        # Mimic the views.py accept flow for evidence copying.
        contribution = Contribution.objects.create(
            user=sub.user,
            contribution_type=sub.contribution_type,
            points=10,
            multiplier_at_creation=1,
            frozen_global_points=10,
        )
        Evidence.objects.bulk_create([
            Evidence(
                contribution=contribution,
                description=ev.description,
                url=ev.url,
                file=ev.file,
                url_type=ev.url_type,
                normalized_url=ev.normalized_url,
            )
        ])

        copied = Evidence.objects.get(contribution=contribution)
        self.assertEqual(copied.url_type_id, ev.url_type_id)
        self.assertEqual(copied.normalized_url, normalize_url(self.REPO_URL))
