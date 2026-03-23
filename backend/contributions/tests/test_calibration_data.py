"""
Tests for the calibration data system — structured data in SubmissionNote.

Verifies that both AI and human review actions store structured data
in the SubmissionNote.data JSONField for later calibration comparison.
"""

from datetime import timedelta

from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from contributions.models import (
    Category,
    ContributionType,
    Evidence,
    SubmissionNote,
    SubmittedContribution,
)
from leaderboard.models import GlobalLeaderboardMultiplier
from stewards.models import ReviewTemplate, Steward, StewardPermission
from users.models import User


def _create_test_fixtures():
    """Create common test fixtures for calibration tests."""
    category, _ = Category.objects.get_or_create(
        slug='builder',
        defaults={'name': 'Builder', 'description': 'Builder category'},
    )
    ct, _ = ContributionType.objects.get_or_create(
        slug='educational-content',
        defaults={
            'name': 'Educational Content',
            'category': category,
            'min_points': 1,
            'max_points': 10,
        },
    )
    # Create multiplier for the contribution type
    GlobalLeaderboardMultiplier.objects.create(
        contribution_type=ct,
        multiplier_value=1.0,
        valid_from=timezone.now() - timedelta(days=30),
    )
    submitter = User.objects.create_user(
        email='submitter@test.com',
        address='0x1111111111111111111111111111111111111111',
    )
    steward_user = User.objects.create_user(
        email='steward@test.com',
        address='0x2222222222222222222222222222222222222222',
        name='Test Steward',
    )
    steward_user.is_staff = True
    steward_user.save()
    steward, _ = Steward.objects.get_or_create(user=steward_user)
    for action in ['accept', 'reject', 'request_more_info', 'propose']:
        StewardPermission.objects.get_or_create(
            steward=steward, contribution_type=ct, action=action,
        )
    ai_user, created = User.objects.get_or_create(
        email='genlayer-steward@genlayer.foundation',
        defaults={
            'address': '0x3333333333333333333333333333333333333333',
            'name': 'GenLayer Steward',
        },
    )

    submission = SubmittedContribution.objects.create(
        user=submitter,
        contribution_type=ct,
        contribution_date=timezone.now(),
        notes='Built a great tutorial about GenLayer smart contracts',
        state='pending',
    )
    Evidence.objects.create(
        submitted_contribution=submission,
        url='https://github.com/user/genlayer-tutorial',
    )

    template = ReviewTemplate.objects.create(
        label='Accept: Good Content',
        text='Thank you for your valuable contribution!',
        action='accept',
    )
    reject_template = ReviewTemplate.objects.create(
        label='Reject: No Evidence',
        text='Your submission lacks evidence of the work described.',
        action='reject',
    )

    return {
        'category': category,
        'ct': ct,
        'submitter': submitter,
        'steward_user': steward_user,
        'steward': steward,
        'ai_user': ai_user,
        'submission': submission,
        'template': template,
        'reject_template': reject_template,
    }


@override_settings(ALLOWED_HOSTS=['*'])
class TestHumanReviewNotes(APITestCase):
    """Test that human steward review actions store structured data in notes."""

    def setUp(self):
        self.fixtures = _create_test_fixtures()
        self.client.force_authenticate(user=self.fixtures['steward_user'])

    def test_human_review_note_captures_data(self):
        """When a steward reviews via /review/, the SubmissionNote.data has structured fields."""
        submission = self.fixtures['submission']
        response = self.client.post(
            f'/api/v1/steward-submissions/{submission.id}/review/',
            data={
                'action': 'reject',
                'staff_reply': 'Not enough evidence provided.',
                'template_id': self.fixtures['reject_template'].id,
            },
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)

        note = SubmissionNote.objects.filter(
            submitted_contribution=submission,
            is_proposal=False,
        ).first()
        self.assertIsNotNone(note)
        self.assertEqual(note.data['action'], 'reject')
        self.assertEqual(note.data['staff_reply'], 'Not enough evidence provided.')
        self.assertEqual(note.data['template_id'], self.fixtures['reject_template'].id)
        self.assertIsNone(note.data['points'])

    def test_human_review_accept_captures_points(self):
        """Accept review captures points in structured data."""
        submission = self.fixtures['submission']
        response = self.client.post(
            f'/api/v1/steward-submissions/{submission.id}/review/',
            data={
                'action': 'accept',
                'points': 5,
                'contribution_type': self.fixtures['ct'].id,
                'staff_reply': 'Great work!',
                'template_id': self.fixtures['template'].id,
            },
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)

        note = SubmissionNote.objects.filter(
            submitted_contribution=submission,
            is_proposal=False,
        ).first()
        self.assertIsNotNone(note)
        self.assertEqual(note.data['action'], 'accept')
        self.assertEqual(note.data['points'], 5)
        self.assertEqual(note.data['template_id'], self.fixtures['template'].id)

    def test_template_id_optional(self):
        """Review works fine without template_id (backwards compatible)."""
        submission = self.fixtures['submission']
        response = self.client.post(
            f'/api/v1/steward-submissions/{submission.id}/review/',
            data={
                'action': 'reject',
                'staff_reply': 'Not enough evidence.',
            },
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)

        note = SubmissionNote.objects.filter(
            submitted_contribution=submission,
            is_proposal=False,
        ).first()
        self.assertIsNotNone(note)
        self.assertEqual(note.data['action'], 'reject')
        self.assertIsNone(note.data.get('template_id'))

    def test_human_propose_note_captures_data(self):
        """When a steward proposes via /propose/, the note.data has structured fields."""
        submission = self.fixtures['submission']
        response = self.client.post(
            f'/api/v1/steward-submissions/{submission.id}/propose/',
            data={
                'proposed_action': 'reject',
                'proposed_staff_reply': 'This looks like spam.',
                'template_id': self.fixtures['reject_template'].id,
            },
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)

        note = SubmissionNote.objects.filter(
            submitted_contribution=submission,
            is_proposal=True,
        ).first()
        self.assertIsNotNone(note)
        self.assertEqual(note.data['action'], 'reject')
        self.assertEqual(note.data['staff_reply'], 'This looks like spam.')
        self.assertEqual(note.data['template_id'], self.fixtures['reject_template'].id)


@override_settings(ALLOWED_HOSTS=['*'])
class TestAIReviewNotes(APITestCase):
    """Test that AI-created notes store structured data."""

    def setUp(self):
        self.fixtures = _create_test_fixtures()

    def test_ai_proposal_note_has_structured_data(self):
        """When AI creates a proposal note, data contains structured review info."""
        submission = self.fixtures['submission']
        ai_user = self.fixtures['ai_user']

        note = SubmissionNote.objects.create(
            submitted_contribution=submission,
            user=ai_user,
            message='AI proposal (medium confidence): reject\nReasoning: Low quality',
            is_proposal=True,
            data={
                'action': 'reject',
                'points': None,
                'staff_reply': 'Your submission lacks evidence.',
                'template_id': self.fixtures['reject_template'].id,
                'confidence': 'medium',
                'flags': ['low_effort'],
                'reasoning': 'Low quality submission with no evidence',
            },
        )

        self.assertEqual(note.data['action'], 'reject')
        self.assertEqual(note.data['confidence'], 'medium')
        self.assertEqual(note.data['template_id'], self.fixtures['reject_template'].id)
        self.assertIn('low_effort', note.data['flags'])
        self.assertIn('Low quality', note.data['reasoning'])

    def test_ai_auto_action_note_has_structured_data(self):
        """When AI auto-rejects (high confidence), the note.data has confidence='high'."""
        submission = self.fixtures['submission']
        ai_user = self.fixtures['ai_user']

        note = SubmissionNote.objects.create(
            submitted_contribution=submission,
            user=ai_user,
            message='AI auto-reject (HIGH confidence): Spam content',
            is_proposal=False,
            data={
                'action': 'reject',
                'points': None,
                'staff_reply': 'Spam submission.',
                'template_id': self.fixtures['reject_template'].id,
                'confidence': 'high',
                'flags': ['ai_generated'],
                'reasoning': 'Clearly spam content',
            },
        )

        self.assertEqual(note.data['confidence'], 'high')
        self.assertFalse(note.is_proposal)

    def test_tier1_reject_note_has_structured_data(self):
        """Tier 1 auto-reject notes have data with action='reject' and the rule reason."""
        submission = self.fixtures['submission']
        ai_user = self.fixtures['ai_user']

        crm_reason = 'Tier 1 auto-reject: No evidence and no notes provided.'
        note = SubmissionNote.objects.create(
            submitted_contribution=submission,
            user=ai_user,
            message=crm_reason,
            is_proposal=False,
            data={
                'action': 'reject',
                'points': None,
                'staff_reply': 'Your submission lacks evidence.',
                'template_id': self.fixtures['reject_template'].id,
                'confidence': 'high',
                'flags': [],
                'reasoning': crm_reason,
            },
        )

        self.assertEqual(note.data['action'], 'reject')
        self.assertEqual(note.data['confidence'], 'high')
        self.assertIn('Tier 1', note.data['reasoning'])


@override_settings(ALLOWED_HOSTS=['*'])
class TestCalibrationComparison(APITestCase):
    """Test that AI vs human notes can be compared for calibration."""

    def setUp(self):
        self.fixtures = _create_test_fixtures()

    def test_can_compare_ai_vs_human_notes(self):
        """For a submission with both AI and human notes, data fields can be compared."""
        submission = self.fixtures['submission']
        ai_user = self.fixtures['ai_user']
        steward_user = self.fixtures['steward_user']

        # AI proposes reject
        ai_note = SubmissionNote.objects.create(
            submitted_contribution=submission,
            user=ai_user,
            message='AI proposal: reject',
            is_proposal=True,
            data={
                'action': 'reject',
                'points': None,
                'staff_reply': 'Low quality.',
                'template_id': self.fixtures['reject_template'].id,
                'confidence': 'medium',
                'flags': ['low_effort'],
                'reasoning': 'Low effort submission',
            },
        )

        # Human accepts instead
        human_note = SubmissionNote.objects.create(
            submitted_contribution=submission,
            user=steward_user,
            message='Reviewed: accept with 3 points',
            is_proposal=False,
            data={
                'action': 'accept',
                'points': 3,
                'staff_reply': 'Decent tutorial, thanks!',
                'template_id': self.fixtures['template'].id,
            },
        )

        # Compare the two notes
        self.assertNotEqual(ai_note.data['action'], human_note.data['action'])
        self.assertEqual(ai_note.data['action'], 'reject')
        self.assertEqual(human_note.data['action'], 'accept')
        self.assertEqual(human_note.data['points'], 3)

    def test_disagreement_detection(self):
        """AI proposed accept, human rejected -> data fields show different actions."""
        submission = self.fixtures['submission']
        ai_user = self.fixtures['ai_user']
        steward_user = self.fixtures['steward_user']

        ai_note = SubmissionNote.objects.create(
            submitted_contribution=submission,
            user=ai_user,
            message='AI proposal: accept',
            is_proposal=True,
            data={'action': 'accept', 'points': 5, 'confidence': 'medium'},
        )

        human_note = SubmissionNote.objects.create(
            submitted_contribution=submission,
            user=steward_user,
            message='Reviewed: reject',
            is_proposal=False,
            data={'action': 'reject', 'points': None},
        )

        # Detect disagreement
        is_disagreement = ai_note.data['action'] != human_note.data['action']
        self.assertTrue(is_disagreement)

    def test_agreement_detection(self):
        """AI proposed reject, human also rejected -> data fields show same action."""
        submission = self.fixtures['submission']
        ai_user = self.fixtures['ai_user']
        steward_user = self.fixtures['steward_user']

        ai_note = SubmissionNote.objects.create(
            submitted_contribution=submission,
            user=ai_user,
            message='AI proposal: reject',
            is_proposal=True,
            data={'action': 'reject', 'points': None, 'confidence': 'high'},
        )

        human_note = SubmissionNote.objects.create(
            submitted_contribution=submission,
            user=steward_user,
            message='Reviewed: reject',
            is_proposal=False,
            data={'action': 'reject', 'points': None},
        )

        # Detect agreement
        is_agreement = ai_note.data['action'] == human_note.data['action']
        self.assertTrue(is_agreement)

    def test_calibration_query_pattern(self):
        """
        Verify the calibration query pattern works: find submissions
        reviewed by humans that also have AI notes, and compare.
        """
        submission = self.fixtures['submission']
        ai_user = self.fixtures['ai_user']
        steward_user = self.fixtures['steward_user']

        # Mark submission as reviewed by human
        submission.state = 'rejected'
        submission.reviewed_by = steward_user
        submission.reviewed_at = timezone.now()
        submission.save()

        # Create AI note and human note
        SubmissionNote.objects.create(
            submitted_contribution=submission,
            user=ai_user,
            message='AI proposal: accept',
            is_proposal=True,
            data={'action': 'accept', 'points': 3, 'confidence': 'medium'},
        )
        SubmissionNote.objects.create(
            submitted_contribution=submission,
            user=steward_user,
            message='Reviewed: reject',
            is_proposal=False,
            data={'action': 'reject', 'points': None},
        )

        # Query pattern: find human-reviewed submissions with AI notes
        reviewed = SubmittedContribution.objects.filter(
            reviewed_at__isnull=False,
        ).exclude(
            reviewed_by=ai_user,
        ).prefetch_related('internal_notes')

        calibration_pairs = []
        for sub in reviewed:
            ai_note = sub.internal_notes.filter(user=ai_user).order_by('-created_at').first()
            human_note = (
                sub.internal_notes
                .filter(is_proposal=False)
                .exclude(user=ai_user)
                .order_by('-created_at')
                .first()
            )
            if ai_note and human_note and ai_note.data and human_note.data:
                calibration_pairs.append({
                    'submission_id': str(sub.id),
                    'ai_action': ai_note.data.get('action'),
                    'human_action': human_note.data.get('action'),
                    'ai_confidence': ai_note.data.get('confidence'),
                })

        self.assertEqual(len(calibration_pairs), 1)
        self.assertEqual(calibration_pairs[0]['ai_action'], 'accept')
        self.assertEqual(calibration_pairs[0]['human_action'], 'reject')
        self.assertEqual(calibration_pairs[0]['ai_confidence'], 'medium')
