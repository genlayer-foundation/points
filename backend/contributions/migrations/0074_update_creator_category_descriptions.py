from django.db import migrations


DESCRIPTIONS = {
    'community': 'Creators who contribute to and grow the ecosystem',
    'steward': 'Stewards who support and grow the ecosystem',
}


def apply(apps, schema_editor):
    Category = apps.get_model('contributions', 'Category')
    for slug, description in DESCRIPTIONS.items():
        Category.objects.filter(slug=slug).update(description=description)


def reverse(apps, schema_editor):
    Category = apps.get_model('contributions', 'Category')
    Category.objects.filter(slug='community').update(
        description='Community members who contribute to the ecosystem'
    )
    Category.objects.filter(slug='steward').update(
        description='Community members who support and grow the ecosystem'
    )


class Migration(migrations.Migration):

    dependencies = [
        ('contributions', '0073_create_community_link_github'),
    ]

    operations = [
        migrations.RunPython(apply, reverse),
    ]
