import logging
import sys

from django.test import SimpleTestCase

from tally.middleware.logging_utils import LayeredFormatter, LayeredJSONFormatter


def _record_with_exception():
    try:
        raise RuntimeError('formatter boom')
    except RuntimeError:
        exc_info = sys.exc_info()
    return logging.LogRecord(
        name='tally.app.users', level=logging.ERROR, pathname=__file__,
        lineno=1, msg='Failed to complete community journey', args=(),
        exc_info=exc_info,
    )


class LayeredFormatterExceptionTest(SimpleTestCase):
    """Both formatters must render exc_info: logger.exception call sites are
    the only durable traceback source once a view catches the error (catching
    suppresses django.request's own 500 logging)."""

    def test_console_formatter_appends_traceback(self):
        output = LayeredFormatter().format(_record_with_exception())
        self.assertIn('[APP] ERROR: Failed to complete community journey', output)
        self.assertIn('Traceback', output)
        self.assertIn('formatter boom', output)

    def test_json_formatter_includes_traceback(self):
        output = LayeredJSONFormatter().format(_record_with_exception())
        self.assertIn('Traceback', output)
        self.assertIn('formatter boom', output)
