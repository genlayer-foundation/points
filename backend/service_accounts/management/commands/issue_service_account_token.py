from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from service_accounts.models import ServiceAccount, ServiceAccountToken


class Command(BaseCommand):
    help = (
        'Issue a service account token. The plaintext is printed once and '
        'never stored. Rotation = issue a new token + revoke the old one '
        '(admin action).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            'account',
            help='Service account name (created if missing)',
        )
        parser.add_argument(
            '--scopes',
            nargs='+',
            required=True,
            help='Scope strings to grant, e.g. myfeature:read myfeature:write',
        )
        parser.add_argument(
            '--expires-days',
            type=int,
            default=None,
            help='Days until the token expires (default: never)',
        )
        parser.add_argument(
            '--description',
            default='',
            help='Description used when creating a new account',
        )

    def handle(self, *args, **options):
        account, created = ServiceAccount.objects.get_or_create(
            name=options['account'],
            defaults={'description': options['description']},
        )
        expires_at = None
        if options['expires_days']:
            expires_at = timezone.now() + timedelta(days=options['expires_days'])

        token, plaintext = ServiceAccountToken.issue(
            account, options['scopes'], expires_at=expires_at,
        )

        if created:
            self.stdout.write(f'Created service account "{account.name}".')
        self.stdout.write(f'Token id: {token.identifier}')
        self.stdout.write(f'Scopes: {", ".join(token.scopes)}')
        self.stdout.write(
            f'Expires: {expires_at.isoformat() if expires_at else "never"}'
        )
        self.stdout.write(self.style.SUCCESS(plaintext))
        self.stdout.write(self.style.WARNING(
            'Store this token now. It cannot be shown again.'
        ))
