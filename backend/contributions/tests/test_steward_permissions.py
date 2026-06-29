from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from contributions.models import (
    SubmittedContribution,
    ContributionType,
    Category,
    Contribution,
    ContributionHighlight,
    SubmissionNote,
)
from leaderboard.models import GlobalLeaderboardMultiplier
from stewards.models import Steward, StewardPermission
from datetime import datetime
from django.utils import timezone

User = get_user_model()


class StewardPermissionTest(TestCase):
    """Test steward permission system."""
    
    def setUp(self):
        """Set up test data."""
        # Create category
        self.category = Category.objects.create(
            name="Test Category",
            slug="test",
            description="Test category"
        )
        
        # Create contribution type
        self.contribution_type = ContributionType.objects.create(
            name="Test Type",
            slug="test-type",
            description="Test contribution type",
            category=self.category,
            min_points=10,
            max_points=100
        )
        self.other_category = Category.objects.create(
            name="Other Category",
            slug="other",
            description="Other category"
        )
        self.other_contribution_type = ContributionType.objects.create(
            name="Other Type",
            slug="other-type",
            description="Other contribution type",
            category=self.other_category,
            min_points=1,
            max_points=5
        )
        for contribution_type in [self.contribution_type, self.other_contribution_type]:
            GlobalLeaderboardMultiplier.objects.create(
                contribution_type=contribution_type,
                multiplier_value=1,
                valid_from=timezone.now() - timezone.timedelta(days=1),
            )
        
        # Create regular user
        self.regular_user = User.objects.create_user(
            email='regular@test.com',
            address='0x1234567890123456789012345678901234567890',
            password='testpass123'
        )
        
        # Create steward user
        self.steward_user = User.objects.create_user(
            email='steward@test.com',
            address='0x0987654321098765432109876543210987654321',
            password='testpass123'
        )
        self.steward = Steward.objects.create(user=self.steward_user)

        # Grant all permissions to steward for the test contribution type
        for action in ['propose', 'accept', 'reject', 'request_more_info']:
            StewardPermission.objects.create(
                steward=self.steward,
                contribution_type=self.contribution_type,
                action=action
            )

        # Create admin user
        self.admin_user = User.objects.create_superuser(
            email='admin@test.com',
            address='0x1111111111111111111111111111111111111111',
            password='testpass123'
        )
        self.reassignment_user = User.objects.create_user(
            email='reassignment@test.com',
            address='0x2222222222222222222222222222222222222222',
            password='testpass123'
        )
        
        # Create a submission
        self.submission = SubmittedContribution.objects.create(
            user=self.regular_user,
            contribution_type=self.contribution_type,
            contribution_date=timezone.now(),
            notes="Test submission",
            state='pending'
        )
        
        self.client = APIClient()
    
    def test_non_authenticated_user_can_view_stats_but_not_protected_steward_endpoints(self):
        """Test that anonymous users can view stats but not protected steward endpoints."""
        # Try to access steward submissions list
        response = self.client.get('/api/v1/steward-submissions/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Try to review a submission
        response = self.client.post(
            f'/api/v1/steward-submissions/{self.submission.id}/review/',
            {'action': 'accept', 'points': 50}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Steward stats are public aggregate counts for the dashboard.
        response = self.client.get('/api/v1/steward-submissions/stats/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['pending_count'], 1)
        self.assertEqual(response.data['total_reviewed'], 0)
    
    def test_regular_user_can_view_stats_but_not_protected_steward_endpoints(self):
        """Test that regular users can view stats but not protected steward endpoints."""
        # Authenticate as regular user
        self.client.force_authenticate(user=self.regular_user)
        
        # Try to access steward submissions list
        response = self.client.get('/api/v1/steward-submissions/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Try to review a submission
        response = self.client.post(
            f'/api/v1/steward-submissions/{self.submission.id}/review/',
            {'action': 'accept', 'points': 50}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Steward stats are public aggregate counts for the dashboard.
        response = self.client.get('/api/v1/steward-submissions/stats/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['pending_count'], 1)
        self.assertEqual(response.data['total_reviewed'], 0)
    
    def test_steward_can_access_steward_endpoints(self):
        """Test that stewards can access steward endpoints."""
        # Authenticate as steward
        self.client.force_authenticate(user=self.steward_user)
        
        # Access steward submissions list
        response = self.client.get('/api/v1/steward-submissions/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        
        # Get stats
        response = self.client.get('/api/v1/steward-submissions/stats/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['pending_count'], 1)

    def test_steward_can_change_pending_submission_type_without_reviewing(self):
        """Stewards can save a new type before making a review decision."""
        StewardPermission.objects.create(
            steward=self.steward,
            contribution_type=self.other_contribution_type,
            action='accept'
        )
        self.submission.proposed_action = 'accept'
        self.submission.proposed_points = 50
        self.submission.proposed_contribution_type = self.contribution_type
        self.submission.proposed_by = self.steward_user
        self.submission.proposed_at = timezone.now()
        self.submission.save()

        self.client.force_authenticate(user=self.steward_user)

        response = self.client.post(
            f'/api/v1/steward-submissions/{self.submission.id}/change-type/',
            {'contribution_type': self.other_contribution_type.id},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.contribution_type, self.other_contribution_type)
        self.assertEqual(self.submission.state, 'pending')
        self.assertIsNone(self.submission.reviewed_by)
        self.assertIsNone(self.submission.reviewed_at)
        self.assertIsNone(self.submission.converted_contribution)
        self.assertIsNone(self.submission.proposed_action)
        self.assertTrue(
            SubmissionNote.objects.filter(
                submitted_contribution=self.submission,
                data__action='change_type',
            ).exists()
        )

    def test_steward_needs_review_permission_on_target_type_to_change_submission_type(self):
        """Changing type cannot move work into a type the steward cannot review."""
        self.client.force_authenticate(user=self.steward_user)

        response = self.client.post(
            f'/api/v1/steward-submissions/{self.submission.id}/change-type/',
            {'contribution_type': self.other_contribution_type.id},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.contribution_type, self.contribution_type)

    def test_steward_cannot_change_type_after_submission_is_accepted(self):
        """Accepted awards must use accepted-submission correction flows."""
        StewardPermission.objects.create(
            steward=self.steward,
            contribution_type=self.other_contribution_type,
            action='accept'
        )
        accepted_contribution = Contribution.objects.create(
            user=self.regular_user,
            contribution_type=self.contribution_type,
            contribution_date=timezone.now(),
            points=50,
        )
        self.submission.state = 'accepted'
        self.submission.converted_contribution = accepted_contribution
        self.submission.reviewed_by = self.steward_user
        self.submission.reviewed_at = timezone.now()
        self.submission.save()

        self.client.force_authenticate(user=self.steward_user)

        response = self.client.post(
            f'/api/v1/steward-submissions/{self.submission.id}/change-type/',
            {'contribution_type': self.other_contribution_type.id},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.contribution_type, self.contribution_type)

    def test_propose_only_steward_only_sees_pending_permitted_submissions(self):
        """Proposal-only stewards cannot browse non-pending review history."""
        StewardPermission.objects.filter(steward=self.steward).delete()
        StewardPermission.objects.create(
            steward=self.steward,
            contribution_type=self.contribution_type,
            action='propose'
        )
        accepted_contribution = Contribution.objects.create(
            user=self.regular_user,
            contribution_type=self.contribution_type,
            contribution_date=timezone.now(),
            points=50,
        )
        accepted_submission = SubmittedContribution.objects.create(
            user=self.regular_user,
            contribution_type=self.contribution_type,
            contribution_date=timezone.now(),
            notes="Already accepted",
            state='accepted',
            reviewed_by=self.steward_user,
            reviewed_at=timezone.now(),
            converted_contribution=accepted_contribution,
        )
        other_pending_submission = SubmittedContribution.objects.create(
            user=self.regular_user,
            contribution_type=self.other_contribution_type,
            contribution_date=timezone.now(),
            notes="Other type",
            state='pending'
        )

        self.client.force_authenticate(user=self.steward_user)

        response = self.client.get('/api/v1/steward-submissions/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result_ids = {str(item['id']) for item in response.data['results']}
        self.assertEqual(result_ids, {str(self.submission.id)})
        self.assertNotIn(str(accepted_submission.id), result_ids)
        self.assertNotIn(str(other_pending_submission.id), result_ids)

        response = self.client.get('/api/v1/steward-submissions/?state=accepted')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'], [])

        response = self.client.get('/api/v1/steward-submissions/stats/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['pending_count'], 1)
        self.assertEqual(response.data['total_reviewed'], 0)
        self.assertEqual(response.data['total_accepted'], 0)

        response = self.client.get('/api/v1/steward-submissions/daily-metrics/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Daily metrics are public aggregate data for the Overview > Metrics
        # page, so they are not scoped to the steward's review permissions.
        self.assertEqual(response.data['totals']['pending_review'], 2)
        self.assertEqual(response.data['totals']['accepted'], 1)
        self.assertEqual(response.data['totals']['points_awarded'], accepted_contribution.frozen_global_points)

    def test_propose_only_steward_can_edit_active_proposal_note(self):
        """Proposal-only stewards can correct their generated note while pending."""
        StewardPermission.objects.filter(steward=self.steward).delete()
        StewardPermission.objects.create(
            steward=self.steward,
            contribution_type=self.contribution_type,
            action='propose'
        )

        self.client.force_authenticate(user=self.steward_user)
        response = self.client.post(
            f'/api/v1/steward-submissions/{self.submission.id}/propose/',
            {
                'proposed_action': 'reject',
                'proposed_staff_reply': 'Initial rejection reason',
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        note = SubmissionNote.objects.get(
            submitted_contribution=self.submission,
            is_proposal=True,
        )
        response = self.client.patch(
            f'/api/v1/steward-submissions/{self.submission.id}/notes/{note.id}/',
            {'message': 'Edited generated proposal note'},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        note.refresh_from_db()
        self.assertEqual(note.message, 'Edited generated proposal note')
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.proposed_action, 'reject')

    def test_proposal_note_cannot_be_edited_after_acceptance(self):
        """Generated proposal notes stay locked after final review."""
        self.submission.proposed_action = 'reject'
        self.submission.proposed_by = self.steward_user
        self.submission.state = 'accepted'
        self.submission.save()
        note = SubmissionNote.objects.create(
            submitted_contribution=self.submission,
            user=self.steward_user,
            message='Proposal note',
            is_proposal=True,
            data={'action': 'reject'},
        )

        self.client.force_authenticate(user=self.steward_user)
        response = self.client.patch(
            f'/api/v1/steward-submissions/{self.submission.id}/notes/{note.id}/',
            {'message': 'Edited after acceptance'},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        note.refresh_from_db()
        self.assertEqual(note.message, 'Proposal note')

    def test_steward_cannot_edit_non_proposal_note(self):
        """Regular CRM notes cannot be edited via the proposal note endpoint."""
        note = SubmissionNote.objects.create(
            submitted_contribution=self.submission,
            user=self.steward_user,
            message='Regular CRM note',
            is_proposal=False,
        )

        self.client.force_authenticate(user=self.steward_user)
        response = self.client.patch(
            f'/api/v1/steward-submissions/{self.submission.id}/notes/{note.id}/',
            {'message': 'Attempted edit'},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        note.refresh_from_db()
        self.assertEqual(note.message, 'Regular CRM note')

    def test_steward_cannot_edit_another_stewards_proposal_note(self):
        """Only the steward who owns the active proposal can edit its note."""
        other_steward_user = User.objects.create_user(
            email='other-steward@test.com',
            address='0x3333333333333333333333333333333333333333',
            password='testpass123',
        )
        other_steward = Steward.objects.create(user=other_steward_user)
        StewardPermission.objects.create(
            steward=other_steward,
            contribution_type=self.contribution_type,
            action='propose',
        )
        self.submission.proposed_action = 'reject'
        self.submission.proposed_by = other_steward_user
        self.submission.save()
        note = SubmissionNote.objects.create(
            submitted_contribution=self.submission,
            user=other_steward_user,
            message='Other steward proposal note',
            is_proposal=True,
            data={'action': 'reject'},
        )

        self.client.force_authenticate(user=self.steward_user)
        response = self.client.patch(
            f'/api/v1/steward-submissions/{self.submission.id}/notes/{note.id}/',
            {'message': 'Edited by wrong steward'},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        note.refresh_from_db()
        self.assertEqual(note.message, 'Other steward proposal note')
    
    def test_steward_can_review_submissions(self):
        """Test that stewards can review submissions."""
        # Authenticate as steward
        self.client.force_authenticate(user=self.steward_user)
        
        # Accept a submission
        response = self.client.post(
            f'/api/v1/steward-submissions/{self.submission.id}/review/',
            {
                'action': 'accept',
                'points': 50,
                'contribution_type': self.contribution_type.id
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Reload submission
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.state, 'accepted')
        self.assertEqual(self.submission.reviewed_by, self.steward_user)
        self.assertIsNotNone(self.submission.converted_contribution)
        self.assertEqual(self.submission.converted_contribution.points, 50)

    def test_second_steward_cannot_accept_already_accepted_submission(self):
        """A stale second accept must not create another contribution."""
        second_steward_user = User.objects.create_user(
            email='second-steward@test.com',
            address='0x3333333333333333333333333333333333333333',
            password='testpass123',
        )
        second_steward = Steward.objects.create(user=second_steward_user)
        StewardPermission.objects.create(
            steward=second_steward,
            contribution_type=self.contribution_type,
            action='accept',
        )

        self.client.force_authenticate(user=self.steward_user)
        first_response = self.client.post(
            f'/api/v1/steward-submissions/{self.submission.id}/review/',
            {
                'action': 'accept',
                'points': 50,
                'contribution_type': self.contribution_type.id
            },
            format='json'
        )
        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.submission.refresh_from_db()
        first_contribution_id = self.submission.converted_contribution_id

        second_client = APIClient()
        second_client.force_authenticate(user=second_steward_user)
        second_response = second_client.post(
            f'/api/v1/steward-submissions/{self.submission.id}/review/',
            {
                'action': 'accept',
                'points': 75,
                'contribution_type': self.contribution_type.id
            },
            format='json'
        )

        self.assertEqual(second_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.reviewed_by, self.steward_user)
        self.assertEqual(self.submission.converted_contribution_id, first_contribution_id)
        self.assertEqual(Contribution.objects.count(), 1)

    def test_accept_checks_permission_against_final_contribution_type(self):
        self.client.force_authenticate(user=self.steward_user)

        response = self.client.post(
            f'/api/v1/steward-submissions/{self.submission.id}/review/',
            {
                'action': 'accept',
                'points': 3,
                'contribution_type': self.other_contribution_type.id,
            },
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.state, 'pending')
        self.assertIsNone(self.submission.converted_contribution)

    def test_accept_validates_points_against_original_type_when_type_omitted(self):
        self.client.force_authenticate(user=self.steward_user)

        response = self.client.post(
            f'/api/v1/steward-submissions/{self.submission.id}/review/',
            {
                'action': 'accept',
                'points': 500,
            },
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.state, 'pending')

    def test_non_staff_steward_cannot_reassign_accepted_contribution(self):
        self.client.force_authenticate(user=self.steward_user)

        response = self.client.post(
            f'/api/v1/steward-submissions/{self.submission.id}/review/',
            {
                'action': 'accept',
                'points': 50,
                'contribution_type': self.contribution_type.id,
                'user': self.reassignment_user.id,
            },
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.state, 'pending')
        self.assertIsNone(self.submission.converted_contribution)
    
    def test_steward_can_reject_submissions(self):
        """Test that stewards can reject submissions."""
        # Authenticate as steward
        self.client.force_authenticate(user=self.steward_user)
        
        # Reject a submission
        response = self.client.post(
            f'/api/v1/steward-submissions/{self.submission.id}/review/',
            {
                'action': 'reject',
                'staff_reply': 'Insufficient evidence provided'
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Reload submission
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.state, 'rejected')
        self.assertEqual(self.submission.staff_reply, 'Insufficient evidence provided')
    
    def test_steward_can_request_more_info(self):
        """Test that stewards can request more information."""
        # Authenticate as steward
        self.client.force_authenticate(user=self.steward_user)
        
        # Request more info
        response = self.client.post(
            f'/api/v1/steward-submissions/{self.submission.id}/review/',
            {
                'action': 'more_info',
                'staff_reply': 'Please provide URL evidence'
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Reload submission
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.state, 'more_info_needed')
        self.assertEqual(self.submission.staff_reply, 'Please provide URL evidence')

    def test_steward_can_accept_more_info_needed_submission(self):
        """A submission waiting for more info remains reviewable after follow-up."""
        self.submission.state = 'more_info_needed'
        self.submission.reviewed_by = self.steward_user
        self.submission.reviewed_at = timezone.now()
        self.submission.staff_reply = 'Please provide URL evidence'
        self.submission.last_edited_at = timezone.now() + timezone.timedelta(minutes=1)
        self.submission.save()

        self.client.force_authenticate(user=self.steward_user)
        response = self.client.post(
            f'/api/v1/steward-submissions/{self.submission.id}/review/',
            {
                'action': 'accept',
                'points': 50,
                'contribution_type': self.contribution_type.id
            },
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.state, 'accepted')
        self.assertIsNotNone(self.submission.converted_contribution)
        self.assertEqual(self.submission.converted_contribution.points, 50)
    
    def test_steward_can_create_highlight(self):
        """Test that stewards can create highlights when accepting."""
        # Authenticate as steward
        self.client.force_authenticate(user=self.steward_user)
        
        # Accept with highlight
        response = self.client.post(
            f'/api/v1/steward-submissions/{self.submission.id}/review/',
            {
                'action': 'accept',
                'points': 75,
                'contribution_type': self.contribution_type.id,
                'create_highlight': True,
                'highlight_title': 'Outstanding Contribution',
                'highlight_description': 'This is an exceptional contribution'
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check highlight was created
        self.submission.refresh_from_db()
        self.assertTrue(self.submission.converted_contribution.highlights.exists())
        highlight = self.submission.converted_contribution.highlights.first()
        self.assertEqual(highlight.title, 'Outstanding Contribution')

    def test_steward_can_update_accepted_submission_points(self):
        """Test that stewards can correct points after accepting."""
        self.client.force_authenticate(user=self.steward_user)
        self.client.post(
            f'/api/v1/steward-submissions/{self.submission.id}/review/',
            {
                'action': 'accept',
                'points': 50,
                'contribution_type': self.contribution_type.id
            },
            format='json'
        )

        response = self.client.post(
            f'/api/v1/steward-submissions/{self.submission.id}/update-accepted/',
            {'points': 80},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.converted_contribution.points, 80)
        self.assertEqual(response.data['contribution']['points'], 80)

    def test_accepted_submission_list_includes_contribution_points(self):
        """Accepted submissions list includes enough contribution data for steward edits."""
        self.client.force_authenticate(user=self.steward_user)
        self.client.post(
            f'/api/v1/steward-submissions/{self.submission.id}/review/',
            {
                'action': 'accept',
                'points': 50,
                'contribution_type': self.contribution_type.id
            },
            format='json'
        )

        response = self.client.get('/api/v1/steward-submissions/?state=accepted')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result = response.data['results'][0]
        self.assertIsNotNone(result['contribution'])
        self.assertEqual(result['contribution']['points'], 50)
        self.assertIn('highlight', result['contribution'])

    def test_steward_can_feature_accepted_submission(self):
        """Test that stewards can feature a contribution after accepting."""
        self.client.force_authenticate(user=self.steward_user)
        self.client.post(
            f'/api/v1/steward-submissions/{self.submission.id}/review/',
            {
                'action': 'accept',
                'points': 50,
                'contribution_type': self.contribution_type.id
            },
            format='json'
        )

        response = self.client.post(
            f'/api/v1/steward-submissions/{self.submission.id}/update-accepted/',
            {
                'points': 50,
                'create_highlight': True,
                'highlight_title': 'Featured after review',
                'highlight_description': 'Added after points were assigned'
            },
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.submission.refresh_from_db()
        highlight = ContributionHighlight.objects.get(
            contribution=self.submission.converted_contribution
        )
        self.assertEqual(highlight.title, 'Featured after review')
        self.assertEqual(response.data['contribution']['highlight']['title'], 'Featured after review')

    def test_steward_can_remove_accepted_submission_highlight(self):
        """Test that stewards can remove a feature after accepting."""
        self.client.force_authenticate(user=self.steward_user)
        self.client.post(
            f'/api/v1/steward-submissions/{self.submission.id}/review/',
            {
                'action': 'accept',
                'points': 50,
                'contribution_type': self.contribution_type.id,
                'create_highlight': True,
                'highlight_title': 'Featured after review',
                'highlight_description': 'Added after points were assigned'
            },
            format='json'
        )

        response = self.client.post(
            f'/api/v1/steward-submissions/{self.submission.id}/update-accepted/',
            {
                'points': 50,
                'remove_highlight': True
            },
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.submission.refresh_from_db()
        self.assertFalse(
            ContributionHighlight.objects.filter(
                contribution=self.submission.converted_contribution
            ).exists()
        )
        self.assertIsNone(response.data['contribution']['highlight'])
    
    def test_points_validation(self):
        """Test that points are validated within contribution type limits."""
        # Authenticate as steward
        self.client.force_authenticate(user=self.steward_user)
        
        # Try to accept with points below minimum
        response = self.client.post(
            f'/api/v1/steward-submissions/{self.submission.id}/review/',
            {
                'action': 'accept',
                'points': 5,  # Below min of 10
                'contribution_type': self.contribution_type.id
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('points', response.data)
        
        # Try to accept with points above maximum
        response = self.client.post(
            f'/api/v1/steward-submissions/{self.submission.id}/review/',
            {
                'action': 'accept',
                'points': 150,  # Above max of 100
                'contribution_type': self.contribution_type.id
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('points', response.data)
    
    def test_required_fields_validation(self):
        """Test that required fields are validated."""
        # Authenticate as steward
        self.client.force_authenticate(user=self.steward_user)
        
        # Try to accept without points
        response = self.client.post(
            f'/api/v1/steward-submissions/{self.submission.id}/review/',
            {
                'action': 'accept'
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('points', response.data)
        
        # Try to reject without staff reply
        response = self.client.post(
            f'/api/v1/steward-submissions/{self.submission.id}/review/',
            {
                'action': 'reject'
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('staff_reply', response.data)
