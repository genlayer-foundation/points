from django.db import migrations


def create_community_category(apps, schema_editor):
    Category = apps.get_model('contributions', 'Category')
    Category.objects.create(
        name='Community',
        slug='community',
        description='Community members who contribute to the ecosystem',
        profile_model=''
    )


def reverse_community_category(apps, schema_editor):
    Category = apps.get_model('contributions', 'Category')
    Category.objects.filter(slug='community').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('contributions', '0044_add_proposed_confidence_and_template'),
    ]

    operations = [
        migrations.RunPython(create_community_category, reverse_community_category),
    ]
