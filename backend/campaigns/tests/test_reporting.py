from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from campaigns.models import CampaignRedirectHit, UserAcquisitionAttribution
from campaigns.services import campaign_report
from campaigns.tests.test_models import make_campaign, make_link
from contributions.models import Category, Contribution, ContributionType, SubmittedContribution
from ethereum_auth.models import PendingWalletSignup
from leaderboard.models import GlobalLeaderboardMultiplier
from social_tasks.models import SocialTask, SocialTaskCompletion

User = get_user_model()


class CampaignReportTests(TestCase):
    def setUp(self):
        self.campaign = make_campaign()
        self.link = make_link(self.campaign)
        self.builder_category, _ = Category.objects.get_or_create(
            slug='builder', defaults={'name': 'Builder'},
        )
        self.community_category, _ = Category.objects.get_or_create(
            slug='community', defaults={'name': 'Community'},
        )
        self.builder_type = ContributionType.objects.create(
            name='Project', slug='project-x', category=self.builder_category,
            min_points=0, max_points=100,
        )
        self.waitlist_type = ContributionType.objects.create(
            name='Validator Waitlist', slug='validator-waitlist',
            min_points=0, max_points=0,
        )
        GlobalLeaderboardMultiplier.objects.create(
            contribution_type=self.waitlist_type,
            multiplier_value=1.0,
            valid_from=timezone.now() - timezone.timedelta(days=1),
        )
        self.flagged_task = SocialTask.objects.create(
            name='Post about GenLayer', slug='post-about-genlayer',
            category=self.community_category, verification_type='click_through',
            action_url='https://x.com', counts_as_activation=True,
        )
        self.unflagged_task = SocialTask.objects.create(
            name='Follow', slug='follow-genlayer-test',
            category=self.community_category, verification_type='click_through',
            action_url='https://x.com',
        )

    def _attributed_user(self, email):
        user = User.objects.create_user(email=email, password='x', visible=True)
        UserAcquisitionAttribution.objects.create(
            user=user,
            campaign_link=self.link,
            link_tracking_id=self.link.tracking_id,
            campaign_key=self.campaign.tracking_key,
            registered_at=timezone.now(),
        )
        return user

    def test_report_counts_distinct_users_not_events(self):
        user = self._attributed_user('builder@example.com')
        for _ in range(2):
            SubmittedContribution.objects.create(
                user=user,
                contribution_type=self.builder_type,
                contribution_date=timezone.now(),
            )
        report = campaign_report(self.campaign)
        self.assertEqual(report['signups'], 1)
        self.assertEqual(report['activations']['builder'], 1)
        self.assertEqual(report['source'], 'portal_db')

    def test_validator_activation_from_waitlist_contribution(self):
        user = self._attributed_user('validator@example.com')
        Contribution.objects.create(
            user=user, contribution_type=self.waitlist_type, points=0,
            contribution_date=timezone.now(),
        )
        report = campaign_report(self.campaign)
        self.assertEqual(report['activations']['validator'], 1)
        self.assertEqual(report['activations']['builder'], 0)

    def test_only_flagged_tasks_count_as_community_activation(self):
        user = self._attributed_user('community@example.com')
        SocialTaskCompletion.objects.create(user=user, task=self.unflagged_task, points_awarded=10)
        self.assertEqual(campaign_report(self.campaign)['activations']['community'], 0)
        SocialTaskCompletion.objects.create(user=user, task=self.flagged_task, points_awarded=10)
        self.assertEqual(campaign_report(self.campaign)['activations']['community'], 1)

    def test_users_from_other_campaigns_excluded(self):
        other_campaign = make_campaign(tracking_key='other_campaign', name='Other')
        other_link = make_link(other_campaign, alias='other')
        user = User.objects.create_user(email='other@example.com', password='x')
        UserAcquisitionAttribution.objects.create(
            user=user,
            campaign_link=other_link,
            link_tracking_id=other_link.tracking_id,
            campaign_key=other_campaign.tracking_key,
            registered_at=timezone.now(),
        )
        SubmittedContribution.objects.create(
            user=user, contribution_type=self.builder_type, contribution_date=timezone.now(),
        )
        report = campaign_report(self.campaign)
        self.assertEqual(report['signups'], 0)
        self.assertEqual(report['activations']['builder'], 0)

    def test_signups_survive_link_deletion_via_snapshot_key(self):
        self._attributed_user('survivor@example.com')
        UserAcquisitionAttribution.objects.update(campaign_link=None)
        self.assertEqual(campaign_report(self.campaign)['signups'], 1)

    def test_hits_and_wallet_connects(self):
        CampaignRedirectHit.objects.create(campaign_link=self.link)
        CampaignRedirectHit.objects.create(campaign_link=self.link, is_probable_bot=True)
        PendingWalletSignup.objects.create(
            address='0x2222222222222222222222222222222222222222',
            expires_at=timezone.now() + timezone.timedelta(minutes=30),
            acquisition_campaign_link=self.link,
            acquisition_captured_at=timezone.now(),
        )
        report = campaign_report(self.campaign)
        self.assertEqual(report['redirect_hits_human'], 1)
        self.assertEqual(report['redirect_hits_bot'], 1)
        self.assertEqual(report['wallet_connects'], 1)
