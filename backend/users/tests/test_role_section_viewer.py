from rest_framework.test import APITestCase

from builders.models import Builder
from creators.models import Creator
from users.models import User
from users.role_access import can_view_role_section, is_role_section_read_only
from validators.models import Validator


class RoleSectionViewerTests(APITestCase):
    def setUp(self):
        self.viewer = User.objects.create_user(
            email='role-section-viewer@example.com',
            password='testpass123',
            visible=True,
            can_view_role_sections=True,
        )
        self.other_user = User.objects.create_user(
            email='other-viewer@example.com',
            password='testpass123',
            visible=True,
        )

    def test_admin_enabled_owner_receives_flag_without_any_role(self):
        self.client.force_authenticate(user=self.viewer)

        response = self.client.get('/api/v1/users/me/')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['can_view_role_sections'])
        self.assertIsNone(response.data['validator'])
        self.assertIsNone(response.data['builder'])
        self.assertIsNone(response.data['creator'])
        self.assertFalse(Validator.objects.filter(user=self.viewer).exists())
        self.assertFalse(Builder.objects.filter(user=self.viewer).exists())
        self.assertFalse(Creator.objects.filter(user=self.viewer).exists())

    def test_flag_allows_only_non_steward_role_sections(self):
        for category in ('builder', 'validator', 'community'):
            with self.subTest(category=category):
                self.assertTrue(can_view_role_section(self.viewer, category))

        self.assertFalse(can_view_role_section(self.viewer, 'steward'))
        self.assertFalse(can_view_role_section(self.viewer, 'global'))

    def test_real_role_overrides_view_only_status_for_its_category(self):
        Builder.objects.create(user=self.viewer)

        self.assertFalse(is_role_section_read_only(self.viewer, 'builder'))
        self.assertTrue(is_role_section_read_only(self.viewer, 'validator'))
        self.assertTrue(is_role_section_read_only(self.viewer, 'community'))

    def test_unconfigured_user_does_not_receive_view_flag(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.client.get('/api/v1/users/me/')

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['can_view_role_sections'])

    def test_view_flag_is_not_exposed_on_public_profile(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.client.get(f'/api/v1/users/by-address/{self.viewer.id}/')

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['can_view_role_sections'])

    def test_profile_api_cannot_enable_view_access(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.client.patch(
            '/api/v1/users/me/',
            {'can_view_role_sections': True},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('can_view_role_sections', response.data)
        self.other_user.refresh_from_db()
        self.assertFalse(self.other_user.can_view_role_sections)
