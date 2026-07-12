from datetime import timedelta
from unittest.mock import patch

from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from contributions.models import (
    Category,
    Contribution,
    ContributionType,
    Evidence,
    ReviewProposal,
    SubmissionNote,
    SubmittedContribution,
)
from contributions.reviewer_rewards import (
    REVIEWER_REWARD_TYPE_SLUG,
    compute_reviewer_reward,
)
from contributions.serializers import SubmittedContributionSerializer
from leaderboard.models import (
    BUILDER_LEADERBOARD_ELIGIBILITY_EXCLUDED_CONTRIBUTION_TYPE_SLUGS,
    GlobalLeaderboardMultiplier,
    REFERRAL_EXCLUDED_SLUGS,
)
from service_accounts.testing import service_account_auth_headers
from stewards.models import Steward, StewardPermission
from users.models import User


def rubric_payload(**overrides):
    payload = {
        'gate_failures': [],
        'sections': {
            'genlayer_fit': {'score': 4, 'reason': 'Strong GenLayer fit.'},
            'contract_quality': {'score': 3, 'reason': 'Meaningful contract state.'},
            'engineering': {'score': 3, 'reason': 'Solid implementation.'},
            'frontend_ux': {'score': 2, 'reason': 'Basic frontend.'},
        },
        'extras': ['live_deployment'],
        'overall_reason': 'Builder project review.',
    }
    payload.update(overrides)
    return payload


def gate_payload():
    return {
        'gate_failures': ['repo_does_not_build'],
        'sections': {},
        'extras': [],
        'overall_reason': 'The repository does not build.',
    }


def adjusted_payload(section_key='engineering', score=2):
    payload = rubric_payload()
    sections = {
        key: dict(value)
        for key, value in payload['sections'].items()
    }
    sections[section_key]['score'] = score
    payload['sections'] = sections
    return payload


@override_settings(ALLOWED_HOSTS=['*'])
class ReviewerRewardTests(APITestCase):
    def setUp(self):
        self.category, _ = Category.objects.get_or_create(
            slug='builder',
            defaults={'name': 'Builder', 'description': 'Builder category'},
        )
        self.project_type = ContributionType.objects.create(
            name='Reviewer Reward Project',
            slug='reviewer-reward-project',
            category=self.category,
            min_points=0,
            max_points=100,
            review_flow=ContributionType.REVIEW_FLOW_BUILDER_PROJECT,
        )
        self.standard_type = ContributionType.objects.create(
            name='Reviewer Reward Standard',
            slug='reviewer-reward-standard',
            category=self.category,
            min_points=0,
            max_points=100,
        )
        self.reward_type, _ = ContributionType.objects.get_or_create(
            slug=REVIEWER_REWARD_TYPE_SLUG,
            defaults={
                'name': 'Project Review Reward',
                'description': 'Reward for accurate Builder Project review proposals',
                'category': self.category,
                'min_points': 0,
                'max_points': 100,
                'is_submittable': False,
            },
        )
        for contribution_type in [self.project_type, self.standard_type, self.reward_type]:
            GlobalLeaderboardMultiplier.objects.get_or_create(
                contribution_type=contribution_type,
                defaults={
                    'multiplier_value': 1.0,
                    'valid_from': timezone.now() - timedelta(days=1),
                },
            )

        self.submitter = self.create_user('submitter@example.com', '0x1000000000000000000000000000000000000001')
        self.proposer = self.create_user('proposer@example.com', '0x1000000000000000000000000000000000000002', name='Proposal Steward')
        self.accepter = self.create_user('accepter@example.com', '0x1000000000000000000000000000000000000003', name='Accept Steward')
        self.other_steward = self.create_user('other@example.com', '0x1000000000000000000000000000000000000004', name='Other Steward')

        self.proposer_steward = Steward.objects.create(user=self.proposer)
        self.accepter_steward = Steward.objects.create(user=self.accepter)
        self.other_steward_profile = Steward.objects.create(user=self.other_steward)

        self.grant_permission(self.proposer_steward, self.project_type, 'propose')
        for action in ['accept', 'reject', 'request_more_info']:
            self.grant_permission(self.accepter_steward, self.project_type, action)
            self.grant_permission(self.other_steward_profile, self.project_type, action)
        for action in ['propose', 'accept', 'reject', 'request_more_info']:
            self.grant_permission(self.accepter_steward, self.standard_type, action)

    def create_user(self, email, address, name=''):
        return User.objects.create_user(
            email=email,
            address=address,
            name=name,
        )

    def grant_permission(self, steward, contribution_type, action):
        StewardPermission.objects.create(
            steward=steward,
            contribution_type=contribution_type,
            action=action,
        )

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
            url='https://github.com/example/reviewer-reward',
        )
        return submission

    def propose(self, submission, *, user=None, action='accept', payload=None):
        self.client.force_authenticate(user=user or self.proposer)
        return self.client.post(
            f'/api/v1/steward-submissions/{submission.id}/propose/',
            data={
                'proposed_action': action,
                'proposed_staff_reply': 'Needs more work.' if action in ('reject', 'more_info') else '',
                'rubric_review': payload or rubric_payload(),
            },
            content_type='application/json',
        )

    def review(self, submission, *, user=None, action='accept', payload=None, points=25):
        self.client.force_authenticate(user=user or self.accepter)
        data = {
            'action': action,
            'staff_reply': 'Final decision.',
        }
        if action == 'accept':
            data['points'] = points
        if payload is not None:
            data['rubric_review'] = payload
        elif action in ('accept', 'reject'):
            data['rubric_review'] = rubric_payload() if action == 'accept' else gate_payload()
        return self.client.post(
            f'/api/v1/steward-submissions/{submission.id}/review/',
            data=data,
            content_type='application/json',
        )

    def test_human_proposal_snapshot_and_exact_match_reward(self):
        submission = self.create_submission()

        propose_response = self.propose(submission)
        self.assertEqual(propose_response.status_code, 200)
        proposal = ReviewProposal.objects.get(submitted_contribution=submission)
        self.assertEqual(proposal.source, ReviewProposal.SOURCE_HUMAN)
        self.assertEqual(proposal.proposer, self.proposer)
        self.assertEqual(proposal.sections['genlayer_fit']['score'], 4)

        review_response = self.review(submission)
        self.assertEqual(review_response.status_code, 200)
        proposal.refresh_from_db()
        self.assertEqual(proposal.decided_by, self.accepter)
        self.assertEqual(proposal.final_action, 'accept')
        self.assertEqual(proposal.reward_points, 10)
        self.assertIsNotNone(proposal.reward_contribution)
        self.assertEqual(proposal.reward_contribution.user, self.proposer)
        self.assertEqual(proposal.reward_contribution.points, 10)
        self.assertEqual(proposal.reward_contribution.contribution_type.slug, REVIEWER_REWARD_TYPE_SLUG)

        note = SubmissionNote.objects.filter(
            submitted_contribution=submission,
            is_proposal=False,
            data__action='accept',
        ).first()
        self.assertEqual(note.data['review_proposal_id'], proposal.id)
        self.assertEqual(note.data['reviewer_reward']['points'], 10)
        self.assertIn('Reviewer reward: **10 points**', note.message)

    def test_reward_reduced_by_rubric_delta_and_zero_on_action_mismatch(self):
        submission = self.create_submission()
        self.assertEqual(self.propose(submission).status_code, 200)

        review_response = self.review(
            submission,
            payload=adjusted_payload('engineering', 1),
        )
        self.assertEqual(review_response.status_code, 200)
        proposal = ReviewProposal.objects.get(submitted_contribution=submission)
        self.assertEqual(proposal.reward_points, 6)
        self.assertEqual(proposal.reward_contribution.points, 6)

        mismatch = self.create_submission()
        self.assertEqual(self.propose(mismatch).status_code, 200)
        mismatch_response = self.review(
            mismatch,
            action='reject',
            payload=gate_payload(),
        )
        self.assertEqual(mismatch_response.status_code, 200)
        mismatch_proposal = ReviewProposal.objects.get(submitted_contribution=mismatch)
        self.assertEqual(mismatch_proposal.reward_points, 0)
        self.assertIsNone(mismatch_proposal.reward_contribution)
        self.assertFalse(
            Contribution.objects.filter(
                user=self.proposer,
                contribution_type=self.reward_type,
                notes__contains=str(mismatch.id),
            ).exists()
        )

    def test_reward_grant_failure_records_no_awarded_points(self):
        submission = self.create_submission()
        self.assertEqual(self.propose(submission).status_code, 200)

        with patch('contributions.views.grant_reviewer_reward', return_value=None):
            review_response = self.review(submission)
        self.assertEqual(review_response.status_code, 200)

        proposal = ReviewProposal.objects.get(submitted_contribution=submission)
        self.assertEqual(proposal.reward_points, 0)
        self.assertIsNone(proposal.reward_contribution)
        self.assertFalse(
            Contribution.objects.filter(
                user=self.proposer,
                contribution_type=self.reward_type,
                notes__contains=str(submission.id),
            ).exists()
        )

        note = SubmissionNote.objects.filter(
            submitted_contribution=submission,
            is_proposal=False,
            data__action='accept',
        ).first()
        self.assertEqual(note.data['reviewer_reward']['reason'], 'grant_failed')
        self.assertEqual(note.data['reviewer_reward']['points'], 0)
        self.assertIsNone(note.data['reviewer_reward']['contribution_id'])
        self.assertIn('Reviewer reward: eligible, but grant failed', note.message)

    def test_questioned_revision_appends_and_outcome_lands_on_latest(self):
        submission = self.create_submission()
        self.assertEqual(self.propose(submission).status_code, 200)
        first = ReviewProposal.objects.get(submitted_contribution=submission)

        self.client.force_authenticate(user=self.accepter)
        question_response = self.client.post(
            f'/api/v1/steward-submissions/{submission.id}/question-proposal/',
            data={'message': 'Recheck engineering evidence.'},
            content_type='application/json',
        )
        self.assertEqual(question_response.status_code, 200)
        first.refresh_from_db()
        self.assertEqual(first.questioned_by, self.accepter)
        self.assertEqual(first.question_feedback, 'Recheck engineering evidence.')

        revised_response = self.propose(
            submission,
            payload=adjusted_payload('engineering', 4),
        )
        self.assertEqual(revised_response.status_code, 200)
        self.assertEqual(ReviewProposal.objects.filter(submitted_contribution=submission).count(), 2)
        latest = ReviewProposal.objects.filter(submitted_contribution=submission).latest('created_at')

        review_response = self.review(
            submission,
            payload=adjusted_payload('engineering', 4),
        )
        self.assertEqual(review_response.status_code, 200)
        first.refresh_from_db()
        latest.refresh_from_db()
        self.assertIsNone(first.decided_at)
        self.assertIsNotNone(latest.decided_at)
        self.assertEqual(latest.reward_points, 10)

    def test_ai_analysis_survives_human_reproposal_and_is_steward_only(self):
        submission = self.create_submission()
        ai_client = APIClient()
        ai_auth = service_account_auth_headers(('ai_review:read', 'ai_review:propose'), name='test-ai-agent')

        ai_response = ai_client.post(
            f'/api/v1/ai-review/{submission.id}/propose/',
            data={
                'proposed_action': 'accept',
                'confidence': 'high',
                'reasoning': 'Project passes the automated review.',
                'synthesis': 'Automated synthesis with **markdown**.',
                'rubric_review': rubric_payload(),
            },
            content_type='application/json',
            **ai_auth,
        )
        self.assertEqual(ai_response.status_code, 200)
        ai_proposal = ReviewProposal.objects.get(
            submitted_contribution=submission,
            source=ReviewProposal.SOURCE_AI,
        )
        self.assertEqual(ai_proposal.synthesis, 'Automated synthesis with **markdown**.')
        self.assertEqual(ai_proposal.service_account_name, 'test-ai-agent')

        human_response = self.propose(
            submission,
            payload=adjusted_payload('contract_quality', 4),
        )
        self.assertEqual(human_response.status_code, 200)
        self.assertEqual(
            ReviewProposal.objects.filter(
                submitted_contribution=submission,
                source=ReviewProposal.SOURCE_AI,
            ).count(),
            1,
        )

        self.client.force_authenticate(user=self.accepter)
        detail_response = self.client.get(f'/api/v1/steward-submissions/{submission.id}/')
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.data['ai_analysis']['synthesis'], 'Automated synthesis with **markdown**.')
        self.assertEqual(
            detail_response.data['ai_analysis']['sections']['frontend_ux'],
            {'score': 2, 'reason': 'Basic frontend.'},
        )

        list_response = self.client.get(
            '/api/v1/steward-submissions/',
            data={'has_ai_analysis': 'true', 'assigned_to': 'unassigned'},
        )
        self.assertEqual(list_response.status_code, 200)
        results = list_response.data['results']
        ids = {str(item['id']) for item in results}
        self.assertIn(str(submission.id), ids)
        list_item = next(item for item in results if str(item['id']) == str(submission.id))
        self.assertEqual(
            list_item['ai_analysis']['sections']['frontend_ux'],
            {'score': 2, 'reason': 'Basic frontend.'},
        )

        submitter_payload = SubmittedContributionSerializer(submission).data
        self.assertNotIn('ai_analysis', submitter_payload)

    def test_self_ai_and_non_builder_reviews_do_not_grant_rewards(self):
        self.grant_permission(self.accepter_steward, self.project_type, 'propose')
        self_proposed = self.create_submission()
        self.assertEqual(self.propose(self_proposed, user=self.accepter).status_code, 200)
        self.assertEqual(self.review(self_proposed, user=self.accepter).status_code, 200)
        self_proposal = ReviewProposal.objects.get(submitted_contribution=self_proposed)
        self.assertEqual(self_proposal.reward_points, 0)
        self.assertIsNone(self_proposal.reward_contribution)

        standard = self.create_submission(self.standard_type)
        self.client.force_authenticate(user=self.accepter)
        standard_response = self.client.post(
            f'/api/v1/steward-submissions/{standard.id}/propose/',
            data={
                'proposed_action': 'accept',
                'proposed_points': 5,
                'proposed_staff_reply': '',
            },
            content_type='application/json',
        )
        self.assertEqual(standard_response.status_code, 200)
        self.assertFalse(ReviewProposal.objects.filter(submitted_contribution=standard).exists())

        ai_submission = self.create_submission()
        ai_client = APIClient()
        ai_auth = service_account_auth_headers(('ai_review:read', 'ai_review:propose'), name='test-ai-agent-2')
        self.assertEqual(
            ai_client.post(
                f'/api/v1/ai-review/{ai_submission.id}/propose/',
                data={
                    'proposed_action': 'accept',
                    'confidence': 'high',
                    'rubric_review': rubric_payload(),
                },
                content_type='application/json',
                **ai_auth,
            ).status_code,
            200,
        )
        self.assertEqual(self.review(ai_submission).status_code, 200)
        ai_proposal = ReviewProposal.objects.get(
            submitted_contribution=ai_submission,
            source=ReviewProposal.SOURCE_AI,
        )
        self.assertEqual(ai_proposal.reward_points, 0)
        self.assertIsNone(ai_proposal.reward_contribution)


class ReviewerRewardMathTests(APITestCase):
    def test_reward_math_and_constants(self):
        base_sections = rubric_payload()['sections']
        self.assertEqual(
            compute_reviewer_reward(
                proposed_action='accept',
                proposed_sections=base_sections,
                final_action='accept',
                final_sections=base_sections,
            ),
            10,
        )
        self.assertEqual(
            compute_reviewer_reward(
                proposed_action='accept',
                proposed_sections=base_sections,
                final_action='accept',
                final_sections=adjusted_payload('genlayer_fit', 3)['sections'],
            ),
            8,
        )
        self.assertEqual(
            compute_reviewer_reward(
                proposed_action='accept',
                proposed_sections=base_sections,
                final_action='reject',
                final_sections={},
            ),
            0,
        )
        self.assertEqual(
            compute_reviewer_reward(
                proposed_action='reject',
                proposed_sections={},
                final_action='reject',
                final_sections={},
            ),
            10,
        )
        self.assertIn(REVIEWER_REWARD_TYPE_SLUG, REFERRAL_EXCLUDED_SLUGS)
        self.assertIn(
            REVIEWER_REWARD_TYPE_SLUG,
            BUILDER_LEADERBOARD_ELIGIBILITY_EXCLUDED_CONTRIBUTION_TYPE_SLUGS,
        )

    @override_settings(REVIEWER_REWARD_BASE_POINTS=20, REVIEWER_REWARD_PENALTY_PER_SCORE_POINT=5)
    def test_settings_override_reward_knobs(self):
        self.assertEqual(
            compute_reviewer_reward(
                proposed_action='accept',
                proposed_sections=rubric_payload()['sections'],
                final_action='accept',
                final_sections=adjusted_payload('engineering', 2)['sections'],
            ),
            15,
        )
