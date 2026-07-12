from django.contrib import admin
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.test.client import RequestFactory
from django.utils import timezone

from contributions.models import (
    Category,
    Contribution,
    ContributionType,
    ProjectMilestoneReview,
    SubmittedContribution,
)
from leaderboard.models import GlobalLeaderboardMultiplier
from users.models import User


class HistoricalContributionPointValidationTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name='Historical Awards',
            slug='historical-awards',
        )
        self.contribution_type = ContributionType.objects.create(
            name='Historical Welcome',
            slug='historical-welcome',
            category=self.category,
            min_points=20,
            max_points=20,
            is_submittable=False,
        )
        GlobalLeaderboardMultiplier.objects.create(
            contribution_type=self.contribution_type,
            multiplier_value=1,
            valid_from=timezone.now() - timezone.timedelta(days=1),
        )
        self.user = User.objects.create_user(email='historical-award@example.com')
        self.contribution = Contribution.objects.create(
            user=self.user,
            contribution_type=self.contribution_type,
            points=20,
            contribution_date=timezone.now(),
        )

        ContributionType.objects.filter(pk=self.contribution_type.pk).update(
            min_points=0,
            max_points=0,
        )
        self.contribution_type.refresh_from_db()
        self.contribution.refresh_from_db()

    def test_unchanged_historical_points_remain_valid_after_range_change(self):
        self.contribution.full_clean()

        self.contribution.refresh_from_db()
        self.assertEqual(self.contribution.points, 20)
        self.assertEqual(self.contribution.frozen_global_points, 20)

    def test_user_admin_inline_accepts_unchanged_historical_points(self):
        from users.admin import ContributionInline

        admin_user = User.objects.create_superuser(
            email='historical-award-admin@example.com',
            password='testpass123',
        )
        request = RequestFactory().post('/admin/users/user/change/')
        request.user = admin_user
        inline = ContributionInline(User, admin.site)
        formset_class = inline.get_formset(request, obj=self.user)
        prefix = formset_class.get_default_prefix()
        contribution_date = timezone.localtime(self.contribution.contribution_date)
        formset = formset_class(
            data={
                f'{prefix}-TOTAL_FORMS': '1',
                f'{prefix}-INITIAL_FORMS': '1',
                f'{prefix}-MIN_NUM_FORMS': '0',
                f'{prefix}-MAX_NUM_FORMS': '1000',
                f'{prefix}-0-id': str(self.contribution.pk),
                f'{prefix}-0-user': str(self.user.pk),
                f'{prefix}-0-contribution_type': str(self.contribution_type.pk),
                f'{prefix}-0-points': '20',
                f'{prefix}-0-contribution_date_0': contribution_date.strftime('%Y-%m-%d'),
                f'{prefix}-0-contribution_date_1': contribution_date.strftime('%H:%M:%S'),
            },
            instance=self.user,
            prefix=prefix,
        )

        self.assertTrue(formset.is_valid(), formset.errors)

    def test_new_contribution_must_use_current_range(self):
        contribution = Contribution(
            user=self.user,
            contribution_type=self.contribution_type,
            points=20,
            contribution_date=timezone.now(),
        )

        with self.assertRaisesMessage(ValidationError, 'Points must be between 0 and 0'):
            contribution.full_clean()

    def test_editing_historical_points_must_use_current_range(self):
        self.contribution.points = 10

        with self.assertRaisesMessage(ValidationError, 'Points must be between 0 and 0'):
            self.contribution.full_clean()

    def test_changing_historical_type_must_use_new_type_range(self):
        replacement_type = ContributionType.objects.create(
            name='Replacement Welcome',
            slug='replacement-welcome',
            category=self.category,
            min_points=0,
            max_points=0,
            is_submittable=False,
        )
        GlobalLeaderboardMultiplier.objects.create(
            contribution_type=replacement_type,
            multiplier_value=1,
            valid_from=timezone.now() - timezone.timedelta(days=1),
        )
        self.contribution.contribution_type = replacement_type

        with self.assertRaisesMessage(ValidationError, 'Points must be between 0 and 0'):
            self.contribution.full_clean()


class ProjectMilestoneReviewModelTests(TestCase):
    def setUp(self):
        self.category, _ = Category.objects.get_or_create(
            slug='builder',
            defaults={
                'name': 'Builder',
                'description': 'Builder category',
            },
        )
        self.project_type = ContributionType.objects.create(
            name='Model Rubric Project',
            slug='model-rubric-project',
            category=self.category,
            min_points=1,
            max_points=100,
            review_flow=ContributionType.REVIEW_FLOW_BUILDER_PROJECT,
        )
        self.standard_type = ContributionType.objects.create(
            name='Model Standard Builder',
            slug='model-standard-builder',
            category=self.category,
            min_points=1,
            max_points=10,
        )
        self.submitter = User.objects.create_user(
            email='model-submit@example.com',
            address='0x5555555555555555555555555555555555555555',
        )

    def create_submission(self, contribution_type):
        return SubmittedContribution.objects.create(
            user=self.submitter,
            contribution_type=contribution_type,
            contribution_date=timezone.now(),
            notes='Project repository and demo.',
            state='pending',
        )

    def assert_validation_error(self, callback):
        try:
            callback()
        except ValidationError:
            return
        self.fail('ValidationError was not raised')

    def test_project_review_model_enforces_builder_project_only(self):
        project_submission = self.create_submission(self.project_type)
        standard_submission = self.create_submission(self.standard_type)

        self.assert_validation_error(
            lambda: ProjectMilestoneReview.objects.create(
                submitted_contribution=project_submission,
                review_flow=ContributionType.REVIEW_FLOW_STANDARD,
                action='accept',
                gate_failures=[],
                sections={},
                extras=[],
                overall_reason='Wrong review flow.',
            )
        )

        self.assert_validation_error(
            lambda: ProjectMilestoneReview.objects.create(
                submitted_contribution=standard_submission,
                review_flow=ContributionType.REVIEW_FLOW_BUILDER_PROJECT,
                action='accept',
                gate_failures=[],
                sections={},
                extras=[],
                overall_reason='Wrong submission type.',
            )
        )
