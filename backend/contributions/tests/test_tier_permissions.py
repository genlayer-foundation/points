from importlib import import_module

from django.apps import apps as django_apps
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from contributions.models import (
    Category,
    ContributionType,
    SubmissionStateTransition,
    SubmittedContribution,
)
from contributions.permissions import (
    effective_steward_tier,
    steward_has_permission,
    steward_permission_map,
    steward_permitted_type_ids,
)
from stewards.models import Steward, StewardPermission


User = get_user_model()


class BuilderReviewHierarchyMigrationTests(TestCase):
    def setUp(self):
        self.builder, _ = Category.objects.get_or_create(
            slug='builder',
            defaults={'name': 'Builder'},
        )
        self.community, _ = Category.objects.get_or_create(
            slug='community',
            defaults={'name': 'Community'},
        )

    def test_forward_backfills_existing_builder_types_only(self):
        builder_type = ContributionType.objects.create(
            name='Existing Builder Type',
            slug='existing-builder-type',
            category=self.builder,
        )
        ContributionType.objects.filter(pk=builder_type.pk).update(
            requires_ai_review=False,
            escalation_threshold_points=None,
        )
        community_type = ContributionType.objects.create(
            name='Existing Community Type',
            slug='existing-community-type',
            category=self.community,
            requires_ai_review=True,
            escalation_threshold_points=250,
        )
        migration = import_module(
            'contributions.migrations.0084_enable_builder_review_hierarchy'
        )

        migration.enable_builder_review_hierarchy(django_apps, None)

        builder_type.refresh_from_db()
        community_type.refresh_from_db()
        self.assertTrue(builder_type.requires_ai_review)
        self.assertEqual(builder_type.escalation_threshold_points, 400)
        self.assertTrue(community_type.requires_ai_review)
        self.assertEqual(community_type.escalation_threshold_points, 250)

    def test_reverse_does_not_overwrite_later_builder_configuration(self):
        builder_type = ContributionType.objects.create(
            name='Configured Builder Type',
            slug='configured-builder-type',
            category=self.builder,
        )
        builder_type.requires_ai_review = False
        builder_type.escalation_threshold_points = None
        builder_type.save(
            update_fields=[
                'requires_ai_review',
                'escalation_threshold_points',
                'updated_at',
            ]
        )
        migration = import_module(
            'contributions.migrations.0084_enable_builder_review_hierarchy'
        )

        migration.Migration.operations[0].reverse_code(django_apps, None)

        builder_type.refresh_from_db()
        self.assertFalse(builder_type.requires_ai_review)
        self.assertIsNone(builder_type.escalation_threshold_points)


class BuilderReviewHierarchyModelTests(TestCase):
    def setUp(self):
        builder, _ = Category.objects.get_or_create(
            slug='builder',
            defaults={'name': 'Builder'},
        )
        community, _ = Category.objects.get_or_create(
            slug='community',
            defaults={'name': 'Community'},
        )
        self.builder = builder
        self.community = community

    def test_builder_types_receive_hierarchy_defaults_on_creation(self):
        builder_type = ContributionType.objects.create(
            name='New Builder Type',
            slug='new-builder-type',
            category=self.builder,
        )
        community_type = ContributionType.objects.create(
            name='New Community Type',
            slug='new-community-type',
            category=self.community,
        )

        self.assertTrue(builder_type.requires_ai_review)
        self.assertEqual(builder_type.escalation_threshold_points, 400)
        self.assertFalse(community_type.requires_ai_review)
        self.assertIsNone(community_type.escalation_threshold_points)

    def test_explicit_builder_creation_values_override_defaults_per_field(self):
        ai_opt_out = ContributionType.objects.create(
            name='AI Opt-out Builder Type',
            slug='ai-opt-out-builder-type',
            category=self.builder,
            requires_ai_review=False,
        )
        threshold_opt_out = ContributionType.objects.create(
            name='Threshold Opt-out Builder Type',
            slug='threshold-opt-out-builder-type',
            category=self.builder,
            escalation_threshold_points=None,
        )
        custom_threshold = ContributionType.objects.create(
            name='Custom Threshold Builder Type',
            slug='custom-threshold-builder-type',
            category=self.builder,
            escalation_threshold_points=250,
        )
        full_opt_out = ContributionType.objects.create(
            name='Opted-out Builder Type',
            slug='create-time-opted-out-builder-type',
            category=self.builder,
            requires_ai_review=False,
            escalation_threshold_points=None,
        )
        assigned_threshold = ContributionType(
            name='Assigned Threshold Builder Type',
            slug='assigned-threshold-builder-type',
            category=self.builder,
        )
        assigned_threshold.escalation_threshold_points = 275
        assigned_threshold.save()

        self.assertFalse(ai_opt_out.requires_ai_review)
        self.assertEqual(ai_opt_out.escalation_threshold_points, 400)
        self.assertTrue(threshold_opt_out.requires_ai_review)
        self.assertIsNone(threshold_opt_out.escalation_threshold_points)
        self.assertTrue(custom_threshold.requires_ai_review)
        self.assertEqual(custom_threshold.escalation_threshold_points, 250)
        self.assertFalse(full_opt_out.requires_ai_review)
        self.assertIsNone(full_opt_out.escalation_threshold_points)
        self.assertTrue(assigned_threshold.requires_ai_review)
        self.assertEqual(assigned_threshold.escalation_threshold_points, 275)

    def test_builder_defaults_can_be_overridden_after_creation(self):
        builder_type = ContributionType.objects.create(
            name='Opted-out Builder Type',
            slug='opted-out-builder-type',
            category=self.builder,
        )
        builder_type.requires_ai_review = False
        builder_type.escalation_threshold_points = None
        builder_type.save()

        builder_type.refresh_from_db()
        self.assertFalse(builder_type.requires_ai_review)
        self.assertIsNone(builder_type.escalation_threshold_points)


class StewardTierPermissionTests(TestCase):
    def setUp(self):
        category = Category.objects.create(name='Tier Tests', slug='tier-tests')
        self.types = [
            ContributionType.objects.create(
                name=f'Tier Test {index}',
                slug=f'tier-test-{index}',
                category=category,
            )
            for index in range(2)
        ]

        self.regular_user = User.objects.create_user(email='regular-tier@example.com')
        self.tier_one_user = User.objects.create_user(email='tier-one@example.com')
        self.tier_one = Steward.objects.create(user=self.tier_one_user)
        StewardPermission.objects.create(
            steward=self.tier_one,
            contribution_type=self.types[0],
            action='accept',
        )

        self.tier_two_user = User.objects.create_user(email='tier-two@example.com')
        self.tier_two = Steward.objects.create(
            user=self.tier_two_user,
            tier=Steward.TIER_TOP_LEVEL,
        )

        self.superuser = User.objects.create_superuser(
            email='super-tier@example.com',
            password='testpass123',
        )
        Steward.objects.create(user=self.superuser)

    def test_effective_tier_requires_a_steward_and_elevates_steward_superusers(self):
        self.assertEqual(effective_steward_tier(None), 0)
        self.assertEqual(effective_steward_tier(AnonymousUser()), 0)
        self.assertEqual(effective_steward_tier(self.regular_user), 0)
        self.assertEqual(effective_steward_tier(self.tier_one_user), 1)
        self.assertEqual(effective_steward_tier(self.tier_two_user), 2)
        self.assertEqual(effective_steward_tier(self.superuser), 3)

    def test_tier_one_permissions_still_come_from_explicit_rows(self):
        self.assertTrue(
            steward_has_permission(self.tier_one_user, self.types[0].id, 'accept')
        )
        self.assertFalse(
            steward_has_permission(self.tier_one_user, self.types[0].id, 'reject')
        )
        self.assertFalse(
            steward_has_permission(self.tier_one_user, self.types[1].id, 'accept')
        )
        self.assertEqual(
            steward_permitted_type_ids(self.tier_one_user, actions=['accept']),
            [self.types[0].id],
        )
        self.assertEqual(
            steward_permission_map(self.tier_one_user),
            {str(self.types[0].id): ['accept']},
        )

    def test_tier_two_receives_the_full_permission_matrix(self):
        actions = {choice[0] for choice in StewardPermission.ACTION_CHOICES}
        type_ids = {contribution_type.id for contribution_type in self.types}

        for contribution_type in self.types:
            for action in actions:
                self.assertTrue(
                    steward_has_permission(
                        self.tier_two_user,
                        contribution_type.id,
                        action,
                    )
                )

        self.assertTrue(
            type_ids <= set(
                steward_permitted_type_ids(
                    self.tier_two_user,
                    actions=['reject'],
                )
            )
        )
        permission_map = steward_permission_map(self.tier_two_user)
        self.assertTrue(
            {str(type_id) for type_id in type_ids} <= set(permission_map)
        )
        for effective_actions in permission_map.values():
            self.assertEqual(set(effective_actions), actions)

    def test_review_hierarchy_model_defaults_and_choices(self):
        contribution_type = self.types[0]
        self.assertFalse(contribution_type.requires_ai_review)
        self.assertIsNone(contribution_type.escalation_threshold_points)
        self.assertEqual(self.tier_one.tier, Steward.TIER_REVIEWER)
        self.assertEqual(self.tier_one.get_tier_display(), 'Reviewer')
        self.assertIn(
            (SubmissionStateTransition.EVENT_ESCALATED, 'Escalated'),
            SubmissionStateTransition.EVENT_CHOICES,
        )

        submission = SubmittedContribution(
            user=self.regular_user,
            contribution_type=contribution_type,
        )
        self.assertIsNone(submission.escalated_at)
