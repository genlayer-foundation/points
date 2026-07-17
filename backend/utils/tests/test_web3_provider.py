from unittest.mock import patch

import requests
from django.conf import settings
from django.test import SimpleTestCase, override_settings

from users.views import UserViewSet
from utils.web3_provider import build_web3_http_provider
from validators.genlayer_validators_service import GenLayerValidatorsService


class Web3HTTPProviderTests(SimpleTestCase):
    def test_default_rpc_boundaries(self):
        self.assertEqual(settings.WEB3_RPC_TIMEOUT_SECONDS, 10)
        self.assertEqual(settings.WEB3_RPC_MAX_RETRIES, 1)

    @override_settings(WEB3_RPC_TIMEOUT_SECONDS=4, WEB3_RPC_MAX_RETRIES=2)
    def test_provider_applies_timeout_and_retry_budget(self):
        provider = build_web3_http_provider('https://rpc.example')

        self.assertEqual(provider.get_request_kwargs()['timeout'], 4)
        # Web3.py 7.16's loop value is total attempts: initial + two retries.
        self.assertEqual(provider.exception_retry_configuration.retries, 3)

    @override_settings(WEB3_RPC_TIMEOUT_SECONDS=10, WEB3_RPC_MAX_RETRIES=1)
    def test_one_retry_occurs_after_initial_timeout(self):
        provider = build_web3_http_provider('https://rpc.example')
        response = b'{"jsonrpc":"2.0","id":0,"result":"0x1"}'

        with (
            patch.object(
                provider._request_session_manager,
                'make_post_request',
                side_effect=[requests.Timeout('timed out'), response],
            ) as make_post_request,
            patch('web3.providers.rpc.rpc.time.sleep'),
        ):
            result = provider.make_request('eth_call', [])

        self.assertEqual(result['result'], '0x1')
        self.assertEqual(make_post_request.call_count, 2)

    @override_settings(WEB3_RPC_TIMEOUT_SECONDS=10, WEB3_RPC_MAX_RETRIES=1)
    def test_one_retry_occurs_after_initial_connection_error(self):
        provider = build_web3_http_provider('https://rpc.example')
        response = b'{"jsonrpc":"2.0","id":0,"result":"0x1"}'

        with (
            patch.object(
                provider._request_session_manager,
                'make_post_request',
                side_effect=[requests.ConnectionError('connection failed'), response],
            ) as make_post_request,
            patch('web3.providers.rpc.rpc.time.sleep'),
        ):
            result = provider.make_request('eth_call', [])

        self.assertEqual(result['result'], '0x1')
        self.assertEqual(make_post_request.call_count, 2)

    @override_settings(WEB3_RPC_TIMEOUT_SECONDS=6, WEB3_RPC_MAX_RETRIES=1)
    def test_validator_sync_uses_bounded_provider(self):
        service = GenLayerValidatorsService(network_key='asimov')

        self.assertEqual(service.w3.provider.get_request_kwargs()['timeout'], 6)
        self.assertEqual(service.w3.provider.exception_retry_configuration.retries, 2)

    @override_settings(WEB3_RPC_TIMEOUT_SECONDS=7, WEB3_RPC_MAX_RETRIES=1)
    def test_users_validators_contract_uses_bounded_provider(self):
        contract = UserViewSet()._get_web3_contract()

        self.assertEqual(contract.w3.provider.get_request_kwargs()['timeout'], 7)
        self.assertEqual(contract.w3.provider.exception_retry_configuration.retries, 2)
