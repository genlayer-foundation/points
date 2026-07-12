from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from contributions.models import Category, ContributionType, SubmittedContribution
from stewards.models import Steward, StewardPermission

User = get_user_model()


class QuestionedProposalVisibilityTest(TestCase):
    """A proposer must be able to find their own questioned proposals via the
    steward list filters the search bar sends (proposed_by + proposal_review_status)."""

    def setUp(self):
        self.category = Category.objects.create(name='Cat', slug='cat', description='')
        self.contribution_type = ContributionType.objects.create(
            name='Type', slug='type', description='',
            category=self.category, min_points=1, max_points=100,
        )
        self.proposer = User.objects.create_user(
            email='proposer@test.com',
            address='0x1111111111111111111111111111111111111111',
            password='pass',
        )
        self.decider = User.objects.create_user(
            email='decider@test.com',
            address='0x2222222222222222222222222222222222222222',
            password='pass',
        )
        self.submitter = User.objects.create_user(
            email='submitter@test.com',
            address='0x3333333333333333333333333333333333333333',
            password='pass',
        )
        self.proposer_steward = Steward.objects.create(user=self.proposer)
        StewardPermission.objects.create(
            steward=self.proposer_steward,
            contribution_type=self.contribution_type,
            action='propose',
        )
        self.client = APIClient()

    def _make_questioned_submission(self, state='pending'):
        return SubmittedContribution.objects.create(
            user=self.submitter,
            contribution_type=self.contribution_type,
            contribution_date=timezone.now(),
            state=state,
            proposed_action='accept',
            proposed_points=10,
            proposed_by=self.proposer,
            proposed_at=timezone.now(),
            proposal_review_status='questioned',
            proposal_review_feedback='Please double check the evidence',
            proposal_questioned_by=self.decider,
            proposal_questioned_at=timezone.now(),
        )

    def _list(self, **params):
        response = self.client.get('/api/v1/steward-submissions/', params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response.data['results'] if 'results' in response.data else response.data

    def test_propose_only_steward_sees_own_questioned_proposal(self):
        submission = self._make_questioned_submission()
        self.client.force_authenticate(user=self.proposer)

        # Exactly what the search bar sends for:
        #   status dropdown=pending + "proposed-by:me proposal-status:questioned"
        results = self._list(
            state='pending',
            proposed_by=self.proposer.id,
            proposal_review_status='questioned',
        )
        self.assertEqual([r['id'] for r in results], [str(submission.id)])

    def test_questioned_filter_alone_returns_it(self):
        submission = self._make_questioned_submission()
        self.client.force_authenticate(user=self.proposer)
        results = self._list(state='pending', proposal_review_status='questioned')
        self.assertIn(str(submission.id), [r['id'] for r in results])

    def test_has_proposal_true_alone_hides_questioned(self):
        """Documents the trap: has_proposal=true without an explicit
        proposal_review_status restricts to pending_review, hiding questioned."""
        self._make_questioned_submission()
        self.client.force_authenticate(user=self.proposer)
        results = self._list(state='pending', has_proposal='true')
        self.assertEqual(results, [])

    def test_propose_only_steward_sees_questioned_on_more_info_submission(self):
        """The proposer clause lifts the propose-only state='pending' ceiling
        for their own proposals: a questioned proposal on a more_info_needed
        submission must stay reachable by its author."""
        submission = self._make_questioned_submission(state='more_info_needed')
        self.client.force_authenticate(user=self.proposer)
        results = self._list(
            proposed_by=self.proposer.id,
            proposal_review_status='questioned',
        )
        self.assertEqual([r['id'] for r in results], [str(submission.id)])

    def test_proposer_keeps_seeing_own_proposal_after_permissions_revoked(self):
        """Losing propose permission must not orphan an active proposal the
        portal is still asking the author to revise."""
        submission = self._make_questioned_submission()
        StewardPermission.objects.filter(steward=self.proposer_steward).delete()
        self.client.force_authenticate(user=self.proposer)
        results = self._list(proposed_by=self.proposer.id)
        self.assertEqual([r['id'] for r in results], [str(submission.id)])

    def test_notification_deep_link_query_finds_the_submission(self):
        """The questioned notification links to status='' (All) + q=<uuid>;
        the free-text search must resolve the UUID for the proposer even on a
        non-pending submission."""
        submission = self._make_questioned_submission(state='more_info_needed')
        self.client.force_authenticate(user=self.proposer)
        results = self._list(search=str(submission.id))
        self.assertEqual([r['id'] for r in results], [str(submission.id)])
