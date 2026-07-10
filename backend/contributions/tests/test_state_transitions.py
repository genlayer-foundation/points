from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from contributions.ai_attribution import get_ai_steward
from contributions.management.commands.review_submissions import Command as ReviewCommand
from contributions.models import (
    Category,
    ContributionType,
    SubmissionNote,
    SubmissionStateTransition,
    SubmittedContribution,
)
from leaderboard.models import GlobalLeaderboardMultiplier
from stewards.models import ReviewTemplate, Steward, StewardPermission

User = get_user_model()


class SubmissionStateTransitionTest(TestCase):
    """Every lifecycle path must leave an append-only transition row."""

    def setUp(self):
        self.category = Category.objects.create(
            name='Test Category', slug='test', description='Test',
        )
        self.contribution_type = ContributionType.objects.create(
            name='Test Type', slug='test-type',
            description='Test contribution type',
            category=self.category, min_points=1, max_points=100,
        )
        GlobalLeaderboardMultiplier.objects.create(
            contribution_type=self.contribution_type,
            multiplier_value=1,
            valid_from=timezone.now() - timezone.timedelta(days=1),
        )
        self.owner = User.objects.create_user(
            email='owner@test.com',
            address='0x1111111111111111111111111111111111111111',
            password='pass',
        )
        self.steward_user = User.objects.create_user(
            email='steward@test.com',
            address='0x2222222222222222222222222222222222222222',
            password='pass',
        )
        self.steward = Steward.objects.create(user=self.steward_user)
        for action in ('accept', 'reject', 'request_more_info'):
            StewardPermission.objects.create(
                steward=self.steward,
                contribution_type=self.contribution_type,
                action=action,
            )
        self.client = APIClient()

    def _make_submission(self, state='pending', **kwargs):
        return SubmittedContribution.objects.create(
            user=self.owner,
            contribution_type=self.contribution_type,
            contribution_date=timezone.now(),
            state=state,
            **kwargs,
        )

    def _transitions(self, submission, event=None):
        qs = SubmissionStateTransition.objects.filter(
            submitted_contribution=submission
        ).order_by('created_at')
        if event:
            qs = qs.filter(event=event)
        return list(qs)

    def test_creation_logs_submitted_transition(self):
        submission = self._make_submission()
        transitions = self._transitions(submission)
        self.assertEqual(len(transitions), 1)
        t = transitions[0]
        self.assertEqual(t.event, 'submitted')
        self.assertEqual(t.from_state, '')
        self.assertEqual(t.to_state, 'pending')
        self.assertEqual(t.actor, self.owner)

    def test_review_reject_logs_review_transition(self):
        submission = self._make_submission()
        self.client.force_authenticate(user=self.steward_user)
        response = self.client.post(
            f'/api/v1/steward-submissions/{submission.id}/review/',
            {'action': 'reject', 'staff_reply': 'Not enough evidence'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        (t,) = self._transitions(submission, event='review')
        self.assertEqual(t.from_state, 'pending')
        self.assertEqual(t.to_state, 'rejected')
        self.assertEqual(t.actor, self.steward_user)

    def test_bulk_reject_logs_transitions_and_decision_notes(self):
        first = self._make_submission()
        second = self._make_submission(state='more_info_needed')
        self.client.force_authenticate(user=self.steward_user)
        response = self.client.post(
            '/api/v1/steward-submissions/bulk-reject/',
            {'submission_ids': [str(first.id), str(second.id)], 'staff_reply': 'Spam'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        (t1,) = self._transitions(first, event='bulk_reject')
        self.assertEqual((t1.from_state, t1.to_state), ('pending', 'rejected'))
        self.assertEqual(t1.actor, self.steward_user)
        (t2,) = self._transitions(second, event='bulk_reject')
        self.assertEqual((t2.from_state, t2.to_state), ('more_info_needed', 'rejected'))

        # Bulk rejects now leave the same durable decision note single rejects do
        for submission in (first, second):
            note = SubmissionNote.objects.get(submitted_contribution=submission)
            self.assertFalse(note.is_proposal)
            self.assertEqual(note.user, self.steward_user)
            self.assertEqual(note.data['action'], 'reject')
            self.assertTrue(note.data['bulk'])
            self.assertEqual(note.data['staff_reply'], 'Spam')

    def test_edit_after_more_info_logs_edited_transition(self):
        submission = self._make_submission(
            state='more_info_needed',
            reviewed_by=self.steward_user,
            reviewed_at=timezone.now(),
        )
        self.client.force_authenticate(user=self.owner)
        response = self.client.patch(
            f'/api/v1/submissions/{submission.id}/',
            {'notes': 'Here is the extra information'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        (t,) = self._transitions(submission, event='edited')
        self.assertEqual((t.from_state, t.to_state), ('more_info_needed', 'pending'))
        self.assertEqual(t.actor, self.owner)

    def test_cancel_logs_canceled_transition(self):
        submission = self._make_submission()
        self.client.force_authenticate(user=self.owner)
        response = self.client.delete(f'/api/v1/submissions/{submission.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        (t,) = self._transitions(submission, event='canceled')
        self.assertEqual((t.from_state, t.to_state), ('pending', 'canceled'))
        self.assertEqual(t.actor, self.owner)

    def test_appeal_logs_appeal_transition(self):
        submission = self._make_submission(
            state='rejected',
            staff_reply='Rejected',
            reviewed_by=self.steward_user,
            reviewed_at=timezone.now(),
        )
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            f'/api/v1/submissions/{submission.id}/appeal/',
            {'reason': 'Please reconsider'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        (t,) = self._transitions(submission, event='appeal')
        self.assertEqual((t.from_state, t.to_state), ('rejected', 'pending'))
        self.assertEqual(t.actor, self.owner)

    def test_add_evidence_logs_only_when_review_fields_cleared(self):
        reviewed = self._make_submission(
            state='more_info_needed',
            reviewed_by=self.steward_user,
            reviewed_at=timezone.now(),
        )
        fresh = self._make_submission()
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            f'/api/v1/submissions/{reviewed.id}/add-evidence/',
            {'url': 'https://example.com/proof'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        (t,) = self._transitions(reviewed, event='evidence_added')
        self.assertEqual(t.from_state, t.to_state)
        self.assertEqual(t.actor, self.owner)

        response = self.client.post(
            f'/api/v1/submissions/{fresh.id}/add-evidence/',
            {'url': 'https://example.com/proof'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self._transitions(fresh, event='evidence_added'), [])

    def test_admin_review_field_edit_logs_admin_transition(self):
        from types import SimpleNamespace
        from django.contrib.admin.sites import AdminSite
        from contributions.admin import SubmittedContributionAdmin

        submission = self._make_submission(
            state='more_info_needed',
            reviewed_by=self.steward_user,
            reviewed_at=timezone.now(),
        )
        model_admin = SubmittedContributionAdmin(SubmittedContribution, AdminSite())
        request = SimpleNamespace(user=self.steward_user)

        # Clearing reviewed_by without touching state must still hit the log
        submission.reviewed_by = None
        form = SimpleNamespace(
            changed_data=['reviewed_by'],
            initial={'state': 'more_info_needed'},
        )
        model_admin.save_model(request, submission, form, change=True)
        (t,) = self._transitions(submission, event='admin')
        self.assertEqual((t.from_state, t.to_state), ('more_info_needed', 'more_info_needed'))
        self.assertEqual(t.actor, self.steward_user)

    def test_gate_reject_logs_transition_with_ai_actor(self):
        submission = self._make_submission()
        ai_user = get_ai_steward()
        template = ReviewTemplate.objects.create(
            label='No evidence', text='No evidence URL provided.', action='reject',
        )
        ReviewCommand()._apply_reject(submission, ai_user, template, 'No evidence URL')
        (t,) = self._transitions(submission, event='gate_reject')
        self.assertEqual((t.from_state, t.to_state), ('pending', 'rejected'))
        self.assertEqual(t.actor, ai_user)
