from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

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

    def test_new_partners_default_out_of_overview(self):
        partner = Partner.objects.create(
            name='Overview Partner',
            slug='overview-partner',
            website_url='https://overview.example.com',
        )

        self.assertFalse(partner.show_in_overview)


class PartnerAdminTest(TestCase):
    def setUp(self):
        self.admin_user = get_user_model().objects.create_superuser(
            email='partner-admin@example.com',
            password='adminpass123',
        )
        self.client.force_login(self.admin_user)

    def test_admin_can_create_ecosystem_partner_without_overview_image(self):
        res = self.client.post(
            '/admin/partners/partner/add/',
            {
                'name': 'Ecosystem Only',
                'slug': 'ecosystem-only',
                'description': '',
                'is_active': 'on',
                'logo_url': 'https://example.com/base.png',
                'overview_logo_url': '',
                'website_url': 'https://ecosystem.example.com',
                'url': '',
                'display_order': 0,
                '_save': 'Save',
            },
        )

        self.assertEqual(res.status_code, 302)
        partner = Partner.objects.get(slug='ecosystem-only')
        self.assertFalse(partner.show_in_overview)
        self.assertEqual(partner.logo_url, 'https://example.com/base.png')
        self.assertEqual(partner.overview_logo_url, '')

    def test_admin_requires_overview_image_when_selecting_overview(self):
        res = self.client.post(
            '/admin/partners/partner/add/',
            {
                'name': 'Missing Overview',
                'slug': 'missing-overview',
                'description': '',
                'is_active': 'on',
                'show_in_overview': 'on',
                'logo_url': 'https://example.com/base.png',
                'overview_logo_url': '',
                'website_url': 'https://missing.example.com',
                'url': '',
                'display_order': 0,
                '_save': 'Save',
            },
        )

        self.assertEqual(res.status_code, 200)
        self.assertContains(
            res,
            'Provide an overview logo URL or upload an overview image before showing this partner in the overview.',
        )
        self.assertFalse(Partner.objects.filter(slug='missing-overview').exists())

    @patch('utils.admin_mixins.CloudinaryService.upload_image')
    def test_admin_allows_overview_image_upload_when_selecting_overview(self, upload_image):
        upload_image.return_value = {
            'url': 'https://res.cloudinary.com/example/overview.png',
            'public_id': 'tally/partners/overview/uploaded-partner',
        }
        overview_file = SimpleUploadedFile(
            'overview.png',
            b'fake image bytes',
            content_type='image/png',
        )

        res = self.client.post(
            '/admin/partners/partner/add/',
            {
                'name': 'Uploaded Partner',
                'slug': 'uploaded-partner',
                'description': '',
                'is_active': 'on',
                'show_in_overview': 'on',
                'logo_url': 'https://example.com/base.png',
                'overview_logo_url': '',
                'overview_logo_url_upload': overview_file,
                'website_url': 'https://uploaded.example.com',
                'url': '',
                'display_order': 0,
                '_save': 'Save',
            },
        )

        self.assertEqual(res.status_code, 302)
        partner = Partner.objects.get(slug='uploaded-partner')
        self.assertTrue(partner.show_in_overview)
        self.assertEqual(partner.logo_url, 'https://example.com/base.png')
        self.assertEqual(partner.overview_logo_url, 'https://res.cloudinary.com/example/overview.png')
        self.assertEqual(partner.overview_logo_public_id, 'tally/partners/overview/uploaded-partner')
        upload_image.assert_called_once()


class PartnerAPITest(TestCase):
    def setUp(self):
        Partner.objects.create(
            name='Active One',
            slug='active-one',
            logo_url='https://example.com/a.png',
            overview_logo_url='https://example.com/overview-a.png',
            website_url='https://a.example.com',
            show_in_overview=True,
        )
        Partner.objects.create(
            name='Active Two',
            slug='active-two',
            logo_url='https://example.com/b.png',
            overview_logo_url='https://example.com/overview-b.png',
            website_url='https://b.example.com',
            show_in_overview=True,
        )
        Partner.objects.create(
            name='Inactive',
            slug='inactive',
            logo_url='https://example.com/i.png',
            overview_logo_url='https://example.com/overview-i.png',
            website_url='https://i.example.com',
            is_active=False,
            show_in_overview=True,
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

        active_one = next(p for p in results if p['slug'] == 'active-one')
        self.assertEqual(active_one['logo_url'], 'https://example.com/a.png')
        self.assertEqual(active_one['overview_logo_url'], 'https://example.com/overview-a.png')

    def test_detail_uses_slug_lookup(self):
        res = self.client.get('/api/v1/partners/active-one/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['slug'], 'active-one')

    def test_show_in_overview_filter(self):
        # 'active-two' is hidden from the overview; the filter must exclude it.
        Partner.objects.filter(slug='active-two').update(show_in_overview=False)
        Partner.objects.create(
            name='Missing Overview Logo',
            slug='missing-overview-logo',
            logo_url='https://example.com/base-only.png',
            website_url='https://base-only.example.com',
            show_in_overview=True,
        )
        res = self.client.get('/api/v1/partners/?show_in_overview=true')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        results = data['results'] if isinstance(data, dict) and 'results' in data else data
        slugs = {p['slug'] for p in results}
        self.assertIn('active-one', slugs)
        self.assertNotIn('active-two', slugs)  # hidden from overview
        self.assertNotIn('inactive', slugs)    # inactive everywhere
        self.assertNotIn('missing-overview-logo', slugs)  # selected but unusable for marquee
        # Without the flag, an overview-hidden-but-active partner is still listed.
        no_flag = self.client.get('/api/v1/partners/?page_size=100')
        no_flag_data = no_flag.json()
        no_flag_results = no_flag_data['results'] if isinstance(no_flag_data, dict) and 'results' in no_flag_data else no_flag_data
        no_flag_slugs = {p['slug'] for p in no_flag_results}
        self.assertIn('active-two', no_flag_slugs)
