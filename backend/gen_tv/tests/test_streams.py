from django.test import TestCase
from django.utils import timezone

from gen_tv.models import Stream


class StreamAPITest(TestCase):
    def setUp(self):
        now = timezone.now()
        Stream.objects.create(
            title='Internal Live',
            slug='internal-live',
            url='https://x.com/genlayer/status/1',
            starts_at=now - timezone.timedelta(minutes=10),
            ends_at=now + timezone.timedelta(minutes=50),
            category=Stream.Category.INTERNAL,
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

    def test_detail_uses_slug_lookup(self):
        res = self.client.get('/api/v1/gen-tv/streams/community-upcoming/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['slug'], 'community-upcoming')
