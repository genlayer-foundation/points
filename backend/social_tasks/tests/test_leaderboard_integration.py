"""Verify SocialTaskCompletion points feed the existing leaderboard plumbing."""

from django.conf import settings
from django.test import TestCase
from django.utils import timezone

from builders.models import Builder
from contributions.models import Category, Contribution, ContributionType
from leaderboard.models import (
    GlobalLeaderboardMultiplier,
    LeaderboardEntry,
    calculate_category_points,
    recalculate_all_leaderboards,
)
from social_tasks.models import SocialTask, SocialTaskCompletion
from users.models import User
from validators.models import Validator


def _ensure_multiplier(ct):
    if not GlobalLeaderboardMultiplier.objects.filter(contribution_type=ct).exists():
        GlobalLeaderboardMultiplier.objects.create(
            contribution_type=ct,
            multiplier_value=1.0,
            valid_from=timezone.now() - timezone.timedelta(days=30),
        )


def _create_builder_journey_task(category):
    task, _ = SocialTask.objects.update_or_create(
        slug=settings.BUILDER_JOURNEY_TASK_SLUG,
        defaults={
            'name': 'Star the GenLayer boilerplate',
            'category': category,
            'points': 25,
            'verification_type': 'github_star',
            'target_repo': 'genlayerlabs/genlayer-project-boilerplate',
            'action_url': 'https://github.com/genlayerlabs/genlayer-project-boilerplate',
        },
    )
    return task


class CalculateCategoryPointsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='u@example.com', password='x', visible=True)
        self.builder_cat, _ = Category.objects.get_or_create(slug='builder', defaults={'name': 'Builder'})
        self.community_cat, _ = Category.objects.get_or_create(slug='community', defaults={'name': 'Community'})

    def test_includes_social_task_points_in_category_total(self):
        task = SocialTask.objects.create(
            slug='builder-follow',
            name='Builder follow',
            category=self.builder_cat,
            points=15,
            verification_type='click_through',
            action_url='https://example.com',
        )
        SocialTaskCompletion.objects.create(
            user=self.user,
            task=task,
            points_awarded=15,
            verification_type='click_through',
        )

        total = calculate_category_points(self.user, 'builder')
        self.assertEqual(total, 15)

    def test_includes_builder_journey_star_task_in_category_total(self):
        task = _create_builder_journey_task(self.builder_cat)
        SocialTaskCompletion.objects.create(
            user=self.user,
            task=task,
            points_awarded=25,
            verification_type='github_star',
        )

        total = calculate_category_points(self.user, 'builder')
        self.assertEqual(total, 25)

    def test_includes_eligibility_excluded_builder_contribution_points(self):
        included_type = ContributionType.objects.create(
            name='Builder Demo',
            slug='builder-demo-total-test',
            category=self.builder_cat,
            min_points=10,
            max_points=10,
        )
        _ensure_multiplier(included_type)
        excluded_specs = [
            ('builder-welcome', 'Builder Welcome', 0),
            ('builder', 'Builder', 50),
            ('community-link-github', 'Link GitHub Account', 25),
        ]
        for slug, name, points in excluded_specs:
            excluded_type, _ = ContributionType.objects.get_or_create(
                slug=slug,
                defaults={
                    'name': name,
                    'category': self.builder_cat,
                    'min_points': points,
                    'max_points': points,
                },
            )
            _ensure_multiplier(excluded_type)
            Contribution.objects.create(
                user=self.user,
                contribution_type=excluded_type,
                points=points,
                frozen_global_points=points,
                contribution_date=timezone.now(),
            )
        Contribution.objects.create(
            user=self.user,
            contribution_type=included_type,
            points=10,
            frozen_global_points=10,
            contribution_date=timezone.now(),
        )

        total = calculate_category_points(self.user, 'builder')
        self.assertEqual(total, 85)

    def test_community_category_returns_social_task_only(self):
        task = SocialTask.objects.create(
            slug='community-follow',
            name='Community follow',
            category=self.community_cat,
            points=7,
            verification_type='click_through',
            action_url='https://example.com',
        )
        SocialTaskCompletion.objects.create(
            user=self.user, task=task, points_awarded=7, verification_type='click_through',
        )

        total = calculate_category_points(self.user, 'community')
        self.assertEqual(total, 7)


class SignalUpdatesLeaderboardTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='b@example.com', password='x', visible=True)
        Builder.objects.create(user=self.user)
        self.builder_cat, _ = Category.objects.get_or_create(slug='builder', defaults={'name': 'Builder'})

    def _add_eligible_contribution(self, points=10):
        """A real builder contribution — the write-time eligibility gate."""
        ct, _ = ContributionType.objects.get_or_create(
            slug='builder-real-work-signal',
            defaults={
                'name': 'Builder Real Work',
                'category': self.builder_cat,
                'min_points': points,
                'max_points': points,
            },
        )
        _ensure_multiplier(ct)
        return Contribution.objects.create(
            user=self.user,
            contribution_type=ct,
            points=points,
            frozen_global_points=points,
            contribution_date=timezone.now(),
        )

    def test_completion_alone_does_not_create_builder_entry(self):
        task = SocialTask.objects.create(
            slug='b-follow',
            name='Builder follow',
            category=self.builder_cat,
            points=12,
            verification_type='click_through',
            action_url='https://example.com',
        )

        SocialTaskCompletion.objects.create(
            user=self.user, task=task, points_awarded=12, verification_type='click_through',
        )

        # Social-task points are earnings, not eligibility: without a real
        # builder contribution there is no public leaderboard entry.
        self.assertFalse(
            LeaderboardEntry.objects.filter(user=self.user, type='builder').exists()
        )

    def test_completion_updates_builder_entry_once_eligible(self):
        self._add_eligible_contribution(points=10)
        task = SocialTask.objects.create(
            slug='b-follow',
            name='Builder follow',
            category=self.builder_cat,
            points=12,
            verification_type='click_through',
            action_url='https://example.com',
        )

        SocialTaskCompletion.objects.create(
            user=self.user, task=task, points_awarded=12, verification_type='click_through',
        )

        entry = LeaderboardEntry.objects.get(user=self.user, type='builder')
        self.assertEqual(entry.total_points, 22)

    def test_builder_journey_star_completion_adds_builder_points(self):
        self._add_eligible_contribution(points=10)
        task = _create_builder_journey_task(self.builder_cat)

        SocialTaskCompletion.objects.create(
            user=self.user, task=task, points_awarded=25, verification_type='github_star',
        )

        entry = LeaderboardEntry.objects.get(user=self.user, type='builder')
        self.assertEqual(entry.total_points, 35)


class CommunityCategoryDoesNotMoveLeaderboardTest(TestCase):
    """Confirms the explicit fact: community has no leaderboard, so community
    social-task points stay invisible at the leaderboard layer."""

    def test_no_leaderboard_entry_created_for_community_only(self):
        user = User.objects.create_user(email='c@example.com', password='x', visible=True)
        category, _ = Category.objects.get_or_create(slug='community', defaults={'name': 'Community'})
        task = SocialTask.objects.create(
            slug='c-follow',
            name='Community follow',
            category=category,
            points=10,
            verification_type='click_through',
            action_url='https://example.com',
        )
        SocialTaskCompletion.objects.create(
            user=user, task=task, points_awarded=10, verification_type='click_through',
        )
        self.assertFalse(LeaderboardEntry.objects.filter(user=user).exists())


class RecalculateIncludesSocialTasksTest(TestCase):
    def test_recalculate_skips_completion_only_builders(self):
        user = User.objects.create_user(email='b2@example.com', password='x', visible=True)
        Builder.objects.create(user=user)
        builder_cat, _ = Category.objects.get_or_create(slug='builder', defaults={'name': 'Builder'})

        task = SocialTask.objects.create(
            slug='b2-follow',
            name='Builder follow 2',
            category=builder_cat,
            points=8,
            verification_type='click_through',
            action_url='https://example.com',
        )
        SocialTaskCompletion.objects.create(
            user=user, task=task, points_awarded=8, verification_type='click_through',
        )

        LeaderboardEntry.objects.all().delete()
        recalculate_all_leaderboards()

        # No real builder contribution -> not eligible -> no entry, even
        # though the completion points exist (they surface in profile stats).
        self.assertFalse(
            LeaderboardEntry.objects.filter(user=user, type='builder').exists()
        )

    def test_recalculate_includes_builder_journey_star_task(self):
        user = User.objects.create_user(email='star@example.com', password='x', visible=True)
        Builder.objects.create(user=user)
        builder_cat, _ = Category.objects.get_or_create(slug='builder', defaults={'name': 'Builder'})

        included_type = ContributionType.objects.create(
            name='Builder Real Work',
            slug='builder-real-work-star-recalc',
            category=builder_cat,
            min_points=10,
            max_points=10,
        )
        _ensure_multiplier(included_type)
        Contribution.objects.create(
            user=user,
            contribution_type=included_type,
            points=10,
            frozen_global_points=10,
            contribution_date=timezone.now(),
        )

        task = _create_builder_journey_task(builder_cat)
        SocialTaskCompletion.objects.create(
            user=user, task=task, points_awarded=25, verification_type='github_star',
        )

        LeaderboardEntry.objects.all().delete()
        recalculate_all_leaderboards()

        entry = LeaderboardEntry.objects.get(user=user, type='builder')
        self.assertEqual(entry.total_points, 35)

    def test_recalculate_includes_eligibility_excluded_builder_contribution_points(self):
        user = User.objects.create_user(
            email='simple-builder@example.com',
            password='x',
            visible=True,
        )
        Builder.objects.create(user=user)
        builder_cat, _ = Category.objects.get_or_create(
            slug='builder',
            defaults={'name': 'Builder'},
        )
        included_type = ContributionType.objects.create(
            name='Builder Real Work',
            slug='builder-real-work-recalc',
            category=builder_cat,
            min_points=30,
            max_points=30,
        )
        _ensure_multiplier(included_type)
        github_link_type, _ = ContributionType.objects.get_or_create(
            slug='community-link-github',
            defaults={
                'name': 'Link GitHub Account',
                'category': builder_cat,
                'min_points': 25,
                'max_points': 25,
            },
        )
        _ensure_multiplier(github_link_type)
        for contribution_type, points in (
            (github_link_type, 25),
            (included_type, 30),
        ):
            Contribution.objects.create(
                user=user,
                contribution_type=contribution_type,
                points=points,
                frozen_global_points=points,
                contribution_date=timezone.now(),
            )

        LeaderboardEntry.objects.all().delete()
        recalculate_all_leaderboards()

        entry = LeaderboardEntry.objects.get(user=user, type='builder')
        self.assertEqual(entry.total_points, 55)

    def test_recalculate_sums_contribution_and_social_points(self):
        user = User.objects.create_user(email='vmix@example.com', password='x', visible=True)
        validator_cat, _ = Category.objects.get_or_create(slug='validator', defaults={'name': 'Validator'})
        Validator.objects.create(user=user)

        ct = ContributionType.objects.create(
            name='Test validator contribution',
            slug='test-validator-contrib',
            category=validator_cat,
            min_points=20,
            max_points=20,
        )
        _ensure_multiplier(ct)
        Contribution.objects.create(
            user=user,
            contribution_type=ct,
            points=20,
            contribution_date=timezone.now(),
        )

        task = SocialTask.objects.create(
            slug='v-follow',
            name='Validator follow',
            category=validator_cat,
            points=4,
            verification_type='click_through',
            action_url='https://example.com',
        )
        SocialTaskCompletion.objects.create(
            user=user, task=task, points_awarded=4, verification_type='click_through',
        )

        LeaderboardEntry.objects.all().delete()
        recalculate_all_leaderboards()

        entry = LeaderboardEntry.objects.get(user=user, type='validator')
        self.assertEqual(entry.total_points, 24)
