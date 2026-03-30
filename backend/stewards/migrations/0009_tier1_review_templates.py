"""
Create/update the three ReviewTemplate records used by Tier 1 deterministic rules.
"""

from django.db import migrations


TEMPLATES = [
    {
        'label': 'Reject: No Evidence',
        'action': 'reject',
        'text': (
            "Thanks for your submission! Unfortunately, we weren't able to find "
            "a valid evidence URL attached to it. To get your contribution reviewed, "
            "please resubmit with a link to your work \u2014 for example, a GitHub repo, "
            "blog post, or deployed app. If you feel like this submission was "
            "wrongfully rejected, please let us know on Discord."
        ),
    },
    {
        'label': 'Reject: Duplicate Submission',
        'action': 'reject',
        'text': (
            "Thanks for your submission! However, the evidence URL provided has "
            "already been submitted as part of another contribution. Each submission "
            "needs to include unique evidence of original work. If you feel like this "
            "submission was wrongfully rejected, please let us know on Discord."
        ),
    },
    {
        'label': 'Reject: Invalid Evidence URL',
        'action': 'reject',
        'text': (
            "Thanks for your submission! Unfortunately, the URL provided doesn't "
            "point to valid evidence of your work. We need a direct link to what "
            "you've built or created \u2014 such as a GitHub repo, a blog post, or a "
            "live project. Please resubmit with a link that showcases your "
            "contribution. If you feel like this submission was wrongfully rejected, "
            "please let us know on Discord."
        ),
    },
]


def create_templates(apps, schema_editor):
    ReviewTemplate = apps.get_model('stewards', 'ReviewTemplate')
    for t in TEMPLATES:
        ReviewTemplate.objects.update_or_create(
            label=t['label'],
            defaults={'text': t['text'], 'action': t['action']},
        )


def remove_templates(apps, schema_editor):
    ReviewTemplate = apps.get_model('stewards', 'ReviewTemplate')
    for t in TEMPLATES:
        ReviewTemplate.objects.filter(label=t['label'], text=t['text']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('stewards', '0008_add_wrong_category_template'),
    ]

    operations = [
        migrations.RunPython(create_templates, remove_templates),
    ]
