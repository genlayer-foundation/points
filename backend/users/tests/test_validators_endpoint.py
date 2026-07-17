from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase


User = get_user_model()


class UserValidatorsEndpointTests(APITestCase):
    def setUp(self):
        user = User.objects.create_user(
            email='validator-reader@example.com',
            password='testpass123',
        )
        self.client.force_authenticate(user=user)

    @patch('users.views.UserViewSet._get_web3_contract')
    def test_success_response_still_filters_zero_addresses(self, get_contract):
        valid_address = '0x1111111111111111111111111111111111111111'
        contract = MagicMock()
        contract.functions.getValidatorsAtCurrentEpoch.return_value.call.return_value = [
            valid_address,
            '0x0000000000000000000000000000000000000000',
        ]
        get_contract.return_value = contract

        response = self.client.get('/api/v1/users/validators/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [valid_address])

    @patch(
        'users.views.UserViewSet._get_web3_contract',
        side_effect=RuntimeError('rpc unavailable'),
    )
    def test_failure_response_is_unchanged(self, _get_contract):
        response = self.client.get('/api/v1/users/validators/')

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.data, {'error': 'rpc unavailable'})
