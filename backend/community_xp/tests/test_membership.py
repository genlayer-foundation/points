from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone

from community_xp.models import Mee6CurrentXP, Mee6SyncRun
from community_xp.utils import get_community_member_user_ids
from contributions.models import (
    Category,
    Contribution,
    ContributionDiscordXPState,
    ContributionType,
)
from creators.models import Creator
from leaderboard.models import GlobalLeaderboardMultiplier
from poaps.models import PoapClaim, PoapDrop
from social_tasks.models import SocialTask, SocialTaskCompletion
from users.models import User


@override_settings(MEE6_GUILD_ID='guild-1')
class CommunityMembershipTest(TestCase):
    def setUp(self):
        self.community_category, _ = Category.objects.get_or_create(
            slug='community',
            defaults={'name': 'Community'},
        )
        self.community_type = ContributionType.objects.create(
            name='Community Membership Post',
            slug='community-membership-post',
            category=self.community_category,
            max_points=10_000,
        )
        self.link_type, _ = ContributionType.objects.update_or_create(
            slug='community-link-x',
            defaults={
                'name': 'Community Membership Link',
                'category': self.community_category,
                'min_points': 0,
                'max_points': 500,
            },
        )
        for contribution_type in (self.community_type, self.link_type):
            GlobalLeaderboardMultiplier.objects.get_or_create(
                contribution_type=contribution_type,
                defaults={
                    'multiplier_value': 1,
                    'valid_from': timezone.now() - timedelta(days=30),
                },
            )
        self.drop = PoapDrop.objects.create(
            title='Membership POAP',
            slug='membership-poap',
            event_start_at=timezone.now(),
            status=PoapDrop.STATUS_ACTIVE,
        )
        self._user_index = 0
        self._task_index = 0

    def create_user(self, *, visible=True):
        self._user_index += 1
        suffix = f'{self._user_index:040x}'
        return User.objects.create_user(
            email=f'member-{self._user_index}@example.com',
            password='pass',
            address=f'0x{suffix}',
            visible=visible,
        )

    def create_sync(self, *, guild_id='guild-1', completed_at=None):
        completed_at = completed_at or timezone.now()
        return Mee6SyncRun.objects.create(
            guild_id=guild_id,
            status=Mee6SyncRun.STATUS_SUCCESS,
            completed_at=completed_at,
            applied_at=completed_at,
        )

    def create_xp(self, user, *, guild_id='guild-1', xp=100):
        run = self.create_sync(guild_id=guild_id)
        return Mee6CurrentXP.objects.create(
            guild_id=guild_id,
            discord_id=f'discord-{guild_id}-{user.id}',
            rank=1,
            xp=xp,
            sync_run=run,
            matched_user=user,
            synced_at=run.completed_at,
        )

    def create_completion(self, user, *, points=100):
        self._task_index += 1
        task = SocialTask.objects.create(
            slug=f'membership-task-{self._task_index}',
            name=f'Membership task {self._task_index}',
            category=self.community_category,
            points=points,
            verification_type='click_through',
            action_url='https://example.com',
        )
        return SocialTaskCompletion.objects.create(
            user=user,
            task=task,
            points_awarded=points,
            verification_type='click_through',
        )

    def create_contribution(self, user, *, contribution_type=None, points=100):
        return Contribution.objects.create(
            user=user,
            contribution_type=contribution_type or self.community_type,
            points=points,
            contribution_date=timezone.now(),
        )

    def test_positive_xp_uses_selected_guild_visibility_and_user_ids(self):
        selected = self.create_user()
        other_guild = self.create_user()
        zero_xp = self.create_user()
        hidden = self.create_user(visible=False)
        self.create_xp(selected)
        self.create_xp(other_guild, guild_id='guild-2')
        self.create_xp(zero_xp, xp=0)
        self.create_xp(hidden)

        self.assertEqual(
            get_community_member_user_ids(guild_id='guild-1'),
            {selected.id},
        )
        self.assertEqual(
            get_community_member_user_ids(
                user_ids=[other_guild.id, hidden.id],
                guild_id='guild-2',
                visible_only=False,
            ),
            {other_guild.id},
        )

    def test_pending_social_points_follow_applied_baseline_rules(self):
        baseline_at = timezone.now()
        self.create_sync(completed_at=baseline_at)
        partial_pending = self.create_user()
        covered_distribution = self.create_user()
        post_baseline_distribution = self.create_user()
        hidden_pending = self.create_user(visible=False)

        partial_completion = self.create_completion(partial_pending)
        partial_state = partial_completion.discord_xp_state
        partial_state.awarded_amount = 75
        partial_state.save(update_fields=['awarded_amount', 'updated_at'])

        covered_completion = self.create_completion(covered_distribution)
        covered_state = covered_completion.discord_xp_state
        covered_state.status = ContributionDiscordXPState.STATUS_DISTRIBUTED
        covered_state.awarded_amount = covered_completion.points_awarded
        covered_state.distributed_at = baseline_at - timedelta(minutes=1)
        covered_state.save(update_fields=[
            'status', 'awarded_amount', 'distributed_at', 'updated_at',
        ])

        post_completion = self.create_completion(post_baseline_distribution)
        post_state = post_completion.discord_xp_state
        post_state.status = ContributionDiscordXPState.STATUS_DISTRIBUTED
        post_state.awarded_amount = post_completion.points_awarded
        post_state.distributed_at = baseline_at + timedelta(minutes=1)
        post_state.save(update_fields=[
            'status', 'awarded_amount', 'distributed_at', 'updated_at',
        ])
        self.create_completion(hidden_pending)

        self.assertEqual(
            get_community_member_user_ids(),
            {partial_pending.id, post_baseline_distribution.id},
        )
        self.assertEqual(
            get_community_member_user_ids(visible_only=False),
            {partial_pending.id, post_baseline_distribution.id, hidden_pending.id},
        )

    def test_contributions_and_poaps_preserve_eligibility_filters(self):
        contributor = self.create_user()
        link_only = self.create_user()
        poap_member = self.create_user()
        hidden_poap_member = self.create_user(visible=False)
        self.create_contribution(contributor)
        self.create_contribution(link_only, contribution_type=self.link_type)
        PoapClaim.objects.create(
            drop=self.drop,
            user=poap_member,
            claim_method=PoapClaim.CLAIM_ADMIN,
        )
        PoapClaim.objects.create(
            drop=self.drop,
            user=hidden_poap_member,
            claim_method=PoapClaim.CLAIM_ADMIN,
        )

        self.assertEqual(
            get_community_member_user_ids(),
            {contributor.id, poap_member.id},
        )
        self.assertEqual(
            get_community_member_user_ids(user_ids=[link_only.id, poap_member.id]),
            {poap_member.id},
        )

    def test_since_uses_recent_events_and_conditional_creator_activation(self):
        now = timezone.now()
        since = now - timedelta(days=30)
        recent_contributor = self.create_user()
        old_contributor = self.create_user()
        recently_activated = self.create_user()
        creator_only = self.create_user()
        recent_social_member = self.create_user()
        recent_poap_member = self.create_user()
        old_poap_member = self.create_user()

        recent_contribution = self.create_contribution(recent_contributor)
        old_contribution = self.create_contribution(old_contributor)
        activation_contribution = self.create_contribution(recently_activated)
        Contribution.objects.filter(
            id__in=[old_contribution.id, activation_contribution.id],
        ).update(created_at=since - timedelta(days=1))

        Creator.objects.create(user=recently_activated)
        Creator.objects.create(user=creator_only)

        social_completion = self.create_completion(recent_social_member)
        social_state = social_completion.discord_xp_state
        social_state.status = ContributionDiscordXPState.STATUS_DISTRIBUTED
        social_state.awarded_amount = social_completion.points_awarded
        social_state.distributed_at = now - timedelta(minutes=1)
        social_state.save(update_fields=[
            'status', 'awarded_amount', 'distributed_at', 'updated_at',
        ])
        self.create_sync(completed_at=now)

        recent_claim = PoapClaim.objects.create(
            drop=self.drop,
            user=recent_poap_member,
            claim_method=PoapClaim.CLAIM_ADMIN,
        )
        old_claim = PoapClaim.objects.create(
            drop=self.drop,
            user=old_poap_member,
            claim_method=PoapClaim.CLAIM_ADMIN,
        )
        PoapClaim.objects.filter(id=old_claim.id).update(
            created_at=since - timedelta(days=1),
        )

        self.assertGreaterEqual(recent_contribution.created_at, since)
        self.assertGreaterEqual(recent_claim.created_at, since)
        self.assertEqual(
            get_community_member_user_ids(since=since),
            {
                recent_contributor.id,
                recently_activated.id,
                recent_social_member.id,
                recent_poap_member.id,
            },
        )
        self.assertNotIn(
            creator_only.id,
            get_community_member_user_ids(since=since),
        )
