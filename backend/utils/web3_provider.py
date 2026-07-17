import requests
from django.conf import settings
from web3 import HTTPProvider
from web3.providers.rpc.utils import ExceptionRetryConfiguration


RETRYABLE_HTTP_EXCEPTIONS = (
    requests.ConnectionError,
    requests.HTTPError,
    requests.Timeout,
)


def build_web3_http_provider(endpoint_uri):
    """Build the bounded HTTP provider used for validator RPC reads."""
    max_retries = max(0, settings.WEB3_RPC_MAX_RETRIES)

    # Web3.py 7.16 counts the initial request in its `retries` loop, so add one
    # to keep this setting's meaning as retries after the initial attempt.
    retry_configuration = ExceptionRetryConfiguration(
        errors=RETRYABLE_HTTP_EXCEPTIONS,
        retries=max_retries + 1,
    )

    return HTTPProvider(
        endpoint_uri=endpoint_uri,
        request_kwargs={'timeout': settings.WEB3_RPC_TIMEOUT_SECONDS},
        exception_retry_configuration=retry_configuration,
    )
