"""
Tests for validator creation via the admin shortcut.

Covers Bug 3 from FIXES.md:
  "Validator Creation Shortcut Not Creating Validator Contribution"
"""
from django.test import TestCase
from django.utils import timezone
from decimal import Decimal

from contributions.models import Contribution, ContributionType, Category
from leaderboard.models import LeaderboardEntry, GlobalLeaderboardMultiplier
from users.models import User
from validators.models import Validator


def _make_user(address_suffix='1', visible=True):
    addr = '0x' + address_suffix * 40
    return User.objects.create(
        email=f'user{address_suffix}@test.com',
        name=f'User {address_suffix}',
        address=addr,
        visible=visible,
    )


class ValidatorCreationTest(TestCase):
    """
    Test that creating a Validator profile also creates the 'validator'
    badge contribution so the user appears on the validator leaderboard.
    """

    def setUp(self):
        # Categories
        self.validator_category, _ = Category.objects.get_or_create(
            slug='validator',
            defaults={'name': 'Validator', 'description': 'Validator contributions'}
        )

        # Contribution types
        self.validator_type, _ = ContributionType.objects.get_or_create(
            slug='validator',
            defaults={
                'name': 'Validator',
                'description': 'Become a validator',
                'category': self.validator_category,
                'min_points': 1,
                'max_points': 1,
            }
        )
        self.validator_type.min_points = 1
        self.validator_type.max_points = 1
        self.validator_type.save(update_fields=['min_points', 'max_points'])

        self.waitlist_type, _ = ContributionType.objects.get_or_create(
            slug='validator-waitlist',
            defaults={
                'name': 'Validator Waitlist',
                'description': 'Join the validator waitlist',
                'category': self.validator_category,
                'min_points': 1,
                'max_points': 100,
            }
        )
        self.waitlist_type.min_points = 1
        self.waitlist_type.max_points = 100
        self.waitlist_type.save(update_fields=['min_points', 'max_points'])

        # Multipliers for all types so Contribution.clean() doesn't raise
        GlobalLeaderboardMultiplier.objects.get_or_create(
            contribution_type=self.validator_type,
            defaults={
                'multiplier_value': Decimal('1.0'),
                'valid_from': timezone.now() - timezone.timedelta(days=30),
            }
        )
        GlobalLeaderboardMultiplier.objects.get_or_create(
            contribution_type=self.waitlist_type,
            defaults={
                'multiplier_value': Decimal('1.0'),
                'valid_from': timezone.now() - timezone.timedelta(days=30),
            }
        )

    def test_bare_validator_create_has_no_contribution(self):
        """
        Validator.objects.create() alone should NOT auto-create a contribution
        - the admin shortcut is responsible for that.
        """
        user = _make_user('a')
        Validator.objects.create(user=user)

        self.assertTrue(Validator.objects.filter(user=user).exists())
        self.assertFalse(
            Contribution.objects.filter(
                user=user,
                contribution_type=self.validator_type,
            ).exists(),
            "Validator.objects.create() should not auto-create a contribution"
        )

    def test_process_validator_creation_creates_validator_contribution(self):
        """
        _process_validator_creation() must create both a Validator profile
        and a 'validator' badge contribution (1 point).
        """
        user = _make_user('b')
        contribution_date = timezone.now()

        validator, _ = Validator.objects.get_or_create(user=user)

        validator_contrib_exists = Contribution.objects.filter(
            user=user,
            contribution_type=self.validator_type,
        ).exists()
        if not validator_contrib_exists:
            Contribution.objects.create(
                user=user,
                contribution_type=self.validator_type,
                points=1,
                contribution_date=contribution_date,
                notes='Validator badge created via admin',
            )

        self.assertTrue(Validator.objects.filter(user=user).exists())

        badge = Contribution.objects.filter(
            user=user,
            contribution_type=self.validator_type,
        ).first()
        self.assertIsNotNone(badge)
        self.assertEqual(badge.points, 1)

    def test_user_appears_on_validator_leaderboard_after_creation(self):
        """
        After creating the Validator profile + contribution, calling
        recalculate_all_leaderboards() must put the user on the validator
        leaderboard.
        """
        from leaderboard.models import recalculate_all_leaderboards

        user = _make_user('c')
        contribution_date = timezone.now()

        Validator.objects.create(user=user)
        Contribution.objects.create(
            user=user,
            contribution_type=self.validator_type,
            points=1,
            contribution_date=contribution_date,
        )

        recalculate_all_leaderboards()

        self.assertTrue(
            LeaderboardEntry.objects.filter(
                user=user,
                type='validator',
            ).exists(),
            "User should appear on validator leaderboard after creation"
        )

    def test_no_duplicate_validator_contribution_on_second_call(self):
        """
        Running the creation logic twice must not create a second
        'validator' contribution for the same user.
        """
        user = _make_user('d')
        contribution_date = timezone.now()

        for _ in range(2):
            Validator.objects.get_or_create(user=user)
            if not Contribution.objects.filter(
                user=user,
                contribution_type=self.validator_type,
            ).exists():
                Contribution.objects.create(
                    user=user,
                    contribution_type=self.validator_type,
                    points=1,
                    contribution_date=contribution_date,
                )

        self.assertEqual(
            Contribution.objects.filter(
                user=user,
                contribution_type=self.validator_type,
            ).count(),
            1,
            "Only one 'validator' contribution should ever exist per user"
        )

    def test_graduation_flow_waitlist_to_validator(self):
        """
        A user who is on the waitlist and then gets a Validator profile
        + validator contribution should move off the waitlist leaderboard
        and onto the validator leaderboard.
        """
        from leaderboard.models import recalculate_all_leaderboards

        user = _make_user('e')
        now = timezone.now()

        Contribution.objects.create(
            user=user,
            contribution_type=self.waitlist_type,
            points=1,
            contribution_date=now - timezone.timedelta(days=10),
        )
        recalculate_all_leaderboards()

        self.assertTrue(
            LeaderboardEntry.objects.filter(user=user, type='validator-waitlist').exists()
        )
        self.assertFalse(
            LeaderboardEntry.objects.filter(user=user, type='validator').exists()
        )

        Validator.objects.create(user=user)
        Contribution.objects.create(
            user=user,
            contribution_type=self.validator_type,
            points=1,
            contribution_date=now,
        )
        recalculate_all_leaderboards()

        self.assertTrue(
            LeaderboardEntry.objects.filter(user=user, type='validator').exists(),
            "Graduated user should appear on validator leaderboard"
        )
        self.assertFalse(
            LeaderboardEntry.objects.filter(user=user, type='validator-waitlist').exists(),
            "Graduated user should not still be on waitlist leaderboard"
        )
        self.assertTrue(
            LeaderboardEntry.objects.filter(user=user, type='validator-waitlist-graduation').exists(),
            "Graduated user should appear on graduation leaderboard"
        )
