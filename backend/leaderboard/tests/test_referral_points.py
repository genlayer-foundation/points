from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta

from leaderboard.models import (
    ReferralPoints,
    update_referrer_points,
    recalculate_referrer_points,
    get_eligible_referred_user_ids,
    get_referral_breakdown,
    GlobalLeaderboardMultiplier,
    VALIDATOR_REFERRAL_EXCLUDED_SLUGS,
)
from contributions.models import Contribution, ContributionType, Category

User = get_user_model()


class ReferralPointsExclusionTest(TestCase):
    """Test that validator-waitlist is excluded from validator referral points."""

    def setUp(self):
        # Create categories
        self.validator_category = Category.objects.create(
            name='Validator', slug='validator', description='Validator contributions'
        )
        self.builder_category = Category.objects.create(
            name='Builder', slug='builder', description='Builder contributions'
        )

        # Create contribution types
        self.waitlist_type = ContributionType.objects.create(
            name='Validator Waitlist',
            slug='validator-waitlist',
            description='Joined the validator waitlist',
            category=self.validator_category,
            min_points=20,
            max_points=20,
        )
        self.node_running_type = ContributionType.objects.create(
            name='Node Running',
            slug='node-running',
            description='Running a validator node',
            category=self.validator_category,
            min_points=10,
            max_points=100,
        )
        self.builder_welcome_type = ContributionType.objects.create(
            name='Builder Welcome',
            slug='builder-welcome',
            description='Welcome to the builder community',
            category=self.builder_category,
            min_points=20,
            max_points=20,
        )
        self.blog_type = ContributionType.objects.create(
            name='Blog Post',
            slug='blog-post',
            description='Blog post contribution',
            category=self.builder_category,
            min_points=10,
            max_points=100,
        )

        # Create multipliers (required for frozen_global_points)
        now = timezone.now()
        for ct in [self.waitlist_type, self.node_running_type, self.builder_welcome_type, self.blog_type]:
            GlobalLeaderboardMultiplier.objects.create(
                contribution_type=ct,
                multiplier_value=Decimal('1.0'),
                valid_from=now - timedelta(days=30),
            )

        # Create referrer and referred user
        self.referrer = User.objects.create_user(
            email='referrer@test.com',
            password='testpass123',
            name='Referrer',
            address='0x1111111111111111111111111111111111111111',
        )
        self.referred_user = User.objects.create_user(
            email='referred@test.com',
            password='testpass123',
            name='Referred',
            address='0x2222222222222222222222222222222222222222',
            referred_by=self.referrer,
        )

    def _create_contribution(self, user, contribution_type, points):
        """Helper to create a contribution with frozen_global_points."""
        return Contribution.objects.create(
            user=user,
            contribution_type=contribution_type,
            points=points,
            frozen_global_points=points,
            multiplier_at_creation=Decimal('1.0'),
            contribution_date=timezone.now(),
        )

    def test_validator_waitlist_excluded_from_referral_sum(self):
        """Referred user with only validator-waitlist should give referrer 0 validator referral points."""
        # Give referred user the waitlist badge + a builder contribution (so they pass eligibility gate)
        self._create_contribution(self.referred_user, self.waitlist_type, 20)
        self._create_contribution(self.referred_user, self.blog_type, 50)

        # Trigger referral update
        contribution = Contribution.objects.filter(
            user=self.referred_user, contribution_type=self.blog_type
        ).first()
        update_referrer_points(contribution)

        rp = ReferralPoints.objects.get(user=self.referrer)
        # Validator referral should be 0 (waitlist excluded), not 2 (10% of 20)
        self.assertEqual(rp.validator_points, 0)
        # Builder referral should be 5 (10% of 50)
        self.assertEqual(rp.builder_points, 5)

    def test_real_validator_included_in_referral_sum(self):
        """Referred user with real validator contribution should give referrer correct 10%."""
        self._create_contribution(self.referred_user, self.node_running_type, 100)

        contribution = Contribution.objects.filter(
            user=self.referred_user, contribution_type=self.node_running_type
        ).first()
        update_referrer_points(contribution)

        rp = ReferralPoints.objects.get(user=self.referrer)
        self.assertEqual(rp.validator_points, 10)  # 10% of 100

    def test_mixed_contributions_excludes_badge(self):
        """Referred user with waitlist (20) + node-running (100) should give referrer 10, not 12."""
        self._create_contribution(self.referred_user, self.waitlist_type, 20)
        self._create_contribution(self.referred_user, self.node_running_type, 100)

        contribution = Contribution.objects.filter(
            user=self.referred_user, contribution_type=self.node_running_type
        ).first()
        update_referrer_points(contribution)

        rp = ReferralPoints.objects.get(user=self.referrer)
        # Should be 10% of 100 = 10, NOT 10% of 120 = 12
        self.assertEqual(rp.validator_points, 10)

    def test_eligible_user_filter_unchanged(self):
        """Eligibility gate still works: user with ONLY onboarding badges is not eligible."""
        self._create_contribution(self.referred_user, self.waitlist_type, 20)

        eligible_ids = get_eligible_referred_user_ids(self.referrer)
        self.assertEqual(len(eligible_ids), 0)

    def test_eligible_user_with_real_contribution(self):
        """User with real contribution passes eligibility gate."""
        self._create_contribution(self.referred_user, self.waitlist_type, 20)
        self._create_contribution(self.referred_user, self.node_running_type, 100)

        eligible_ids = get_eligible_referred_user_ids(self.referrer)
        self.assertIn(self.referred_user.id, eligible_ids)

    def test_recalculate_matches_update(self):
        """recalculate_referrer_points gives same result as update_referrer_points."""
        self._create_contribution(self.referred_user, self.waitlist_type, 20)
        self._create_contribution(self.referred_user, self.node_running_type, 100)
        self._create_contribution(self.referred_user, self.blog_type, 50)

        # Use update path
        contribution = Contribution.objects.filter(
            user=self.referred_user, contribution_type=self.node_running_type
        ).first()
        update_referrer_points(contribution)
        rp_update = ReferralPoints.objects.get(user=self.referrer)
        update_builder = rp_update.builder_points
        update_validator = rp_update.validator_points

        # Reset and use recalculate path
        rp_update.builder_points = 0
        rp_update.validator_points = 0
        rp_update.save()

        recalculate_referrer_points(self.referrer)
        rp_recalc = ReferralPoints.objects.get(user=self.referrer)

        self.assertEqual(rp_recalc.builder_points, update_builder)
        self.assertEqual(rp_recalc.validator_points, update_validator)

    def test_constant_contains_validator_waitlist(self):
        """Verify the exclusion constant contains validator-waitlist."""
        self.assertIn('validator-waitlist', VALIDATOR_REFERRAL_EXCLUDED_SLUGS)


class ReferralBreakdownHelperTest(TestCase):
    """Test the shared get_referral_breakdown() helper."""

    def setUp(self):
        # Create categories
        self.validator_category = Category.objects.create(
            name='Validator', slug='validator', description='Validator contributions'
        )
        self.builder_category = Category.objects.create(
            name='Builder', slug='builder', description='Builder contributions'
        )

        # Create contribution types
        self.waitlist_type = ContributionType.objects.create(
            name='Validator Waitlist',
            slug='validator-waitlist',
            description='Joined the validator waitlist',
            category=self.validator_category,
            min_points=20,
            max_points=20,
        )
        self.node_running_type = ContributionType.objects.create(
            name='Node Running',
            slug='node-running',
            description='Running a validator node',
            category=self.validator_category,
            min_points=10,
            max_points=100,
        )
        self.blog_type = ContributionType.objects.create(
            name='Blog Post',
            slug='blog-post',
            description='Blog post contribution',
            category=self.builder_category,
            min_points=10,
            max_points=100,
        )

        # Create multipliers
        now = timezone.now()
        for ct in [self.waitlist_type, self.node_running_type, self.blog_type]:
            GlobalLeaderboardMultiplier.objects.create(
                contribution_type=ct,
                multiplier_value=Decimal('1.0'),
                valid_from=now - timedelta(days=30),
            )

        # Create referrer and referred users
        self.referrer = User.objects.create_user(
            email='referrer@test.com',
            password='testpass123',
            name='Referrer',
            address='0x1111111111111111111111111111111111111111',
        )
        self.referred_user_a = User.objects.create_user(
            email='referred_a@test.com',
            password='testpass123',
            name='Referred A',
            address='0x2222222222222222222222222222222222222222',
            referred_by=self.referrer,
        )
        self.referred_user_b = User.objects.create_user(
            email='referred_b@test.com',
            password='testpass123',
            name='Referred B',
            address='0x3333333333333333333333333333333333333333',
            referred_by=self.referrer,
        )

    def _create_contribution(self, user, contribution_type, points):
        """Helper to create a contribution with frozen_global_points."""
        return Contribution.objects.create(
            user=user,
            contribution_type=contribution_type,
            points=points,
            frozen_global_points=points,
            multiplier_at_creation=Decimal('1.0'),
            contribution_date=timezone.now(),
        )

    def test_returns_correct_structure(self):
        """Helper returns dict with expected keys."""
        result = get_referral_breakdown(self.referrer)
        self.assertIn('total_referrals', result)
        self.assertIn('builder_points', result)
        self.assertIn('validator_points', result)
        self.assertIn('referrals', result)

    def test_no_referrals_returns_zeros(self):
        """User with no referrals returns empty breakdown."""
        loner = User.objects.create_user(
            email='loner@test.com',
            password='testpass123',
            name='Loner',
            address='0x4444444444444444444444444444444444444444',
        )
        result = get_referral_breakdown(loner)
        self.assertEqual(result['total_referrals'], 0)
        self.assertEqual(result['builder_points'], 0)
        self.assertEqual(result['validator_points'], 0)
        self.assertEqual(result['referrals'], [])

    def test_lists_all_referred_users(self):
        """Breakdown includes all referred users regardless of contributions."""
        result = get_referral_breakdown(self.referrer)
        self.assertEqual(result['total_referrals'], 2)
        addresses = {r['address'] for r in result['referrals']}
        self.assertIn(self.referred_user_a.address, addresses)
        self.assertIn(self.referred_user_b.address, addresses)

    def test_excludes_validator_waitlist_from_per_user_breakdown(self):
        """Per-user validator points exclude validator-waitlist contributions."""
        self._create_contribution(self.referred_user_a, self.waitlist_type, 20)
        self._create_contribution(self.referred_user_a, self.node_running_type, 100)

        # Trigger stored referral point calculation
        contribution = Contribution.objects.filter(
            user=self.referred_user_a, contribution_type=self.node_running_type
        ).first()
        update_referrer_points(contribution)

        result = get_referral_breakdown(self.referrer)
        user_a_entry = next(r for r in result['referrals'] if r['id'] == self.referred_user_a.id)
        # Should be 100 (node-running only), not 120 (waitlist + node-running)
        self.assertEqual(user_a_entry['validator_contribution_points'], 100)

    def test_breakdown_sorted_by_total_points_descending(self):
        """Referral list is sorted by total_points descending."""
        self._create_contribution(self.referred_user_a, self.blog_type, 50)
        self._create_contribution(self.referred_user_b, self.blog_type, 200)

        result = get_referral_breakdown(self.referrer)
        self.assertEqual(result['referrals'][0]['id'], self.referred_user_b.id)
        self.assertEqual(result['referrals'][1]['id'], self.referred_user_a.id)

    def test_referral_entry_has_expected_fields(self):
        """Each referral entry has all expected fields."""
        self._create_contribution(self.referred_user_a, self.blog_type, 50)

        result = get_referral_breakdown(self.referrer)
        entry = result['referrals'][0]
        expected_fields = [
            'id', 'name', 'address', 'profile_image_url', 'total_points',
            'builder_contribution_points', 'validator_contribution_points',
            'created_at', 'total_contributions', 'is_validator', 'is_builder',
        ]
        for field in expected_fields:
            self.assertIn(field, entry, f"Missing field: {field}")
