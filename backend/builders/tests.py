from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Builder


User = get_user_model()


class BuilderAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='builder-user@example.com',
            password='testpass123',
        )
        self.client.force_authenticate(user=self.user)

    def test_patch_builder_me_does_not_create_profile(self):
        response = self.client.patch('/api/v1/builders/me/', {})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(Builder.objects.filter(user=self.user).exists())

    def test_regular_user_cannot_create_builder_profile(self):
        response = self.client.post('/api/v1/builders/', {})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Builder.objects.filter(user=self.user).exists())

    def test_regular_user_cannot_mutate_arbitrary_builder_profile(self):
        other_user = User.objects.create_user(
            email='builder-other@example.com',
            password='testpass123',
        )
        builder = Builder.objects.create(user=other_user)

        response = self.client.patch(f'/api/v1/builders/{builder.id}/', {})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
