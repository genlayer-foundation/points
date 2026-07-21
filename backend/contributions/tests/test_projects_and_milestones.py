from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from builders.models import Builder
from contributions.models import (
    Category,
    Contribution,
    ContributionHighlight,
    ContributionType,
    Evidence,
    SubmittedContribution,
)
from leaderboard.models import GlobalLeaderboardMultiplier
from projects.models import Project
from stewards.models import Steward, StewardPermission

User = get_user_model()


class ProjectsAndMilestonesTest(TestCase):
    def setUp(self):
        self.category, _ = Category.objects.get_or_create(
            slug='builder',
            defaults={'name': 'Builder', 'description': 'Builder contributions'},
        )
        # Migration 0068 already creates the projects/milestones types, so a
        # migrated test database has rows with these slugs. Reuse them and pin
        # the fields (point ranges, review flow) the assertions below rely on.
        self.project_type, _ = ContributionType.objects.update_or_create(
            slug='projects',
            defaults={
                'name': 'Projects',
                'description': 'Project submission',
                'category': self.category,
                'min_points': 10,
                'max_points': 100,
                'is_submittable': True,
                'review_flow': ContributionType.REVIEW_FLOW_STANDARD,
            },
        )
        self.milestone_type, _ = ContributionType.objects.update_or_create(
            slug='milestones',
            defaults={
                'name': 'Milestones',
                'description': 'Project milestone',
                'category': self.category,
                'min_points': 5,
                'max_points': 50,
                'is_submittable': True,
                'review_flow': ContributionType.REVIEW_FLOW_STANDARD,
            },
        )
        for contribution_type in (self.project_type, self.milestone_type):
            GlobalLeaderboardMultiplier.objects.create(
                contribution_type=contribution_type,
                multiplier_value=1,
                valid_from=timezone.now(),
            )

        self.user = User.objects.create_user(
            email='builder@test.com',
            address='0x1111111111111111111111111111111111111111',
            password='testpass123',
        )
        Builder.objects.create(user=self.user)

        self.steward_user = User.objects.create_user(
            email='steward@test.com',
            address='0x2222222222222222222222222222222222222222',
            password='testpass123',
        )
        self.steward = Steward.objects.create(user=self.steward_user)
        for contribution_type in (self.project_type, self.milestone_type):
            for action in ('accept', 'reject', 'request_more_info', 'propose'):
                StewardPermission.objects.create(
                    steward=self.steward,
                    contribution_type=contribution_type,
                    action=action,
                )

        self.client = APIClient()
        self.recaptcha_patcher = patch(
            'contributions.recaptcha_field.ReCaptchaField.to_internal_value',
            return_value='test-token',
        )
        self.recaptcha_patcher.start()
        self.addCleanup(self.recaptcha_patcher.stop)

    def _accepted_project_contribution(
        self,
        title='Cognocracy',
        user=None,
        highlighted=True,
    ):
        contribution = Contribution.objects.create(
            user=user or self.user,
            contribution_type=self.project_type,
            points=25,
            contribution_date=timezone.now(),
            title=title,
        )
        Evidence.objects.create(
            contribution=contribution,
            description='Repo',
            url=f'https://github.com/example/{title.lower().replace(" ", "-")}',
        )
        if highlighted:
            ContributionHighlight.objects.create(
                contribution=contribution,
                title=title,
                description='Highlighted project',
            )
        return contribution

    def _post_submission(self, contribution_type, **extra):
        self.client.force_authenticate(user=self.user)
        payload = {
            'contribution_type': contribution_type.id,
            'contribution_date': timezone.now().date().isoformat(),
            'title': 'Submitted work',
            'notes': 'Submitted work notes',
            'recaptcha': 'test-token',
            'evidence_items': [
                {
                    'description': 'Evidence',
                    'url': f'https://example.com/evidence/{timezone.now().timestamp()}',
                },
            ],
            **extra,
        }
        return self.client.post('/api/v1/submissions/', payload, format='json')

    def test_milestone_requires_accepted_project_contribution(self):
        response = self._post_submission(self.milestone_type)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Milestones must be linked', response.data['error'])

    def test_milestone_cannot_link_another_users_project_contribution(self):
        other_user = User.objects.create_user(
            email='other@test.com',
            address='0x3333333333333333333333333333333333333333',
            password='testpass123',
        )
        other_project = self._accepted_project_contribution(title='Other Project', user=other_user)

        response = self._post_submission(
            self.milestone_type, project_contribution=other_project.id,
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_milestone_submission_gets_next_version(self):
        project_contribution = self._accepted_project_contribution()

        first = self._post_submission(
            self.milestone_type, project_contribution=project_contribution.id,
        )
        second = self._post_submission(
            self.milestone_type, project_contribution=project_contribution.id,
        )

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        self.assertEqual(first.data['milestone_version'], 1)
        self.assertEqual(second.data['milestone_version'], 2)
        self.assertEqual(first.data['project_contribution']['id'], project_contribution.id)

    def test_milestone_with_malformed_project_id_returns_client_error(self):
        self._accepted_project_contribution()

        response = self._post_submission(self.milestone_type, project_contribution='abc')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('highlighted projects', response.data['error'])

    def test_editing_milestone_to_other_project_assigns_next_version(self):
        project_a = self._accepted_project_contribution()
        project_b = self._accepted_project_contribution(title='Second Project')

        first = self._post_submission(
            self.milestone_type, project_contribution=project_a.id,
        )
        self._post_submission(self.milestone_type, project_contribution=project_b.id)
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)

        response = self.client.put(
            f"/api/v1/submissions/{first.data['id']}/",
            {
                'contribution_type': self.milestone_type.id,
                'contribution_date': timezone.now().date().isoformat(),
                'notes': 'Updated milestone notes',
                'project_contribution': project_b.id,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['project_contribution']['id'], project_b.id)
        self.assertEqual(response.data['milestone_version'], 2)

    def test_milestone_requires_change_description(self):
        project_contribution = self._accepted_project_contribution()

        response = self._post_submission(
            self.milestone_type,
            project_contribution=project_contribution.id,
            notes='   ',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('changes and improvements', response.data['error'])

    def test_milestone_submission_allows_empty_evidence(self):
        project_contribution = self._accepted_project_contribution()

        response = self._post_submission(
            self.milestone_type,
            project_contribution=project_contribution.id,
            evidence_items=[],
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['milestone_version'], 1)

    def test_project_submission_still_requires_evidence(self):
        response = self._post_submission(self.project_type, evidence_items=[])

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_accepted_projects_endpoint_lists_project_contributions(self):
        project_contribution = self._accepted_project_contribution()
        SubmittedContribution.objects.create(
            user=self.user,
            contribution_type=self.milestone_type,
            project_contribution=project_contribution,
            milestone_version=1,
            contribution_date=timezone.now(),
            notes='Pending milestone',
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/v1/submissions/accepted-projects/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]['id'], project_contribution.id)
        self.assertEqual(response.data[0]['title'], 'Cognocracy')
        self.assertEqual(
            response.data[0]['github_url'],
            'https://github.com/example/cognocracy',
        )
        self.assertEqual(response.data[0]['next_milestone_version'], 2)

    def test_accepted_projects_endpoint_excludes_other_users(self):
        other_user = User.objects.create_user(
            email='other2@test.com',
            address='0x4444444444444444444444444444444444444444',
            password='testpass123',
        )
        self._accepted_project_contribution(title='Other Project', user=other_user)

        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/v1/submissions/accepted-projects/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_accepting_project_submission_does_not_touch_projects_table(self):
        submission = SubmittedContribution.objects.create(
            user=self.user,
            contribution_type=self.project_type,
            contribution_date=timezone.now(),
            title='New Project',
            notes='Project details',
        )
        Evidence.objects.create(
            submitted_contribution=submission,
            description='Repo',
            url='https://github.com/example/new-project',
        )
        projects_before = Project.objects.count()

        self.client.force_authenticate(user=self.steward_user)
        response = self.client.post(
            f'/api/v1/steward-submissions/{submission.id}/review/',
            {
                'action': 'accept',
                'contribution_type': self.project_type.id,
                'user': self.user.id,
                'points': 25,
                'create_highlight': True,
                'highlight_title': 'New Project',
                'highlight_description': 'Highlighted project',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        submission.refresh_from_db()
        contribution = submission.converted_contribution
        self.assertIsNotNone(contribution)
        # The curated projects.Project showcase table is a separate feature
        # and must never gain rows from contribution acceptance.
        self.assertEqual(Project.objects.count(), projects_before)
        # The accepted and highlighted contribution becomes a milestone anchor.
        self.client.force_authenticate(user=self.user)
        eligible = self.client.get('/api/v1/submissions/accepted-projects/')
        self.assertIn(contribution.id, [item['id'] for item in eligible.data])

    def test_accepting_milestone_reassigned_to_other_user_is_rejected(self):
        project_contribution = self._accepted_project_contribution()
        other_user = User.objects.create_user(
            email='reassigned@test.com',
            address='0x5555555555555555555555555555555555555555',
            password='testpass123',
        )
        Builder.objects.create(user=other_user)
        submission = SubmittedContribution.objects.create(
            user=self.user,
            contribution_type=self.milestone_type,
            project_contribution=project_contribution,
            milestone_version=1,
            contribution_date=timezone.now(),
            title='Milestone shipped',
            notes='Milestone details',
        )
        # Reassigning the accepted contribution to another user is a
        # staff-only action; the ownership check is the staff-path defense.
        self.steward_user.is_staff = True
        self.steward_user.save(update_fields=['is_staff'])

        self.client.force_authenticate(user=self.steward_user)
        response = self.client.post(
            f'/api/v1/steward-submissions/{submission.id}/review/',
            {
                'action': 'accept',
                'contribution_type': self.milestone_type.id,
                # Reassigning the milestone to a user who does not own the
                # linked project contribution must be rejected.
                'user': other_user.id,
                'points': 10,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('owned by the selected user', response.data['detail'])

    def test_steward_accepted_projects_endpoint_lists_selected_users_projects(self):
        """Return only the selected user's highlighted Projects for steward review."""
        project_contribution = self._accepted_project_contribution()
        other_user = User.objects.create_user(
            email='other-project-owner@test.com',
            address='0x6666666666666666666666666666666666666666',
            password='testpass123',
        )
        self._accepted_project_contribution(title='Other Project', user=other_user)

        self.client.force_authenticate(user=self.steward_user)
        response = self.client.get(
            '/api/v1/steward-submissions/accepted-projects/',
            {'user': self.user.id},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item['id'] for item in response.data], [project_contribution.id])
        self.assertEqual(response.data[0]['title'], 'Cognocracy')
        self.assertEqual(
            response.data[0]['github_url'],
            'https://github.com/example/cognocracy',
        )

    def test_steward_accepted_projects_endpoint_excludes_current_submission_version(self):
        """Show the current milestone version when reviewing an already-linked milestone."""
        project_contribution = self._accepted_project_contribution()
        submission = SubmittedContribution.objects.create(
            user=self.user,
            contribution_type=self.milestone_type,
            project_contribution=project_contribution,
            milestone_version=1,
            contribution_date=timezone.now(),
            title='Milestone shipped',
            notes='Milestone details',
        )

        self.client.force_authenticate(user=self.steward_user)
        response = self.client.get(
            '/api/v1/steward-submissions/accepted-projects/',
            {'user': self.user.id, 'submission': submission.id},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]['id'], project_contribution.id)
        self.assertEqual(response.data[0]['next_milestone_version'], 1)

    def test_accepting_submission_as_milestone_uses_selected_project_contribution(self):
        """Accept a submission as a milestone linked to the steward-selected project."""
        project_contribution = self._accepted_project_contribution()
        submission = SubmittedContribution.objects.create(
            user=self.user,
            contribution_type=self.project_type,
            contribution_date=timezone.now(),
            title='Actually a milestone',
            notes='Milestone details',
        )
        Evidence.objects.create(
            submitted_contribution=submission,
            description='Changes',
            url='https://example.com/milestone',
        )

        self.client.force_authenticate(user=self.steward_user)
        response = self.client.post(
            f'/api/v1/steward-submissions/{submission.id}/review/',
            {
                'action': 'accept',
                'contribution_type': self.milestone_type.id,
                'project_contribution': project_contribution.id,
                'user': self.user.id,
                'points': 10,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        submission.refresh_from_db()
        contribution = submission.converted_contribution
        self.assertEqual(submission.contribution_type, self.milestone_type)
        self.assertEqual(submission.project_contribution, project_contribution)
        self.assertEqual(submission.milestone_version, 1)
        self.assertEqual(contribution.project_contribution, project_contribution)
        self.assertEqual(contribution.milestone_version, 1)

    def test_accepting_milestone_links_contribution_to_project_contribution(self):
        project_contribution = self._accepted_project_contribution()
        submission = SubmittedContribution.objects.create(
            user=self.user,
            contribution_type=self.milestone_type,
            project_contribution=project_contribution,
            milestone_version=1,
            contribution_date=timezone.now(),
            title='Milestone shipped',
            notes='Milestone details',
        )

        self.client.force_authenticate(user=self.steward_user)
        response = self.client.post(
            f'/api/v1/steward-submissions/{submission.id}/review/',
            {
                'action': 'accept',
                'contribution_type': self.milestone_type.id,
                'user': self.user.id,
                'points': 10,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        submission.refresh_from_db()
        contribution = submission.converted_contribution
        self.assertEqual(contribution.project_contribution, project_contribution)
        self.assertEqual(contribution.milestone_version, 1)
        self.assertTrue(
            project_contribution.milestones.filter(id=contribution.id).exists()
        )

    def test_unhighlighted_project_cannot_receive_new_milestone(self):
        project_contribution = self._accepted_project_contribution(
            highlighted=False,
        )

        self.client.force_authenticate(user=self.user)
        picker_response = self.client.get('/api/v1/submissions/accepted-projects/')
        response = self._post_submission(
            self.milestone_type,
            project_contribution=project_contribution.id,
        )

        self.assertEqual(picker_response.status_code, status.HTTP_200_OK)
        self.assertEqual(picker_response.data, [])
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('highlighted projects', response.data['error'])

    def test_existing_pending_milestone_keeps_unhighlighted_project(self):
        project_contribution = self._accepted_project_contribution(
            highlighted=False,
        )
        submission = SubmittedContribution.objects.create(
            user=self.user,
            contribution_type=self.milestone_type,
            project_contribution=project_contribution,
            milestone_version=1,
            contribution_date=timezone.now(),
            title='Existing milestone',
            notes='Existing milestone details',
        )

        self.client.force_authenticate(user=self.user)
        picker_response = self.client.get(
            '/api/v1/submissions/accepted-projects/',
            {'submission': submission.id},
        )
        edit_response = self.client.patch(
            f'/api/v1/submissions/{submission.id}/',
            {'notes': 'Updated existing milestone details'},
            format='json',
        )

        self.assertEqual(picker_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item['id'] for item in picker_response.data],
            [project_contribution.id],
        )
        self.assertEqual(edit_response.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(user=self.steward_user)
        review_response = self.client.post(
            f'/api/v1/steward-submissions/{submission.id}/review/',
            {
                'action': 'accept',
                'contribution_type': self.milestone_type.id,
                'user': self.user.id,
                'points': 10,
            },
            format='json',
        )

        self.assertEqual(review_response.status_code, status.HTTP_200_OK)
