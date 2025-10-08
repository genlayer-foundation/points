import string
import secrets
from django.db import migrations


def generate_referral_codes_for_existing_users(apps, schema_editor):
    User = apps.get_model('users', 'User')
    users_without_codes = User.objects.filter(referral_code__isnull=True) | User.objects.filter(referral_code='')
    
    characters = string.ascii_uppercase + string.digits
    
    for user in users_without_codes:
        # Generate unique code
        for _ in range(100):
            code = ''.join(secrets.choice(characters) for _ in range(8))
            if not User.objects.filter(referral_code=code).exists():
                user.referral_code = code
                user.save(update_fields=['referral_code'])
                break


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0014_add_referral_system'),
    ]

    operations = [
        migrations.RunPython(
            generate_referral_codes_for_existing_users
        ),
    ]
