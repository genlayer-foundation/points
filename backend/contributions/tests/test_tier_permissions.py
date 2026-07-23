from importlib import import_module

from django import forms
from django.apps import apps as django_apps
from django.contrib import admin
from django.contrib.admin.utils import flatten_fieldsets
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase

from contributions.admin import ContributionTypeAdmin
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

    def _contribution_type_admin_form(
        self,
        *,
        category,
        apply_builder_defaults,
        include_review_fields=True,
        requires_ai_review=False,
        escalation_threshold_points='',
    ):
        data = {
            'name': 'Admin Builder Type',
            'slug': 'admin-builder-type',
            'category': category.pk,
            'min_points': 0,
            'max_points': 100,
            'rubric_extra_points': 2,
            'is_submittable': 'on',
            'review_flow': ContributionType.REVIEW_FLOW_STANDARD,
            'escalation_threshold_points': escalation_threshold_points,
            'examples': '[]',
            'required_social_accounts': '[]',
            'required_evidence_url_type_groups': '[]',
        }
        if apply_builder_defaults:
            data['apply_builder_review_defaults'] = 'on'
        if requires_ai_review:
            data['requires_ai_review'] = 'on'
        request = RequestFactory().post(
            '/admin/contributions/contributiontype/add/',
            data,
        )
        request.user = User(
            is_active=True,
            is_staff=True,
            is_superuser=True,
        )
        model_admin = admin.site._registry[ContributionType]
        self.assertIsInstance(model_admin, ContributionTypeAdmin)
        fields = flatten_fieldsets(model_admin.get_fieldsets(request))
        if not include_review_fields:
            fields = [
                field
                for field in fields
                if field not in ContributionType.BUILDER_REVIEW_DEFAULT_FIELDS
            ]
        form_class = model_admin.get_form(
            request,
            change=False,
            fields=fields,
        )
        form = form_class(data=request.POST)
        self.assertTrue(form.is_valid(), form.errors)
        return request, model_admin, form

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
        assigned_opt_out = ContributionType(
            name='Assigned Opt-out Builder Type',
            slug='assigned-opt-out-builder-type',
            category=self.builder,
        )
        assigned_opt_out.requires_ai_review = False
        assigned_opt_out.escalation_threshold_points = None
        assigned_opt_out.save()
        constructed_opt_out = ContributionType(
            name='Constructed Opt-out Builder Type',
            slug='constructed-opt-out-builder-type',
            category=self.builder,
            requires_ai_review=False,
            escalation_threshold_points=None,
        )
        constructed_opt_out.save()

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
        self.assertFalse(assigned_opt_out.requires_ai_review)
        self.assertIsNone(assigned_opt_out.escalation_threshold_points)
        self.assertFalse(constructed_opt_out.requires_ai_review)
        self.assertIsNone(constructed_opt_out.escalation_threshold_points)

    def test_registered_admin_form_applies_builder_defaults_by_default(self):
        request, model_admin, form = self._contribution_type_admin_form(
            category=self.builder,
            apply_builder_defaults=True,
        )
        self.assertTrue(form.fields['apply_builder_review_defaults'].initial)
        contribution_type = model_admin.save_form(request, form, change=False)

        model_admin.save_model(
            request,
            contribution_type,
            form,
            change=False,
        )

        contribution_type.refresh_from_db()
        self.assertTrue(contribution_type.requires_ai_review)
        self.assertEqual(contribution_type.escalation_threshold_points, 400)

    def test_registered_admin_form_preserves_explicit_builder_opt_out(self):
        request, model_admin, form = self._contribution_type_admin_form(
            category=self.builder,
            apply_builder_defaults=False,
        )
        contribution_type = model_admin.save_form(request, form, change=False)

        model_admin.save_model(
            request,
            contribution_type,
            form,
            change=False,
        )

        contribution_type.refresh_from_db()
        self.assertFalse(contribution_type.requires_ai_review)
        self.assertIsNone(contribution_type.escalation_threshold_points)

    def test_registered_admin_form_preserves_custom_builder_settings(self):
        request, model_admin, form = self._contribution_type_admin_form(
            category=self.builder,
            apply_builder_defaults=False,
            requires_ai_review=True,
            escalation_threshold_points=275,
        )
        contribution_type = model_admin.save_form(request, form, change=False)

        model_admin.save_model(
            request,
            contribution_type,
            form,
            change=False,
        )

        contribution_type.refresh_from_db()
        self.assertTrue(contribution_type.requires_ai_review)
        self.assertEqual(contribution_type.escalation_threshold_points, 275)

    def test_registered_admin_form_defaults_excluded_builder_review_fields(self):
        request, model_admin, form = self._contribution_type_admin_form(
            category=self.builder,
            apply_builder_defaults=False,
            include_review_fields=False,
        )
        contribution_type = model_admin.save_form(request, form, change=False)

        model_admin.save_model(
            request,
            contribution_type,
            form,
            change=False,
        )

        contribution_type.refresh_from_db()
        self.assertTrue(contribution_type.requires_ai_review)
        self.assertEqual(contribution_type.escalation_threshold_points, 400)

    def test_registered_admin_form_leaves_non_builder_defaults_unchanged(self):
        request, model_admin, form = self._contribution_type_admin_form(
            category=self.community,
            apply_builder_defaults=True,
        )
        contribution_type = model_admin.save_form(request, form, change=False)

        model_admin.save_model(
            request,
            contribution_type,
            form,
            change=False,
        )

        contribution_type.refresh_from_db()
        self.assertFalse(contribution_type.requires_ai_review)
        self.assertIsNone(contribution_type.escalation_threshold_points)

    def test_registered_admin_form_supports_commit_true(self):
        _request, _model_admin, form = self._contribution_type_admin_form(
            category=self.builder,
            apply_builder_defaults=True,
        )

        contribution_type = form.save(commit=True)

        contribution_type.refresh_from_db()
        self.assertTrue(contribution_type.requires_ai_review)
        self.assertEqual(contribution_type.escalation_threshold_points, 400)

    def test_registered_admin_hides_builder_default_control_on_change(self):
        contribution_type = ContributionType.objects.create(
            name='Existing Admin Builder Type',
            slug='existing-admin-builder-type',
            category=self.builder,
        )
        request = RequestFactory().get(
            f'/admin/contributions/contributiontype/{contribution_type.pk}/change/'
        )
        request.user = User(
            is_active=True,
            is_staff=True,
            is_superuser=True,
        )
        model_admin = admin.site._registry[ContributionType]
        fields = flatten_fieldsets(
            model_admin.get_fieldsets(request, contribution_type)
        )
        form_class = model_admin.get_form(
            request,
            contribution_type,
            change=True,
            fields=fields,
        )

        form = form_class(instance=contribution_type)
        default_control = form.fields['apply_builder_review_defaults']

        self.assertTrue(default_control.disabled)
        self.assertIsInstance(default_control.widget, forms.HiddenInput)

    def test_generic_model_form_preserves_builder_opt_out_assignments(self):
        form_class = forms.modelform_factory(
            ContributionType,
            fields=(
                'name',
                'slug',
                'category',
                'requires_ai_review',
                'escalation_threshold_points',
            ),
        )
        form = form_class(data={
            'name': 'Generic Form Opt-out Builder Type',
            'slug': 'generic-form-opt-out-builder-type',
            'category': self.builder.pk,
            'escalation_threshold_points': '',
        })
        self.assertTrue(form.is_valid(), form.errors)

        contribution_type = form.save()

        self.assertFalse(contribution_type.requires_ai_review)
        self.assertIsNone(contribution_type.escalation_threshold_points)

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

    def test_reclassifying_an_existing_type_does_not_apply_defaults(self):
        contribution_type = ContributionType.objects.create(
            name='Reclassified Type',
            slug='reclassified-type',
            category=self.community,
        )

        contribution_type.category = self.builder
        contribution_type.save()

        contribution_type.refresh_from_db()
        self.assertFalse(contribution_type.requires_ai_review)
        self.assertIsNone(contribution_type.escalation_threshold_points)


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
