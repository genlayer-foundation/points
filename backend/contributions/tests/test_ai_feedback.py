from copy import deepcopy
from datetime import timedelta
from unittest.mock import Mock, patch

from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from contributions.ai_attribution import get_ai_steward
from contributions.models import (
    AIReviewFeedback,
    Category,
    ContributionType,
    Evidence,
    ReviewProposal,
    SubmissionNote,
    SubmissionStateTransition,
    SubmittedContribution,
)
from leaderboard.models import GlobalLeaderboardMultiplier
from service_accounts.models import ServiceAccount, ServiceAccountToken
from stewards.models import Steward, StewardPermission
from users.models import User


SHA = 'a' * 40
RUBRIC_SECTIONS = {
    'genlayer_fit': {'score': 4, 'reason': 'Uses GenLayer directly.'},
    'contract_quality': {'score': 4, 'reason': 'Contract is well structured.'},
    'engineering': {'score': 3, 'reason': 'Implementation is complete.'},
    'frontend_ux': {'score': 3, 'reason': 'Frontend is usable.'},
}


def _address(number):
    return f'0x{number:040x}'


def _grant_permissions(user, contribution_type, actions=None):
    steward = Steward.objects.create(user=user)
    for action in actions or ('propose', 'accept', 'reject', 'request_more_info'):
        StewardPermission.objects.create(
            steward=steward,
            contribution_type=contribution_type,
            action=action,
        )
    return steward


def _issue(scopes=('ai_review:read',), name='feedback-benchmark'):
    account = ServiceAccount.objects.create(name=name)
    _, plaintext = ServiceAccountToken.issue(account, list(scopes))
    return plaintext


def _bearer(plaintext):
    return {'HTTP_AUTHORIZATION': f'Bearer {plaintext}'}


@override_settings(ALLOWED_HOSTS=['*'])
class StewardAIFeedbackTests(APITestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name='Feedback Builder',
            slug='feedback-builder',
        )
        self.contribution_type = ContributionType.objects.create(
            name='Feedback Project',
            slug='feedback-project',
            category=self.category,
            min_points=1,
            max_points=100,
            review_flow=ContributionType.REVIEW_FLOW_BUILDER_PROJECT,
        )
        GlobalLeaderboardMultiplier.objects.create(
            contribution_type=self.contribution_type,
            multiplier_value=1,
            valid_from=timezone.now() - timedelta(days=1),
        )
        self.submitter = User.objects.create_user(
            email='feedback-submitter@test.com',
            address=_address(1),
            name='Submitter',
        )
        self.reviewer = User.objects.create_user(
            email='feedback-reviewer@test.com',
            address=_address(2),
            name='Reviewer One',
        )
        _grant_permissions(self.reviewer, self.contribution_type)
        self.ai_user = get_ai_steward()
        self.submission = self._make_submission(
            proposed_by=self.ai_user,
            proposed_action='accept',
        )
        self.proposal = self._make_proposal(self.submission)
        self.url = (
            f'/api/v1/steward-submissions/{self.submission.id}/ai-feedback/'
        )
        self.client.force_authenticate(user=self.reviewer)

    def _make_submission(self, **overrides):
        values = {
            'user': self.submitter,
            'contribution_type': self.contribution_type,
            'contribution_date': timezone.now(),
            'title': 'Structured feedback project',
            'notes': 'A project submission for feedback tests.',
            'state': 'pending',
        }
        values.update(overrides)
        return SubmittedContribution.objects.create(**values)

    def _make_proposal(self, submission, **overrides):
        values = {
            'submitted_contribution': submission,
            'proposer': self.ai_user,
            'source': ReviewProposal.SOURCE_AI,
            'service_account_name': 'test-agent',
            'action': 'accept',
            'points': 50,
            'confidence': 'high',
            'sections': RUBRIC_SECTIONS,
            'overall_reason': 'Good submission.',
            'synthesis': 'The submission meets the rubric.',
        }
        values.update(overrides)
        return ReviewProposal.objects.create(**values)

    def _payload(self, **overrides):
        payload = {
            'review_proposal_id': self.proposal.id,
            'verdict': 'agree',
        }
        payload.update(overrides)
        return payload

    def _revision_payload(self, record, **overrides):
        return self._payload(
            expected_updated_at=record.data['updated_at'],
            **overrides,
        )

    def test_one_click_agree_binds_without_submission_side_effects(self):
        initial_updated_at = self.submission.updated_at
        initial_proposal_updated_at = self.proposal.updated_at
        transition_count = SubmissionStateTransition.objects.filter(
            submitted_contribution=self.submission,
        ).count()
        note_count = SubmissionNote.objects.filter(
            submitted_contribution=self.submission,
        ).count()

        with patch('contributions.ai_feedback.requests.get') as request_get:
            response = self.client.post(self.url, self._payload(), format='json')

        self.assertEqual(response.status_code, 201, response.data)
        request_get.assert_not_called()
        feedback = AIReviewFeedback.objects.get()
        self.assertEqual(feedback.review_proposal, self.proposal)
        self.assertEqual(
            feedback.proposal_source,
            AIReviewFeedback.PROPOSAL_SOURCE_REVIEW,
        )
        self.assertEqual(feedback.proposal_source_id, self.proposal.id)
        self.assertEqual(feedback.proposal_ref, self.proposal.created_at)
        self.assertEqual(feedback.reviewer, self.reviewer)
        self.assertEqual(feedback.verdict, 'agree')
        self.assertEqual(feedback.criteria, {})
        self.assertEqual(feedback.error_claims, [])
        self.assertEqual(response.data['reviewed_commit_sha'], None)
        self.assertEqual(response.data['correct_decision'], None)

        self.submission.refresh_from_db()
        self.assertEqual(self.submission.state, 'pending')
        self.assertEqual(self.submission.updated_at, initial_updated_at)
        self.assertEqual(self.submission.proposed_action, 'accept')
        self.assertEqual(self.submission.proposed_by, self.ai_user)
        self.proposal.refresh_from_db()
        self.assertEqual(self.proposal.updated_at, initial_proposal_updated_at)
        self.assertEqual(
            SubmissionStateTransition.objects.filter(
                submitted_contribution=self.submission,
            ).count(),
            transition_count,
        )
        self.assertEqual(
            SubmissionNote.objects.filter(
                submitted_contribution=self.submission,
            ).count(),
            note_count,
        )

    def test_closed_vocabularies_and_exact_shapes_return_400(self):
        invalid_payloads = [
            self._payload(verdict='mostly_agree'),
            self._payload(
                verdict='disagree',
                correct_decision='revise',
            ),
            self._payload(unexpected=True),
            self._payload(gate_failures=None),
            self._payload(criteria=None),
            self._payload(error_claims=None),
            self._payload(expected_updated_at='not-a-timestamp'),
            self._payload(criteria={'unknown_section': {'agree': True}}),
            self._payload(criteria={'engineering': 4}),
            self._payload(criteria={'engineering': {'agree': False}}),
            self._payload(
                criteria={'engineering': {'agree': True, 'extra': True}},
            ),
            self._payload(
                criteria={'engineering': {'range': [3], 'reason': ''}},
            ),
            self._payload(
                criteria={'engineering': {'range': [False, 4], 'reason': ''}},
            ),
            self._payload(
                criteria={'engineering': {'range': [4, 3], 'reason': ''}},
            ),
            self._payload(
                criteria={'engineering': {'range': [3, 4], 'reason': 3}},
            ),
            self._payload(
                criteria={
                    'engineering': {'range': [3, 4], 'reason': 'x' * 501},
                },
            ),
            self._payload(
                verdict='disagree',
                correct_decision='reject',
                gate_failures=['unknown_gate'],
            ),
            self._payload(
                verdict='disagree',
                correct_decision='reject',
                gate_failures=[{'bad': 'shape'}],
            ),
            self._payload(
                verdict='agree_with_corrections',
                error_claims=[{'type': 'opinion', 'text': 'Wrong.'}],
            ),
            self._payload(
                verdict='agree_with_corrections',
                error_claims=[{'type': 'factual_error', 'text': ' '}],
            ),
            self._payload(
                verdict='agree_with_corrections',
                error_claims=[{
                    'type': 'factual_error',
                    'text': 'x' * 501,
                }],
            ),
            self._payload(
                verdict='agree_with_corrections',
                error_claims=[{
                    'type': 'factual_error',
                    'text': 'Wrong.',
                    'evidence_ref': 'x' * 301,
                }],
            ),
            self._payload(
                verdict='agree_with_corrections',
                error_claims=[{
                    'type': 'factual_error',
                    'text': 'Wrong.',
                    'anchor': 'decision',
                }],
            ),
            self._payload(
                verdict='agree_with_corrections',
                error_claims=[{
                    'type': 'factual_error',
                    'text': 'Wrong.',
                    'unexpected': True,
                }],
            ),
        ]

        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                response = self.client.post(self.url, payload, format='json')
                self.assertEqual(response.status_code, 400, response.data)

        self.assertFalse(AIReviewFeedback.objects.exists())

    def test_conditional_verdict_decision_and_gate_rules(self):
        invalid_payloads = [
            self._payload(verdict='disagree'),
            self._payload(verdict='agree', correct_decision='accept'),
            self._payload(verdict='agree', correct_decision=False),
            self._payload(
                verdict='disagree',
                correct_decision='accept',
                gate_failures=['branding_only'],
            ),
            self._payload(
                verdict='agree',
                criteria={
                    'engineering': {'range': [2, 3], 'reason': 'Too high.'},
                },
            ),
            self._payload(
                verdict='agree',
                error_claims=[{
                    'type': 'missed_issue',
                    'text': 'A test is missing.',
                }],
            ),
            self._payload(
                verdict='agree_with_corrections',
                criteria={'engineering': {'agree': True}},
            ),
        ]

        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                response = self.client.post(self.url, payload, format='json')
                self.assertEqual(response.status_code, 400, response.data)

        valid_disagreement = self.client.post(
            self.url,
            self._payload(
                verdict='disagree',
                correct_decision='reject',
                gate_failures=['branding_only'],
            ),
            format='json',
        )
        self.assertEqual(valid_disagreement.status_code, 201, valid_disagreement.data)

        valid_correction = self.client.post(
            self.url,
            self._revision_payload(
                valid_disagreement,
                verdict='agree_with_corrections',
                criteria={
                    'engineering': {'range': [2, 3], 'reason': ''},
                    'genlayer_fit': {'agree': True},
                },
                error_claims=[{
                    'type': 'missed_strength',
                    'text': 'The analysis missed the integration tests.',
                    'evidence_ref': 'tests/test_contract.py:test_integration',
                    'anchor': 'engineering',
                }],
            ),
            format='json',
        )
        self.assertEqual(valid_correction.status_code, 200, valid_correction.data)

    def test_every_reasoning_anchor_is_accepted(self):
        claims = [
            {
                'type': 'wrong_weight',
                'text': f'The {anchor} analysis is weighted incorrectly.',
                'anchor': anchor,
            }
            for anchor in (
                'genlayer_fit',
                'contract_quality',
                'engineering',
                'frontend_ux',
                'synthesis',
            )
        ]

        response = self.client.post(
            self.url,
            self._payload(
                verdict='agree_with_corrections',
                error_claims=claims,
            ),
            format='json',
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(
            [claim['anchor'] for claim in response.data['error_claims']],
            [claim['anchor'] for claim in claims],
        )
        self.assertTrue(all(
            claim['evidence_ref'] == ''
            for claim in response.data['error_claims']
        ))

    def test_revision_and_two_reviewer_coexistence(self):
        create = self.client.post(self.url, self._payload(), format='json')
        update = self.client.post(
            self.url,
            self._revision_payload(
                create,
                verdict='agree_with_corrections',
                criteria={
                    'contract_quality': {
                        'range': [2, 3],
                        'reason': 'One edge case is missing.',
                    },
                },
            ),
            format='json',
        )

        self.assertEqual(create.status_code, 201, create.data)
        self.assertEqual(update.status_code, 200, update.data)
        self.assertEqual(create.data['id'], update.data['id'])
        self.assertEqual(AIReviewFeedback.objects.count(), 1)

        second_reviewer = User.objects.create_user(
            email='feedback-reviewer-two@test.com',
            address=_address(3),
            name='Reviewer Two',
        )
        _grant_permissions(second_reviewer, self.contribution_type)
        self.client.force_authenticate(user=second_reviewer)
        second = self.client.post(self.url, self._payload(), format='json')
        self.assertEqual(second.status_code, 201, second.data)
        self.assertEqual(AIReviewFeedback.objects.count(), 2)

        records = self.client.get(self.url)
        self.assertEqual(records.status_code, 200)
        self.assertEqual(len(records.data), 2)
        self.assertEqual(
            {record['reviewer_id'] for record in records.data},
            {self.reviewer.id, second_reviewer.id},
        )

    def test_revisions_require_the_current_version(self):
        created = self.client.post(self.url, self._payload(), format='json')
        self.assertEqual(created.status_code, 201, created.data)

        missing_version = self.client.post(
            self.url,
            self._payload(verdict='disagree', correct_decision='skip'),
            format='json',
        )
        self.assertEqual(missing_version.status_code, 409, missing_version.data)

        winning = self.client.post(
            self.url,
            self._revision_payload(
                created,
                verdict='disagree',
                correct_decision='skip',
            ),
            format='json',
        )
        self.assertEqual(winning.status_code, 200, winning.data)

        stale = self.client.post(
            self.url,
            self._revision_payload(created, verdict='agree'),
            format='json',
        )
        self.assertEqual(stale.status_code, 409, stale.data)
        feedback = AIReviewFeedback.objects.get(pk=created.data['id'])
        self.assertEqual(feedback.verdict, 'disagree')
        self.assertEqual(feedback.correct_decision, 'skip')

        uncreated_proposal = self._make_proposal(self.submission)
        missing_record = self.client.post(
            self.url,
            {
                'review_proposal_id': uncreated_proposal.id,
                'expected_updated_at': winning.data['updated_at'],
                'verdict': 'agree',
            },
            format='json',
        )
        self.assertEqual(missing_record.status_code, 409, missing_record.data)
        self.assertEqual(AIReviewFeedback.objects.count(), 1)

    def test_equal_proposal_timestamps_keep_distinct_source_records(self):
        second_proposal = self._make_proposal(self.submission)
        shared_timestamp = timezone.now() - timedelta(minutes=5)
        ReviewProposal.objects.filter(
            pk__in=(self.proposal.id, second_proposal.id),
        ).update(created_at=shared_timestamp)
        self.proposal.refresh_from_db()
        second_proposal.refresh_from_db()

        first = self.client.post(self.url, self._payload(), format='json')
        second = self.client.post(
            self.url,
            {
                'review_proposal_id': second_proposal.id,
                'verdict': 'agree',
            },
            format='json',
        )

        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(second.status_code, 201, second.data)
        self.assertNotEqual(first.data['id'], second.data['id'])
        self.assertEqual(first.data['proposal_ref'], second.data['proposal_ref'])
        self.assertEqual(
            {first.data['proposal_source_id'], second.data['proposal_source_id']},
            {self.proposal.id, second_proposal.id},
        )
        self.assertEqual(AIReviewFeedback.objects.count(), 2)

        revised_first = self.client.post(
            self.url,
            self._revision_payload(
                first,
                verdict='disagree',
                correct_decision='skip',
            ),
            format='json',
        )
        self.assertEqual(revised_first.status_code, 200, revised_first.data)
        self.assertEqual(revised_first.data['id'], first.data['id'])
        self.assertEqual(AIReviewFeedback.objects.count(), 2)

    def test_reproposal_creates_distinct_binding_and_stale_explicit_id_is_honored(self):
        first = self.client.post(self.url, self._payload(), format='json')
        self.assertEqual(first.status_code, 201, first.data)

        latest_proposal = self._make_proposal(
            self.submission,
            action='reject',
            points=None,
            staff_reply='Repository does not build.',
        )
        latest = self.client.post(
            self.url,
            {'verdict': 'disagree', 'correct_decision': 'accept'},
            format='json',
        )

        self.assertEqual(latest.status_code, 201, latest.data)
        self.assertEqual(latest.data['review_proposal_id'], latest_proposal.id)
        self.assertEqual(AIReviewFeedback.objects.count(), 2)

        stale_update = self.client.post(
            self.url,
            self._revision_payload(
                first,
                verdict='agree_with_corrections',
                error_claims=[{
                    'type': 'wrong_weight',
                    'text': 'The original proposal overweights presentation.',
                    'anchor': 'synthesis',
                }],
            ),
            format='json',
        )
        self.assertEqual(stale_update.status_code, 200, stale_update.data)
        self.assertEqual(stale_update.data['review_proposal_id'], self.proposal.id)
        self.assertEqual(AIReviewFeedback.objects.count(), 2)
        self.assertEqual(
            set(AIReviewFeedback.objects.values_list('proposal_ref', flat=True)),
            {self.proposal.created_at, latest_proposal.created_at},
        )

    def test_standard_flow_ai_note_is_used_as_fallback(self):
        self.contribution_type.review_flow = ContributionType.REVIEW_FLOW_STANDARD
        self.contribution_type.save(update_fields=['review_flow', 'updated_at'])
        submission = self._make_submission(proposed_by=None, proposed_action=None)
        note = SubmissionNote.objects.create(
            submitted_contribution=submission,
            user=self.ai_user,
            message='AI proposal fallback',
            is_proposal=True,
            data={'action': 'accept'},
        )
        url = f'/api/v1/steward-submissions/{submission.id}/ai-feedback/'

        response = self.client.post(url, {'verdict': 'agree'}, format='json')

        self.assertEqual(response.status_code, 201, response.data)
        feedback = AIReviewFeedback.objects.get(submitted_contribution=submission)
        self.assertIsNone(feedback.review_proposal)
        self.assertEqual(
            feedback.proposal_source,
            AIReviewFeedback.PROPOSAL_SOURCE_NOTE,
        )
        self.assertEqual(feedback.proposal_source_id, note.id)
        self.assertEqual(feedback.proposal_ref, note.created_at)

    def test_equal_standard_note_timestamps_keep_distinct_source_records(self):
        self.contribution_type.review_flow = ContributionType.REVIEW_FLOW_STANDARD
        self.contribution_type.save(update_fields=['review_flow', 'updated_at'])
        submission = self._make_submission(proposed_by=None, proposed_action=None)
        shared_timestamp = timezone.now() - timedelta(minutes=5)
        first_note = SubmissionNote.objects.create(
            submitted_contribution=submission,
            user=self.ai_user,
            message='First AI proposal fallback',
            is_proposal=True,
            data={'action': 'accept'},
        )
        SubmissionNote.objects.filter(pk=first_note.pk).update(
            created_at=shared_timestamp,
        )
        url = f'/api/v1/steward-submissions/{submission.id}/ai-feedback/'
        first = self.client.post(url, {'verdict': 'agree'}, format='json')

        second_note = SubmissionNote.objects.create(
            submitted_contribution=submission,
            user=self.ai_user,
            message='Second AI proposal fallback',
            is_proposal=True,
            data={'action': 'reject'},
        )
        SubmissionNote.objects.filter(pk=second_note.pk).update(
            created_at=shared_timestamp,
        )
        second = self.client.post(url, {'verdict': 'agree'}, format='json')

        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(second.status_code, 201, second.data)
        self.assertEqual(first.data['proposal_ref'], second.data['proposal_ref'])
        self.assertEqual(
            {first.data['proposal_source_id'], second.data['proposal_source_id']},
            {first_note.id, second_note.id},
        )
        self.assertEqual(
            AIReviewFeedback.objects.filter(
                submitted_contribution=submission,
            ).count(),
            2,
        )

    def test_explicit_proposal_must_be_ai_owned_by_the_submission(self):
        other_submission = self._make_submission()
        other_proposal = self._make_proposal(other_submission)
        human_proposal = self._make_proposal(
            self.submission,
            proposer=self.reviewer,
            source=ReviewProposal.SOURCE_HUMAN,
        )

        for proposal_id in (other_proposal.id, human_proposal.id):
            with self.subTest(proposal_id=proposal_id):
                response = self.client.post(
                    self.url,
                    {
                        'review_proposal_id': proposal_id,
                        'verdict': 'agree',
                    },
                    format='json',
                )
                self.assertEqual(response.status_code, 400, response.data)

        self.assertFalse(AIReviewFeedback.objects.exists())

    def test_no_ai_proposal_returns_400(self):
        submission = self._make_submission(proposed_by=None, proposed_action=None)
        url = f'/api/v1/steward-submissions/{submission.id}/ai-feedback/'

        response = self.client.post(url, {'verdict': 'agree'}, format='json')

        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(
            AIReviewFeedback.objects.filter(
                submitted_contribution=submission,
            ).exists(),
        )

    def test_feedback_survives_review_and_can_be_revised_after_finalization(self):
        self.contribution_type.review_flow = ContributionType.REVIEW_FLOW_STANDARD
        self.contribution_type.save(update_fields=['review_flow', 'updated_at'])
        initial = self.client.post(self.url, self._payload(), format='json')
        self.assertEqual(initial.status_code, 201, initial.data)

        review = self.client.post(
            f'/api/v1/steward-submissions/{self.submission.id}/review/',
            {'action': 'reject', 'staff_reply': 'Not ready yet.'},
            format='json',
        )
        self.assertEqual(review.status_code, 200, review.data)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.state, 'rejected')
        self.assertIsNone(self.submission.proposed_by)
        self.assertTrue(AIReviewFeedback.objects.filter(pk=initial.data['id']).exists())

        revised = self.client.post(
            self.url,
            self._revision_payload(
                initial,
                verdict='disagree',
                correct_decision='accept',
            ),
            format='json',
        )
        self.assertEqual(revised.status_code, 200, revised.data)
        self.assertEqual(revised.data['proposal_ref'], initial.data['proposal_ref'])

    def test_serializer_marks_only_ai_active_proposals(self):
        detail_url = f'/api/v1/steward-submissions/{self.submission.id}/'
        ai_response = self.client.get(detail_url)
        self.assertEqual(ai_response.status_code, 200, ai_response.data)
        self.assertIs(ai_response.data['proposal_is_ai'], True)

        self.submission.proposed_by = self.reviewer
        self.submission.save(update_fields=['proposed_by', 'updated_at'])
        human_response = self.client.get(detail_url)
        self.assertEqual(human_response.status_code, 200, human_response.data)
        self.assertIs(human_response.data['proposal_is_ai'], False)

    def test_permissions_include_propose_only_and_visible_no_permission_403(self):
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get(self.url).status_code, 403)

        regular_user = User.objects.create_user(
            email='feedback-regular@test.com',
            address=_address(4),
        )
        self.client.force_authenticate(user=regular_user)
        self.assertEqual(self.client.get(self.url).status_code, 403)

        no_permission_user = User.objects.create_user(
            email='feedback-no-permission@test.com',
            address=_address(5),
        )
        Steward.objects.create(user=no_permission_user)
        self.submission.proposed_by = no_permission_user
        self.submission.save(update_fields=['proposed_by', 'updated_at'])
        self.client.force_authenticate(user=no_permission_user)
        self.assertEqual(self.client.get(self.url).status_code, 403)

        propose_only_user = User.objects.create_user(
            email='feedback-propose-only@test.com',
            address=_address(6),
        )
        _grant_permissions(
            propose_only_user,
            self.contribution_type,
            actions=('propose',),
        )
        self.client.force_authenticate(user=propose_only_user)
        allowed = self.client.post(self.url, self._payload(), format='json')
        self.assertEqual(allowed.status_code, 201, allowed.data)

    def test_submission_author_can_read_but_cannot_file_feedback(self):
        _grant_permissions(self.submitter, self.contribution_type)
        self.client.force_authenticate(user=self.submitter)

        read = self.client.get(self.url)
        blocked = self.client.post(self.url, self._payload(), format='json')

        self.assertEqual(read.status_code, 200, read.data)
        self.assertEqual(blocked.status_code, 403, blocked.data)
        self.assertFalse(AIReviewFeedback.objects.exists())

        self.client.force_authenticate(user=self.reviewer)
        allowed = self.client.post(self.url, self._payload(), format='json')
        self.assertEqual(allowed.status_code, 201, allowed.data)

    def test_feedback_action_does_not_use_heavy_steward_queryset(self):
        with patch(
            'contributions.views.StewardSubmissionViewSet.get_queryset',
            side_effect=AssertionError('heavy queryset should not be used'),
        ):
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200, response.data)

    def test_steward_export_normalizes_legacy_claim_evidence_reference(self):
        feedback = AIReviewFeedback.objects.create(
            submitted_contribution=self.submission,
            review_proposal=self.proposal,
            proposal_source=AIReviewFeedback.PROPOSAL_SOURCE_REVIEW,
            proposal_source_id=self.proposal.id,
            proposal_ref=self.proposal.created_at,
            reviewer=self.reviewer,
            verdict='agree_with_corrections',
            error_claims=[{
                'type': 'missed_issue',
                'text': 'The analysis missed an authorization check.',
                'anchor': 'engineering',
            }],
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200, response.data)
        record = next(item for item in response.data if item['id'] == feedback.id)
        self.assertEqual(record['error_claims'][0]['evidence_ref'], '')

    @override_settings(GITHUB_METRICS_TOKEN='github-token')
    @patch('contributions.ai_feedback.requests.get')
    def test_sha_success_uses_repository_head_and_token(self, request_get):
        Evidence.objects.create(
            submitted_contribution=self.submission,
            url='https://example.com/not-github',
        )
        Evidence.objects.create(
            submitted_contribution=self.submission,
            url='https://github.com/acme/widget/tree/main',
        )
        request_get.return_value = Mock(status_code=200, text=SHA)

        response = self.client.post(self.url, self._payload(), format='json')

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['reviewed_commit_sha'], SHA)
        request_get.assert_called_once_with(
            'https://api.github.com/repos/acme/widget/commits/HEAD',
            headers={
                'Accept': 'application/vnd.github.sha',
                'Authorization': 'Bearer github-token',
            },
            timeout=5,
        )

    @patch('contributions.ai_feedback.requests.get')
    def test_sha_is_pinned_on_first_save(self, request_get):
        Evidence.objects.create(
            submitted_contribution=self.submission,
            url='https://github.com/acme/widget',
        )
        request_get.return_value = Mock(status_code=200, text=SHA)

        created = self.client.post(self.url, self._payload(), format='json')
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(created.data['reviewed_commit_sha'], SHA)

        request_get.reset_mock()
        request_get.side_effect = RuntimeError('transport failed')
        failed_lookup_revision = self.client.post(
            self.url,
            self._revision_payload(
                created,
                verdict='disagree',
                correct_decision='skip',
            ),
            format='json',
        )
        self.assertEqual(
            failed_lookup_revision.status_code,
            200,
            failed_lookup_revision.data,
        )
        self.assertEqual(failed_lookup_revision.data['reviewed_commit_sha'], SHA)
        request_get.assert_not_called()

        request_get.side_effect = None
        request_get.return_value = Mock(status_code=200, text='b' * 40)
        different_head_revision = self.client.post(
            self.url,
            self._revision_payload(failed_lookup_revision, verdict='agree'),
            format='json',
        )
        self.assertEqual(
            different_head_revision.status_code,
            200,
            different_head_revision.data,
        )
        self.assertEqual(different_head_revision.data['reviewed_commit_sha'], SHA)
        request_get.assert_not_called()

    @patch('contributions.ai_feedback.requests.get')
    def test_failed_first_sha_lookup_remains_pinned_as_null(self, request_get):
        Evidence.objects.create(
            submitted_contribution=self.submission,
            url='https://github.com/acme/widget',
        )
        request_get.side_effect = RuntimeError('transport failed')

        created = self.client.post(self.url, self._payload(), format='json')
        self.assertEqual(created.status_code, 201, created.data)
        self.assertIsNone(created.data['reviewed_commit_sha'])
        request_get.assert_called_once()

        request_get.reset_mock()
        request_get.side_effect = None
        request_get.return_value = Mock(status_code=200, text=SHA)
        revised = self.client.post(
            self.url,
            self._revision_payload(
                created,
                verdict='disagree',
                correct_decision='skip',
            ),
            format='json',
        )
        self.assertEqual(revised.status_code, 200, revised.data)
        self.assertIsNone(revised.data['reviewed_commit_sha'])
        request_get.assert_not_called()

    @override_settings(GITHUB_METRICS_TOKEN='')
    @patch('contributions.ai_feedback.requests.get')
    def test_sha_failures_never_block_and_blank_token_omits_header(self, request_get):
        Evidence.objects.create(
            submitted_contribution=self.submission,
            url='https://github.com/acme/widget',
        )
        outcomes = [
            Mock(status_code=503, text='unavailable'),
            Mock(status_code=200, text='not-a-sha'),
            RuntimeError('transport failed'),
        ]

        for index, outcome in enumerate(outcomes):
            with self.subTest(outcome=index):
                AIReviewFeedback.objects.all().delete()
                request_get.reset_mock()
                if isinstance(outcome, Exception):
                    request_get.side_effect = outcome
                    request_get.return_value = Mock()
                else:
                    request_get.side_effect = None
                    request_get.return_value = outcome

                response = self.client.post(
                    self.url,
                    self._payload(
                        verdict='disagree',
                        correct_decision='skip',
                    ),
                    format='json',
                )

                self.assertIn(response.status_code, (200, 201), response.data)
                self.assertIsNone(response.data['reviewed_commit_sha'])
                _, kwargs = request_get.call_args
                self.assertEqual(
                    kwargs['headers'],
                    {'Accept': 'application/vnd.github.sha'},
                )


@override_settings(ALLOWED_HOSTS=['*'])
class BenchmarkAIFeedbackTests(APITestCase):
    def setUp(self):
        category = Category.objects.create(
            name='Benchmark Builder',
            slug='benchmark-builder',
        )
        self.contribution_type = ContributionType.objects.create(
            name='Benchmark Project',
            slug='benchmark-project',
            category=category,
            min_points=1,
            max_points=10,
        )
        self.submitter = User.objects.create_user(
            email='benchmark-submitter@test.com',
            address=_address(10),
        )
        self.reviewer = User.objects.create_user(
            email='benchmark-reviewer@test.com',
            address=_address(11),
            name='Benchmark Reviewer',
        )
        self.ai_user = get_ai_steward()
        self.submission = self._make_submission('First benchmark submission')
        self.proposal = ReviewProposal.objects.create(
            submitted_contribution=self.submission,
            proposer=self.ai_user,
            source=ReviewProposal.SOURCE_AI,
            action='accept',
            points=5,
        )
        self.feedback = AIReviewFeedback.objects.create(
            submitted_contribution=self.submission,
            review_proposal=self.proposal,
            proposal_source=AIReviewFeedback.PROPOSAL_SOURCE_REVIEW,
            proposal_source_id=self.proposal.id,
            proposal_ref=self.proposal.created_at,
            reviewer=self.reviewer,
            verdict='agree',
        )
        self.url = '/api/v1/ai-review/feedback/'

    def _make_submission(self, title):
        return SubmittedContribution.objects.create(
            user=self.submitter,
            contribution_type=self.contribution_type,
            contribution_date=timezone.now(),
            title=title,
            notes='Benchmark submission.',
            state='pending',
        )

    def _make_feedback(self, submission, reviewer_number):
        reviewer = User.objects.create_user(
            email=f'benchmark-reviewer-{reviewer_number}@test.com',
            address=_address(20 + reviewer_number),
            name=f'Benchmark Reviewer {reviewer_number}',
        )
        proposal = ReviewProposal.objects.create(
            submitted_contribution=submission,
            proposer=self.ai_user,
            source=ReviewProposal.SOURCE_AI,
            action='reject',
            staff_reply='No.',
        )
        return AIReviewFeedback.objects.create(
            submitted_contribution=submission,
            review_proposal=proposal,
            proposal_source=AIReviewFeedback.PROPOSAL_SOURCE_REVIEW,
            proposal_source_id=proposal.id,
            proposal_ref=proposal.created_at,
            reviewer=reviewer,
            verdict='disagree',
            correct_decision='accept',
        )

    def test_read_scope_pagination_order_and_exact_contract(self):
        second = self._make_feedback(self.submission, 1)
        third = self._make_feedback(self.submission, 2)
        tied_updated_at = timezone.now() - timedelta(hours=1)
        for feedback in (self.feedback, second, third):
            AIReviewFeedback.objects.filter(pk=feedback.pk).update(
                updated_at=tied_updated_at,
            )

        plaintext = _issue(name='feedback-read-pagination')
        response = self.client.get(
            f'{self.url}?page_size=2',
            **_bearer(plaintext),
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['count'], 3)
        self.assertIsNotNone(response.data['next'])
        self.assertEqual(
            [record['id'] for record in response.data['results']],
            [self.feedback.id, second.id],
        )
        self.assertEqual(
            set(response.data['results'][0]),
            {
                'id',
                'submission_id',
                'review_proposal_id',
                'proposal_source',
                'proposal_source_id',
                'proposal_ref',
                'reviewer',
                'reviewer_id',
                'reviewed_commit_sha',
                'verdict',
                'correct_decision',
                'gate_failures',
                'criteria',
                'error_claims',
                'created_at',
                'updated_at',
            },
        )
        first_record = response.data['results'][0]
        self.assertEqual(first_record['submission_id'], str(self.submission.id))
        self.assertEqual(
            first_record['proposal_source'],
            AIReviewFeedback.PROPOSAL_SOURCE_REVIEW,
        )
        self.assertEqual(first_record['proposal_source_id'], self.proposal.id)
        self.assertEqual(first_record['reviewer'], self.reviewer.name)
        self.assertIsNone(first_record['reviewed_commit_sha'])
        self.assertIsNone(first_record['correct_decision'])

        second_page = self.client.get(
            f'{self.url}?page_size=2&page=2',
            **_bearer(plaintext),
        )
        self.assertEqual(second_page.status_code, 200, second_page.data)
        self.assertEqual(
            [record['id'] for record in second_page.data['results']],
            [third.id],
        )

    def test_mutation_between_pages_is_detected_and_retry_is_complete(self):
        second = self._make_feedback(self.submission, 1)
        third = self._make_feedback(self.submission, 2)
        baseline = timezone.now() - timedelta(hours=1)
        for offset, feedback in enumerate((self.feedback, second, third)):
            AIReviewFeedback.objects.filter(pk=feedback.pk).update(
                updated_at=baseline + timedelta(seconds=offset),
            )

        plaintext = _issue(name='feedback-read-mutation')
        first_page = self.client.get(
            f'{self.url}?page_size=2',
            **_bearer(plaintext),
        )
        self.assertEqual(first_page.status_code, 200, first_page.data)

        AIReviewFeedback.objects.filter(pk=self.feedback.pk).update(
            updated_at=baseline + timedelta(seconds=10),
        )
        shifted_second_page = self.client.get(
            f'{self.url}?page_size=2&page=2',
            **_bearer(plaintext),
        )
        self.assertEqual(
            shifted_second_page.status_code,
            200,
            shifted_second_page.data,
        )

        shifted_ids = [
            *(record['id'] for record in first_page.data['results']),
            *(record['id'] for record in shifted_second_page.data['results']),
        ]
        self.assertEqual(first_page.data['count'], shifted_second_page.data['count'])
        self.assertLess(len(set(shifted_ids)), first_page.data['count'])

        retry_first = self.client.get(
            f'{self.url}?page_size=2',
            **_bearer(plaintext),
        )
        retry_second = self.client.get(
            f'{self.url}?page_size=2&page=2',
            **_bearer(plaintext),
        )
        retry_ids = [
            *(record['id'] for record in retry_first.data['results']),
            *(record['id'] for record in retry_second.data['results']),
        ]
        self.assertEqual(len(set(retry_ids)), retry_first.data['count'])
        self.assertEqual(
            set(retry_ids),
            {self.feedback.id, second.id, third.id},
        )

    def test_updated_after_includes_cursor_overlap_and_submission_filter(self):
        other_submission = self._make_submission('Other benchmark submission')
        other_feedback = self._make_feedback(other_submission, 3)
        cutoff = timezone.now() - timedelta(minutes=5)
        AIReviewFeedback.objects.filter(pk=self.feedback.pk).update(
            updated_at=cutoff,
        )
        AIReviewFeedback.objects.filter(pk=other_feedback.pk).update(
            updated_at=cutoff,
        )
        plaintext = _issue(name='feedback-read-filters')

        updated = self.client.get(
            self.url,
            {'updated_after': cutoff.isoformat()},
            **_bearer(plaintext),
        )
        filtered_submission = self.client.get(
            self.url,
            {'submission': self.submission.id},
            **_bearer(plaintext),
        )

        self.assertEqual(updated.status_code, 200, updated.data)
        self.assertEqual(
            [record['id'] for record in updated.data['results']],
            [self.feedback.id, other_feedback.id],
        )
        self.assertEqual(filtered_submission.status_code, 200, filtered_submission.data)
        self.assertEqual(
            [record['id'] for record in filtered_submission.data['results']],
            [self.feedback.id],
        )

    def test_export_always_includes_claim_evidence_reference(self):
        self.feedback.verdict = 'agree_with_corrections'
        self.feedback.error_claims = [{
            'type': 'missed_issue',
            'text': 'The analysis missed an authorization check.',
            'anchor': 'engineering',
        }]
        self.feedback.save(update_fields=['verdict', 'error_claims', 'updated_at'])
        plaintext = _issue(name='feedback-claim-shape')

        response = self.client.get(self.url, **_bearer(plaintext))

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            response.data['results'][0]['error_claims'][0]['evidence_ref'],
            '',
        )

    def test_scope_enforcement(self):
        read_token = _issue(name='feedback-read-scope')
        propose_token = _issue(
            scopes=('ai_review:propose',),
            name='feedback-propose-scope',
        )

        self.assertEqual(
            self.client.get(self.url, **_bearer(read_token)).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(self.url, **_bearer(propose_token)).status_code,
            403,
        )
        self.assertEqual(self.client.get(self.url).status_code, 401)
