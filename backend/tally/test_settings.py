"""
Test settings: disables migrations so the test DB is built directly from the
current model state. Avoids brittle data migrations (e.g. ones that hard-fail
on missing seed users) blocking the test suite on fresh dev environments.
"""

from .settings import *  # noqa: F401,F403


class _DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None


MIGRATION_MODULES = _DisableMigrations()
