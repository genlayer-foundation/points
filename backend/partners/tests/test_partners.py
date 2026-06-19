from django.test import TestCase
from django.urls import reverse

from partners.models import Partner


class PartnerModelTest(TestCase):
    def test_default_ordering_uses_display_order_then_name(self):
        Partner.objects.create(
            name='Beta',
            slug='beta',
            logo_url='https://example.com/b.png',
            website_url='https://beta.example.com',
            display_order=10,
        )
        Partner.objects.create(
            name='Alpha',
            slug='alpha',
            logo_url='https://example.com/a.png',
            website_url='https://alpha.example.com',
            display_order=5,
        )
        Partner.objects.create(
            name='Carbon',
            slug='carbon',
            logo_url='https://example.com/c.png',
            website_url='https://carbon.example.com',
            display_order=5,
        )
        names = list(
            Partner.objects
            .filter(slug__in=['alpha', 'carbon', 'beta'])
            .values_list('name', flat=True)
        )
        self.assertEqual(names, ['Alpha', 'Carbon', 'Beta'])


class PartnerAPITest(TestCase):
    def setUp(self):
        Partner.objects.create(
            name='Active One',
            slug='active-one',
            logo_url='https://example.com/a.png',
            website_url='https://a.example.com',
        )
        Partner.objects.create(
            name='Active Two',
            slug='active-two',
            logo_url='https://example.com/b.png',
            website_url='https://b.example.com',
        )
        Partner.objects.create(
            name='Inactive',
            slug='inactive',
            logo_url='https://example.com/i.png',
            website_url='https://i.example.com',
            is_active=False,
        )

    def test_list_excludes_inactive(self):
        res = self.client.get('/api/v1/partners/')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        results = data['results'] if isinstance(data, dict) and 'results' in data else data
        slugs = {p['slug'] for p in results}
        self.assertIn('active-one', slugs)
        self.assertIn('active-two', slugs)
        self.assertNotIn('inactive', slugs)

    def test_detail_uses_slug_lookup(self):
        res = self.client.get('/api/v1/partners/active-one/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['slug'], 'active-one')

    def test_show_in_overview_filter(self):
        # 'active-two' is hidden from the overview; the filter must exclude it.
        Partner.objects.filter(slug='active-two').update(show_in_overview=False)
        res = self.client.get('/api/v1/partners/?show_in_overview=true')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        results = data['results'] if isinstance(data, dict) and 'results' in data else data
        slugs = {p['slug'] for p in results}
        self.assertIn('active-one', slugs)
        self.assertNotIn('active-two', slugs)  # hidden from overview
        self.assertNotIn('inactive', slugs)    # inactive everywhere
        # Without the flag, an overview-hidden-but-active partner is still listed.
        no_flag = self.client.get('/api/v1/partners/?page_size=100')
        no_flag_data = no_flag.json()
        no_flag_results = no_flag_data['results'] if isinstance(no_flag_data, dict) and 'results' in no_flag_data else no_flag_data
        no_flag_slugs = {p['slug'] for p in no_flag_results}
        self.assertIn('active-two', no_flag_slugs)
