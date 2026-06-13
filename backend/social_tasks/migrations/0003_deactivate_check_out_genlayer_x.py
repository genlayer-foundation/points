from django.db import migrations


TASK_SLUG = 'check-out-genlayer-on-x'


def deactivate_task(apps, schema_editor):
    SocialTask = apps.get_model('social_tasks', 'SocialTask')
    SocialTask.objects.filter(slug=TASK_SLUG).update(is_active=False)


def reactivate_task(apps, schema_editor):
    SocialTask = apps.get_model('social_tasks', 'SocialTask')
    SocialTask.objects.filter(slug=TASK_SLUG).update(is_active=True)


class Migration(migrations.Migration):

    dependencies = [
        ('social_tasks', '0002_alter_socialtask_points'),
    ]

    operations = [
        migrations.RunPython(deactivate_task, reactivate_task),
    ]
