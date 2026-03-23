"""
Add a 'reject' template for non-technical community content submitted
under Builder categories. Directs users to Discord for now.
"""

from django.db import migrations


def create_template(apps, schema_editor):
    ReviewTemplate = apps.get_model('stewards', 'ReviewTemplate')
    ReviewTemplate.objects.create(
        label='Not for Builders: Community Content',
        text=(
            "Thanks for sharing this! However, this type of content \u2014 social media "
            "posts, general awareness tweets, and non-technical overviews \u2014 doesn't "
            "qualify for the Builder category, which requires in-depth technical work "
            "like tutorials with code, detailed guides, working projects, or original "
            "research. To earn XP for community content like this, please submit it "
            "through our Discord community instead. A dedicated Community section on "
            "the platform is coming soon! In the meantime, head over to Discord to "
            "submit your contribution and get rewarded for it."
        ),
        action='reject',
    )


def remove_template(apps, schema_editor):
    ReviewTemplate = apps.get_model('stewards', 'ReviewTemplate')
    ReviewTemplate.objects.filter(label='Not for Builders: Community Content').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('stewards', '0007_add_action_to_reviewtemplate'),
    ]

    operations = [
        migrations.RunPython(create_template, remove_template),
    ]
