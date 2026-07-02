from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient


User = get_user_model()


class ReferralCodeTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='referral-owner@example.com',
            password='testpass123',
            address='0x1234567890abcdef1234567890abcdef12345678',
            is_email_verified=True,
        )
        User.objects.filter(pk=self.user.pk).update(referral_code='')
        self.user.refresh_from_db()

    def test_me_does_not_generate_missing_referral_code_on_get(self):
        self.client.force_authenticate(self.user)

        response = self.client.get('/api/v1/users/me/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['referral_code'], '')
        self.user.refresh_from_db()
        self.assertEqual(self.user.referral_code, '')

    def test_ensure_referral_code_persists_and_returns_generated_code(self):
        code = self.user.ensure_referral_code()

        self.assertRegex(code, r'^[A-Z0-9]{8}$')
        self.user.refresh_from_db()
        self.assertEqual(code, self.user.referral_code)

    def test_public_profile_does_not_expose_referral_code(self):
        response = self.client.get(f'/api/v1/users/by-address/{self.user.address}/')

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('referral_code', response.data)
        self.user.refresh_from_db()
        self.assertEqual(self.user.referral_code, '')
