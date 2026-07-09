import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contributions', '0076_submission_proposal_review_status'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ReviewProposal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('source', models.CharField(choices=[('ai', 'AI'), ('human', 'Human')], db_index=True, max_length=20)),
                ('service_account_name', models.CharField(blank=True, default='', max_length=255)),
                ('action', models.CharField(choices=[('accept', 'Accept'), ('reject', 'Reject'), ('more_info', 'More Info')], max_length=20)),
                ('points', models.PositiveIntegerField(blank=True, null=True)),
                ('staff_reply', models.TextField(blank=True)),
                ('confidence', models.CharField(blank=True, choices=[('high', 'High'), ('medium', 'Medium'), ('low', 'Low')], max_length=10, null=True)),
                ('gate_failures', models.JSONField(blank=True, default=list)),
                ('sections', models.JSONField(blank=True, default=dict)),
                ('extras', models.JSONField(blank=True, default=list)),
                ('overall_reason', models.TextField(blank=True)),
                ('synthesis', models.TextField(blank=True)),
                ('questioned_at', models.DateTimeField(blank=True, null=True)),
                ('question_feedback', models.TextField(blank=True)),
                ('decided_at', models.DateTimeField(blank=True, null=True)),
                ('final_action', models.CharField(blank=True, choices=[('accept', 'Accept'), ('reject', 'Reject'), ('more_info', 'More Info')], max_length=20, null=True)),
                ('final_points', models.PositiveIntegerField(blank=True, null=True)),
                ('final_sections', models.JSONField(blank=True, default=dict)),
                ('reward_points', models.PositiveIntegerField(blank=True, null=True)),
                ('decided_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='decided_review_proposal_snapshots', to=settings.AUTH_USER_MODEL)),
                ('proposer', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='review_proposal_snapshots', to=settings.AUTH_USER_MODEL)),
                ('questioned_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='questioned_review_proposal_snapshots', to=settings.AUTH_USER_MODEL)),
                ('reward_contribution', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='review_reward_proposals', to='contributions.contribution')),
                ('submitted_contribution', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='review_proposals', to='contributions.submittedcontribution')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='reviewproposal',
            index=models.Index(fields=['submitted_contribution', 'created_at'], name='contributio_submitt_498b9f_idx'),
        ),
        migrations.AddIndex(
            model_name='reviewproposal',
            index=models.Index(fields=['proposer', 'decided_at'], name='contributio_propose_a6b7ae_idx'),
        ),
    ]
