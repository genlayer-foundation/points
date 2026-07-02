from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone

from contributions.node_upgrade.models import TargetNodeVersion
from users.models import User
from validators.models import Validator, ValidatorWallet
from validators.version_status import compute_version_status


class ComputeVersionStatusTests(TestCase):
    def _wallet(self, node_version='1.0.0', network='asimov'):
        user = User.objects.create_user(
            email=f'v-{node_version}-{network}@example.com',
            password='password',
            name='Op',
            address=f'0xop{node_version}{network}'.ljust(42, '0')[:42],
        )
        validator = Validator.objects.create(
            user=user, **{f'node_version_{network}': node_version}
        )
        return ValidatorWallet.objects.create(
            address=f'0xw{node_version}{network}'.ljust(42, '0')[:42],
            network=network,
            operator=validator,
            operator_address=user.address,
            status='active',
        )

    def test_no_target_is_unknown(self):
        ctx = compute_version_status(self._wallet(), None, timezone.now())
        self.assertEqual(ctx['status'], 'unknown')

    def test_up_to_date_is_on(self):
        now = timezone.now()
        target = TargetNodeVersion.objects.create(
            version='1.0.0', network='asimov',
            target_date=now - timedelta(days=10), is_active=True,
        )
        ctx = compute_version_status(self._wallet('1.2.0'), target, now)
        self.assertEqual(ctx['status'], 'on')

    def test_within_grace_is_warning(self):
        now = timezone.now()
        target = TargetNodeVersion.objects.create(
            version='2.0.0', network='asimov',
            target_date=now - timedelta(days=2), is_active=True,
        )
        ctx = compute_version_status(self._wallet('1.0.0'), target, now)
        self.assertEqual(ctx['status'], 'warning')
        self.assertEqual(ctx['grace_days_remaining'], 1)  # default grace 3, 2 elapsed

    def test_after_grace_is_shame_at_target_plus_grace(self):
        now = timezone.now()
        target = TargetNodeVersion.objects.create(
            version='2.0.0', network='asimov',
            target_date=now - timedelta(days=5), is_active=True,
        )
        ctx = compute_version_status(self._wallet('1.0.0'), target, now)
        self.assertEqual(ctx['status'], 'shame')
        self.assertEqual(
            ctx['shame_started_at'].replace(microsecond=0),
            (target.target_date + timedelta(days=3)).replace(microsecond=0),
        )

    @override_settings(NODE_VERSION_SHAME_GRACE_DAYS=7)
    def test_grace_period_is_configurable_via_setting(self):
        now = timezone.now()
        # 5 days elapsed would be shame under the default 3, but the setting grants 7.
        target = TargetNodeVersion.objects.create(
            version='2.0.0', network='asimov',
            target_date=now - timedelta(days=5), is_active=True,
        )
        ctx = compute_version_status(self._wallet('1.0.0'), target, now)
        self.assertEqual(ctx['status'], 'warning')
        self.assertEqual(ctx['grace_days'], 7)
        self.assertEqual(ctx['grace_days_remaining'], 2)
