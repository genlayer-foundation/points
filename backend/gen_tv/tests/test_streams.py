from django.test import TestCase
from django.utils import timezone

from gen_tv.models import Stream, StreamCategory


class StreamAPITest(TestCase):
    def setUp(self):
        now = timezone.now()
        self.product_category = StreamCategory.objects.create(
            name='Product Updates',
            slug='product-updates',
            group=StreamCategory.Group.INTERNAL,
            display_order=1,
        )
        self.community_category = StreamCategory.objects.create(
            name='Community AMAs',
            slug='community-amas',
            group=StreamCategory.Group.COMMUNITY,
            display_order=2,
        )
        self.hidden_category = StreamCategory.objects.create(
            name='Hidden Category',
            slug='hidden-category',
            group=StreamCategory.Group.INTERNAL,
            is_active=False,
        )
        Stream.objects.create(
            title='Internal Live',
            slug='internal-live',
            url='https://x.com/genlayer/status/1',
            starts_at=now - timezone.timedelta(minutes=10),
            ends_at=now + timezone.timedelta(minutes=50),
            category=Stream.Category.INTERNAL,
            detailed_category=self.product_category,
        )
        Stream.objects.create(
            title='Internal Past',
            slug='internal-past',
            url='https://x.com/genlayer/status/2',
            starts_at=now - timezone.timedelta(hours=2),
            ends_at=now - timezone.timedelta(hours=1),
            category=Stream.Category.INTERNAL,
        )
        Stream.objects.create(
            title='Community Upcoming',
            slug='community-upcoming',
            url='https://x.com/community/status/3',
            starts_at=now + timezone.timedelta(hours=1),
            ends_at=now + timezone.timedelta(hours=2),
            category=Stream.Category.COMMUNITY,
            detailed_category=self.community_category,
        )
        Stream.objects.create(
            title='Inactive',
            slug='inactive',
            url='https://x.com/genlayer/status/9',
            starts_at=now - timezone.timedelta(minutes=10),
            ends_at=now + timezone.timedelta(minutes=50),
            category=Stream.Category.INTERNAL,
            is_active=False,
        )

    def test_list_excludes_inactive(self):
        res = self.client.get('/api/v1/gen-tv/streams/')
        self.assertEqual(res.status_code, 200)
        results = res.json()
        slugs = {s['slug'] for s in results}
        self.assertSetEqual(
            slugs,
            {'internal-live', 'internal-past', 'community-upcoming'},
        )

    def test_filter_by_category_and_status(self):
        res = self.client.get('/api/v1/gen-tv/streams/?category=internal&status=live')
        self.assertEqual(res.status_code, 200)
        results = res.json()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['slug'], 'internal-live')
        self.assertEqual(results[0]['category_display'], 'Internal team')
        self.assertEqual(results[0]['detailed_category']['slug'], 'product-updates')

    def test_filter_by_detailed_category(self):
        res = self.client.get('/api/v1/gen-tv/streams/?detailed_category=community-amas')
        self.assertEqual(res.status_code, 200)
        results = res.json()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['slug'], 'community-upcoming')

    def test_inactive_detailed_category_is_hidden_from_stream_payloads(self):
        now = timezone.now()
        stream = Stream.objects.create(
            title='Hidden Category Stream',
            slug='hidden-category-stream',
            url='https://x.com/genlayer/status/10',
            starts_at=now - timezone.timedelta(minutes=20),
            ends_at=now + timezone.timedelta(minutes=40),
            category=Stream.Category.INTERNAL,
            detailed_category=self.hidden_category,
        )

        list_res = self.client.get('/api/v1/gen-tv/streams/')
        self.assertEqual(list_res.status_code, 200)
        list_payload = next(
            item for item in list_res.json() if item['slug'] == stream.slug
        )
        self.assertIsNone(list_payload['detailed_category'])

        detail_res = self.client.get(f'/api/v1/gen-tv/streams/{stream.slug}/')
        self.assertEqual(detail_res.status_code, 200)
        self.assertIsNone(detail_res.json()['detailed_category'])

    def test_filter_by_inactive_detailed_category_returns_no_streams(self):
        now = timezone.now()
        Stream.objects.create(
            title='Hidden Category Stream',
            slug='hidden-category-stream',
            url='https://x.com/genlayer/status/10',
            starts_at=now - timezone.timedelta(minutes=20),
            ends_at=now + timezone.timedelta(minutes=40),
            category=Stream.Category.INTERNAL,
            detailed_category=self.hidden_category,
        )

        res = self.client.get('/api/v1/gen-tv/streams/?detailed_category=hidden-category')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), [])

    def test_detail_uses_slug_lookup(self):
        res = self.client.get('/api/v1/gen-tv/streams/community-upcoming/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['slug'], 'community-upcoming')

    def test_category_list_excludes_inactive(self):
        res = self.client.get('/api/v1/gen-tv/categories/')
        self.assertEqual(res.status_code, 200)
        slugs = [category['slug'] for category in res.json()]
        self.assertEqual(slugs, ['product-updates', 'community-amas'])
