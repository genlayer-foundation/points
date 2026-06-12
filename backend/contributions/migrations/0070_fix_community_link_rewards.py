from django.db import migrations


LINK_REWARD_SLUGS = ('community-link-x', 'community-link-discord')
OLD_REWARD = 20
NEW_REWARD = 500


def recalculate_link_contributions(Contribution, from_points, to_points):
    contributions = list(Contribution.objects.filter(
        contribution_type__slug__in=LINK_REWARD_SLUGS,
        points=from_points,
    ))
    for contribution in contributions:
        multiplier = float(contribution.multiplier_at_creation or 1)
        contribution.points = to_points
        contribution.frozen_global_points = round(to_points * multiplier)
    if contributions:
        Contribution.objects.bulk_update(
            contributions,
            ['points', 'frozen_global_points'],
            batch_size=1000,
        )


def refresh_discord_xp_states(ContributionDiscordXPState):
    states = list(ContributionDiscordXPState.objects.filter(
        contribution__contribution_type__slug__in=LINK_REWARD_SLUGS,
    ).select_related('contribution'))
    states_to_update = []
    for state in states:
        target = int(state.contribution.frozen_global_points or 0)
        awarded = int(state.awarded_amount or 0)
        next_status = state.status

        if awarded > target:
            next_status = 'needs_review'
        elif awarded == target:
            next_status = 'distributed'
        elif state.status != 'needs_review':
            next_status = 'pending'

        if next_status != state.status:
            state.status = next_status
            states_to_update.append(state)

    if states_to_update:
        ContributionDiscordXPState.objects.bulk_update(
            states_to_update,
            ['status'],
            batch_size=1000,
        )


def apply_reward_fix(apps, schema_editor):
    ContributionType = apps.get_model('contributions', 'ContributionType')
    Contribution = apps.get_model('contributions', 'Contribution')
    ContributionDiscordXPState = apps.get_model('contributions', 'ContributionDiscordXPState')

    ContributionType.objects.filter(slug__in=LINK_REWARD_SLUGS).update(
        min_points=NEW_REWARD,
        max_points=NEW_REWARD,
    )

    recalculate_link_contributions(Contribution, OLD_REWARD, NEW_REWARD)
    refresh_discord_xp_states(ContributionDiscordXPState)


def reverse_reward_fix(apps, schema_editor):
    ContributionType = apps.get_model('contributions', 'ContributionType')
    Contribution = apps.get_model('contributions', 'Contribution')
    ContributionDiscordXPState = apps.get_model('contributions', 'ContributionDiscordXPState')

    ContributionType.objects.filter(slug__in=LINK_REWARD_SLUGS).update(
        min_points=OLD_REWARD,
        max_points=OLD_REWARD,
    )

    recalculate_link_contributions(Contribution, NEW_REWARD, OLD_REWARD)
    refresh_discord_xp_states(ContributionDiscordXPState)


class Migration(migrations.Migration):

    dependencies = [
        ('contributions', '0069_alter_contributiondiscordxpstate_options_and_more'),
    ]

    operations = [
        migrations.RunPython(apply_reward_fix, reverse_reward_fix),
    ]
