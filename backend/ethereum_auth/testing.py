"""Test helpers for building a real portal wallet session."""

MODEL_BACKEND = 'django.contrib.auth.backends.ModelBackend'


def login_wallet_session(client, user, address=None):
    """
    Seed a session identical to the one ethereum_auth.views.login creates.

    Uses Django's real login machinery so the session carries _auth_user_id,
    _auth_user_backend and _auth_user_hash, which is what EthereumAuthentication
    resolves the user from. Hand-seeding only 'ethereum_address' and
    'authenticated' produces a session the authenticator rejects.

    Pass ``address`` verbatim to simulate signup_email_confirm, which stores the
    address in database casing rather than lowercased.

    Prefer DRF's force_authenticate for view-logic tests; use this when the test
    is about session, authentication-chain, or CSRF behaviour.
    """
    client.force_login(user, backend=MODEL_BACKEND)
    session = client.session
    session['ethereum_address'] = (
        address if address is not None else (user.address or '').lower()
    )
    session['authenticated'] = True
    session.save()
    return session
