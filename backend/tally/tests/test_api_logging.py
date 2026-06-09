from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings

from tally.middleware.api_logging import APILoggingMiddleware, redact_sensitive_path


class APILoggingMiddlewareTest(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_redacts_poap_claim_link_token_from_sensitive_path(self):
        path = '/api/v1/poaps/claim-link/synthetic-claim-token/'

        redacted = redact_sensitive_path(path)

        self.assertEqual(redacted, '/api/v1/poaps/claim-link/<redacted>/')
        self.assertNotIn('synthetic-claim-token', redacted)

    @override_settings(DEBUG=True)
    def test_debug_logging_redacts_poap_claim_link_token(self):
        token = 'debug-synthetic-claim-token'
        request = self.factory.post(f'/api/v1/poaps/claim-link/{token}/')
        middleware = APILoggingMiddleware(lambda _request: HttpResponse('ok', status=200))

        with self.assertLogs('tally.api', level='DEBUG') as captured:
            middleware(request)

        logs = '\n'.join(captured.output)
        self.assertIn('/api/v1/poaps/claim-link/<redacted>/', logs)
        self.assertNotIn(token, logs)

    @override_settings(DEBUG=False)
    def test_server_error_logging_redacts_poap_claim_link_token(self):
        token = 'error-synthetic-claim-token'
        request = self.factory.post(f'/api/v1/poaps/claim-link/{token}/')
        middleware = APILoggingMiddleware(lambda _request: HttpResponse('boom', status=500))

        with self.assertLogs('tally.api', level='ERROR') as captured:
            middleware(request)

        logs = '\n'.join(captured.output)
        self.assertIn('/api/v1/poaps/claim-link/<redacted>/', logs)
        self.assertIn('500', logs)
        self.assertNotIn(token, logs)
