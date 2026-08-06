from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from contributions.models import (
    Category,
    ContributionType,
    Evidence,
    EvidenceURLType,
    SubmissionMoreInfoResponse,
    SubmissionNote,
    SubmissionStateTransition,
    SubmittedContribution,
)
from leaderboard.models import GlobalLeaderboardMultiplier
from notifications.models import Notification
from social_connections.models import DiscordRole
from stewards.models import Steward, StewardPermission


User = get_user_model()


class MoreInfoResponseAPITest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name='Response Test',
            slug='response-test',
            description='Response test category',
        )
        self.contribution_type = ContributionType.objects.create(
            name='Response Test Type',
            slug='response-test-type',
            description='Response test contribution type',
            category=self.category,
            min_points=1,
            max_points=100,
        )
        GlobalLeaderboardMultiplier.objects.create(
            contribution_type=self.contribution_type,
            multiplier_value=1,
            valid_from=timezone.now() - timezone.timedelta(days=1),
        )
        self.other_evidence_type, _ = EvidenceURLType.objects.update_or_create(
            slug='other',
            defaults={
                'name': 'Other',
                'url_patterns': [],
                'is_generic': True,
                'order': 99,
            },
        )
        self.owner = User.objects.create_user(
            email='response-owner@test.com',
            address='0x1111111111111111111111111111111111111111',
            password='pass',
            name='Response Owner',
        )
        self.other_user = User.objects.create_user(
            email='response-other@test.com',
            address='0x2222222222222222222222222222222222222222',
            password='pass',
        )
        self.steward_user = User.objects.create_user(
            email='response-steward@test.com',
            address='0x3333333333333333333333333333333333333333',
            password='pass',
            name='Response Steward',
        )
        self.steward = Steward.objects.create(user=self.steward_user)
        StewardPermission.objects.create(
            steward=self.steward,
            contribution_type=self.contribution_type,
            action='accept',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.owner)

    def _make_more_info_submission(
        self,
        *,
        request_message='Please document the repository setup.',
        structured=True,
        owner=None,
    ):
        owner = owner or self.owner
        submission = SubmittedContribution.objects.create(
            user=owner,
            contribution_type=self.contribution_type,
            contribution_date=timezone.now(),
            title='Repository work',
            notes='Original submission notes',
            state='more_info_needed',
            staff_reply=request_message,
            reviewed_by=self.steward_user,
            reviewed_at=timezone.now(),
            assigned_to=self.steward_user,
            gate_reviewed=True,
        )
        Evidence.objects.create(
            submitted_contribution=submission,
            url=f'https://example.com/proof/{submission.id}',
            description='Proof',
            url_type=self.other_evidence_type,
        )
        note = None
        if structured:
            note = SubmissionNote.objects.create(
                submitted_contribution=submission,
                user=self.steward_user,
                message=f'Reviewed: **more_info**\n\n> {request_message}',
                is_proposal=False,
                data={
                    'action': 'more_info',
                    'staff_reply': request_message,
                },
            )
        return submission, note

    def _response_payload(self, note, message='Updated the repository documentation.'):
        return {
            'more_info_response': {
                'request_id': note.id if note else None,
                'message': message,
            },
        }

    def test_response_is_required_and_blank_or_too_long_is_rejected(self):
        submission, note = self._make_more_info_submission()
        url = f'/api/v1/submissions/{submission.id}/'

        missing = self.client.patch(url, {'notes': 'Edited'}, format='json')
        self.assertEqual(missing.status_code, status.HTTP_400_BAD_REQUEST)

        blank = self.client.patch(
            url,
            self._response_payload(note, message='   '),
            format='json',
        )
        self.assertEqual(blank.status_code, status.HTTP_400_BAD_REQUEST)

        too_long = self.client.patch(
            url,
            self._response_payload(note, message='x' * 1001),
            format='json',
        )
        self.assertEqual(too_long.status_code, status.HTTP_400_BAD_REQUEST)

        submission.refresh_from_db()
        self.assertEqual(submission.state, 'more_info_needed')
        self.assertEqual(submission.notes, 'Original submission notes')
        self.assertFalse(
            SubmissionMoreInfoResponse.objects.filter(
                submitted_contribution=submission,
            ).exists()
        )

    def test_direct_response_reopens_submission_and_serializes_pair(self):
        submission, note = self._make_more_info_submission()

        response = self.client.patch(
            f'/api/v1/submissions/{submission.id}/',
            self._response_payload(note),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        submission.refresh_from_db()
        self.assertEqual(submission.state, 'pending')
        self.assertEqual(submission.staff_reply, '')
        self.assertFalse(submission.gate_reviewed)
        self.assertIsNone(submission.reviewed_by)
        self.assertIsNone(submission.reviewed_at)

        stored = SubmissionMoreInfoResponse.objects.get(
            submitted_contribution=submission,
        )
        self.assertEqual(stored.request_note, note)
        self.assertEqual(stored.request_message, note.data['staff_reply'])
        self.assertEqual(stored.requested_by, self.steward_user)
        self.assertEqual(stored.responder, self.owner)

        (request_data,) = response.data['more_info_requests']
        self.assertEqual(request_data['id'], note.id)
        self.assertEqual(request_data['message'], note.data['staff_reply'])
        self.assertEqual(
            request_data['response']['message'],
            'Updated the repository documentation.',
        )
        self.assertEqual(request_data['response']['user'], self.owner.id)
        self.assertIsNotNone(request_data['response']['created_at'])

        transition = SubmissionStateTransition.objects.get(
            submitted_contribution=submission,
            event=SubmissionStateTransition.EVENT_EDITED,
        )
        self.assertEqual(
            (transition.from_state, transition.to_state),
            ('more_info_needed', 'pending'),
        )
        notification = Notification.objects.get(
            recipient=self.steward_user,
            event_type='submission.more_info_resubmitted',
        )
        self.assertIn('responded to your more-information request', notification.body)

    def test_stale_mismatched_and_duplicate_responses_are_rejected(self):
        submission, stale_note = self._make_more_info_submission()
        current_note = SubmissionNote.objects.create(
            submitted_contribution=submission,
            user=self.steward_user,
            message='Reviewed: **more_info**\n\n> Send the latest release link.',
            data={
                'action': 'more_info',
                'staff_reply': 'Send the latest release link.',
            },
        )

        stale = self.client.patch(
            f'/api/v1/submissions/{submission.id}/',
            self._response_payload(stale_note),
            format='json',
        )
        self.assertEqual(stale.status_code, status.HTTP_409_CONFLICT)

        other_submission, other_note = self._make_more_info_submission()
        mismatched = self.client.patch(
            f'/api/v1/submissions/{submission.id}/',
            self._response_payload(other_note),
            format='json',
        )
        self.assertEqual(mismatched.status_code, status.HTTP_409_CONFLICT)

        successful = self.client.patch(
            f'/api/v1/submissions/{submission.id}/',
            self._response_payload(current_note),
            format='json',
        )
        self.assertEqual(successful.status_code, status.HTTP_200_OK)

        duplicate = self.client.patch(
            f'/api/v1/submissions/{submission.id}/',
            self._response_payload(current_note),
            format='json',
        )
        self.assertEqual(duplicate.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            SubmissionMoreInfoResponse.objects.filter(
                submitted_contribution=submission,
            ).count(),
            1,
        )
        self.assertEqual(other_submission.state, 'more_info_needed')

    def test_source_and_request_are_owner_scoped(self):
        submission, note = self._make_more_info_submission()
        self.client.force_authenticate(user=self.other_user)

        response = self.client.patch(
            f'/api/v1/submissions/{submission.id}/',
            self._response_payload(note),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        submission.refresh_from_db()
        self.assertEqual(submission.state, 'more_info_needed')
        self.assertFalse(
            SubmissionMoreInfoResponse.objects.filter(
                submitted_contribution=submission,
            ).exists()
        )

    def test_failed_snapshot_validation_rolls_back_edits_and_response(self):
        submission, note = self._make_more_info_submission()
        github_type, _ = EvidenceURLType.objects.update_or_create(
            slug='github-repo',
            defaults={
                'name': 'GitHub Repository',
                'url_patterns': [r'^https?://github\.com/[^/]+/[^/]+/?$'],
                'is_generic': False,
                'order': 1,
                'ownership_social_account': '',
            },
        )
        self.contribution_type.required_evidence_url_types.set([github_type])
        payload = self._response_payload(note)
        payload['notes'] = 'This edit must roll back.'

        response = self.client.patch(
            f'/api/v1/submissions/{submission.id}/',
            payload,
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        submission.refresh_from_db()
        self.assertEqual(submission.state, 'more_info_needed')
        self.assertEqual(submission.notes, 'Original submission notes')
        self.assertFalse(
            SubmissionMoreInfoResponse.objects.filter(
                submitted_contribution=submission,
            ).exists()
        )

    @patch(
        'contributions.views.SubmissionMoreInfoResponse.objects.create',
        side_effect=IntegrityError('simulated response write failure'),
    )
    def test_response_write_failure_rolls_back_submission_edits(self, _create):
        submission, note = self._make_more_info_submission()
        self.client.raise_request_exception = False
        payload = self._response_payload(note)
        payload['notes'] = 'This must be rolled back with the response.'

        response = self.client.patch(
            f'/api/v1/submissions/{submission.id}/',
            payload,
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        submission.refresh_from_db()
        self.assertEqual(submission.state, 'more_info_needed')
        self.assertEqual(submission.notes, 'Original submission notes')
        self.assertEqual(submission.staff_reply, note.data['staff_reply'])
        self.assertFalse(submission.more_info_responses.exists())

    def test_current_social_requirement_blocks_direct_resubmission(self):
        submission, note = self._make_more_info_submission()
        self.contribution_type.required_social_accounts = ['github']
        self.contribution_type.save(update_fields=['required_social_accounts'])

        response = self.client.patch(
            f'/api/v1/submissions/{submission.id}/',
            self._response_payload(note),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        submission.refresh_from_db()
        self.assertEqual(submission.state, 'more_info_needed')
        self.assertFalse(submission.more_info_responses.exists())

    def test_current_discord_role_requirement_blocks_direct_resubmission(self):
        submission, note = self._make_more_info_submission()
        role = DiscordRole.objects.create(
            guild_id='response-guild',
            role_id='response-role',
            name='Response reviewer',
            position=1,
        )
        self.contribution_type.required_discord_roles.add(role)

        response = self.client.patch(
            f'/api/v1/submissions/{submission.id}/',
            self._response_payload(note),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        submission.refresh_from_db()
        self.assertEqual(submission.state, 'more_info_needed')
        self.assertFalse(submission.more_info_responses.exists())

    def test_current_url_ownership_rule_blocks_direct_resubmission(self):
        submission, note = self._make_more_info_submission()
        github_type, _ = EvidenceURLType.objects.update_or_create(
            slug='github-repo',
            defaults={
                'name': 'GitHub Repository',
                'url_patterns': [r'^https?://github\.com/[^/]+/[^/]+/?$'],
                'handle_extract_pattern': r'github\.com/(?P<handle>[^/]+)/',
                'ownership_social_account': 'github',
                'allow_duplicate': False,
                'is_generic': False,
                'order': 1,
            },
        )
        self.contribution_type.accepted_evidence_url_types.set([github_type])
        evidence = submission.evidence_items.get()
        evidence.url = 'https://github.com/a-different-owner/project'
        evidence.url_type = github_type
        evidence.save()

        response = self.client.patch(
            f'/api/v1/submissions/{submission.id}/',
            self._response_payload(note),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        submission.refresh_from_db()
        self.assertEqual(submission.state, 'more_info_needed')
        self.assertFalse(submission.more_info_responses.exists())

    def test_legacy_request_is_snapshotted_without_fabricating_history(self):
        submission, note = self._make_more_info_submission(structured=False)
        self.assertIsNone(note)

        before = self.client.get(f'/api/v1/submissions/{submission.id}/')
        self.assertEqual(before.status_code, status.HTTP_200_OK)
        (active_request,) = before.data['more_info_requests']
        self.assertTrue(active_request['legacy'])
        self.assertIsNone(active_request['response'])
        self.assertEqual(
            SubmissionMoreInfoResponse.objects.filter(
                submitted_contribution=submission,
            ).count(),
            0,
        )

        response = self.client.patch(
            f'/api/v1/submissions/{submission.id}/',
            self._response_payload(None),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        stored = SubmissionMoreInfoResponse.objects.get(
            submitted_contribution=submission,
        )
        self.assertIsNone(stored.request_note)
        self.assertEqual(
            stored.request_message,
            'Please document the repository setup.',
        )
        (paired_request,) = response.data['more_info_requests']
        self.assertTrue(paired_request['legacy'])
        self.assertIsNotNone(paired_request['response'])

    def test_each_more_information_cycle_keeps_its_own_response(self):
        submission, first_note = self._make_more_info_submission(
            request_message='Add setup instructions.',
        )
        first = self.client.patch(
            f'/api/v1/submissions/{submission.id}/',
            self._response_payload(first_note, 'Added setup instructions.'),
            format='json',
        )
        self.assertEqual(first.status_code, status.HTTP_200_OK, first.data)

        submission.refresh_from_db()
        submission.state = 'more_info_needed'
        submission.staff_reply = 'Now add a release link.'
        submission.reviewed_by = self.steward_user
        submission.reviewed_at = timezone.now()
        submission.save(update_fields=[
            'state', 'staff_reply', 'reviewed_by', 'reviewed_at', 'updated_at',
        ])
        second_note = SubmissionNote.objects.create(
            submitted_contribution=submission,
            user=self.steward_user,
            message='Reviewed: **more_info**\n\n> Now add a release link.',
            data={
                'action': 'more_info',
                'staff_reply': 'Now add a release link.',
            },
        )

        second = self.client.patch(
            f'/api/v1/submissions/{submission.id}/',
            self._response_payload(second_note, 'Added the release link.'),
            format='json',
        )

        self.assertEqual(second.status_code, status.HTTP_200_OK, second.data)
        self.assertEqual(
            SubmissionMoreInfoResponse.objects.filter(
                submitted_contribution=submission,
            ).count(),
            2,
        )
        pairs = {
            request['message']: request['response']['message']
            for request in second.data['more_info_requests']
        }
        self.assertEqual(pairs, {
            'Add setup instructions.': 'Added setup instructions.',
            'Now add a release link.': 'Added the release link.',
        })

    def test_legacy_fallback_can_follow_an_answered_structured_cycle(self):
        submission, first_note = self._make_more_info_submission(
            request_message='Add setup instructions.',
        )
        first = self.client.patch(
            f'/api/v1/submissions/{submission.id}/',
            self._response_payload(first_note, 'Added setup instructions.'),
            format='json',
        )
        self.assertEqual(first.status_code, status.HTTP_200_OK, first.data)

        submission.refresh_from_db()
        submission.state = 'more_info_needed'
        submission.staff_reply = 'Add deployment notes from the legacy review.'
        submission.reviewed_by = self.steward_user
        submission.reviewed_at = timezone.now()
        submission.save(update_fields=[
            'state', 'staff_reply', 'reviewed_by', 'reviewed_at', 'updated_at',
        ])

        second = self.client.patch(
            f'/api/v1/submissions/{submission.id}/',
            self._response_payload(None, 'Added the deployment notes.'),
            format='json',
        )

        self.assertEqual(second.status_code, status.HTTP_200_OK, second.data)
        self.assertEqual(
            SubmissionMoreInfoResponse.objects.filter(
                submitted_contribution=submission,
            ).count(),
            2,
        )
        legacy_pair = next(
            request
            for request in second.data['more_info_requests']
            if request['legacy']
        )
        self.assertEqual(
            legacy_pair['message'],
            'Add deployment notes from the legacy review.',
        )
        self.assertEqual(
            legacy_pair['response']['message'],
            'Added the deployment notes.',
        )

    def test_steward_search_matches_response_text(self):
        submission, note = self._make_more_info_submission()
        response = self.client.patch(
            f'/api/v1/submissions/{submission.id}/',
            self._response_payload(
                note,
                'Published the uncommon-response-token release notes.',
            ),
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        self.client.force_authenticate(user=self.steward_user)
        search = self.client.get('/api/v1/steward-submissions/', {
            'state': 'pending',
            'search': 'uncommon-response-token',
        })

        self.assertEqual(search.status_code, status.HTTP_200_OK, search.data)
        result_ids = {str(item['id']) for item in search.data['results']}
        self.assertEqual(result_ids, {str(submission.id)})
