import time

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


@override_settings(DEBUG=False, SLOW_REQUEST_LOG_MS=50)
class SlowRequestLoggingTest(SimpleTestCase):
    """
    Production logged only 5xx, so a flood of slow successful requests left no
    trace. These pin the threshold, the redaction, and the no-double-log rule.
    """

    def setUp(self):
        self.factory = RequestFactory()

    def _middleware(self, status=200, delay=0.0):
        def view(_request):
            if delay:
                time.sleep(delay)
            return HttpResponse('ok', status=status)
        return APILoggingMiddleware(view)

    def test_slow_successful_request_logs_one_warning(self):
        request = self.factory.get('/api/v1/notifications/unread-count/')

        with self.assertLogs('tally.api', level='WARNING') as captured:
            self._middleware(delay=0.08)(request)

        self.assertEqual(len(captured.records), 1)
        record = captured.records[0]
        self.assertEqual(record.levelname, 'WARNING')
        self.assertIn('GET', record.getMessage())
        self.assertIn('/api/v1/notifications/unread-count/', record.getMessage())
        self.assertIn('200', record.getMessage())
        self.assertIn('ms', record.getMessage())

    def test_fast_request_logs_nothing(self):
        request = self.factory.get('/api/v1/notifications/unread-count/')

        with self.assertNoLogs('tally.api', level='DEBUG'):
            self._middleware()(request)

    def test_slow_server_error_logs_only_the_error(self):
        request = self.factory.get('/api/v1/notifications/unread-count/')

        with self.assertLogs('tally.api', level='DEBUG') as captured:
            self._middleware(status=500, delay=0.08)(request)

        levels = [record.levelname for record in captured.records]
        self.assertEqual(levels, ['ERROR'])

    def test_slow_4xx_still_logs_a_warning(self):
        request = self.factory.get('/api/v1/notifications/unread-count/')

        with self.assertLogs('tally.api', level='WARNING') as captured:
            self._middleware(status=403, delay=0.08)(request)

        self.assertEqual(len(captured.records), 1)
        self.assertIn('403', captured.records[0].getMessage())

    def test_slow_request_redacts_sensitive_path(self):
        token = 'slow-synthetic-claim-token'
        request = self.factory.post(f'/api/v1/poaps/claim-link/{token}/')

        with self.assertLogs('tally.api', level='WARNING') as captured:
            self._middleware(delay=0.08)(request)

        logs = '\n'.join(captured.output)
        self.assertIn('/api/v1/poaps/claim-link/<redacted>/', logs)
        self.assertNotIn(token, logs)

    def test_query_string_is_never_logged(self):
        request = self.factory.get(
            '/api/v1/notifications/', {'secret_token': 'do-not-log-me'}
        )

        with self.assertLogs('tally.api', level='WARNING') as captured:
            self._middleware(delay=0.08)(request)

        self.assertNotIn('do-not-log-me', '\n'.join(captured.output))

    def test_skipped_paths_log_nothing_even_when_slow(self):
        request = self.factory.get('/health/')

        with self.assertNoLogs('tally.api', level='DEBUG'):
            self._middleware(delay=0.08)(request)
