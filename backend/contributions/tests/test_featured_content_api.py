from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from contributions.models import FeaturedContent

User = get_user_model()


class FeaturedContentAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='featured-user@example.com',
            address='0x1234567890123456789012345678901234567890',
            password='testpass123',
        )

    def create_hero(self, title, placements=None, status_value='active', order=0):
        data = {
            'content_type': 'hero',
            'title': title,
            'description': 'Featured hero',
            'user': self.user,
            'status': status_value,
            'order': order,
        }
        if placements is not None:
            data['hero_placements'] = placements
        return FeaturedContent.objects.create(**data)

    def test_hero_placement_filter_includes_all_and_matching_surface(self):
        self.create_hero('All surfaces', placements=['all'], order=0)
        self.create_hero('Builder only', placements=['builder'], order=1)
        self.create_hero('Overview only', placements=['overview'], order=2)
        self.create_hero('Inactive builder', placements=['builder'], status_value='idle', order=3)

        response = self.client.get('/api/v1/featured/?type=hero&placement=builder')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item['title'] for item in response.json()],
            ['All surfaces', 'Builder only'],
        )

    def test_hero_placement_filter_supports_overview(self):
        self.create_hero('All surfaces', placements=['all'], order=0)
        self.create_hero('Overview only', placements=['overview'], order=1)
        self.create_hero('Community only', placements=['community'], order=2)

        response = self.client.get('/api/v1/featured/?type=hero&placement=overview')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item['title'] for item in response.json()],
            ['All surfaces', 'Overview only'],
        )

    def test_hero_placement_filter_rejects_unknown_surface(self):
        response = self.client.get('/api/v1/featured/?type=hero&placement=unknown')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_default_hero_placements_keep_existing_surfaces(self):
        hero = self.create_hero('Default surfaces')

        self.assertTrue(hero.shows_in_placement('overview'))
        self.assertTrue(hero.shows_in_placement('builder'))
        self.assertTrue(hero.shows_in_placement('community'))
        self.assertFalse(hero.shows_in_placement('validator'))
