from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from campaigns.models import (
    CampaignLink,
    MarketingCampaign,
    generate_tracking_id,
    validate_destination_path,
)


def make_campaign(**kwargs):
    defaults = {'name': 'ETHCC Role Recruitment', 'tracking_key': 'ethcc_role_recruitment'}
    defaults.update(kwargs)
    return MarketingCampaign.objects.create(**defaults)


def make_link(campaign=None, **kwargs):
    campaign = campaign or make_campaign()
    defaults = {
        'campaign': campaign,
        'role': 'builder',
        'alias': 'ethcc',
        'destination_path': '/builders',
        'utm_source': 'x',
        'utm_medium': 'organic_social',
    }
    defaults.update(kwargs)
    return CampaignLink.objects.create(**defaults)


class DestinationValidationTests(TestCase):
    def test_valid_destinations(self):
        for path in ('/', '/builders', '/builders/tasks', '/community', '/how-it-works'):
            validate_destination_path(path)

    def test_invalid_destinations_rejected(self):
        bad = [
            '',
            None,
            'https://evil.example.com',
            '//evil.example.com',
            '/builders/../admin',
            '/builders/%2e%2e/admin',
            '/builders/%2E%2E/admin',
            '/admin',
            '/admin/login',
            '/api/v1/users',
            '/join/builders/x',
            '/oauth',
            '/static/app.js',
            '/campaigns/redirect/builders/x',
            '/builders#frag',
            '/builders?x=1',
            '/builders with space',
            '/not-a-real-prefix',
            '/' + 'a' * 400,
        ]
        for path in bad:
            with self.assertRaises(ValidationError, msg=f'accepted: {path!r}'):
                validate_destination_path(path)


class CampaignModelTests(TestCase):
    def test_tracking_key_rejects_bad_characters(self):
        campaign = MarketingCampaign(name='X', tracking_key='Bad-Key!')
        with self.assertRaises(ValidationError):
            campaign.full_clean()

    def test_date_window_validation(self):
        now = timezone.now()
        campaign = MarketingCampaign(
            name='X', tracking_key='x_campaign', starts_at=now, ends_at=now - timezone.timedelta(days=1),
        )
        with self.assertRaises(ValidationError):
            campaign.full_clean()

    def test_tracking_key_immutable_once_links_exist(self):
        link = make_link()
        campaign = link.campaign
        campaign.tracking_key = 'renamed_key'
        with self.assertRaises(ValidationError):
            campaign.full_clean()

    def test_tracking_key_editable_while_campaign_has_no_links(self):
        campaign = make_campaign(tracking_key='draft_key')
        campaign.tracking_key = 'renamed_key'
        campaign.full_clean()


class CampaignLinkModelTests(TestCase):
    def test_clean_normalizes_utm_values(self):
        link = make_link()
        link.utm_source = '  X '
        link.utm_medium = 'Organic_Social'
        link.utm_content = ' Launch_Post_01 '
        link.full_clean()
        self.assertEqual(link.utm_source, 'x')
        self.assertEqual(link.utm_medium, 'organic_social')
        self.assertEqual(link.utm_content, 'launch_post_01')

    def test_alias_rejects_script_html_and_uppercase(self):
        link = make_link()
        for alias in ('<script>', 'a b', 'a/b', 'a?b', 'UPPER'):
            link.alias = alias
            with self.assertRaises(ValidationError, msg=f'accepted: {alias!r}'):
                link.full_clean()

    def test_duplicate_role_alias_rejected(self):
        campaign = make_campaign()
        make_link(campaign, role='builder', alias='ethcc')
        with self.assertRaises(IntegrityError):
            make_link(campaign, role='builder', alias='ethcc')

    def test_same_alias_allowed_across_roles(self):
        campaign = make_campaign()
        make_link(campaign, role='builder', alias='ethcc')
        make_link(campaign, role='validator', alias='ethcc', destination_path='/validators')

    def test_tracking_id_generated_and_unique(self):
        link_a = make_link(alias='a')
        link_b = make_link(link_a.campaign, alias='b')
        self.assertTrue(link_a.tracking_id.startswith('cl-'))
        self.assertNotEqual(link_a.tracking_id, link_b.tracking_id)
        self.assertNotEqual(generate_tracking_id(), generate_tracking_id())

    def test_url_construction(self):
        link = make_link(utm_content='launch_post_01')
        with self.settings(FRONTEND_URL='https://portal.example.com'):
            self.assertEqual(link.public_url, 'https://portal.example.com/join/builders/ethcc')
            target = link.redirect_target
        self.assertIn('/builders?', target)
        self.assertIn(f'utm_id={link.tracking_id}', target)
        self.assertIn('utm_source=x', target)
        self.assertIn('utm_medium=organic_social', target)
        self.assertIn('utm_campaign=ethcc_role_recruitment', target)
        self.assertIn('utm_content=launch_post_01', target)
        self.assertNotIn('utm_term', target)

    def test_live_and_expired_windows_combine_link_and_campaign(self):
        now = timezone.now()
        campaign = make_campaign(ends_at=now + timezone.timedelta(days=10))
        link = make_link(campaign)
        self.assertTrue(link.is_live_at(now))
        self.assertFalse(link.is_expired_at(now))

        link.ends_at = now - timezone.timedelta(minutes=1)
        self.assertTrue(link.is_expired_at(now))
        self.assertFalse(link.is_live_at(now))

        link.ends_at = None
        campaign.ends_at = now - timezone.timedelta(minutes=1)
        self.assertTrue(link.is_expired_at(now))

        campaign.ends_at = None
        campaign.is_active = False
        self.assertFalse(link.is_live_at(now))
        self.assertFalse(link.is_expired_at(now))

        campaign.is_active = True
        link.is_active = False
        self.assertFalse(link.is_live_at(now))

        link.is_active = True
        link.starts_at = now + timezone.timedelta(days=1)
        self.assertFalse(link.is_live_at(now))
