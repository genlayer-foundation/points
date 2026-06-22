from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from contributions.models import Category, ContributionType, SubmittedContribution
from .models import FeatureCandidateScore, Steward


User = get_user_model()


class StewardAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='steward-user@example.com',
            password='testpass123',
        )
        self.client.force_authenticate(user=self.user)

    def test_patch_steward_me_does_not_create_profile(self):
        response = self.client.patch('/api/v1/stewards/me/', {})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(Steward.objects.filter(user=self.user).exists())

    def test_regular_user_cannot_create_steward_profile(self):
        response = self.client.post('/api/v1/stewards/', {})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Steward.objects.filter(user=self.user).exists())

    def test_regular_user_cannot_mutate_arbitrary_steward_profile(self):
        other_user = User.objects.create_user(
            email='steward-other@example.com',
            password='testpass123',
        )
        steward = Steward.objects.create(user=other_user)

        response = self.client.patch(f'/api/v1/stewards/{steward.id}/', {})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class FeatureCandidateReviewAPITestCase(APITestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name='Builder',
            slug='builder',
        )
        self.contribution_type = ContributionType.objects.create(
            name='Projects',
            slug='projects',
            category=self.category,
            min_points=0,
            max_points=100,
        )
        self.submitter = User.objects.create_user(
            email='submitter@example.com',
            password='testpass123',
            name='Submitter',
        )
        self.submission = SubmittedContribution.objects.create(
            user=self.submitter,
            contribution_type=self.contribution_type,
            contribution_date=timezone.now(),
            title='Interesting project',
            notes='A GenLayer-native project.',
            is_interesting=True,
        )
        self.uninteresting_submission = SubmittedContribution.objects.create(
            user=self.submitter,
            contribution_type=self.contribution_type,
            contribution_date=timezone.now(),
            title='Hidden project',
            notes='Not flagged.',
            is_interesting=False,
        )
        self.reviewer_user = User.objects.create_user(
            email='reviewer@example.com',
            password='testpass123',
            name='Reviewer',
        )
        self.reviewer_steward = Steward.objects.create(
            user=self.reviewer_user,
            can_review_feature_candidates=True,
        )
        self.denied_user = User.objects.create_user(
            email='denied@example.com',
            password='testpass123',
            name='Denied',
        )
        Steward.objects.create(user=self.denied_user)
        self.staff_user = User.objects.create_user(
            email='staff@example.com',
            password='testpass123',
            is_staff=True,
            name='Staff',
        )

    def test_access_endpoint_reports_reviewer_permission(self):
        self.client.force_authenticate(user=self.reviewer_user)

        response = self.client.get('/api/v1/stewards/feature-reviews/access/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'can_review': True, 'can_admin': False})

    def test_reviewer_list_is_blind_and_only_includes_interesting_submissions(self):
        other_user = User.objects.create_user(
            email='other-reviewer@example.com',
            password='testpass123',
        )
        other_steward = Steward.objects.create(
            user=other_user,
            can_review_feature_candidates=True,
        )
        FeatureCandidateScore.objects.create(
            submission=self.submission,
            steward=other_steward,
            score=3,
        )
        self.client.force_authenticate(user=self.reviewer_user)

        response = self.client.get('/api/v1/stewards/feature-reviews/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['progress'], {'scored': 0, 'total': 1})
        self.assertEqual(len(response.data['results']), 1)
        row = response.data['results'][0]
        self.assertEqual(row['id'], str(self.submission.id))
        self.assertIsNone(row['own_score'])
        self.assertNotIn('id', row['user_details'])
        self.assertNotIn('address', row['user_details'])
        self.assertNotIn('median_score', row)
        self.assertNotIn('reviewer_count', row)

    def test_reviewer_can_create_and_edit_own_score(self):
        self.client.force_authenticate(user=self.reviewer_user)

        create_response = self.client.post(
            f'/api/v1/stewards/feature-reviews/{self.submission.id}/score/',
            {'score': 2},
        )
        edit_response = self.client.post(
            f'/api/v1/stewards/feature-reviews/{self.submission.id}/score/',
            {'score': 3},
        )

        self.assertEqual(create_response.status_code, status.HTTP_200_OK)
        self.assertEqual(edit_response.status_code, status.HTTP_200_OK)
        scores = FeatureCandidateScore.objects.filter(
            submission=self.submission,
            steward=self.reviewer_steward,
        )
        self.assertEqual(scores.count(), 1)
        self.assertEqual(scores.get().score, 3)

    def test_unpermitted_steward_cannot_score(self):
        self.client.force_authenticate(user=self.denied_user)

        response = self.client.post(
            f'/api/v1/stewards/feature-reviews/{self.submission.id}/score/',
            {'score': 2},
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(FeatureCandidateScore.objects.exists())

    def test_reviewer_score_validation_rejects_invalid_values(self):
        self.client.force_authenticate(user=self.reviewer_user)
        url = f'/api/v1/stewards/feature-reviews/{self.submission.id}/score/'

        for payload in (
            {'score': -1},
            {'score': 4},
            {'score': 'x'},
            {'score': 1.5},
            {'score': None},
        ):
            with self.subTest(payload=payload):
                response = self.client.post(url, payload)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn('score', response.data)
                self.assertFalse(FeatureCandidateScore.objects.exists())

    def test_staff_admin_sees_aggregates_and_manual_review_flag(self):
        second_user = User.objects.create_user(
            email='second-reviewer@example.com',
            password='testpass123',
        )
        second_steward = Steward.objects.create(
            user=second_user,
            can_review_feature_candidates=True,
        )
        FeatureCandidateScore.objects.create(
            submission=self.submission,
            steward=self.reviewer_steward,
            score=0,
        )
        FeatureCandidateScore.objects.create(
            submission=self.submission,
            steward=second_steward,
            score=3,
        )
        self.client.force_authenticate(user=self.staff_user)

        response = self.client.get('/api/v1/stewards/feature-reviews/admin/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        row = response.data['results'][0]
        self.assertEqual(row['median_score'], 1.5)
        self.assertEqual(row['reviewer_count'], 2)
        self.assertEqual(row['spread'], 3)
        self.assertEqual(row['decision'], 'manual_review')
        self.assertTrue(row['manual_review'])
