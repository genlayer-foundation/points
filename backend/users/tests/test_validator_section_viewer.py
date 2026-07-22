from django.test import override_settings
from rest_framework.test import APITestCase

from users.models import User
from validators.models import Validator


class ValidatorSectionViewerTests(APITestCase):
    def setUp(self):
        self.viewer = User.objects.create_user(
            email='validator-section-viewer@example.com',
            password='testpass123',
            visible=True,
        )
        self.other_user = User.objects.create_user(
            email='other-viewer@example.com',
            password='testpass123',
            visible=True,
        )

    def test_configured_owner_receives_view_flag_without_validator_role(self):
        self.client.force_authenticate(user=self.viewer)

        with override_settings(VALIDATOR_SECTION_VIEWER_USER_ID=self.viewer.id):
            response = self.client.get('/api/v1/users/me/')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['can_view_validator_sections'])
        self.assertIsNone(response.data['validator'])
        self.assertFalse(Validator.objects.filter(user=self.viewer).exists())

    def test_unconfigured_user_does_not_receive_view_flag(self):
        self.client.force_authenticate(user=self.other_user)

        with override_settings(VALIDATOR_SECTION_VIEWER_USER_ID=self.viewer.id):
            response = self.client.get('/api/v1/users/me/')

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['can_view_validator_sections'])

    def test_view_flag_is_not_exposed_on_the_configured_users_public_profile(self):
        self.client.force_authenticate(user=self.other_user)

        with override_settings(VALIDATOR_SECTION_VIEWER_USER_ID=self.viewer.id):
            response = self.client.get(f'/api/v1/users/by-address/{self.viewer.id}/')

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['can_view_validator_sections'])

    @override_settings(VALIDATOR_SECTION_VIEWER_USER_ID=None)
    def test_exception_is_disabled_when_setting_is_empty(self):
        self.client.force_authenticate(user=self.viewer)

        response = self.client.get('/api/v1/users/me/')

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['can_view_validator_sections'])
