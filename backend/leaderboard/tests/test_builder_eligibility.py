"""Write-time builder leaderboard eligibility: entry existence == eligibility.

Eligible = Builder profile + ≥1 builder-category contribution whose slug is not
an excluded role/onboarding marker. Excluded-slug and social-task points still
count toward the total once eligible.
"""

from django.test import TestCase
from django.utils import timezone

from builders.models import Builder
from contributions.models import Category, Contribution, ContributionType
from leaderboard.models import (
    GlobalLeaderboardMultiplier,
    LeaderboardEntry,
    has_eligible_builder_contribution,
    update_user_leaderboard_entries,
)
from users.models import User


class BuilderEligibilityTest(TestCase):
    def setUp(self):
        self.builder_cat, _ = Category.objects.get_or_create(
            slug='builder', defaults={'name': 'Builder'}
        )
        self.real_type = self._type('builder-real-work-elig', 'Builder Real Work', 10)
        self.excluded_type = self._type('community-link-github', 'Link GitHub Account', 25)
        self.user = User.objects.create_user(
            email='eligibility@example.com',
            password='x',
            visible=True,
            address='0x00000000000000000000000000000000000000e1',
        )
        Builder.objects.create(user=self.user)

    def _type(self, slug, name, points):
        contribution_type, _ = ContributionType.objects.get_or_create(
            slug=slug,
            defaults={
                'name': name,
                'category': self.builder_cat,
                'min_points': points,
                'max_points': points,
            },
        )
        if not GlobalLeaderboardMultiplier.objects.filter(
            contribution_type=contribution_type
        ).exists():
            GlobalLeaderboardMultiplier.objects.create(
                contribution_type=contribution_type,
                multiplier_value=1.0,
                valid_from=timezone.now() - timezone.timedelta(days=30),
            )
        return contribution_type

    def _contribute(self, user, contribution_type, points):
        return Contribution.objects.create(
            user=user,
            contribution_type=contribution_type,
            points=points,
            frozen_global_points=points,
            contribution_date=timezone.now(),
        )

    def test_helper_requires_a_non_excluded_builder_contribution(self):
        self.assertFalse(has_eligible_builder_contribution(self.user))
        self._contribute(self.user, self.excluded_type, 25)
        self.assertFalse(has_eligible_builder_contribution(self.user))
        self._contribute(self.user, self.real_type, 10)
        self.assertTrue(has_eligible_builder_contribution(self.user))

    def test_entry_created_when_first_eligible_contribution_lands(self):
        self._contribute(self.user, self.excluded_type, 25)
        self.assertFalse(
            LeaderboardEntry.objects.filter(user=self.user, type='builder').exists()
        )

        self._contribute(self.user, self.real_type, 10)

        entry = LeaderboardEntry.objects.get(user=self.user, type='builder')
        # Previously excluded-slug points fold into the total once eligible.
        self.assertEqual(entry.total_points, 35)
        self.assertEqual(entry.rank, 1)

    def test_builder_profile_created_after_contribution_creates_entry(self):
        # Steward-accept ordering: the Contribution is created while the user is
        # not yet a Builder, then ensure_builder_status creates the profile —
        # the Builder post_save signal must produce the entry.
        user = User.objects.create_user(
            email='accepted-later@example.com',
            password='x',
            visible=True,
            address='0x00000000000000000000000000000000000000e2',
        )
        self._contribute(user, self.real_type, 10)
        self.assertFalse(
            LeaderboardEntry.objects.filter(user=user, type='builder').exists()
        )

        Builder.objects.create(user=user)

        entry = LeaderboardEntry.objects.get(user=user, type='builder')
        self.assertEqual(entry.total_points, 10)

    def test_stale_ineligible_entry_removed_on_next_update(self):
        LeaderboardEntry.objects.create(
            user=self.user, type='builder', total_points=99, rank=1
        )

        update_user_leaderboard_entries(self.user)

        self.assertFalse(
            LeaderboardEntry.objects.filter(user=self.user, type='builder').exists()
        )

    def test_deleting_a_contribution_refreshes_the_entry_total(self):
        self._contribute(self.user, self.real_type, 10)
        extra = self._contribute(self.user, self.real_type, 10)
        self.assertEqual(
            LeaderboardEntry.objects.get(user=self.user, type='builder').total_points,
            20,
        )

        extra.delete()

        self.assertEqual(
            LeaderboardEntry.objects.get(user=self.user, type='builder').total_points,
            10,
        )

    def test_deleting_last_eligible_contribution_removes_the_entry(self):
        contribution = self._contribute(self.user, self.real_type, 10)
        self.assertTrue(
            LeaderboardEntry.objects.filter(user=self.user, type='builder').exists()
        )

        contribution.delete()

        self.assertFalse(
            LeaderboardEntry.objects.filter(user=self.user, type='builder').exists()
        )

    def test_user_delete_cascade_does_not_resurrect_entries(self):
        self._contribute(self.user, self.real_type, 10)
        user_id = self.user.id

        # Cascade deletes contributions (firing the post_delete hook) and
        # entries in arbitrary order; the hook must not recreate rows that
        # would break the final user delete.
        self.user.delete()

        self.assertFalse(LeaderboardEntry.objects.filter(user_id=user_id).exists())
        self.assertFalse(User.objects.filter(id=user_id).exists())
