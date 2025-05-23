from django.db import migrations, models


def fix_duplicate_addresses(apps, schema_editor):
    """
    Make all duplicate addresses unique by appending the id to them.
    Also handle null and empty addresses.
    """
    User = apps.get_model('users', 'User')
    
    # First, handle null addresses
    users_with_null_address = User.objects.filter(address__isnull=True)
    for user in users_with_null_address:
        user.address = f'null_{user.id}'
        user.save()
    
    # Then, handle empty string addresses
    users_with_empty_address = User.objects.filter(address='')
    for user in users_with_empty_address:
        user.address = f'empty_{user.id}'
        user.save()
    
    # Find all addresses that appear more than once
    duplicates = User.objects.values('address').annotate(
        count=models.Count('id')
    ).filter(count__gt=1).exclude(address__isnull=True).exclude(address='')
    
    # For each duplicate address
    for dup in duplicates:
        address = dup['address']
        # Get all users with this address except the first one
        users_with_dup = User.objects.filter(address=address)[1:]
        
        # Update each duplicate to make it unique
        for i, user in enumerate(users_with_dup):
            user.address = f"{address}_{user.id}"
            user.save()


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_update_address_field'),
    ]

    operations = [
        # First run a data migration to fix any duplicates
        migrations.RunPython(fix_duplicate_addresses, migrations.RunPython.noop),
        
        # Then add the constraint
        migrations.AddConstraint(
            model_name='user',
            constraint=models.UniqueConstraint(condition=models.Q(('address__isnull', False)), fields=('address',), name='unique_address_when_not_null'),
        ),
    ]