from datetime import timedelta
from io import StringIO
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone

from contributions.models import (
    Category, ContributionType, Evidence,
    SubmittedContribution, SubmissionNote,
)
from contributions.management.commands.review_submissions import (
    TIER1_RULES,
    rule_no_evidence_no_notes,
    rule_no_evidence_short_notes,
    rule_spam_notes,
    rule_duplicate_pending_from_same_user,
    rule_resubmitted_rejected_url,
    rule_same_url_reused_by_same_user,
    rule_blocklisted_evidence_url,
    rule_cross_user_duplicate_url,
    rule_cross_user_identical_notes,
)
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


class RuleNoEvidenceNoNotesTest(Tier1RuleTestBase):
    """Test rule_no_evidence_no_notes."""

    def test_catches_empty_submission(self):
        sub = self._create_submission(notes='')
        result = rule_no_evidence_no_notes(sub, [])
        self.assertIsNotNone(result)
        self.assertEqual(result[0], 'Reject: No Evidence')

    def test_passes_with_notes(self):
        sub = self._create_submission(notes='I built something')
        result = rule_no_evidence_no_notes(sub, [])
        self.assertIsNone(result)

    def test_passes_with_evidence(self):
        sub = self._create_submission(notes='')
        ev = self._add_evidence(sub, url='https://github.com/test/repo')
        result = rule_no_evidence_no_notes(sub, [ev])
        self.assertIsNone(result)


class RuleNoEvidenceShortNotesTest(Tier1RuleTestBase):
    """Test rule_no_evidence_short_notes."""

    def test_catches_short_notes_no_evidence(self):
        sub = self._create_submission(notes='ok')
        result = rule_no_evidence_short_notes(sub, [])
        self.assertIsNotNone(result)
        self.assertEqual(result[0], 'Reject: No Evidence')

    def test_passes_longer_notes(self):
        sub = self._create_submission(notes='This is a longer note')
        result = rule_no_evidence_short_notes(sub, [])
        self.assertIsNone(result)

    def test_passes_with_evidence(self):
        sub = self._create_submission(notes='ok')
        ev = self._add_evidence(sub, url='https://example.com')
        result = rule_no_evidence_short_notes(sub, [ev])
        self.assertIsNone(result)

    def test_boundary_10_chars(self):
        sub = self._create_submission(notes='1234567890')
        result = rule_no_evidence_short_notes(sub, [])
        self.assertIsNotNone(result)

    def test_11_chars_passes(self):
        sub = self._create_submission(notes='12345678901')
        result = rule_no_evidence_short_notes(sub, [])
        self.assertIsNone(result)


class RuleSpamNotesTest(Tier1RuleTestBase):
    """Test rule_spam_notes."""

    def test_catches_spam_words(self):
        for word in ['good', 'hello', 'test', 'airdrop', 'nothing']:
            sub = self._create_submission(notes=word)
            result = rule_spam_notes(sub, [])
            self.assertIsNotNone(result, f'Should catch spam word: {word}')
            self.assertEqual(result[0], 'Reject: Unintelligible Notes')

    def test_catches_gibberish(self):
        sub = self._create_submission(notes='12345')
        result = rule_spam_notes(sub, [])
        self.assertIsNotNone(result)

    def test_catches_symbols(self):
        sub = self._create_submission(notes='!!!')
        result = rule_spam_notes(sub, [])
        self.assertIsNotNone(result)

    def test_passes_real_notes(self):
        sub = self._create_submission(
            notes='I built a smart contract for GenLayer',
        )
        result = rule_spam_notes(sub, [])
        self.assertIsNone(result)

    def test_case_insensitive(self):
        sub = self._create_submission(notes='GOOD')
        result = rule_spam_notes(sub, [])
        self.assertIsNotNone(result)


class RuleDuplicatePendingTest(Tier1RuleTestBase):
    """Test rule_duplicate_pending_from_same_user."""

    def test_catches_duplicate_notes_same_user(self):
        older = self._create_submission(
            notes='My project', created_at=timezone.now() - timedelta(days=2),
        )
        newer = self._create_submission(
            notes='My project', created_at=timezone.now(),
        )
        result = rule_duplicate_pending_from_same_user(newer, [])
        self.assertIsNotNone(result)
        self.assertEqual(result[0], 'Reject: Duplicate Submission')

    def test_keeps_older_submission(self):
        older = self._create_submission(
            notes='My project', created_at=timezone.now() - timedelta(days=2),
        )
        newer = self._create_submission(
            notes='My project', created_at=timezone.now(),
        )
        result = rule_duplicate_pending_from_same_user(older, [])
        self.assertIsNone(result)

    def test_different_notes_pass(self):
        self._create_submission(
            notes='Project A', created_at=timezone.now() - timedelta(days=2),
        )
        newer = self._create_submission(
            notes='Project B', created_at=timezone.now(),
        )
        result = rule_duplicate_pending_from_same_user(newer, [])
        self.assertIsNone(result)

    def test_different_user_passes(self):
        self._create_submission(
            user=self.other_user, notes='Same notes',
            created_at=timezone.now() - timedelta(days=2),
        )
        newer = self._create_submission(
            notes='Same notes', created_at=timezone.now(),
        )
        result = rule_duplicate_pending_from_same_user(newer, [])
        self.assertIsNone(result)

    def test_empty_notes_skipped(self):
        self._create_submission(
            notes='', created_at=timezone.now() - timedelta(days=2),
        )
        newer = self._create_submission(
            notes='', created_at=timezone.now(),
        )
        result = rule_duplicate_pending_from_same_user(newer, [])
        self.assertIsNone(result)


class RuleResubmittedRejectedUrlTest(Tier1RuleTestBase):
    """Test rule_resubmitted_rejected_url."""

    def test_catches_previously_rejected_url(self):
        rejected_sub = self._create_submission(
            notes='Old submission', state='rejected',
        )
        self._add_evidence(rejected_sub, url='https://example.com/my-post')

        new_sub = self._create_submission(notes='Resubmitting')
        ev = self._add_evidence(new_sub, url='https://example.com/my-post')

        result = rule_resubmitted_rejected_url(new_sub, [ev])
        self.assertIsNotNone(result)
        self.assertEqual(result[0], 'Reject: Duplicate Submission')

    def test_passes_new_url(self):
        rejected_sub = self._create_submission(
            notes='Old submission', state='rejected',
        )
        self._add_evidence(rejected_sub, url='https://example.com/old-post')

        new_sub = self._create_submission(notes='New content')
        ev = self._add_evidence(new_sub, url='https://example.com/new-post')

        result = rule_resubmitted_rejected_url(new_sub, [ev])
        self.assertIsNone(result)

    def test_different_user_passes(self):
        """URL rejected for another user is not caught by this rule."""
        rejected_sub = self._create_submission(
            user=self.other_user, notes='Their submission', state='rejected',
        )
        self._add_evidence(rejected_sub, url='https://example.com/post')

        new_sub = self._create_submission(notes='My submission')
        ev = self._add_evidence(new_sub, url='https://example.com/post')

        result = rule_resubmitted_rejected_url(new_sub, [ev])
        self.assertIsNone(result)

    def test_no_evidence_passes(self):
        sub = self._create_submission(notes='No evidence')
        result = rule_resubmitted_rejected_url(sub, [])
        self.assertIsNone(result)


class RuleSameUrlReusedTest(Tier1RuleTestBase):
    """Test rule_same_url_reused_by_same_user."""

    def test_catches_url_reuse(self):
        older = self._create_submission(
            notes='First use', created_at=timezone.now() - timedelta(days=1),
        )
        self._add_evidence(older, url='https://example.com/my-repo')

        newer = self._create_submission(
            notes='Second use', created_at=timezone.now(),
        )
        ev = self._add_evidence(newer, url='https://example.com/my-repo')

        result = rule_same_url_reused_by_same_user(newer, [ev])
        self.assertIsNotNone(result)
        self.assertEqual(result[0], 'Reject: Duplicate Submission')

    def test_older_submission_passes(self):
        older = self._create_submission(
            notes='First use', created_at=timezone.now() - timedelta(days=1),
        )
        ev_older = self._add_evidence(
            older, url='https://example.com/my-repo',
        )

        self._create_submission(
            notes='Second use', created_at=timezone.now(),
        )

        result = rule_same_url_reused_by_same_user(older, [ev_older])
        self.assertIsNone(result)


class RuleBlocklistedUrlTest(Tier1RuleTestBase):
    """Test rule_blocklisted_evidence_url."""

    def test_catches_studio_url(self):
        sub = self._create_submission(notes='My work')
        ev = self._add_evidence(
            sub, url='https://studio.genlayer.com/run-debug',
        )
        result = rule_blocklisted_evidence_url(sub, [ev])
        self.assertIsNotNone(result)
        self.assertEqual(result[0], 'Reject: No Evidence')

    def test_catches_points_url(self):
        sub = self._create_submission(notes='My work')
        ev = self._add_evidence(
            sub, url='https://points.genlayer.foundation/#/submit',
        )
        result = rule_blocklisted_evidence_url(sub, [ev])
        self.assertIsNotNone(result)

    def test_catches_studio_url_with_fragment(self):
        sub = self._create_submission(notes='My work')
        ev = self._add_evidence(
            sub, url='https://studio.genlayer.com/run-debug#something',
        )
        result = rule_blocklisted_evidence_url(sub, [ev])
        self.assertIsNotNone(result)

    def test_passes_real_evidence(self):
        sub = self._create_submission(notes='My work')
        ev = self._add_evidence(
            sub, url='https://github.com/user/genlayer-project',
        )
        result = rule_blocklisted_evidence_url(sub, [ev])
        self.assertIsNone(result)

    def test_passes_if_mixed_evidence(self):
        """If one URL is blocklisted but another is real, don't reject."""
        sub = self._create_submission(notes='My work')
        ev1 = self._add_evidence(
            sub, url='https://studio.genlayer.com/run-debug',
        )
        ev2 = self._add_evidence(
            sub, url='https://github.com/user/real-project',
        )
        result = rule_blocklisted_evidence_url(sub, [ev1, ev2])
        self.assertIsNone(result)


class RuleCrossUserDuplicateUrlTest(Tier1RuleTestBase):
    """Test rule_cross_user_duplicate_url."""

    def test_catches_cross_user_tweet(self):
        """Same tweet URL submitted by different users."""
        other_sub = self._create_submission(
            user=self.other_user, notes='My tweet',
        )
        self._add_evidence(
            other_sub, url='https://x.com/i/status/123456789',
        )

        my_sub = self._create_submission(notes='Also my tweet')
        ev = self._add_evidence(
            my_sub, url='https://x.com/i/status/123456789',
        )

        result = rule_cross_user_duplicate_url(my_sub, [ev])
        self.assertIsNotNone(result)
        self.assertEqual(result[0], 'Reject: Duplicate Submission')

    def test_github_repos_excluded(self):
        """GitHub repo URLs are excluded (can be forked legitimately)."""
        other_sub = self._create_submission(
            user=self.other_user, notes='My repo',
        )
        self._add_evidence(
            other_sub, url='https://github.com/other/genlayer-tool',
        )

        my_sub = self._create_submission(notes='My fork')
        ev = self._add_evidence(
            my_sub, url='https://github.com/other/genlayer-tool',
        )

        result = rule_cross_user_duplicate_url(my_sub, [ev])
        self.assertIsNone(result)

    def test_same_user_passes(self):
        """Same user reusing a URL is handled by another rule."""
        older = self._create_submission(
            notes='First', created_at=timezone.now() - timedelta(days=1),
        )
        self._add_evidence(
            older, url='https://x.com/i/status/123456789',
        )

        newer = self._create_submission(notes='Second')
        ev = self._add_evidence(
            newer, url='https://x.com/i/status/123456789',
        )

        result = rule_cross_user_duplicate_url(newer, [ev])
        self.assertIsNone(result)


class RuleCrossUserIdenticalNotesTest(Tier1RuleTestBase):
    """Test rule_cross_user_identical_notes."""

    def test_catches_farming_template(self):
        """Same long notes from different users."""
        long_notes = 'I shared GenLayer information on Telegram group for airdrop farming and community building.'
        self._create_submission(user=self.other_user, notes=long_notes)
        my_sub = self._create_submission(notes=long_notes)

        result = rule_cross_user_identical_notes(my_sub, [])
        self.assertIsNotNone(result)
        self.assertEqual(result[0], 'Reject: Duplicate Submission')

    def test_short_notes_ignored(self):
        """Notes <= 20 chars are not checked."""
        self._create_submission(user=self.other_user, notes='short note here')
        my_sub = self._create_submission(notes='short note here')

        result = rule_cross_user_identical_notes(my_sub, [])
        self.assertIsNone(result)

    def test_system_generated_ignored(self):
        """System-generated notes starting with 'Automatic submission' are skipped."""
        auto_notes = 'Automatic submission for node upgrade to version 1.2.3'
        self._create_submission(user=self.other_user, notes=auto_notes)
        my_sub = self._create_submission(notes=auto_notes)

        result = rule_cross_user_identical_notes(my_sub, [])
        self.assertIsNone(result)

    def test_same_user_passes(self):
        """Same user with identical notes handled by duplicate rule."""
        notes = 'A detailed description of my contribution to GenLayer ecosystem'
        self._create_submission(
            notes=notes, created_at=timezone.now() - timedelta(days=1),
        )
        newer = self._create_submission(notes=notes)

        result = rule_cross_user_identical_notes(newer, [])
        self.assertIsNone(result)


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

        # Create a review template so the command doesn't exit early
        ReviewTemplate.objects.create(
            label='Reject: No Evidence',
            text='Your submission lacks evidence.',
        )

    @patch('contributions.management.commands.review_submissions.call_openrouter')
    def test_auto_ban_spammer(self, mock_openrouter):
        """User with 5+ rejections and 0 acceptances gets auto-banned."""
        out = StringIO()
        call_command(
            'review_submissions', '--tier1-only', '--batch-size', '0',
            stdout=out,
        )
        self.spammer.refresh_from_db()
        self.assertTrue(self.spammer.is_banned)
        self.assertIn('6', self.spammer.ban_reason)  # mentions rejection count
        self.assertIsNotNone(self.spammer.banned_at)

    @patch('contributions.management.commands.review_submissions.call_openrouter')
    def test_no_ban_legit_user(self, mock_openrouter):
        """User with acceptances is not auto-banned."""
        out = StringIO()
        call_command(
            'review_submissions', '--tier1-only', '--batch-size', '0',
            stdout=out,
        )
        self.legit_user.refresh_from_db()
        self.assertFalse(self.legit_user.is_banned)

    @patch('contributions.management.commands.review_submissions.call_openrouter')
    def test_no_ban_below_threshold(self, mock_openrouter):
        """User with <5 rejections is not auto-banned."""
        out = StringIO()
        call_command(
            'review_submissions', '--tier1-only', '--batch-size', '0',
            stdout=out,
        )
        self.borderline_user.refresh_from_db()
        self.assertFalse(self.borderline_user.is_banned)

    @patch('contributions.management.commands.review_submissions.call_openrouter')
    def test_dry_run_no_ban(self, mock_openrouter):
        """Dry run does not actually ban users."""
        out = StringIO()
        call_command(
            'review_submissions', '--tier1-only', '--dry-run',
            '--batch-size', '0', stdout=out,
        )
        self.spammer.refresh_from_db()
        self.assertFalse(self.spammer.is_banned)
        self.assertIn('auto-ban', out.getvalue().lower())

    @patch('contributions.management.commands.review_submissions.call_openrouter')
    def test_already_banned_not_rebanned(self, mock_openrouter):
        """Already-banned user is not processed again."""
        self.spammer.is_banned = True
        self.spammer.ban_reason = 'Already banned'
        self.spammer.save()

        out = StringIO()
        call_command(
            'review_submissions', '--tier1-only', '--batch-size', '0',
            stdout=out,
        )
        self.spammer.refresh_from_db()
        # ban_reason should not be overwritten
        self.assertEqual(self.spammer.ban_reason, 'Already banned')
