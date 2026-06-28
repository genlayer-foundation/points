from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('social_tasks', '0004_seed_builder_star_task'),
    ]

    operations = [
        migrations.AddField(
            model_name='socialtask',
            name='eligibility_requirements',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text=(
                    'Optional completion gate. Examples: '
                    '{"type":"accepted_submittable_contribution","category":"task","minimum":1} '
                    'or {"any":[{"type":"community_points","minimum":100},'
                    '{"type":"accepted_submittable_contribution","category":"task","minimum":1}]}. '
                    'Use category "task" to target this task category.'
                ),
            ),
        ),
    ]
