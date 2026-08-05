from importlib import import_module

from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client, TestCase

from campaigns.models import MarketingCampaign

User = get_user_model()


def _run_marketing_group_migration():
    # Migrations do not run under tally.test_settings; invoke the data
    # migration function directly against the live apps registry.
    module = import_module('campaigns.migrations.0002_marketing_group')
    module.create_marketing_group(apps, None)


class MarketingGroupTests(TestCase):
    def setUp(self):
        _run_marketing_group_migration()
        self.group = Group.objects.get(name='Marketing')
        self.marketer = User.objects.create_user(
            email='marketing@example.com', password='pass12345', is_staff=True,
        )
        self.marketer.groups.add(self.group)
        self.client = Client()
        self.client.force_login(self.marketer)

    def test_group_has_exactly_the_campaign_permissions(self):
        granted = set(
            self.group.permissions.values_list('content_type__app_label', 'codename')
        )
        expected = {
            ('campaigns', 'add_marketingcampaign'),
            ('campaigns', 'change_marketingcampaign'),
            ('campaigns', 'view_marketingcampaign'),
            ('campaigns', 'add_campaignlink'),
            ('campaigns', 'change_campaignlink'),
            ('campaigns', 'view_campaignlink'),
            ('campaigns', 'view_campaignredirecthit'),
            ('campaigns', 'view_useracquisitionattribution'),
        }
        self.assertEqual(granted, expected)

    def test_marketing_user_can_manage_campaigns(self):
        response = self.client.get('/admin/campaigns/marketingcampaign/')
        self.assertEqual(response.status_code, 200)
        response = self.client.post('/admin/campaigns/marketingcampaign/add/', {
            'name': 'Test Campaign',
            'tracking_key': 'test_campaign',
            'description': '',
            'is_active': 'on',
            'links-TOTAL_FORMS': '0',
            'links-INITIAL_FORMS': '0',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(MarketingCampaign.objects.filter(tracking_key='test_campaign').exists())

    def test_marketing_user_cannot_access_other_apps(self):
        response = self.client.get('/admin/users/user/')
        self.assertEqual(response.status_code, 403)

    def test_anonymous_denied(self):
        anonymous = Client()
        response = anonymous.get('/admin/campaigns/marketingcampaign/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login', response['Location'])

    def test_non_staff_denied(self):
        plain = User.objects.create_user(email='plain@example.com', password='pass12345')
        client = Client()
        client.force_login(plain)
        response = client.get('/admin/campaigns/marketingcampaign/')
        self.assertEqual(response.status_code, 302)
