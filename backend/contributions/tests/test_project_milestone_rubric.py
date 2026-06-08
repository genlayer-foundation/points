from datetime import timedelta

from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from contributions.models import (
    Category,
    ContributionType,
    Evidence,
    ProjectMilestoneReview,
    SubmissionNote,
    SubmittedContribution,
)
from leaderboard.models import GlobalLeaderboardMultiplier
from stewards.models import Steward, StewardPermission
from users.models import User


def rubric_payload(**overrides):
    payload = {
        'gate_failures': [],
        'sections': {
            'genlayer_fit': {'score': 3, 'reason': 'Trustless adjudication is useful.'},
            'contract_quality': {'score': 2, 'reason': 'Contract has state and a meaningful validator.'},
            'engineering': {'score': 2, 'reason': 'Repository builds and has original structure.'},
            'frontend_ux': {'score': 1, 'reason': 'Basic UI is wired to the contract.'},
        },
        'extras': ['live_deployment'],
        'overall_reason': 'Valid project with a conservative score.',
    }
    payload.update(overrides)
    return payload


def gate_payload():
    return {
        'gate_failures': ['repo_does_not_build'],
        'sections': {},
        'extras': [],
        'overall_reason': 'The repository does not build locally.',
    }


@override_settings(ALLOWED_HOSTS=['*'])
class ProjectMilestoneRubricHumanProposalTests(APITestCase):
    def setUp(self):
        self.category, _ = Category.objects.get_or_create(
            slug='builder',
            defaults={
                'name': 'Builder',
                'description': 'Builder category',
            },
        )
        self.project_type = ContributionType.objects.create(
            name='Rubric Project',
            slug='rubric-project-human',
            category=self.category,
            min_points=1,
            max_points=100,
            review_flow=ContributionType.REVIEW_FLOW_BUILDER_PROJECT,
        )
        self.standard_type = ContributionType.objects.create(
            name='Standard Builder',
            slug='standard-builder',
            category=self.category,
            min_points=1,
            max_points=10,
        )
        for contribution_type in [self.project_type, self.standard_type]:
            GlobalLeaderboardMultiplier.objects.create(
                contribution_type=contribution_type,
                multiplier_value=1.0,
                valid_from=timezone.now() - timedelta(days=1),
            )

        self.submitter = User.objects.create_user(
            email='submitter@example.com',
            address='0x1111111111111111111111111111111111111111',
        )
        self.steward_user = User.objects.create_user(
            email='steward@example.com',
            address='0x2222222222222222222222222222222222222222',
            name='Reviewer',
        )
        steward = Steward.objects.create(user=self.steward_user)
        for contribution_type in [self.project_type, self.standard_type]:
            for action in ['propose', 'accept', 'reject', 'request_more_info']:
                StewardPermission.objects.create(
                    steward=steward,
                    contribution_type=contribution_type,
                    action=action,
                )

        self.client.force_authenticate(user=self.steward_user)

    def create_submission(self, contribution_type=None):
        submission = SubmittedContribution.objects.create(
            user=self.submitter,
            contribution_type=contribution_type or self.project_type,
            contribution_date=timezone.now(),
            notes='Project repository and demo.',
            state='pending',
        )
        Evidence.objects.create(
            submitted_contribution=submission,
            url='https://github.com/example/project',
        )
        return submission

    def test_project_proposal_requires_rubric_review(self):
        submission = self.create_submission()

        response = self.client.post(
            f'/api/v1/steward-submissions/{submission.id}/propose/',
            data={
                'proposed_action': 'accept',
                'proposed_staff_reply': '',
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('rubric_review', response.data)

    def test_gate_failure_forces_reject_and_creates_rubric_record(self):
        submission = self.create_submission()

        response = self.client.post(
            f'/api/v1/steward-submissions/{submission.id}/propose/',
            data={
                'proposed_action': 'reject',
                'proposed_staff_reply': 'The repository does not build.',
                'rubric_review': gate_payload(),
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        review = ProjectMilestoneReview.objects.get(submitted_contribution=submission)
        self.assertEqual(review.action, 'reject')
        self.assertEqual(review.gate_failures, ['repo_does_not_build'])
        self.assertEqual(review.sections, {})
        self.assertEqual(response.data['rubric_review']['gate_failures'], ['repo_does_not_build'])

        note = SubmissionNote.objects.filter(
            submitted_contribution=submission,
            is_proposal=True,
        ).first()
        self.assertIsNotNone(note)
        self.assertEqual(note.data['rubric_review_id'], review.id)
        self.assertIn('Gate failed', note.message)

    def test_gate_failure_rejects_non_reject_action(self):
        submission = self.create_submission()

        response = self.client.post(
            f'/api/v1/steward-submissions/{submission.id}/propose/',
            data={
                'proposed_action': 'accept',
                'rubric_review': gate_payload(),
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(ProjectMilestoneReview.objects.filter(submitted_contribution=submission).exists())

    def test_project_accept_proposal_allows_no_points(self):
        submission = self.create_submission()
        payload = rubric_payload(
            extras=['live_deployment', 'public_post'],
            overall_reason='Human reviewer found enough evidence for a project accept.',
        )

        response = self.client.post(
            f'/api/v1/steward-submissions/{submission.id}/propose/',
            data={
                'proposed_action': 'accept',
                'proposed_contribution_type': self.project_type.id,
                'proposed_user': self.submitter.id,
                'rubric_review': payload,
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        submission.refresh_from_db()
        self.assertEqual(submission.proposed_action, 'accept')
        self.assertIsNone(submission.proposed_points)
        review = submission.project_milestone_review
        self.assertEqual(review.action, 'accept')
        self.assertEqual(review.review_flow, ContributionType.REVIEW_FLOW_BUILDER_PROJECT)
        self.assertEqual(review.gate_failures, [])
        self.assertEqual(review.extras, ['live_deployment', 'public_post'])
        self.assertEqual(review.overall_reason, 'Human reviewer found enough evidence for a project accept.')
        self.assertEqual(review.sections['genlayer_fit']['score'], 3)
        self.assertEqual(review.sections['genlayer_fit']['reason'], 'Trustless adjudication is useful.')
        self.assertEqual(review.sections['contract_quality']['score'], 2)
        self.assertEqual(review.sections['contract_quality']['reason'], 'Contract has state and a meaningful validator.')
        self.assertEqual(review.sections['engineering']['score'], 2)
        self.assertEqual(review.sections['engineering']['reason'], 'Repository builds and has original structure.')
        self.assertEqual(review.sections['frontend_ux']['score'], 1)
        self.assertEqual(review.sections['frontend_ux']['reason'], 'Basic UI is wired to the contract.')
        self.assertEqual(response.data['rubric_review']['sections'], review.sections)
        self.assertEqual(response.data['rubric_review']['extras'], review.extras)
        self.assertEqual(response.data['rubric_review']['overall_reason'], review.overall_reason)
        note = SubmissionNote.objects.filter(
            submitted_contribution=submission,
            is_proposal=True,
        ).first()
        self.assertIsNotNone(note)
        self.assertNotIn('points**', note.message)

    def test_direct_project_accept_and_reject_require_rubric_review(self):
        for action in ['accept', 'reject']:
            submission = self.create_submission()
            data = {'action': action}
            if action == 'accept':
                data.update({
                    'points': 75,
                    'contribution_type': self.project_type.id,
                    'user': self.submitter.id,
                })
            else:
                data['staff_reply'] = 'Not enough project evidence.'

            with self.subTest(action=action):
                response = self.client.post(
                    f'/api/v1/steward-submissions/{submission.id}/review/',
                    data=data,
                    content_type='application/json',
                )

                self.assertEqual(response.status_code, 400)
                self.assertIn('rubric_review', response.data)
                self.assertFalse(ProjectMilestoneReview.objects.filter(submitted_contribution=submission).exists())

    def test_direct_standard_accept_does_not_require_rubric_review(self):
        submission = self.create_submission(self.standard_type)

        response = self.client.post(
            f'/api/v1/steward-submissions/{submission.id}/review/',
            data={
                'action': 'accept',
                'points': 5,
                'contribution_type': self.standard_type.id,
                'user': self.submitter.id,
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        submission.refresh_from_db()
        self.assertEqual(submission.state, 'accepted')
        self.assertFalse(ProjectMilestoneReview.objects.filter(submitted_contribution=submission).exists())

    def test_direct_standard_submission_reclassified_to_project_requires_and_stores_rubric(self):
        submission = self.create_submission(self.standard_type)

        missing_rubric_response = self.client.post(
            f'/api/v1/steward-submissions/{submission.id}/review/',
            data={
                'action': 'accept',
                'points': 75,
                'contribution_type': self.project_type.id,
                'user': self.submitter.id,
            },
            content_type='application/json',
        )

        self.assertEqual(missing_rubric_response.status_code, 400)
        self.assertIn('rubric_review', missing_rubric_response.data)

        response = self.client.post(
            f'/api/v1/steward-submissions/{submission.id}/review/',
            data={
                'action': 'accept',
                'points': 75,
                'contribution_type': self.project_type.id,
                'user': self.submitter.id,
                'rubric_review': rubric_payload(overall_reason=''),
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        submission.refresh_from_db()
        self.assertEqual(submission.state, 'accepted')
        self.assertEqual(submission.contribution_type, self.project_type)
        review = ProjectMilestoneReview.objects.get(submitted_contribution=submission)
        self.assertEqual(review.action, 'accept')
        self.assertEqual(review.review_flow, ContributionType.REVIEW_FLOW_BUILDER_PROJECT)
        self.assertEqual(response.data['rubric_review']['sections'], review.sections)

    def test_direct_project_more_info_clears_stale_proposal_rubric_review(self):
        submission = self.create_submission()
        self.client.post(
            f'/api/v1/steward-submissions/{submission.id}/propose/',
            data={
                'proposed_action': 'accept',
                'proposed_contribution_type': self.project_type.id,
                'proposed_user': self.submitter.id,
                'rubric_review': rubric_payload(),
            },
            content_type='application/json',
        )
        self.assertTrue(ProjectMilestoneReview.objects.filter(submitted_contribution=submission).exists())

        response = self.client.post(
            f'/api/v1/steward-submissions/{submission.id}/review/',
            data={
                'action': 'more_info',
                'staff_reply': 'Please add clearer milestone evidence.',
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        submission.refresh_from_db()
        self.assertEqual(submission.state, 'more_info_needed')
        self.assertIsNone(submission.proposed_action)
        self.assertFalse(ProjectMilestoneReview.objects.filter(submitted_contribution=submission).exists())
        self.assertIsNone(response.data['rubric_review'])

    def test_direct_project_accept_stores_rubric_review(self):
        submission = self.create_submission()
        payload = rubric_payload(
            sections={
                'genlayer_fit': {'score': 4},
                'contract_quality': {'score': 3, 'reason': ''},
                'engineering': {'score': 3, 'reason': '   '},
                'frontend_ux': {'score': 2},
            },
            extras=['live_deployment'],
            overall_reason='',
        )

        response = self.client.post(
            f'/api/v1/steward-submissions/{submission.id}/review/',
            data={
                'action': 'accept',
                'points': 75,
                'contribution_type': self.project_type.id,
                'user': self.submitter.id,
                'rubric_review': payload,
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        submission.refresh_from_db()
        self.assertEqual(submission.state, 'accepted')
        review = ProjectMilestoneReview.objects.get(submitted_contribution=submission)
        self.assertEqual(review.action, 'accept')
        self.assertIsNone(review.confidence)
        self.assertEqual(review.gate_failures, [])
        self.assertEqual(review.extras, ['live_deployment'])
        self.assertEqual(review.overall_reason, '')
        self.assertEqual(review.sections['genlayer_fit']['score'], 4)
        self.assertEqual(review.sections['genlayer_fit']['reason'], '')
        self.assertEqual(review.sections['engineering']['reason'], '')
        self.assertEqual(response.data['rubric_review']['sections'], review.sections)

        note = SubmissionNote.objects.filter(
            submitted_contribution=submission,
            is_proposal=False,
        ).first()
        self.assertIsNotNone(note)
        self.assertEqual(note.data['rubric_review_id'], review.id)
        self.assertIn('Rubric scores', note.message)

    def test_direct_project_reject_stores_gate_failure_rubric_review(self):
        submission = self.create_submission()

        response = self.client.post(
            f'/api/v1/steward-submissions/{submission.id}/review/',
            data={
                'action': 'reject',
                'staff_reply': 'The repository does not build.',
                'rubric_review': gate_payload(),
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        submission.refresh_from_db()
        self.assertEqual(submission.state, 'rejected')
        review = ProjectMilestoneReview.objects.get(submitted_contribution=submission)
        self.assertEqual(review.action, 'reject')
        self.assertEqual(review.gate_failures, ['repo_does_not_build'])
        self.assertEqual(review.sections, {})
        self.assertEqual(response.data['rubric_review']['gate_failures'], ['repo_does_not_build'])

        note = SubmissionNote.objects.filter(
            submitted_contribution=submission,
            is_proposal=False,
        ).first()
        self.assertIsNotNone(note)
        self.assertEqual(note.data['rubric_review_id'], review.id)
        self.assertIn('Gate failed', note.message)

    def test_direct_project_accept_rejects_gate_failure_rubric_review(self):
        submission = self.create_submission()

        response = self.client.post(
            f'/api/v1/steward-submissions/{submission.id}/review/',
            data={
                'action': 'accept',
                'points': 75,
                'contribution_type': self.project_type.id,
                'user': self.submitter.id,
                'rubric_review': gate_payload(),
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('action', response.data)
        self.assertFalse(ProjectMilestoneReview.objects.filter(submitted_contribution=submission).exists())

    def test_project_reject_proposal_stores_scores_reasons_and_extras_when_gate_passes(self):
        submission = self.create_submission()
        payload = rubric_payload(
            extras=['demo_video', 'public_post'],
            overall_reason='The work is real, but not enough for acceptance.',
        )

        response = self.client.post(
            f'/api/v1/steward-submissions/{submission.id}/propose/',
            data={
                'proposed_action': 'reject',
                'proposed_staff_reply': 'Not enough evidence for acceptance.',
                'rubric_review': payload,
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        review = ProjectMilestoneReview.objects.get(submitted_contribution=submission)
        self.assertEqual(review.action, 'reject')
        self.assertEqual(review.gate_failures, [])
        self.assertEqual(review.extras, ['demo_video', 'public_post'])
        self.assertEqual(review.overall_reason, 'The work is real, but not enough for acceptance.')
        self.assertEqual(review.sections['genlayer_fit']['score'], 3)
        self.assertEqual(review.sections['genlayer_fit']['reason'], 'Trustless adjudication is useful.')
        self.assertEqual(review.sections['contract_quality']['score'], 2)
        self.assertEqual(review.sections['contract_quality']['reason'], 'Contract has state and a meaningful validator.')
        self.assertEqual(review.sections['engineering']['score'], 2)
        self.assertEqual(review.sections['engineering']['reason'], 'Repository builds and has original structure.')
        self.assertEqual(review.sections['frontend_ux']['score'], 1)
        self.assertEqual(review.sections['frontend_ux']['reason'], 'Basic UI is wired to the contract.')
        self.assertEqual(response.data['rubric_review']['sections'], review.sections)
        self.assertEqual(response.data['rubric_review']['extras'], review.extras)

    def test_project_accept_proposal_allows_blank_section_reasons(self):
        submission = self.create_submission()
        payload = rubric_payload(sections={
            'genlayer_fit': {'score': 3},
            'contract_quality': {'score': 2, 'reason': ''},
            'engineering': {'score': 2, 'reason': '   '},
            'frontend_ux': {'score': 1},
        })

        response = self.client.post(
            f'/api/v1/steward-submissions/{submission.id}/propose/',
            data={
                'proposed_action': 'accept',
                'proposed_contribution_type': self.project_type.id,
                'proposed_user': self.submitter.id,
                'rubric_review': payload,
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        review = ProjectMilestoneReview.objects.get(submitted_contribution=submission)
        self.assertEqual(review.sections['genlayer_fit']['score'], 3)
        self.assertEqual(review.sections['genlayer_fit']['reason'], '')
        self.assertEqual(review.sections['engineering']['reason'], '')

    def test_project_proposal_requires_overall_reason(self):
        submission = self.create_submission()

        response = self.client.post(
            f'/api/v1/steward-submissions/{submission.id}/propose/',
            data={
                'proposed_action': 'accept',
                'proposed_contribution_type': self.project_type.id,
                'proposed_user': self.submitter.id,
                'rubric_review': rubric_payload(overall_reason=''),
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('overall_reason', response.data)

    def test_project_proposal_rejects_fractional_scores(self):
        submission = self.create_submission()

        for invalid_score in [4.9, '4.9']:
            payload = rubric_payload()
            payload['sections']['genlayer_fit']['score'] = invalid_score

            with self.subTest(invalid_score=invalid_score):
                response = self.client.post(
                    f'/api/v1/steward-submissions/{submission.id}/propose/',
                    data={
                        'proposed_action': 'accept',
                        'proposed_contribution_type': self.project_type.id,
                        'proposed_user': self.submitter.id,
                        'rubric_review': payload,
                    },
                    content_type='application/json',
                )

                self.assertEqual(response.status_code, 400)
                self.assertIn('sections', response.data)

        self.assertFalse(ProjectMilestoneReview.objects.filter(submitted_contribution=submission).exists())

    def test_standard_submission_reclassified_to_project_requires_and_stores_rubric(self):
        submission = self.create_submission(self.standard_type)

        missing_rubric_response = self.client.post(
            f'/api/v1/steward-submissions/{submission.id}/propose/',
            data={
                'proposed_action': 'accept',
                'proposed_contribution_type': self.project_type.id,
                'proposed_user': self.submitter.id,
            },
            content_type='application/json',
        )

        self.assertEqual(missing_rubric_response.status_code, 400)
        self.assertIn('rubric_review', missing_rubric_response.data)

        response = self.client.post(
            f'/api/v1/steward-submissions/{submission.id}/propose/',
            data={
                'proposed_action': 'accept',
                'proposed_contribution_type': self.project_type.id,
                'proposed_user': self.submitter.id,
                'rubric_review': rubric_payload(),
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        review = ProjectMilestoneReview.objects.get(submitted_contribution=submission)
        self.assertEqual(review.review_flow, ContributionType.REVIEW_FLOW_BUILDER_PROJECT)
        self.assertEqual(review.sections['genlayer_fit']['score'], 3)

    def test_project_submission_reclassified_to_standard_clears_existing_rubric(self):
        submission = self.create_submission()
        self.client.post(
            f'/api/v1/steward-submissions/{submission.id}/propose/',
            data={
                'proposed_action': 'accept',
                'proposed_contribution_type': self.project_type.id,
                'proposed_user': self.submitter.id,
                'rubric_review': rubric_payload(),
            },
            content_type='application/json',
        )
        self.assertTrue(ProjectMilestoneReview.objects.filter(submitted_contribution=submission).exists())

        response = self.client.post(
            f'/api/v1/steward-submissions/{submission.id}/propose/',
            data={
                'proposed_action': 'accept',
                'proposed_points': 5,
                'proposed_contribution_type': self.standard_type.id,
                'proposed_user': self.submitter.id,
                'rubric_review': rubric_payload(),
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(ProjectMilestoneReview.objects.filter(submitted_contribution=submission).exists())

    def test_standard_proposal_keeps_existing_points_requirement(self):
        submission = self.create_submission(self.standard_type)

        response = self.client.post(
            f'/api/v1/steward-submissions/{submission.id}/propose/',
            data={
                'proposed_action': 'accept',
                'proposed_contribution_type': self.standard_type.id,
                'proposed_user': self.submitter.id,
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('proposed_points', response.data)

        reject_response = self.client.post(
            f'/api/v1/steward-submissions/{submission.id}/propose/',
            data={
                'proposed_action': 'reject',
                'proposed_staff_reply': 'Not enough evidence.',
            },
            content_type='application/json',
        )

        self.assertEqual(reject_response.status_code, 200)
        self.assertFalse(ProjectMilestoneReview.objects.filter(submitted_contribution=submission).exists())

    def test_standard_proposal_rejects_unexpected_rubric_payload(self):
        submission = self.create_submission(self.standard_type)

        response = self.client.post(
            f'/api/v1/steward-submissions/{submission.id}/propose/',
            data={
                'proposed_action': 'reject',
                'proposed_staff_reply': 'Not enough evidence.',
                'rubric_review': {'unexpected': 'payload'},
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('rubric_review', response.data)
        self.assertFalse(ProjectMilestoneReview.objects.filter(submitted_contribution=submission).exists())


@override_settings(ALLOWED_HOSTS=['*'], AI_REVIEW_API_KEY='test-ai-review-key')
class ProjectMilestoneRubricAIProposalTests(APITestCase):
    def setUp(self):
        self.category, _ = Category.objects.get_or_create(
            slug='builder',
            defaults={
                'name': 'Builder',
                'description': 'Builder category',
            },
        )
        self.project_type = ContributionType.objects.create(
            name='Project',
            slug='ai-project',
            category=self.category,
            min_points=1,
            max_points=100,
            review_flow=ContributionType.REVIEW_FLOW_BUILDER_PROJECT,
        )
        self.standard_type = ContributionType.objects.create(
            name='AI Standard Builder',
            slug='ai-standard-builder',
            category=self.category,
            min_points=1,
            max_points=10,
        )
        self.submitter = User.objects.create_user(
            email='submitter-ai@example.com',
            address='0x3333333333333333333333333333333333333333',
        )
        self.ai_user, _ = User.objects.get_or_create(
            email='genlayer-steward@genlayer.foundation',
            defaults={
                'address': '0x4444444444444444444444444444444444444444',
                'name': 'GenLayer Steward',
                'visible': False,
            },
        )
        if not self.ai_user.name:
            self.ai_user.name = 'GenLayer Steward'
            self.ai_user.save(update_fields=['name'])

    def create_submission(self, contribution_type=None):
        submission = SubmittedContribution.objects.create(
            user=self.submitter,
            contribution_type=contribution_type or self.project_type,
            contribution_date=timezone.now(),
            notes='Project repository and demo.',
            state='pending',
        )
        Evidence.objects.create(
            submitted_contribution=submission,
            url='https://github.com/example/ai-project',
        )
        return submission

    def test_ai_project_proposal_stores_rubric_review(self):
        submission = self.create_submission()
        payload = rubric_payload(
            extras=['live_deployment', 'demo_video'],
            overall_reason='AI reviewer found enough evidence for an accept proposal.',
        )

        response = self.client.post(
            f'/api/v1/ai-review/{submission.id}/propose/',
            data={
                'proposed_action': 'accept',
                'confidence': 'medium',
                'reasoning': 'Project passes the gate.',
                'rubric_review': payload,
            },
            content_type='application/json',
            HTTP_X_AI_REVIEW_KEY='test-ai-review-key',
        )

        self.assertEqual(response.status_code, 200)
        review = ProjectMilestoneReview.objects.get(submitted_contribution=submission)
        self.assertEqual(review.proposer, self.ai_user)
        self.assertEqual(review.action, 'accept')
        self.assertEqual(review.confidence, 'medium')
        self.assertEqual(review.gate_failures, [])
        self.assertEqual(review.extras, ['live_deployment', 'demo_video'])
        self.assertEqual(review.overall_reason, 'AI reviewer found enough evidence for an accept proposal.')
        self.assertEqual(review.sections['genlayer_fit']['score'], 3)
        self.assertEqual(review.sections['genlayer_fit']['reason'], 'Trustless adjudication is useful.')
        self.assertEqual(review.sections['contract_quality']['score'], 2)
        self.assertEqual(review.sections['contract_quality']['reason'], 'Contract has state and a meaningful validator.')
        self.assertEqual(review.sections['engineering']['score'], 2)
        self.assertEqual(review.sections['engineering']['reason'], 'Repository builds and has original structure.')
        self.assertEqual(review.sections['frontend_ux']['score'], 1)
        self.assertEqual(review.sections['frontend_ux']['reason'], 'Basic UI is wired to the contract.')
        self.assertEqual(response.data['rubric_review']['sections'], review.sections)
        self.assertEqual(response.data['rubric_review']['extras'], review.extras)
        self.assertEqual(response.data['rubric_review']['overall_reason'], review.overall_reason)

        detail_response = self.client.get(
            f'/api/v1/ai-review/{submission.id}/',
            HTTP_X_AI_REVIEW_KEY='test-ai-review-key',
        )
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.data['rubric_review']['sections'], review.sections)
        self.assertEqual(detail_response.data['rubric_review']['gate_failures'], [])
        self.assertEqual(detail_response.data['rubric_review']['extras'], ['live_deployment', 'demo_video'])

        note = SubmissionNote.objects.filter(
            submitted_contribution=submission,
            user=self.ai_user,
            is_proposal=True,
        ).first()
        self.assertEqual(note.data['rubric_review_id'], review.id)
        self.assertNotIn('None points', note.message)
        self.assertNotIn('points**', note.message)

    def test_ai_project_proposal_put_updates_existing_rubric_review(self):
        submission = self.create_submission()
        self.client.post(
            f'/api/v1/ai-review/{submission.id}/propose/',
            data={
                'proposed_action': 'reject',
                'proposed_staff_reply': 'The repository does not build.',
                'confidence': 'low',
                'rubric_review': gate_payload(),
            },
            content_type='application/json',
            HTTP_X_AI_REVIEW_KEY='test-ai-review-key',
        )

        response = self.client.put(
            f'/api/v1/ai-review/{submission.id}/propose/',
            data={
                'proposed_action': 'accept',
                'confidence': 'high',
                'reasoning': 'Updated after a second pass.',
                'rubric_review': rubric_payload(overall_reason='Updated rubric after the repo was reviewed again.'),
            },
            content_type='application/json',
            HTTP_X_AI_REVIEW_KEY='test-ai-review-key',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ProjectMilestoneReview.objects.filter(submitted_contribution=submission).count(), 1)
        review = ProjectMilestoneReview.objects.get(submitted_contribution=submission)
        self.assertEqual(review.action, 'accept')
        self.assertEqual(review.confidence, 'high')
        self.assertEqual(review.gate_failures, [])

    def test_ai_standard_proposal_rejects_unexpected_rubric_payload(self):
        submission = self.create_submission(self.standard_type)

        response = self.client.post(
            f'/api/v1/ai-review/{submission.id}/propose/',
            data={
                'proposed_action': 'reject',
                'proposed_staff_reply': 'Not enough evidence.',
                'confidence': 'low',
                'rubric_review': {'unexpected': 'payload'},
            },
            content_type='application/json',
            HTTP_X_AI_REVIEW_KEY='test-ai-review-key',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('rubric_review', response.data)
        self.assertFalse(ProjectMilestoneReview.objects.filter(submitted_contribution=submission).exists())
