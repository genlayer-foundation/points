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
        names = list(Partner.objects.values_list('name', flat=True))
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
        self.assertSetEqual(slugs, {'active-one', 'active-two'})

    def test_detail_uses_slug_lookup(self):
        res = self.client.get('/api/v1/partners/active-one/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['slug'], 'active-one')
