from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from contributions.models import (
    Category,
    Contribution,
    ContributionType,
    Evidence,
    SubmissionNote,
    SubmissionStateTransition,
    SubmittedContribution,
)
from leaderboard.models import GlobalLeaderboardMultiplier
from stewards.models import Steward, StewardPermission


User = get_user_model()


class StewardSubmissionSearchTest(TestCase):
    """Test steward submission search and ordering behavior."""

    def setUp(self):
        self.category = Category.objects.create(
            name='Test Category',
            slug='test',
            description='Test category',
        )
        self.contribution_type = ContributionType.objects.create(
            name='Test Type',
            slug='test-type',
            description='Test contribution type',
            category=self.category,
            min_points=0,
            max_points=100,
        )
        GlobalLeaderboardMultiplier.objects.create(
            contribution_type=self.contribution_type,
            multiplier_value=1,
            valid_from=timezone.now() - timezone.timedelta(days=1),
        )
        self.regular_user = User.objects.create_user(
            email='regular@test.com',
            address='0x1234567890123456789012345678901234567890',
            password='testpass123',
        )
        self.steward_user = User.objects.create_user(
            email='steward@test.com',
            address='0x0987654321098765432109876543210987654321',
            password='testpass123',
        )
        self.other_steward_user = User.objects.create_user(
            email='joaquin@test.com',
            address='0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
            password='testpass123',
            name='Joaquin Bressan',
        )
        self.steward = Steward.objects.create(user=self.steward_user)
        self.other_steward = Steward.objects.create(user=self.other_steward_user)
        StewardPermission.objects.create(
            steward=self.steward,
            contribution_type=self.contribution_type,
            action='accept',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.steward_user)

    def _create_accepted_submission(
        self,
        *,
        points=50,
        reviewed_at=None,
        submitted_url=None,
        converted_url=None,
        title='Accepted submission',
    ) -> SubmittedContribution:
        contribution = Contribution.objects.create(
            user=self.regular_user,
            contribution_type=self.contribution_type,
            contribution_date=timezone.now(),
            points=points,
            title=title,
            notes=f'{title} contribution notes',
        )
        if converted_url:
            Evidence.objects.create(
                contribution=contribution,
                url=converted_url,
                description=f'{title} converted evidence',
            )

        submission = SubmittedContribution.objects.create(
            user=self.regular_user,
            contribution_type=self.contribution_type,
            contribution_date=timezone.now(),
            notes=f'{title} submission notes',
            title=title,
            state='accepted',
            reviewed_by=self.steward_user,
            reviewed_at=reviewed_at or timezone.now(),
            converted_contribution=contribution,
        )
        if submitted_url:
            Evidence.objects.create(
                submitted_contribution=submission,
                url=submitted_url,
                description=f'{title} submitted evidence',
            )
        return submission

    def test_accepted_submission_search_matches_submitted_and_converted_evidence(self):
        """Accepted search covers original submitted evidence and copied contribution evidence."""
        submitted_match = self._create_accepted_submission(
            title='Submitted evidence match',
            submitted_url='https://x.com/FIREDRAGON10101/status/2060708443153928646',
        )
        converted_match = self._create_accepted_submission(
            title='Converted evidence match',
            converted_url='https://github.com/GenLayerLabs/search-demo',
        )

        response = self.client.get('/api/v1/steward-submissions/', {
            'state': 'accepted',
            'include_content': 'https://x.com/FIREDRAGON10101/status/2060708443153928646',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result_ids = {str(item['id']) for item in response.data['results']}
        self.assertEqual(result_ids, {str(submitted_match.id)})

        response = self.client.get('/api/v1/steward-submissions/', {
            'state': 'accepted',
            'include_content': 'https://github.com/GenLayerLabs/search-demo',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result_ids = {str(item['id']) for item in response.data['results']}
        self.assertEqual(result_ids, {str(converted_match.id)})

    def test_accepted_submission_search_matches_normalized_url(self):
        """Tracking params should not prevent URL searches from finding accepted evidence."""
        submission = self._create_accepted_submission(
            submitted_url='https://x.com/FIREDRAGON10101/status/2060708443153928646',
        )

        response = self.client.get('/api/v1/steward-submissions/', {
            'state': 'accepted',
            'include_content': 'https://x.com/FIREDRAGON10101/status/2060708443153928646?s=20',
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result_ids = {str(item['id']) for item in response.data['results']}
        self.assertEqual(result_ids, {str(submission.id)})

    def test_accepted_submissions_can_order_by_points_and_reviewed_time(self):
        older_low = self._create_accepted_submission(
            points=20,
            reviewed_at=timezone.now() - timezone.timedelta(days=2),
            title='Older low points',
        )
        newer_high = self._create_accepted_submission(
            points=90,
            reviewed_at=timezone.now() - timezone.timedelta(days=1),
            title='Newer high points',
        )

        response = self.client.get('/api/v1/steward-submissions/', {
            'state': 'accepted',
            'ordering': '-converted_contribution__frozen_global_points',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result_ids = [str(item['id']) for item in response.data['results']]
        self.assertEqual(result_ids[:2], [str(newer_high.id), str(older_low.id)])

        response = self.client.get('/api/v1/steward-submissions/', {
            'state': 'accepted',
            'ordering': '-reviewed_at',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result_ids = [str(item['id']) for item in response.data['results']]
        self.assertEqual(result_ids[:2], [str(newer_high.id), str(older_low.id)])

    def test_can_exclude_multiple_assignment_values(self):
        unassigned = SubmittedContribution.objects.create(
            user=self.regular_user,
            contribution_type=self.contribution_type,
            contribution_date=timezone.now(),
            notes='Unassigned submission',
            state='pending',
        )
        assigned_to_other = SubmittedContribution.objects.create(
            user=self.regular_user,
            contribution_type=self.contribution_type,
            contribution_date=timezone.now(),
            notes='Assigned to Joaquin',
            state='pending',
            assigned_to=self.other_steward_user,
        )
        assigned_to_current = SubmittedContribution.objects.create(
            user=self.regular_user,
            contribution_type=self.contribution_type,
            contribution_date=timezone.now(),
            notes='Assigned to current steward',
            state='pending',
            assigned_to=self.steward_user,
        )

        response = self.client.get('/api/v1/steward-submissions/', {
            'state': 'pending',
            'exclude_assigned_to': f'unassigned,{self.other_steward_user.id}',
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result_ids = {str(item['id']) for item in response.data['results']}
        self.assertNotIn(str(unassigned.id), result_ids)
        self.assertNotIn(str(assigned_to_other.id), result_ids)
        self.assertIn(str(assigned_to_current.id), result_ids)

    def test_can_include_multiple_assignment_values(self):
        unassigned = SubmittedContribution.objects.create(
            user=self.regular_user,
            contribution_type=self.contribution_type,
            contribution_date=timezone.now(),
            notes='Unassigned submission',
            state='pending',
        )
        assigned_to_other = SubmittedContribution.objects.create(
            user=self.regular_user,
            contribution_type=self.contribution_type,
            contribution_date=timezone.now(),
            notes='Assigned to Joaquin',
            state='pending',
            assigned_to=self.other_steward_user,
        )
        assigned_to_current = SubmittedContribution.objects.create(
            user=self.regular_user,
            contribution_type=self.contribution_type,
            contribution_date=timezone.now(),
            notes='Assigned to current steward',
            state='pending',
            assigned_to=self.steward_user,
        )

        response = self.client.get('/api/v1/steward-submissions/', {
            'state': 'pending',
            'assigned_to': f'unassigned,{self.other_steward_user.id}',
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result_ids = {str(item['id']) for item in response.data['results']}
        self.assertIn(str(unassigned.id), result_ids)
        self.assertIn(str(assigned_to_other.id), result_ids)
        self.assertNotIn(str(assigned_to_current.id), result_ids)

    def test_can_filter_unassigned_more_info_resubmissions_from_transition_history(self):
        resubmitted = SubmittedContribution.objects.create(
            user=self.regular_user,
            contribution_type=self.contribution_type,
            contribution_date=timezone.now(),
            notes='User supplied the requested follow-up.',
            state='pending',
        )
        SubmissionStateTransition.record(
            resubmitted,
            SubmissionStateTransition.EVENT_EDITED,
            from_state='more_info_needed',
            actor=self.regular_user,
        )
        ordinary_pending = SubmittedContribution.objects.create(
            user=self.regular_user,
            contribution_type=self.contribution_type,
            contribution_date=timezone.now(),
            notes='Ordinary pending submission.',
            state='pending',
        )
        assigned_resubmission = SubmittedContribution.objects.create(
            user=self.regular_user,
            contribution_type=self.contribution_type,
            contribution_date=timezone.now(),
            notes='Resubmitted but already assigned.',
            state='pending',
            assigned_to=self.other_steward_user,
        )
        SubmissionStateTransition.record(
            assigned_resubmission,
            SubmissionStateTransition.EVENT_EDITED,
            from_state='more_info_needed',
            actor=self.regular_user,
        )

        response = self.client.get('/api/v1/steward-submissions/', {
            'state': 'pending',
            'assigned_to': 'unassigned',
            'is_more_info_resubmitted': 'true',
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result_ids = {str(item['id']) for item in response.data['results']}
        self.assertEqual(result_ids, {str(resubmitted.id)})

        response = self.client.get('/api/v1/steward-submissions/', {
            'state': 'pending',
            'is_more_info_resubmitted': 'false',
        })
        result_ids = {str(item['id']) for item in response.data['results']}
        self.assertIn(str(ordinary_pending.id), result_ids)
        self.assertNotIn(str(resubmitted.id), result_ids)
        self.assertNotIn(str(assigned_resubmission.id), result_ids)

    def test_can_filter_pending_unassigned_submissions_with_more_info_request_blocks(self):
        requested = SubmittedContribution.objects.create(
            user=self.regular_user,
            contribution_type=self.contribution_type,
            contribution_date=timezone.now(),
            notes='Currently pending after a request.',
            state='pending',
        )
        SubmissionNote.objects.create(
            submitted_contribution=requested,
            user=self.steward_user,
            message='Reviewed: more_info\n\n> Please provide a clearer link.',
            is_proposal=False,
            data={
                'action': 'more_info',
                'staff_reply': 'Please provide a clearer link.',
            },
        )
        ordinary_pending = SubmittedContribution.objects.create(
            user=self.regular_user,
            contribution_type=self.contribution_type,
            contribution_date=timezone.now(),
            notes='No more-information request.',
            state='pending',
        )

        response = self.client.get('/api/v1/steward-submissions/', {
            'state': 'pending',
            'assigned_to': 'unassigned',
            'has_more_info_request': 'true',
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result_ids = {str(item['id']) for item in response.data['results']}
        self.assertEqual(result_ids, {str(requested.id)})

        response = self.client.get('/api/v1/steward-submissions/', {
            'state': 'pending',
            'has_more_info_request': 'false',
        })
        result_ids = {str(item['id']) for item in response.data['results']}
        self.assertIn(str(ordinary_pending.id), result_ids)
        self.assertNotIn(str(requested.id), result_ids)

    def test_can_filter_escalated_submissions_and_serialize_review_layer_fields(self):
        self.contribution_type.requires_ai_review = True
        self.contribution_type.escalation_threshold_points = 400
        self.contribution_type.save(update_fields=[
            'requires_ai_review',
            'escalation_threshold_points',
        ])
        escalated_at = timezone.now()
        escalated = SubmittedContribution.objects.create(
            user=self.regular_user,
            contribution_type=self.contribution_type,
            contribution_date=timezone.now(),
            notes='Escalated submission',
            state='pending',
            proposed_action='accept',
            proposed_points=50,
            proposed_by=self.steward_user,
            proposed_at=escalated_at,
            escalated_at=escalated_at,
        )
        ordinary = SubmittedContribution.objects.create(
            user=self.regular_user,
            contribution_type=self.contribution_type,
            contribution_date=timezone.now(),
            notes='Ordinary appealed submission',
            state='pending',
            has_appeal=True,
        )

        response = self.client.get('/api/v1/steward-submissions/', {
            'state': 'pending',
            'is_escalated': 'true',
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        result = response.data['results'][0]
        self.assertEqual(str(result['id']), str(escalated.id))
        self.assertIsNotNone(result['escalated_at'])
        self.assertTrue(result['contribution_type_details']['requires_ai_review'])
        self.assertEqual(
            result['contribution_type_details']['escalation_threshold_points'],
            400,
        )

        response = self.client.get('/api/v1/steward-submissions/', {
            'state': 'pending',
            'is_escalated': 'false',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result_ids = {str(item['id']) for item in response.data['results']}
        self.assertIn(str(ordinary.id), result_ids)
        self.assertNotIn(str(escalated.id), result_ids)

        type_response = self.client.get(
            f'/api/v1/contribution-types/{self.contribution_type.id}/'
        )
        self.assertEqual(type_response.status_code, status.HTTP_200_OK)
        self.assertTrue(type_response.data['requires_ai_review'])
        self.assertEqual(type_response.data['escalation_threshold_points'], 400)

    def test_user_serializer_exposes_effective_steward_tier(self):
        self.steward.tier = Steward.TIER_TOP_LEVEL
        self.steward.save(update_fields=['tier'])

        response = self.client.get('/api/v1/users/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['steward_tier'], Steward.TIER_TOP_LEVEL)

        self.steward_user.is_superuser = True
        self.steward_user.save(update_fields=['is_superuser'])
        response = self.client.get('/api/v1/users/me/')
        self.assertEqual(response.data['steward_tier'], Steward.TIER_APEX)

        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get('/api/v1/users/me/')
        self.assertIsNone(response.data['steward_tier'])

        response = self.client.get(
            f'/api/v1/users/by-address/{self.steward_user.id}/'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data['steward_tier'])

    def test_invalid_steward_id_filters_do_not_error(self):
        pending = SubmittedContribution.objects.create(
            user=self.regular_user,
            contribution_type=self.contribution_type,
            contribution_date=timezone.now(),
            notes='Pending proposal',
            state='pending',
            assigned_to=self.other_steward_user,
            proposed_action='reject',
            proposed_by=self.other_steward_user,
        )
        reviewed = self._create_accepted_submission(title='Reviewed submission')

        include_assigned = self.client.get('/api/v1/steward-submissions/', {
            'state': 'pending',
            'assigned_to': 'abc',
        })
        self.assertEqual(include_assigned.status_code, status.HTTP_200_OK)
        self.assertEqual(include_assigned.data['results'], [])

        exclude_assigned = self.client.get('/api/v1/steward-submissions/', {
            'state': 'pending',
            'exclude_assigned_to': 'abc',
        })
        self.assertEqual(exclude_assigned.status_code, status.HTTP_200_OK)
        self.assertIn(str(pending.id), {str(item['id']) for item in exclude_assigned.data['results']})

        include_reviewed = self.client.get('/api/v1/steward-submissions/', {
            'state': 'accepted',
            'reviewed_by': 'abc',
        })
        self.assertEqual(include_reviewed.status_code, status.HTTP_200_OK)
        self.assertEqual(include_reviewed.data['results'], [])

        exclude_reviewed = self.client.get('/api/v1/steward-submissions/', {
            'state': 'accepted',
            'exclude_reviewed_by': 'abc',
        })
        self.assertEqual(exclude_reviewed.status_code, status.HTTP_200_OK)
        self.assertIn(str(reviewed.id), {str(item['id']) for item in exclude_reviewed.data['results']})

        include_proposed = self.client.get('/api/v1/steward-submissions/', {
            'state': 'pending',
            'proposed_by': 'abc',
        })
        self.assertEqual(include_proposed.status_code, status.HTTP_200_OK)
        self.assertEqual(include_proposed.data['results'], [])

        exclude_proposed = self.client.get('/api/v1/steward-submissions/', {
            'state': 'pending',
            'exclude_proposed_by': 'abc',
        })
        self.assertEqual(exclude_proposed.status_code, status.HTTP_200_OK)
        self.assertIn(str(pending.id), {str(item['id']) for item in exclude_proposed.data['results']})
