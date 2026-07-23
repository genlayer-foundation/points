from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from contributions.ai_attribution import AI_STEWARD_EMAIL, get_ai_steward
from contributions.models import (
    Category,
    Contribution,
    ContributionHighlight,
    ContributionType,
    ProjectMilestoneReview,
    ReviewProposal,
    SubmissionNote,
    SubmissionStateTransition,
    SubmittedContribution,
)
from contributions.reviewer_rewards import REVIEWER_REWARD_TYPE_SLUG
from leaderboard.models import GlobalLeaderboardMultiplier
from stewards.models import Steward, StewardPermission
from users.models import User


def project_rubric():
    return {
        'gate_failures': [],
        'sections': {
            'genlayer_fit': {'score': 3, 'reason': 'Strong fit.'},
            'contract_quality': {'score': 2, 'reason': 'Sound contract.'},
            'engineering': {'score': 2, 'reason': 'Solid engineering.'},
            'frontend_ux': {'score': 1, 'reason': 'Usable frontend.'},
        },
        'extras': [],
        'overall_reason': 'Meets the project rubric.',
    }


class EscalationReviewTests(APITestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name='Escalation Tests',
            slug='escalation-tests',
            description='Escalation test category',
        )
        self.review_type = self.create_type(
            'Escalated Review',
            'escalated-review',
            threshold=400,
            multiplier=2,
        )
        self.no_threshold_type = self.create_type(
            'Ordinary Review',
            'ordinary-review',
            threshold=None,
            multiplier=2,
        )
        self.reward_type = ContributionType.objects.get(
            slug=REVIEWER_REWARD_TYPE_SLUG,
        )
        self.submitter = self.create_user(
            'escalation-submitter@example.com',
            '0x1000000000000000000000000000000000000001',
        )
        self.reviewer = self.create_user(
            'escalation-reviewer@example.com',
            '0x1000000000000000000000000000000000000002',
            name='Tier One',
        )
        self.other_reviewer = self.create_user(
            'escalation-other-reviewer@example.com',
            '0x1000000000000000000000000000000000000009',
            name='Other Tier One',
        )
        self.top_level = self.create_user(
            'escalation-top@example.com',
            '0x1000000000000000000000000000000000000003',
            name='Top Level',
        )
        self.apex_superuser = self.create_user(
            'escalation-admin@example.com',
            '0x1000000000000000000000000000000000000004',
            is_superuser=True,
            is_staff=True,
        )

        self.reviewer_steward = Steward.objects.create(user=self.reviewer)
        self.other_reviewer_steward = Steward.objects.create(user=self.other_reviewer)
        Steward.objects.create(user=self.top_level, tier=Steward.TIER_TOP_LEVEL)
        Steward.objects.create(user=self.apex_superuser)
        for contribution_type in (self.review_type, self.no_threshold_type):
            for steward in (self.reviewer_steward, self.other_reviewer_steward):
                for action in ('propose', 'accept', 'reject', 'request_more_info'):
                    StewardPermission.objects.create(
                        steward=steward,
                        contribution_type=contribution_type,
                        action=action,
                    )

        self.client = APIClient()

    def create_user(self, email, address, **extra):
        return User.objects.create_user(email=email, address=address, **extra)

    def create_type(self, name, slug, *, threshold, multiplier, review_flow='standard'):
        contribution_type, _ = ContributionType.objects.get_or_create(
            slug=slug,
            defaults={
                'name': name,
                'category': self.category,
                'min_points': 0,
                'max_points': 1000,
                'requires_ai_review': False,
                'escalation_threshold_points': threshold,
                'review_flow': review_flow,
            },
        )
        contribution_type.name = name
        contribution_type.category = self.category
        contribution_type.min_points = 0
        contribution_type.max_points = 1000
        contribution_type.requires_ai_review = False
        contribution_type.escalation_threshold_points = threshold
        contribution_type.review_flow = review_flow
        contribution_type.save(update_fields=[
            'name',
            'category',
            'min_points',
            'max_points',
            'requires_ai_review',
            'escalation_threshold_points',
            'review_flow',
            'updated_at',
        ])
        multipliers = GlobalLeaderboardMultiplier.objects.filter(
            contribution_type=contribution_type,
        )
        if multipliers.exists():
            multipliers.update(multiplier_value=multiplier)
        else:
            GlobalLeaderboardMultiplier.objects.create(
                contribution_type=contribution_type,
                multiplier_value=multiplier,
                valid_from=timezone.now() - timedelta(days=1),
            )
        return contribution_type

    def create_submission(self, contribution_type=None, *, user=None):
        return SubmittedContribution.objects.create(
            user=user or self.submitter,
            contribution_type=contribution_type or self.review_type,
            contribution_date=timezone.now(),
            notes='Review this contribution.',
            state='pending',
        )

    def review(
        self,
        submission,
        user,
        *,
        action='accept',
        points=200,
        contribution_type=None,
        **extra,
    ):
        self.client.force_authenticate(user=user)
        payload = {'action': action, **extra}
        if action == 'accept':
            payload['points'] = points
        else:
            payload.setdefault('staff_reply', 'Direct tier-one decision.')
        if contribution_type:
            payload['contribution_type'] = contribution_type.id
        return self.client.post(
            f'/api/v1/steward-submissions/{submission.id}/review/',
            payload,
            format='json',
        )

    def decision_rewards(self, user, submission, action):
        return Contribution.objects.filter(
            user=user,
            contribution_type=self.reward_type,
            notes=f"Review decision reward for submission {submission.id} [{action}]",
        )

    def test_threshold_boundary_converts_accept_to_proposal(self):
        below = self.create_submission()
        below_response = self.review(below, self.reviewer, points=199)
        self.assertEqual(below_response.status_code, status.HTTP_200_OK, below_response.data)
        below.refresh_from_db()
        self.assertEqual(below.state, 'accepted')
        self.assertEqual(below.converted_contribution.frozen_global_points, 398)

        at_threshold = self.create_submission()
        response = self.review(at_threshold, self.reviewer, points=200)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['state'], 'pending')
        self.assertIsNotNone(response.data['escalated_at'])

        at_threshold.refresh_from_db()
        self.assertEqual(at_threshold.state, 'pending')
        self.assertEqual(at_threshold.proposed_action, 'accept')
        self.assertEqual(at_threshold.proposed_points, 200)
        self.assertEqual(at_threshold.proposed_contribution_type, self.review_type)
        self.assertEqual(at_threshold.proposed_user, self.submitter)
        self.assertEqual(at_threshold.proposed_by, self.reviewer)
        self.assertEqual(
            at_threshold.proposal_review_status,
            SubmittedContribution.PROPOSAL_STATUS_PENDING_REVIEW,
        )
        self.assertIsNone(at_threshold.reviewed_by)
        self.assertIsNone(at_threshold.reviewed_at)
        self.assertIsNone(at_threshold.converted_contribution)
        proposal = ReviewProposal.objects.get(
            submitted_contribution=at_threshold,
            source=ReviewProposal.SOURCE_HUMAN,
        )
        self.assertEqual(proposal.proposer, self.reviewer)
        self.assertEqual(proposal.action, 'accept')
        self.assertEqual(proposal.points, 200)
        self.assertEqual(proposal.sections, {})
        self.assertFalse(
            self.decision_rewards(self.reviewer, at_threshold, 'accept').exists()
        )
        self.assertTrue(
            SubmissionStateTransition.objects.filter(
                submitted_contribution=at_threshold,
                event=SubmissionStateTransition.EVENT_ESCALATED,
                from_state='pending',
                to_state='pending',
                actor=self.reviewer,
            ).exists()
        )
        note = SubmissionNote.objects.get(
            submitted_contribution=at_threshold,
            data__action='escalate',
        )
        self.assertEqual(note.data['final_points'], 400)
        self.assertEqual(note.data['threshold'], 400)

    def test_missing_date_specific_multiplier_uses_one_for_escalation(self):
        submission = SubmittedContribution.objects.create(
            user=self.submitter,
            contribution_type=self.review_type,
            contribution_date=timezone.now() - timedelta(days=2),
            notes='Predates the available multiplier.',
            state='pending',
        )

        response = self.review(submission, self.reviewer, points=400)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        submission.refresh_from_db()
        self.assertEqual(submission.state, 'pending')
        self.assertIsNotNone(submission.escalated_at)
        self.assertIsNone(submission.converted_contribution)
        note = SubmissionNote.objects.get(
            submitted_contribution=submission,
            data__action='escalate',
        )
        self.assertEqual(note.data['final_points'], 400)
        self.assertEqual(note.data['threshold'], 400)

    def test_standard_escalation_rewards_follow_top_level_outcome(self):
        for action, final_points, expected_reward in (
            ('accept', 200, 10),
            ('accept', 100, 5),
            ('reject', None, 0),
        ):
            with self.subTest(
                action=action,
                final_points=final_points,
                expected_reward=expected_reward,
            ):
                submission = self.create_submission()
                escalated = self.review(submission, self.reviewer, points=200)
                self.assertEqual(
                    escalated.status_code,
                    status.HTTP_200_OK,
                    escalated.data,
                )
                proposal = ReviewProposal.objects.get(
                    submitted_contribution=submission,
                    source=ReviewProposal.SOURCE_HUMAN,
                )

                response = self.review(
                    submission,
                    self.top_level,
                    action=action,
                    points=final_points or 0,
                )

                self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
                proposal.refresh_from_db()
                self.assertEqual(proposal.decided_by, self.top_level)
                self.assertEqual(proposal.final_action, action)
                self.assertEqual(proposal.reward_points, expected_reward)
                if expected_reward:
                    self.assertEqual(proposal.reward_contribution.user, self.reviewer)
                    self.assertEqual(
                        proposal.reward_contribution.contribution_type,
                        self.reward_type,
                    )
                    self.assertEqual(
                        proposal.reward_contribution.points,
                        expected_reward,
                    )
                else:
                    self.assertIsNone(proposal.reward_contribution)
                    self.assertFalse(
                        Contribution.objects.filter(
                            user=self.reviewer,
                            contribution_type=self.reward_type,
                            notes=f"Project review reward for submission {submission.id}",
                        ).exists()
                    )

    def test_null_threshold_and_tier_two_accept_normally(self):
        ordinary = self.create_submission(self.no_threshold_type)
        ordinary_response = self.review(ordinary, self.reviewer, points=500)
        self.assertEqual(ordinary_response.status_code, status.HTTP_200_OK, ordinary_response.data)
        ordinary.refresh_from_db()
        self.assertEqual(ordinary.state, 'accepted')
        self.assertIsNone(ordinary.escalated_at)
        self.assertFalse(
            self.decision_rewards(self.reviewer, ordinary, 'accept').exists()
        )

        top_level_submission = self.create_submission()
        top_response = self.review(top_level_submission, self.top_level, points=200)
        self.assertEqual(top_response.status_code, status.HTTP_200_OK, top_response.data)
        top_level_submission.refresh_from_db()
        self.assertEqual(top_level_submission.state, 'accepted')
        self.assertEqual(top_level_submission.reviewed_by, self.top_level)
        self.assertFalse(
            self.decision_rewards(
                self.top_level,
                top_level_submission,
                'accept',
            ).exists()
        )

        superuser_submission = self.create_submission()
        super_response = self.review(superuser_submission, self.apex_superuser, points=200)
        self.assertEqual(super_response.status_code, status.HTTP_200_OK, super_response.data)
        superuser_submission.refresh_from_db()
        self.assertEqual(superuser_submission.state, 'accepted')
        self.assertFalse(
            self.decision_rewards(
                self.apex_superuser,
                superuser_submission,
                'accept',
            ).exists()
        )

    def test_tier_one_direct_reject_grants_once_and_records_note_data(self):
        submission = self.create_submission()

        response = self.review(submission, self.reviewer, action='reject')

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        reward = self.decision_rewards(
            self.reviewer,
            submission,
            'reject',
        ).get()
        self.assertEqual(reward.points, 10)
        self.assertEqual(reward.title, 'Review Decision Reward')
        note = SubmissionNote.objects.get(
            submitted_contribution=submission,
            is_proposal=False,
            data__action='reject',
        )
        self.assertEqual(note.data['decision_reward']['reason'], 'granted')
        self.assertEqual(note.data['decision_reward']['points'], 10)
        self.assertEqual(
            note.data['decision_reward']['contribution_id'],
            reward.id,
        )
        self.assertIn('Decision reward: **10 points** to Tier One.', note.message)

    def test_direct_decision_reward_is_deduplicated_after_appeal(self):
        submission = self.create_submission()
        first = self.review(submission, self.reviewer, action='reject')
        self.assertEqual(first.status_code, status.HTTP_200_OK, first.data)

        self.client.force_authenticate(user=self.submitter)
        appeal = self.client.post(
            f'/api/v1/submissions/{submission.id}/appeal/',
            {'reason': 'Please reconsider this decision.'},
            format='json',
        )
        self.assertEqual(appeal.status_code, status.HTTP_200_OK, appeal.data)

        second = self.review(submission, self.reviewer, action='reject')

        self.assertEqual(second.status_code, status.HTTP_200_OK, second.data)
        self.assertEqual(
            self.decision_rewards(
                self.reviewer,
                submission,
                'reject',
            ).count(),
            1,
        )
        duplicate_note = SubmissionNote.objects.filter(
            submitted_contribution=submission,
            is_proposal=False,
            data__action='reject',
        ).first()
        self.assertEqual(
            duplicate_note.data['decision_reward'],
            {
                'reason': 'duplicate',
                'points': 0,
                'contribution_id': None,
            },
        )

    def test_more_info_then_below_threshold_accept_grants_distinct_rewards(self):
        submission = self.create_submission()

        more_info = self.review(submission, self.reviewer, action='more_info')
        self.assertEqual(
            more_info.status_code,
            status.HTTP_200_OK,
            more_info.data,
        )
        accepted = self.review(submission, self.reviewer, points=199)

        self.assertEqual(accepted.status_code, status.HTTP_200_OK, accepted.data)
        self.assertEqual(
            self.decision_rewards(
                self.reviewer,
                submission,
                'more_info',
            ).get().points,
            10,
        )
        self.assertEqual(
            self.decision_rewards(
                self.reviewer,
                submission,
                'accept',
            ).get().points,
            10,
        )
        self.assertEqual(
            Contribution.objects.filter(
                user=self.reviewer,
                contribution_type=self.reward_type,
            ).count(),
            2,
        )

    def test_self_review_does_not_grant_direct_decision_reward(self):
        submission = self.create_submission(user=self.reviewer)

        response = self.review(submission, self.reviewer, action='reject')

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertFalse(
            self.decision_rewards(self.reviewer, submission, 'reject').exists()
        )

    def test_ai_steward_cannot_receive_direct_decision_reward(self):
        submission = self.create_submission()
        ai_user = get_ai_steward()

        response = self.review(submission, ai_user, action='reject')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(
            self.decision_rewards(ai_user, submission, 'reject').exists()
        )

    def test_threshold_uses_final_contribution_type(self):
        source_type = self.create_type(
            'Source Type',
            'escalation-source',
            threshold=None,
            multiplier=1,
        )
        for action in ('accept', 'reject', 'request_more_info'):
            StewardPermission.objects.create(
                steward=self.reviewer_steward,
                contribution_type=source_type,
                action=action,
            )
        submission = self.create_submission(source_type)

        response = self.review(
            submission,
            self.reviewer,
            points=200,
            contribution_type=self.review_type,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        submission.refresh_from_db()
        self.assertEqual(submission.state, 'pending')
        self.assertEqual(submission.contribution_type, source_type)
        self.assertEqual(submission.proposed_contribution_type, self.review_type)

    def test_escalated_proposal_can_be_reescalated_or_finalized_below_threshold(self):
        submission = self.create_submission()
        first_response = self.review(submission, self.reviewer, points=200)
        self.assertEqual(first_response.status_code, status.HTTP_200_OK, first_response.data)
        submission.refresh_from_db()
        first_escalated_at = submission.escalated_at

        second_response = self.review(submission, self.reviewer, points=250)
        self.assertEqual(second_response.status_code, status.HTTP_200_OK, second_response.data)
        submission.refresh_from_db()
        self.assertEqual(submission.state, 'pending')
        self.assertEqual(submission.proposed_points, 250)
        self.assertGreaterEqual(submission.escalated_at, first_escalated_at)
        self.assertEqual(
            SubmissionStateTransition.objects.filter(
                submitted_contribution=submission,
                event=SubmissionStateTransition.EVENT_ESCALATED,
            ).count(),
            2,
        )

        final_response = self.review(submission, self.reviewer, points=199)
        self.assertEqual(final_response.status_code, status.HTTP_200_OK, final_response.data)
        submission.refresh_from_db()
        self.assertEqual(submission.state, 'accepted')
        self.assertIsNone(submission.escalated_at)
        self.assertIsNone(submission.proposed_action)

    def test_more_info_accept_reopens_as_pending_when_escalated(self):
        submission = self.create_submission()
        submission.state = 'more_info_needed'
        submission.staff_reply = 'Please add deployment evidence.'
        submission.reviewed_by = self.reviewer
        submission.reviewed_at = timezone.now()
        submission.save()

        response = self.review(submission, self.reviewer, points=200)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        submission.refresh_from_db()
        self.assertEqual(submission.state, 'pending')
        self.assertEqual(submission.staff_reply, '')
        self.assertIsNone(submission.reviewed_by)
        self.assertIsNone(submission.reviewed_at)
        self.assertIsNotNone(submission.escalated_at)
        self.assertTrue(
            SubmissionStateTransition.objects.filter(
                submitted_contribution=submission,
                event=SubmissionStateTransition.EVENT_ESCALATED,
                from_state='more_info_needed',
                to_state='pending',
            ).exists()
        )

    def test_submitter_cancel_clears_escalation_marker(self):
        submission = self.create_submission()
        response = self.review(submission, self.reviewer, points=200)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        self.client.force_authenticate(user=self.submitter)
        response = self.client.delete(f'/api/v1/submissions/{submission.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        submission.refresh_from_db()
        self.assertEqual(submission.state, 'canceled')
        self.assertIsNone(submission.escalated_at)

    def test_submitter_sees_escalated_accept_as_pending_without_internal_marker(self):
        submission = self.create_submission()
        response = self.review(submission, self.reviewer, points=200)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        self.client.force_authenticate(user=self.submitter)
        response = self.client.get(f'/api/v1/submissions/{submission.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['state'], 'pending')
        self.assertNotIn('escalated_at', response.data)

    def test_tier_one_can_reject_or_request_more_info_on_escalated_proposal(self):
        for action, expected_state in (
            ('reject', 'rejected'),
            ('more_info', 'more_info_needed'),
        ):
            with self.subTest(action=action):
                submission = self.create_submission()
                response = self.review(submission, self.reviewer, points=200)
                self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

                self.client.force_authenticate(user=self.reviewer)
                response = self.client.post(
                    f'/api/v1/steward-submissions/{submission.id}/review/',
                    {
                        'action': action,
                        'staff_reply': 'Direct tier-one decision.',
                    },
                    format='json',
                )

                self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
                submission.refresh_from_db()
                self.assertEqual(submission.state, expected_state)
                self.assertIsNone(submission.escalated_at)
                self.assertIsNone(submission.proposed_action)

    def test_tier_one_rejecting_another_reviewers_escalation_gets_direct_reward(self):
        submission = self.create_submission()
        escalated = self.review(submission, self.reviewer, points=200)
        self.assertEqual(
            escalated.status_code,
            status.HTTP_200_OK,
            escalated.data,
        )
        proposal = ReviewProposal.objects.get(
            submitted_contribution=submission,
            source=ReviewProposal.SOURCE_HUMAN,
        )

        rejected = self.review(
            submission,
            self.other_reviewer,
            action='reject',
        )

        self.assertEqual(rejected.status_code, status.HTTP_200_OK, rejected.data)
        proposal.refresh_from_db()
        self.assertEqual(proposal.decided_by, self.other_reviewer)
        self.assertEqual(proposal.final_action, 'reject')
        self.assertEqual(proposal.reward_points, 0)
        self.assertIsNone(proposal.reward_contribution)
        self.assertEqual(
            self.decision_rewards(
                self.other_reviewer,
                submission,
                'reject',
            ).get().points,
            10,
        )

    def test_accept_only_escalator_can_revise_after_question(self):
        accept_only_user = self.create_user(
            'accept-only-escalator@example.com',
            '0x1000000000000000000000000000000000000005',
            name='Accept Only',
        )
        accept_only_steward = Steward.objects.create(user=accept_only_user)
        StewardPermission.objects.create(
            steward=accept_only_steward,
            contribution_type=self.review_type,
            action='accept',
        )
        submission = self.create_submission()

        response = self.review(submission, accept_only_user, points=200)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        self.client.force_authenticate(user=self.top_level)
        response = self.client.post(
            f'/api/v1/steward-submissions/{submission.id}/question-proposal/',
            {'message': 'Explain the requested award.'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        response = self.review(submission, accept_only_user, points=200)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        submission.refresh_from_db()
        self.assertEqual(submission.state, 'pending')
        self.assertEqual(
            submission.proposal_review_status,
            SubmittedContribution.PROPOSAL_STATUS_PENDING_REVIEW,
        )
        self.assertEqual(submission.proposal_review_feedback, '')
        self.assertIsNone(submission.proposal_questioned_by)
        self.assertIsNotNone(submission.escalated_at)
        self.assertEqual(
            SubmissionStateTransition.objects.filter(
                submitted_contribution=submission,
                event=SubmissionStateTransition.EVENT_ESCALATED,
            ).count(),
            2,
        )

    def test_finalizing_accept_as_milestone_recomputes_reserved_versions(self):
        source_type = self.create_type(
            'Milestone Source',
            'milestone-source',
            threshold=None,
            multiplier=1,
        )
        project_type = self.create_type(
            'Projects',
            'projects',
            threshold=None,
            multiplier=1,
        )
        milestone_type = self.create_type(
            'Milestones',
            'milestones',
            threshold=10,
            multiplier=1,
        )
        for contribution_type in (source_type, milestone_type):
            StewardPermission.objects.create(
                steward=self.reviewer_steward,
                contribution_type=contribution_type,
                action='accept',
            )
        project = Contribution.objects.create(
            user=self.submitter,
            contribution_type=project_type,
            points=10,
            title='Highlighted project',
        )
        ContributionHighlight.objects.create(
            contribution=project,
            title='Highlighted project',
            description='Milestone anchor.',
        )
        submissions = [self.create_submission(source_type) for _ in range(2)]

        for submission in submissions:
            response = self.review(
                submission,
                self.reviewer,
                points=10,
                contribution_type=milestone_type,
                project_contribution=project.id,
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            submission.refresh_from_db()
            self.assertEqual(submission.state, 'pending')

        for submission in submissions:
            response = self.review(
                submission,
                self.top_level,
                points=10,
                contribution_type=milestone_type,
                project_contribution=project.id,
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        versions = []
        for submission in submissions:
            submission.refresh_from_db()
            versions.append(submission.converted_contribution.milestone_version)
        self.assertEqual(versions, [1, 2])

    def test_changed_type_escalation_preserves_existing_milestone_link(self):
        project_type = self.create_type(
            'Projects',
            'projects',
            threshold=None,
            multiplier=1,
        )
        milestone_type = self.create_type(
            'Milestones',
            'milestones',
            threshold=None,
            multiplier=1,
        )
        StewardPermission.objects.create(
            steward=self.reviewer_steward,
            contribution_type=milestone_type,
            action='accept',
        )
        project = Contribution.objects.create(
            user=self.submitter,
            contribution_type=project_type,
            points=10,
            title='Existing milestone project',
        )
        ContributionHighlight.objects.create(
            contribution=project,
            title='Existing milestone project',
            description='Milestone anchor.',
        )
        submission = self.create_submission(milestone_type)
        submission.project_contribution = project
        submission.milestone_version = 3
        submission.save(update_fields=[
            'project_contribution',
            'milestone_version',
            'updated_at',
        ])

        response = self.review(
            submission,
            self.reviewer,
            points=200,
            contribution_type=self.review_type,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        submission.refresh_from_db()
        self.assertEqual(submission.state, 'pending')
        self.assertEqual(submission.project_contribution, project)
        self.assertEqual(submission.milestone_version, 3)

        ContributionHighlight.objects.filter(contribution=project).delete()

        response = self.review(
            submission,
            self.reviewer,
            points=10,
            contribution_type=milestone_type,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        submission.refresh_from_db()
        self.assertEqual(submission.state, 'accepted')
        self.assertEqual(submission.converted_contribution.project_contribution, project)
        self.assertEqual(submission.converted_contribution.milestone_version, 3)

    def test_new_proposal_and_bulk_reject_clear_escalation_marker(self):
        proposed = self.create_submission()
        self.review(proposed, self.reviewer, points=200)
        self.client.force_authenticate(user=self.reviewer)
        proposal_response = self.client.post(
            f'/api/v1/steward-submissions/{proposed.id}/propose/',
            {
                'proposed_action': 'accept',
                'proposed_points': 100,
            },
            format='json',
        )
        self.assertEqual(proposal_response.status_code, status.HTTP_200_OK, proposal_response.data)
        proposed.refresh_from_db()
        self.assertIsNone(proposed.escalated_at)

        rejected = self.create_submission()
        self.review(rejected, self.reviewer, points=200)
        bulk_response = self.client.post(
            '/api/v1/steward-submissions/bulk-reject/',
            {
                'submission_ids': [str(rejected.id)],
                'staff_reply': 'Not eligible.',
            },
            format='json',
        )
        self.assertEqual(bulk_response.status_code, status.HTTP_200_OK, bulk_response.data)
        rejected.refresh_from_db()
        self.assertEqual(rejected.state, 'rejected')
        self.assertIsNone(rejected.escalated_at)
        self.assertFalse(
            self.decision_rewards(self.reviewer, rejected, 'reject').exists()
        )

    def test_standard_proposal_does_not_rebind_superseded_escalation_snapshot(self):
        submission = self.create_submission()
        escalated = self.review(submission, self.reviewer, points=200)
        self.assertEqual(escalated.status_code, status.HTTP_200_OK, escalated.data)
        escalation_proposal = ReviewProposal.objects.get(
            submitted_contribution=submission,
            source=ReviewProposal.SOURCE_HUMAN,
        )

        self.client.force_authenticate(user=self.reviewer)
        replacement = self.client.post(
            f'/api/v1/steward-submissions/{submission.id}/propose/',
            {
                'proposed_action': 'accept',
                'proposed_points': 100,
            },
            format='json',
        )
        self.assertEqual(
            replacement.status_code,
            status.HTTP_200_OK,
            replacement.data,
        )

        project_type = self.create_type(
            'Replacement Project',
            'replacement-project',
            threshold=None,
            multiplier=1,
            review_flow=ContributionType.REVIEW_FLOW_BUILDER_PROJECT,
        )
        finalized = self.review(
            submission,
            self.top_level,
            points=100,
            contribution_type=project_type,
            rubric_review=project_rubric(),
        )

        self.assertEqual(finalized.status_code, status.HTTP_200_OK, finalized.data)
        escalation_proposal.refresh_from_db()
        self.assertIsNone(escalation_proposal.decided_at)
        self.assertIsNone(escalation_proposal.reward_points)
        self.assertIsNone(escalation_proposal.reward_contribution)
        note = SubmissionNote.objects.get(
            submitted_contribution=submission,
            is_proposal=False,
            data__action='accept',
        )
        self.assertIsNone(note.data['review_proposal_id'])
        self.assertIsNone(note.data['reviewer_reward'])

    def test_update_accepted_cannot_cross_threshold_at_tier_one(self):
        submission = self.create_submission()
        accepted_response = self.review(submission, self.top_level, points=100)
        self.assertEqual(accepted_response.status_code, status.HTTP_200_OK, accepted_response.data)

        self.client.force_authenticate(user=self.reviewer)
        blocked = self.client.post(
            f'/api/v1/steward-submissions/{submission.id}/update-accepted/',
            {'points': 200},
            format='json',
        )
        self.assertEqual(blocked.status_code, status.HTTP_403_FORBIDDEN, blocked.data)
        submission.refresh_from_db()
        self.assertEqual(submission.converted_contribution.points, 100)

        allowed = self.client.post(
            f'/api/v1/steward-submissions/{submission.id}/update-accepted/',
            {'points': 199},
            format='json',
        )
        self.assertEqual(allowed.status_code, status.HTTP_200_OK, allowed.data)
        submission.refresh_from_db()
        self.assertEqual(submission.converted_contribution.frozen_global_points, 398)

    def test_update_accepted_allows_downward_and_unchanged_above_threshold(self):
        submission = self.create_submission()
        accepted_response = self.review(submission, self.top_level, points=500)
        self.assertEqual(accepted_response.status_code, status.HTTP_200_OK, accepted_response.data)

        self.client.force_authenticate(user=self.reviewer)
        downward = self.client.post(
            f'/api/v1/steward-submissions/{submission.id}/update-accepted/',
            {'points': 250},
            format='json',
        )
        self.assertEqual(downward.status_code, status.HTTP_200_OK, downward.data)
        submission.refresh_from_db()
        self.assertEqual(submission.converted_contribution.frozen_global_points, 500)

        unchanged = self.client.post(
            f'/api/v1/steward-submissions/{submission.id}/update-accepted/',
            {
                'points': 250,
                'create_highlight': True,
                'highlight_title': 'Corrected contribution',
                'highlight_description': 'Points unchanged.',
            },
            format='json',
        )
        self.assertEqual(unchanged.status_code, status.HTTP_200_OK, unchanged.data)
        submission.refresh_from_db()
        self.assertEqual(submission.converted_contribution.frozen_global_points, 500)
        self.assertTrue(
            ContributionHighlight.objects.filter(
                contribution=submission.converted_contribution,
                title='Corrected contribution',
            ).exists()
        )

    def test_tier_one_finalizer_can_receive_decision_and_proposal_rewards(self):
        project_type = self.create_type(
            'Direct Reward Project',
            'direct-reward-project',
            threshold=20,
            multiplier=1,
            review_flow=ContributionType.REVIEW_FLOW_BUILDER_PROJECT,
        )
        for steward in (self.reviewer_steward, self.other_reviewer_steward):
            for action in ('propose', 'accept', 'reject', 'request_more_info'):
                StewardPermission.objects.create(
                    steward=steward,
                    contribution_type=project_type,
                    action=action,
                )
        submission = self.create_submission(project_type)

        self.client.force_authenticate(user=self.reviewer)
        proposed = self.client.post(
            f'/api/v1/steward-submissions/{submission.id}/propose/',
            {
                'proposed_action': 'accept',
                'proposed_points': 10,
                'rubric_review': project_rubric(),
            },
            format='json',
        )
        self.assertEqual(proposed.status_code, status.HTTP_200_OK, proposed.data)
        proposal = ReviewProposal.objects.get(
            submitted_contribution=submission,
            source=ReviewProposal.SOURCE_HUMAN,
        )

        accepted = self.review(
            submission,
            self.other_reviewer,
            points=10,
            rubric_review=project_rubric(),
        )

        self.assertEqual(accepted.status_code, status.HTTP_200_OK, accepted.data)
        proposal.refresh_from_db()
        self.assertEqual(proposal.reward_points, 10)
        self.assertEqual(proposal.reward_contribution.user, self.reviewer)
        decision_reward = self.decision_rewards(
            self.other_reviewer,
            submission,
            'accept',
        ).get()
        self.assertEqual(decision_reward.points, 10)
        note = SubmissionNote.objects.get(
            submitted_contribution=submission,
            is_proposal=False,
            data__action='accept',
        )
        self.assertEqual(note.data['reviewer_reward']['points'], 10)
        self.assertEqual(note.data['decision_reward']['points'], 10)
        self.assertEqual(
            Contribution.objects.filter(
                contribution_type=self.reward_type,
            ).count(),
            2,
        )

    def test_project_escalation_creates_human_rubric_proposal(self):
        project_type = self.create_type(
            'Escalated Project',
            'escalated-project',
            threshold=10,
            multiplier=1,
            review_flow=ContributionType.REVIEW_FLOW_BUILDER_PROJECT,
        )
        for action in ('accept', 'reject', 'request_more_info'):
            StewardPermission.objects.create(
                steward=self.reviewer_steward,
                contribution_type=project_type,
                action=action,
            )
        submission = self.create_submission(project_type)

        response = self.review(
            submission,
            self.reviewer,
            points=10,
            rubric_review=project_rubric(),
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        rubric = ProjectMilestoneReview.objects.get(submitted_contribution=submission)
        proposal = ReviewProposal.objects.get(
            submitted_contribution=submission,
            source=ReviewProposal.SOURCE_HUMAN,
        )
        self.assertEqual(rubric.proposer, self.reviewer)
        self.assertEqual(rubric.action, 'accept')
        self.assertEqual(proposal.proposer, self.reviewer)
        self.assertEqual(proposal.points, 10)
        self.assertEqual(proposal.sections, rubric.sections)

        top_response = self.review(
            submission,
            self.top_level,
            points=10,
            rubric_review=project_rubric(),
        )

        self.assertEqual(top_response.status_code, status.HTTP_200_OK, top_response.data)
        submission.refresh_from_db()
        proposal.refresh_from_db()
        self.assertEqual(submission.state, 'accepted')
        self.assertEqual(proposal.decided_by, self.top_level)
        self.assertEqual(proposal.reward_points, 10)
        self.assertEqual(proposal.reward_contribution.user, self.reviewer)
        self.assertEqual(
            proposal.reward_contribution.contribution_type,
            self.reward_type,
        )


class AIReviewGateVisibilityTests(APITestCase):
    def setUp(self):
        category = Category.objects.create(
            name='Gate Tests',
            slug='gate-tests',
            description='Gate test category',
        )
        self.gated_type = ContributionType.objects.create(
            name='AI Gated',
            slug='ai-gated',
            category=category,
            min_points=0,
            max_points=100,
            requires_ai_review=True,
        )
        self.ungated_type = ContributionType.objects.create(
            name='Human Review',
            slug='human-review',
            category=category,
            min_points=0,
            max_points=100,
            requires_ai_review=False,
        )
        self.submitter = User.objects.create_user(
            email='gate-submitter@example.com',
            address='0x2000000000000000000000000000000000000001',
        )
        self.reviewer = User.objects.create_user(
            email='gate-reviewer@example.com',
            address='0x2000000000000000000000000000000000000002',
        )
        self.proposer = User.objects.create_user(
            email='gate-proposer@example.com',
            address='0x2000000000000000000000000000000000000003',
        )
        self.top_level = User.objects.create_user(
            email='gate-top@example.com',
            address='0x2000000000000000000000000000000000000004',
        )
        reviewer = Steward.objects.create(user=self.reviewer)
        proposer = Steward.objects.create(user=self.proposer)
        Steward.objects.create(user=self.top_level, tier=Steward.TIER_TOP_LEVEL)
        for contribution_type in (self.gated_type, self.ungated_type):
            StewardPermission.objects.create(
                steward=reviewer,
                contribution_type=contribution_type,
                action='accept',
            )
            StewardPermission.objects.create(
                steward=proposer,
                contribution_type=contribution_type,
                action='propose',
            )
        self.client = APIClient()

    def create_submission(self, contribution_type=None, **extra):
        return SubmittedContribution.objects.create(
            user=self.submitter,
            contribution_type=contribution_type or self.gated_type,
            contribution_date=timezone.now(),
            notes='AI gate test.',
            state='pending',
            **extra,
        )

    def visible_ids(self, user):
        self.client.force_authenticate(user=user)
        response = self.client.get('/api/v1/steward-submissions/')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return {str(item['id']) for item in response.data['results']}

    def test_unreviewed_gated_submission_is_hidden_from_tier_one_roles(self):
        submission = self.create_submission()

        self.assertNotIn(str(submission.id), self.visible_ids(self.reviewer))
        self.assertNotIn(str(submission.id), self.visible_ids(self.proposer))

        self.client.force_authenticate(user=self.reviewer)
        detail = self.client.get(f'/api/v1/steward-submissions/{submission.id}/')
        self.assertEqual(detail.status_code, status.HTTP_404_NOT_FOUND)
        review = self.client.post(
            f'/api/v1/steward-submissions/{submission.id}/review/',
            {'action': 'accept', 'points': 10},
            format='json',
        )
        self.assertEqual(review.status_code, status.HTTP_404_NOT_FOUND)

    def test_gate_visibility_query_does_not_create_ai_steward(self):
        self.create_submission()
        ai_steward_count = User.objects.filter(email=AI_STEWARD_EMAIL).count()

        self.visible_ids(self.reviewer)

        self.assertEqual(
            User.objects.filter(email=AI_STEWARD_EMAIL).count(),
            ai_steward_count,
        )

    def test_gate_exceptions_are_visible_to_tier_one(self):
        ai_user = get_ai_steward()
        with_ai_note = self.create_submission()
        SubmissionNote.objects.create(
            submitted_contribution=with_ai_note,
            user=ai_user,
            message='AI proposal recorded.',
            is_proposal=True,
        )

        with_ai_rubric = self.create_submission()
        ReviewProposal.objects.create(
            submitted_contribution=with_ai_rubric,
            proposer=ai_user,
            source=ReviewProposal.SOURCE_AI,
            action='accept',
            points=10,
        )

        with_human_proposal = self.create_submission(
            proposed_action='accept',
            proposed_points=10,
            proposed_by=self.proposer,
            proposed_at=timezone.now(),
        )
        appealed = self.create_submission(has_appeal=True, appeal_reason='Reconsider.')
        resubmitted = self.create_submission()
        SubmissionStateTransition.objects.create(
            submitted_contribution=resubmitted,
            event=SubmissionStateTransition.EVENT_EDITED,
            from_state='more_info_needed',
            to_state='pending',
            actor=self.submitter,
        )

        expected = {
            str(with_ai_note.id),
            str(with_ai_rubric.id),
            str(with_human_proposal.id),
            str(appealed.id),
            str(resubmitted.id),
        }
        self.assertTrue(expected <= self.visible_ids(self.reviewer))
        self.assertTrue(expected <= self.visible_ids(self.proposer))

    def test_assigned_gated_submission_is_visible_only_to_its_tier_one_assignee(self):
        assigned = self.create_submission(assigned_to=self.reviewer)

        self.assertIn(str(assigned.id), self.visible_ids(self.reviewer))
        self.assertNotIn(str(assigned.id), self.visible_ids(self.proposer))

        self.client.force_authenticate(user=self.reviewer)
        detail = self.client.get(f'/api/v1/steward-submissions/{assigned.id}/')
        self.assertEqual(detail.status_code, status.HTTP_200_OK, detail.data)

    def test_tier_two_and_ungated_types_bypass_gate(self):
        gated = self.create_submission()
        ungated = self.create_submission(self.ungated_type)

        self.assertIn(str(ungated.id), self.visible_ids(self.reviewer))
        self.assertNotIn(str(gated.id), self.visible_ids(self.reviewer))
        self.assertTrue(
            {str(gated.id), str(ungated.id)} <= self.visible_ids(self.top_level)
        )
