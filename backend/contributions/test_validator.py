"""
Quick test script for validator creation functionality.
Run with: python manage.py shell < contributions/test_validator.py
"""

from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, date
from contributions.models import ContributionType, Contribution
from contributions.validator_forms import CreateValidatorForm
from leaderboard.models import GlobalLeaderboardMultiplier

User = get_user_model()

# Create test data
print("Setting up test data...")

# Create a contribution type with is_default=True
contrib_type, created = ContributionType.objects.get_or_create(
    name="Test Validator Contribution",
    defaults={
        'description': 'Test contribution for validators',
        'min_points': 10,
        'max_points': 100,
        'is_default': True
    }
)
if not created:
    contrib_type.is_default = True
    contrib_type.save()

print(f"ContributionType created/updated: {contrib_type.name}, is_default={contrib_type.is_default}")

# Ensure there's a multiplier for this contribution type
multiplier, created = GlobalLeaderboardMultiplier.objects.get_or_create(
    contribution_type=contrib_type,
    defaults={
        'multiplier_value': 1.5,
        'valid_from': timezone.now(),
        'description': 'Test multiplier'
    }
)
print(f"Multiplier {'created' if created else 'exists'}: {multiplier.multiplier_value}x")

# Test the form
print("\nTesting CreateValidatorForm...")

# Prepare form data
form_data = {
    'name': 'Test Validator',
    'blockchain_address': '0x1234567890123456789012345678901234567890',
    'contribution_date': date.today(),
    f'include_{contrib_type.id}': True,
    f'points_{contrib_type.id}': 50,
}

# Create and validate form
form = CreateValidatorForm(data=form_data)

if form.is_valid():
    print("✓ Form is valid")
    print(f"  - Name: {form.cleaned_data['name']}")
    print(f"  - Address: {form.cleaned_data['blockchain_address']}")
    print(f"  - Date: {form.cleaned_data['contribution_date']}")
    
    contributions = form.get_selected_contributions()
    print(f"  - Selected contributions: {contributions}")
else:
    print("✗ Form has errors:")
    for field, errors in form.errors.items():
        print(f"  - {field}: {errors}")

# Clean up test data (optional)
print("\nTest complete. Test data remains in database for manual inspection.")
print(f"You can check the admin at /admin/contributions/contributiontype/ to see the is_default field.")
print(f"You can test the validator creation at /admin/contributions/contribution/create-validator/")