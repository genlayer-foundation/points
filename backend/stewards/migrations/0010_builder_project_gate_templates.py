"""
Create/update reject templates for Builder Project gate failures.
"""

from django.db import migrations


TEMPLATES = [
    {
        'label': 'Reject: Project Has No Real GenLayer Contract',
        'action': 'reject',
        'text': (
            "Thanks for your submission. This project does not qualify as a "
            "Builder Project because we could not verify a real GenLayer "
            "contract as part of the work. Builder Project submissions need "
            "to include a working GenLayer contract or intelligent contract "
            "implementation with evidence that it is used by the project."
        ),
    },
    {
        'label': 'Reject: GenLayer Is Branding Only',
        'action': 'reject',
        'text': (
            "Thanks for your submission. This project does not qualify as a "
            "Builder Project because GenLayer appears to be used only as "
            "branding or description, without the project actually calling or "
            "using a GenLayer contract. Please resubmit if you can provide "
            "evidence of real GenLayer contract integration."
        ),
    },
    {
        'label': 'Reject: Project Does Not Build',
        'action': 'reject',
        'text': (
            "Thanks for your submission. We could not accept this Builder "
            "Project because the repository does not build or the project "
            "does not work from the submitted evidence. Please resubmit with "
            "a working repository, setup instructions, and any deployment or "
            "demo evidence needed to verify it."
        ),
    },
    {
        'label': 'Reject: Empty Fork or Boilerplate',
        'action': 'reject',
        'text': (
            "Thanks for your submission. This project does not qualify as a "
            "Builder Project because it appears to be an empty fork, a plain "
            "boilerplate project, or a renamed example without enough original "
            "implementation. Please resubmit once the project includes "
            "substantial original work."
        ),
    },
]


def create_templates(apps, schema_editor):
    ReviewTemplate = apps.get_model('stewards', 'ReviewTemplate')
    for template in TEMPLATES:
        ReviewTemplate.objects.update_or_create(
            label=template['label'],
            defaults={
                'text': template['text'],
                'action': template['action'],
            },
        )


def remove_templates(apps, schema_editor):
    ReviewTemplate = apps.get_model('stewards', 'ReviewTemplate')
    for template in TEMPLATES:
        ReviewTemplate.objects.filter(label=template['label']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('stewards', '0009_tier1_review_templates'),
    ]

    operations = [
        migrations.RunPython(create_templates, remove_templates),
    ]
