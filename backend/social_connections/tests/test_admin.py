from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse


class DiscordEarnedRoleAssignmentAdminTest(TestCase):
    def setUp(self):
        self.superuser = get_user_model().objects.create_superuser(
            email='admin@test.com',
            password='password',
        )
        self.client.force_login(self.superuser)
        self.changelist_url = reverse(
            'admin:social_connections_discordearnedroleassignment_changelist'
        )
        self.run_url = reverse(
            'admin:social_connections_discordearnedroleassignment_run_assignment'
        )

    def test_changelist_shows_run_button(self):
        response = self.client.get(self.changelist_url)

        self.assertContains(response, self.run_url)
        self.assertContains(response, 'Run earned role assignment')

    @patch('social_connections.admin.start_earned_role_assignment')
    def test_confirmation_does_not_start_assignment(self, mock_start):
        response = self.client.get(self.run_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'It never removes roles.')
        mock_start.assert_not_called()

    @patch(
        'social_connections.admin.start_earned_role_assignment',
        return_value=(True, None),
    )
    def test_post_starts_assignment(self, mock_start):
        response = self.client.post(self.run_url, follow=True)

        self.assertRedirects(response, self.changelist_url)
        self.assertContains(response, 'Earned Discord role assignment started.')
        mock_start.assert_called_once_with()

    @patch(
        'social_connections.admin.start_earned_role_assignment',
        return_value=(False, 12),
    )
    def test_post_reports_existing_run(self, mock_start):
        response = self.client.post(self.run_url, follow=True)

        self.assertRedirects(response, self.changelist_url)
        self.assertContains(response, 'already running')
        self.assertContains(response, '12 seconds ago')
        mock_start.assert_called_once_with()

    def test_staff_with_view_permission_cannot_run_assignment(self):
        staff = get_user_model().objects.create_user(
            email='staff@test.com',
            password='password',
            is_staff=True,
        )
        staff.user_permissions.add(
            Permission.objects.get(codename='view_discordearnedroleassignment')
        )
        self.client.force_login(staff)

        changelist_response = self.client.get(self.changelist_url)
        confirmation_response = self.client.get(self.run_url)
        run_response = self.client.post(self.run_url)

        self.assertNotContains(changelist_response, 'Run earned role assignment')
        self.assertEqual(confirmation_response.status_code, 403)
        self.assertEqual(run_response.status_code, 403)

    @patch(
        'social_connections.admin.start_earned_role_assignment',
        return_value=(True, None),
    )
    def test_staff_with_run_permission_can_run_assignment(self, mock_start):
        staff = get_user_model().objects.create_user(
            email='role-manager@test.com',
            password='password',
            is_staff=True,
        )
        staff.user_permissions.add(
            Permission.objects.get(codename='run_discord_earned_role_assignment')
        )
        self.client.force_login(staff)

        admin_index_response = self.client.get(reverse('admin:index'))
        changelist_response = self.client.get(self.changelist_url)
        confirmation_response = self.client.get(self.run_url)
        run_response = self.client.post(self.run_url, follow=True)

        self.assertContains(admin_index_response, self.changelist_url)
        self.assertEqual(changelist_response.status_code, 200)
        self.assertContains(changelist_response, 'Run earned role assignment')
        self.assertEqual(confirmation_response.status_code, 200)
        self.assertRedirects(run_response, self.changelist_url)
        self.assertContains(run_response, 'Earned Discord role assignment started.')
        mock_start.assert_called_once_with()
