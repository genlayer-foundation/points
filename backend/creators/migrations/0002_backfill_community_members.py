from django.db import migrations


def backfill_community_members(apps, schema_editor):
    # Creator rows are granted only through the community journey completion
    # endpoint. Keep this historical migration as a no-op for fresh databases.
    return


class Migration(migrations.Migration):

    dependencies = [
        ('creators', '0001_initial'),
        ('contributions', '0061_featuredcontent_hero_placements'),
        ('poaps', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(backfill_community_members, migrations.RunPython.noop),
    ]
