from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from contributions.models import (
    SubmittedContribution,
    SubmissionNote,
    ContributionType,
    Category,
)

User = get_user_model()


class AppealEndpointTest(TestCase):
    """Tests for POST /api/v1/submissions/{id}/appeal/."""

    def setUp(self):
        self.category = Category.objects.create(
            name='Test Category', slug='test', description='Test',
        )
        self.contribution_type = ContributionType.objects.create(
            name='Test Type', slug='test-type',
            description='Test contribution type',
            category=self.category, min_points=1, max_points=100,
        )
        self.owner = User.objects.create_user(
            email='owner@test.com',
            address='0x1111111111111111111111111111111111111111',
            password='pass',
        )
        self.other = User.objects.create_user(
            email='other@test.com',
            address='0x2222222222222222222222222222222222222222',
            password='pass',
        )
        self.reviewer = User.objects.create_user(
            email='reviewer@test.com',
            address='0x3333333333333333333333333333333333333333',
            password='pass',
        )
        self.client = APIClient()

    def _make_submission(self, state='rejected', has_appeal=False):
        return SubmittedContribution.objects.create(
            user=self.owner,
            contribution_type=self.contribution_type,
            contribution_date=timezone.now(),
            state=state,
            staff_reply='Original rejection reason',
            reviewed_by=self.reviewer,
            reviewed_at=timezone.now(),
            has_appeal=has_appeal,
        )

    def _appeal_url(self, submission):
        return f'/api/v1/submissions/{submission.id}/appeal/'

    def test_owner_can_appeal_rejected_submission(self):
        submission = self._make_submission()
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            self._appeal_url(submission),
            {'reason': 'I think this was unfair'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        submission.refresh_from_db()
        self.assertTrue(submission.has_appeal)
        self.assertEqual(submission.appeal_reason, 'I think this was unfair')
        self.assertEqual(submission.state, 'pending')
        # Original rejection reason is preserved as audit context
        self.assertEqual(submission.staff_reply, 'Original rejection reason')
        # Review metadata cleared so AI queue / stats treat it as fresh-pending
        self.assertIsNone(submission.reviewed_by)
        self.assertIsNone(submission.reviewed_at)

    def test_appeal_creates_internal_note(self):
        submission = self._make_submission()
        self.client.force_authenticate(user=self.owner)

        self.client.post(
            self._appeal_url(submission),
            {'reason': 'Reconsider please'},
            format='json',
        )

        notes = SubmissionNote.objects.filter(submitted_contribution=submission)
        self.assertEqual(notes.count(), 1)
        note = notes.first()
        self.assertEqual(note.user, self.owner)
        self.assertTrue(note.message.startswith('APPEAL: '))
        self.assertIn('Reconsider please', note.message)

    def test_non_owner_cannot_appeal(self):
        submission = self._make_submission()
        self.client.force_authenticate(user=self.other)

        response = self.client.post(
            self._appeal_url(submission),
            {'reason': 'Not mine but appealing'},
            format='json',
        )
        # Owner-only via queryset filter -> 404
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_cannot_appeal(self):
        submission = self._make_submission()
        response = self.client.post(
            self._appeal_url(submission),
            {'reason': 'No auth'},
            format='json',
        )
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_cannot_appeal_pending_submission(self):
        submission = self._make_submission(state='pending')
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            self._appeal_url(submission),
            {'reason': 'Trying to appeal a pending one'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_appeal_twice(self):
        submission = self._make_submission()
        self.client.force_authenticate(user=self.owner)

        first = self.client.post(
            self._appeal_url(submission),
            {'reason': 'First appeal'},
            format='json',
        )
        self.assertEqual(first.status_code, status.HTTP_200_OK)

        # Re-reject the now-pending submission so the state check passes
        submission.refresh_from_db()
        submission.state = 'rejected'
        submission.save(update_fields=['state'])

        second = self.client.post(
            self._appeal_url(submission),
            {'reason': 'Second appeal'},
            format='json',
        )
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)

    def test_banned_user_cannot_appeal(self):
        submission = self._make_submission()
        self.owner.is_banned = True
        self.owner.save()
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            self._appeal_url(submission),
            {'reason': 'I am banned but trying'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        submission.refresh_from_db()
        self.assertFalse(submission.has_appeal)
        self.assertEqual(submission.state, 'rejected')

    def test_empty_reason_rejected(self):
        submission = self._make_submission()
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            self._appeal_url(submission),
            {'reason': '   '},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_oversized_reason_rejected(self):
        submission = self._make_submission()
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            self._appeal_url(submission),
            {'reason': 'x' * 5001},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_appealed_pending_submission_cannot_be_patched(self):
        submission = self._make_submission()
        self.client.force_authenticate(user=self.owner)

        self.client.post(
            self._appeal_url(submission),
            {'reason': 'Appeal'},
            format='json',
        )

        # State is now 'pending' — locked
        response = self.client.patch(
            f'/api/v1/submissions/{submission.id}/',
            {'notes': 'Sneaky edit'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_appealed_pending_submission_cannot_add_evidence(self):
        submission = self._make_submission()
        self.client.force_authenticate(user=self.owner)

        self.client.post(
            self._appeal_url(submission),
            {'reason': 'Appeal'},
            format='json',
        )

        # State is now 'pending' — locked
        response = self.client.post(
            f'/api/v1/submissions/{submission.id}/add-evidence/',
            {'description': 'New evidence', 'url': 'https://example.com'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_appealed_more_info_needed_submission_can_be_patched(self):
        """Once a steward asks for more info on an appealed submission,
        the submitter can edit it to respond."""
        submission = self._make_submission()
        self.client.force_authenticate(user=self.owner)

        self.client.post(
            self._appeal_url(submission),
            {'reason': 'Appeal'},
            format='json',
        )

        # Steward moves it to more_info_needed
        submission.refresh_from_db()
        submission.state = 'more_info_needed'
        submission.save(update_fields=['state'])

        response = self.client.patch(
            f'/api/v1/submissions/{submission.id}/',
            {'notes': 'Here is more info'},
            format='json',
        )
        # Lock should NOT apply — should not be 403 from the appeal lock
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cancelling_appealed_preserves_rejection_reason(self):
        submission = self._make_submission()
        self.client.force_authenticate(user=self.owner)

        self.client.post(
            self._appeal_url(submission),
            {'reason': 'Appeal'},
            format='json',
        )

        response = self.client.delete(f'/api/v1/submissions/{submission.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        submission.refresh_from_db()
        self.assertEqual(submission.state, 'canceled')
        # Original staff_reply is preserved on cancel because it was appealed
        self.assertEqual(submission.staff_reply, 'Original rejection reason')

    def test_cancelling_pending_submission_marks_canceled(self):
        submission = self._make_submission(state='pending')
        submission.staff_reply = ''
        submission.reviewed_by = None
        submission.reviewed_at = None
        submission.save(
            update_fields=['staff_reply', 'reviewed_by', 'reviewed_at']
        )
        self.client.force_authenticate(user=self.owner)

        response = self.client.delete(f'/api/v1/submissions/{submission.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        submission.refresh_from_db()
        self.assertEqual(submission.state, 'canceled')
        self.assertEqual(submission.staff_reply, 'Canceled by user')
        self.assertIsNotNone(submission.reviewed_at)
