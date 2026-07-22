from django.test import TestCase

from builders.models import Builder
from users.models import User
from users.role_access import can_view_role_section, is_role_section_read_only


class RoleAccessTests(TestCase):
    def setUp(self):
        self.viewer = User.objects.create_user(
            email='role-access-viewer@example.com',
            password='testpass123',
            visible=True,
            can_view_role_sections=True,
        )

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
