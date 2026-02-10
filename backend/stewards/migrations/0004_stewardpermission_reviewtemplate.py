from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('stewards', '0003_workinggroup_icon_workinggroup_description'),
        ('contributions', '0031_rename_suggested_points_to_proposed_points'),
    ]

    operations = [
        migrations.CreateModel(
            name='StewardPermission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('action', models.CharField(choices=[('propose', 'Propose'), ('accept', 'Accept'), ('reject', 'Reject'), ('request_more_info', 'Request More Info')], max_length=20)),
                ('contribution_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='steward_permissions', to='contributions.contributiontype')),
                ('steward', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='permissions', to='stewards.steward')),
            ],
            options={
                'ordering': ['steward', 'contribution_type', 'action'],
                'unique_together': {('steward', 'contribution_type', 'action')},
            },
        ),
        migrations.CreateModel(
            name='ReviewTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('label', models.CharField(help_text="Short label, e.g. 'Insufficient evidence'", max_length=100)),
                ('text', models.TextField(help_text='Full template text to insert into reply fields')),
            ],
            options={
                'ordering': ['label'],
            },
        ),
    ]
