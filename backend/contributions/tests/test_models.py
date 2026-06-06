from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from contributions.models import (
    Category,
    ContributionType,
    ProjectMilestoneReview,
    SubmittedContribution,
)
from users.models import User


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
