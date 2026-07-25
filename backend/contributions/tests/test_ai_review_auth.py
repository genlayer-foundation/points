"""
Integration tests for the AI review API's service-account authentication:
scope enforcement per action and proposal attribution.

The token/auth machinery itself is tested consumer-independently in
service_accounts/tests/test_service_accounts.py.
"""

from datetime import timedelta

from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from contributions.ai_attribution import get_ai_steward
from contributions.models import (
    Category,
    ContributionType,
    Evidence,
    SubmissionNote,
    SubmittedContribution,
)
from leaderboard.models import GlobalLeaderboardMultiplier
from service_accounts.models import ServiceAccount, ServiceAccountToken
from users.models import User

LIST_URL = '/api/v1/ai-review/'


def _bearer(plaintext):
    return {'HTTP_AUTHORIZATION': f'Bearer {plaintext}'}


def _issue(scopes=('ai_review:read', 'ai_review:propose'), name='test-ai-agent'):
    account, _ = ServiceAccount.objects.get_or_create(name=name)
    token, plaintext = ServiceAccountToken.issue(account, list(scopes))
    return account, token, plaintext


def _make_submission():
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
    GlobalLeaderboardMultiplier.objects.create(
        contribution_type=ct,
        multiplier_value=1.0,
        valid_from=timezone.now() - timedelta(days=30),
    )
    submitter = User.objects.create_user(
        email='submitter@test.com',
        address='0x1111111111111111111111111111111111111111',
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
    return submission


@override_settings(ALLOWED_HOSTS=['*'])
class AIReviewScopeTests(APITestCase):
    """Per-action scope enforcement and proposal attribution."""

    def test_read_token_can_use_every_read_endpoint(self):
        submission = _make_submission()
        _, _, plaintext = _issue(scopes=('ai_review:read',))
        auth = _bearer(plaintext)

        for url in (
            LIST_URL,
            f'{LIST_URL}{submission.id}/',
            f'{LIST_URL}proposed/',
            f'{LIST_URL}reviewed/',
            f'{LIST_URL}feedback/',
            f'{LIST_URL}templates/',
        ):
            response = self.client.get(url, **auth)
            self.assertEqual(response.status_code, 200, url)

    def test_appealed_submissions_are_included_by_default_and_filterable(self):
        submission = _make_submission()
        submission.has_appeal = True
        submission.appeal_reason = 'The evidence was misunderstood.'
        submission.appealed_at = timezone.now()
        submission.save(update_fields=['has_appeal', 'appeal_reason', 'appealed_at'])
        _, _, plaintext = _issue(scopes=('ai_review:read',))
        auth = _bearer(plaintext)

        response = self.client.get(LIST_URL, **auth)
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            str(submission.id),
            {str(item['id']) for item in response.data['results']},
        )
        self.assertEqual(
            self.client.get(f'{LIST_URL}{submission.id}/', **auth).status_code,
            200,
        )

        appealed_only = self.client.get(LIST_URL, {'has_appeal': 'true'}, **auth)
        self.assertEqual(appealed_only.status_code, 200)
        self.assertIn(
            str(submission.id),
            {str(item['id']) for item in appealed_only.data['results']},
        )

        without_appeals = self.client.get(LIST_URL, {'has_appeal': 'false'}, **auth)
        self.assertEqual(without_appeals.status_code, 200)
        self.assertNotIn(
            str(submission.id),
            {str(item['id']) for item in without_appeals.data['results']},
        )

    def test_read_only_token_gets_403_on_propose(self):
        submission = _make_submission()
        _, _, plaintext = _issue(scopes=('ai_review:read',))
        response = self.client.post(
            f'{LIST_URL}{submission.id}/propose/',
            data={'proposed_action': 'accept', 'proposed_points': 5},
            format='json',
            **_bearer(plaintext),
        )
        self.assertEqual(response.status_code, 403)

    def test_propose_only_token_gets_403_on_read(self):
        _, _, plaintext = _issue(scopes=('ai_review:propose',))
        response = self.client.get(LIST_URL, **_bearer(plaintext))
        self.assertEqual(response.status_code, 403)

    def test_missing_bearer_gets_401(self):
        self.assertEqual(self.client.get(LIST_URL).status_code, 401)

    def test_propose_attributes_to_the_ai_steward_with_account_audit(self):
        submission = _make_submission()
        account, _, plaintext = _issue()

        response = self.client.post(
            f'{LIST_URL}{submission.id}/propose/',
            data={
                'proposed_action': 'accept',
                'proposed_points': 5,
                'confidence': 'high',
                'reasoning': 'Clear evidence of real work.',
            },
            format='json',
            **_bearer(plaintext),
        )

        ai_user = get_ai_steward()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['proposed_by'], ai_user.id)
        self.assertEqual(response.data['proposed_by_name'], ai_user.name)

        submission.refresh_from_db()
        self.assertEqual(submission.proposed_by, ai_user)

        note = SubmissionNote.objects.get(
            submitted_contribution=submission, is_proposal=True,
        )
        self.assertEqual(note.user, ai_user)
        self.assertEqual(note.data['service_account'], account.name)

    def test_put_updates_an_ai_proposal(self):
        submission = _make_submission()
        _, _, plaintext = _issue()
        auth = _bearer(plaintext)
        propose_url = f'{LIST_URL}{submission.id}/propose/'

        create = self.client.post(
            propose_url,
            data={'proposed_action': 'accept', 'proposed_points': 5},
            format='json',
            **auth,
        )
        self.assertEqual(create.status_code, 200)

        update = self.client.put(
            propose_url,
            data={'proposed_action': 'reject', 'proposed_staff_reply': 'Not enough evidence.'},
            format='json',
            **auth,
        )
        self.assertEqual(update.status_code, 200)
        submission.refresh_from_db()
        self.assertEqual(submission.proposed_action, 'reject')

    def test_put_rejected_on_human_created_proposal(self):
        submission = _make_submission()
        steward = User.objects.create_user(
            email='human-steward@test.com',
            address='0x2222222222222222222222222222222222222222',
        )
        submission.proposed_action = 'accept'
        submission.proposed_points = 3
        submission.proposed_by = steward
        submission.save()

        _, _, plaintext = _issue()
        response = self.client.put(
            f'{LIST_URL}{submission.id}/propose/',
            data={'proposed_action': 'reject', 'proposed_staff_reply': 'Nope.'},
            format='json',
            **_bearer(plaintext),
        )
        self.assertEqual(response.status_code, 403)
