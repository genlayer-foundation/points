import decimal

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = (
        'Repairs corrupt multiplier_at_creation values in contributions. '
        'Only rows whose stored value cannot be parsed as a decimal are '
        'rewritten (multiplier reset to 1.0, frozen_global_points recomputed '
        'as points x 1.0); valid frozen multiplier history is never touched. '
        'Dry run by default; pass --apply to write the fixes.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Write the fixes. Without this flag the command only reports corrupt rows.',
        )

    @staticmethod
    def _is_valid_decimal(raw_value):
        if raw_value is None:
            return True
        try:
            decimal.Decimal(str(raw_value))
            return True
        except (decimal.InvalidOperation, ValueError, TypeError):
            return False

    def handle(self, *args, **options):
        apply_changes = options['apply']

        # Read the column as text so corrupt values (possible on SQLite, which
        # does not enforce column types) can be inspected without tripping the
        # ORM's decimal conversion.
        corrupt_ids = []
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, CAST(multiplier_at_creation AS TEXT)
                FROM contributions_contribution
            """)
            for row_id, multiplier_raw in cursor.fetchall():
                if not self._is_valid_decimal(multiplier_raw):
                    corrupt_ids.append(row_id)
                    self.stdout.write(
                        f'Corrupt multiplier_at_creation on contribution id={row_id}: {multiplier_raw!r}'
                    )

        if not corrupt_ids:
            self.stdout.write(self.style.SUCCESS('No corrupt decimal values found. Nothing to do.'))
            return

        if not apply_changes:
            self.stdout.write(self.style.WARNING(
                f'Dry run: {len(corrupt_ids)} corrupt row(s) found. '
                'Re-run with --apply to reset their multiplier to 1.0 and '
                'recompute frozen_global_points.'
            ))
            return

        with connection.cursor() as cursor:
            placeholders = ','.join(['%s'] * len(corrupt_ids))
            cursor.execute(
                f"""
                UPDATE contributions_contribution
                SET multiplier_at_creation = '1.0',
                    frozen_global_points = points
                WHERE id IN ({placeholders})
                """,
                corrupt_ids,
            )

        self.stdout.write(self.style.SUCCESS(
            f'Fixed {len(corrupt_ids)} corrupt row(s); all other rows left untouched.'
        ))
