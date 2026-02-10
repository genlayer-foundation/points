from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('contributions', '0031_rename_suggested_points_to_proposed_points'),
    ]

    operations = [
        migrations.AddField(
            model_name='submittedcontribution',
            name='proposed_action',
            field=models.CharField(blank=True, choices=[('accept', 'Accept'), ('reject', 'Reject'), ('more_info', 'More Info')], help_text='Proposed review action', max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='submittedcontribution',
            name='proposed_contribution_type',
            field=models.ForeignKey(blank=True, help_text='Proposed contribution type for acceptance', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='proposed_submissions', to='contributions.contributiontype'),
        ),
        migrations.AddField(
            model_name='submittedcontribution',
            name='proposed_user',
            field=models.ForeignKey(blank=True, help_text='Proposed user to assign the contribution to', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='proposed_contributions', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='submittedcontribution',
            name='proposed_staff_reply',
            field=models.TextField(blank=True, default='', help_text='Proposed staff reply message'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='submittedcontribution',
            name='proposed_create_highlight',
            field=models.BooleanField(default=False, help_text='Whether to create a highlight for the contribution'),
        ),
        migrations.AddField(
            model_name='submittedcontribution',
            name='proposed_highlight_title',
            field=models.CharField(blank=True, default='', help_text='Proposed highlight title', max_length=200),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='submittedcontribution',
            name='proposed_highlight_description',
            field=models.TextField(blank=True, default='', help_text='Proposed highlight description'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='submittedcontribution',
            name='proposed_by',
            field=models.ForeignKey(blank=True, help_text='Steward who made the proposal', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='submission_proposals', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='submittedcontribution',
            name='proposed_at',
            field=models.DateTimeField(blank=True, help_text='When the proposal was made', null=True),
        ),
        migrations.CreateModel(
            name='SubmissionNote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('message', models.TextField()),
                ('is_proposal', models.BooleanField(default=False, help_text='True for auto-generated proposal notes')),
                ('submitted_contribution', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='internal_notes', to='contributions.submittedcontribution')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='submission_notes', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),
    ]
