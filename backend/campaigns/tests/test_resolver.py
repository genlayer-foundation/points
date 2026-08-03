from datetime import timedelta
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from campaigns.models import CampaignLink, CampaignRedirectHit
from campaigns.tests.test_models import make_campaign, make_link

BROWSER_UA = (
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/126.0 Safari/537.36'
)


@override_settings(FRONTEND_URL='https://portal.example.com')
class CampaignRedirectResolverTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.link = make_link()

    def _get(self, path=None, **extra):
        extra.setdefault('HTTP_USER_AGENT', BROWSER_UA)
        return self.client.get(path or '/campaigns/redirect/builders/ethcc', **extra)

    def test_active_link_redirects_with_utms_and_no_store(self):
        response = self._get()
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].startswith('https://portal.example.com/builders?'))
        self.assertIn(f'utm_id={self.link.tracking_id}', response['Location'])
        self.assertIn('utm_campaign=ethcc_role_recruitment', response['Location'])
        self.assertEqual(response['Cache-Control'], 'no-store')

    def test_trailing_slash_also_resolves(self):
        response = self._get('/campaigns/redirect/builders/ethcc/')
        self.assertEqual(response.status_code, 302)

    def test_public_join_path_resolves_directly(self):
        # The backend serves the public /join contract itself so the portal
        # CDN only needs a pass-through, no edge URL rewriting.
        response = self._get('/join/builders/ethcc')
        self.assertEqual(response.status_code, 302)
        self.assertIn(f'utm_id={self.link.tracking_id}', response['Location'])
        self.assertEqual(self._get('/join/builders/nope').status_code, 404)

    def test_head_request_works(self):
        response = self.client.head('/campaigns/redirect/builders/ethcc', HTTP_USER_AGENT=BROWSER_UA)
        self.assertEqual(response.status_code, 302)

    def test_unknown_role_and_alias_return_404(self):
        self.assertEqual(self._get('/campaigns/redirect/wizards/ethcc').status_code, 404)
        self.assertEqual(self._get('/campaigns/redirect/builders/nope').status_code, 404)

    def test_inactive_link_returns_404(self):
        CampaignLink.objects.filter(pk=self.link.pk).update(is_active=False)
        self.assertEqual(self._get().status_code, 404)

    def test_inactive_campaign_returns_404(self):
        self.link.campaign.is_active = False
        self.link.campaign.save()
        self.assertEqual(self._get().status_code, 404)

    def test_future_window_returns_404(self):
        CampaignLink.objects.filter(pk=self.link.pk).update(
            starts_at=timezone.now() + timedelta(days=1),
        )
        self.assertEqual(self._get().status_code, 404)

    def test_expired_link_returns_410(self):
        CampaignLink.objects.filter(pk=self.link.pk).update(
            ends_at=timezone.now() - timedelta(minutes=1),
        )
        self.assertEqual(self._get().status_code, 410)

    def test_expired_campaign_returns_410(self):
        self.link.campaign.ends_at = timezone.now() - timedelta(minutes=1)
        self.link.campaign.save()
        self.assertEqual(self._get().status_code, 410)

    def test_corrupt_stored_destination_fails_closed(self):
        # Bypass clean() the way corrupt data would.
        CampaignLink.objects.filter(pk=self.link.pk).update(destination_path='https://evil.example.com')
        self.assertEqual(self._get().status_code, 404)

    def test_hit_recorded_with_browser_classification(self):
        self._get()
        hit = CampaignRedirectHit.objects.get()
        self.assertEqual(hit.campaign_link, self.link)
        self.assertFalse(hit.is_probable_bot)
        self.assertEqual(hit.device_category, CampaignRedirectHit.DEVICE_DESKTOP)
        self.assertEqual(hit.user_agent_family, 'chrome')

    def test_bot_ua_classified_and_separated(self):
        self._get(HTTP_USER_AGENT='Slackbot-LinkExpanding 1.0 (+https://api.slack.com/robots)')
        self._get(HTTP_USER_AGENT='')
        hits = CampaignRedirectHit.objects.all()
        self.assertEqual(hits.count(), 2)
        self.assertTrue(all(hit.is_probable_bot for hit in hits))

    def test_referrer_stores_hostname_only(self):
        self._get(HTTP_REFERER='https://x.com/some/post?utm_source=leak&token=secret')
        hit = CampaignRedirectHit.objects.get()
        self.assertEqual(hit.referrer_host, 'x.com')

    def test_hit_logging_failure_does_not_block_redirect(self):
        with mock.patch(
            'campaigns.services.CampaignRedirectHit.objects.create',
            side_effect=RuntimeError('db down'),
        ):
            response = self._get()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(CampaignRedirectHit.objects.count(), 0)

    def test_click_ids_forwarded_but_nothing_else(self):
        response = self._get('/campaigns/redirect/builders/ethcc?gclid=abc123&fbclid=f1&evil=1&redirect=https://evil.example.com')
        location = response['Location']
        self.assertIn('gclid=abc123', location)
        self.assertIn('fbclid=f1', location)
        self.assertNotIn('evil', location)
        self.assertNotIn('redirect=', location)

    def test_oversized_click_id_truncated(self):
        response = self._get('/campaigns/redirect/builders/ethcc?gclid=' + 'x' * 500)
        self.assertIn('gclid=' + 'x' * 100, response['Location'])
        self.assertNotIn('x' * 101, response['Location'])

    def test_resolver_query_count_is_bounded(self):
        with self.assertNumQueries(2):  # link lookup + hit insert
            self._get()


class PurgeCampaignHitsCommandTests(TestCase):
    def setUp(self):
        self.link = make_link(make_campaign(tracking_key='purge_test'))
        old = CampaignRedirectHit.objects.create(campaign_link=self.link)
        CampaignRedirectHit.objects.filter(pk=old.pk).update(
            occurred_at=timezone.now() - timedelta(days=120),
        )
        CampaignRedirectHit.objects.create(campaign_link=self.link)

    def test_purges_only_old_hits(self):
        out = StringIO()
        call_command('purge_campaign_hits', stdout=out)
        self.assertEqual(CampaignRedirectHit.objects.count(), 1)
        self.assertIn('Deleted 1', out.getvalue())

    def test_dry_run_deletes_nothing(self):
        out = StringIO()
        call_command('purge_campaign_hits', '--dry-run', stdout=out)
        self.assertEqual(CampaignRedirectHit.objects.count(), 2)
        self.assertIn('Would delete 1', out.getvalue())

    def test_days_override(self):
        call_command('purge_campaign_hits', '--days', '365', stdout=StringIO())
        self.assertEqual(CampaignRedirectHit.objects.count(), 2)
