from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('contributions', '0067_contributiontype_rubric_extra_points'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('stewards', '0010_builder_project_gate_templates'),
    ]

    operations = [
        migrations.AddField(
            model_name='steward',
            name='can_review_feature_candidates',
            field=models.BooleanField(default=False, help_text='Can access the blind reviewer scoring view for interesting submissions.'),
        ),
        migrations.CreateModel(
            name='FeatureCandidateScore',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('score', models.PositiveSmallIntegerField(help_text='0 = not interesting, 1 = weak, 2 = good, 3 = strong.', validators=[MinValueValidator(0), MaxValueValidator(3)])),
                ('steward', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='feature_candidate_scores', to='stewards.steward')),
                ('submission', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='feature_candidate_scores', to='contributions.submittedcontribution')),
            ],
            options={
                'ordering': ['submission', 'steward'],
                'indexes': [
                    models.Index(fields=['submission', 'score'], name='stewards_fe_submiss_99a39d_idx'),
                    models.Index(fields=['steward', 'updated_at'], name='stewards_fe_steward_63fd7c_idx'),
                ],
                'constraints': [
                    models.CheckConstraint(condition=models.Q(('score__gte', 0), ('score__lte', 3)), name='feature_candidate_score_score_range_0_3'),
                ],
                'unique_together': {('submission', 'steward')},
            },
        ),
    ]
