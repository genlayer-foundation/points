from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import ContributionType, Contribution
import re

User = get_user_model()


class CreateValidatorForm(forms.Form):
    """Form for creating a validator with contributions."""
    
    name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'class': 'vTextField'}),
        help_text="Validator's name"
    )
    
    address = forms.CharField(
        max_length=42,
        required=True,
        widget=forms.TextInput(attrs={'class': 'vTextField'}),
        help_text="Ethereum address (0x...)",
        label="Blockchain Address"
    )
    
    contribution_date = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'vDateField'}),
        help_text="Date to assign contributions"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Get all default contribution types, sorted alphabetically
        default_types = ContributionType.objects.filter(is_default=True).order_by('name')
        
        # Add fields for each default contribution type
        for contrib_type in default_types:
            # Checkbox field
            self.fields[f'include_{contrib_type.id}'] = forms.BooleanField(
                required=False,
                initial=True,
                label=contrib_type.name,
                widget=forms.CheckboxInput(attrs={'class': 'contribution-checkbox'})
            )
            
            # Points field with min/max display
            self.fields[f'points_{contrib_type.id}'] = forms.IntegerField(
                required=False,
                initial=contrib_type.min_points,
                min_value=contrib_type.min_points,
                max_value=contrib_type.max_points,
                widget=forms.NumberInput(attrs={
                    'class': 'vIntegerField contribution-points',
                    'data-contrib-id': contrib_type.id,
                    'style': 'width: 100px;'
                }),
                help_text=f"Min: {contrib_type.min_points}, Max: {contrib_type.max_points}"
            )
    
    def clean_address(self):
        """Validate and normalize the blockchain address."""
        address = self.cleaned_data['address']
        
        # Basic Ethereum address validation
        if not re.match(r'^0x[a-fA-F0-9]{40}$', address):
            raise ValidationError('Invalid Ethereum address format. Must be 0x followed by 40 hexadecimal characters.')
        
        # Normalize to lowercase
        return address.lower()
    
    def clean_contribution_date(self):
        """Validate the contribution date is not in the future."""
        date = self.cleaned_data['contribution_date']
        
        if date > timezone.now().date():
            raise ValidationError('Contribution date cannot be in the future.')
        
        return date
    
    def clean(self):
        """Validate the form data."""
        cleaned_data = super().clean()
        
        # Check that at least one contribution is selected
        has_contribution = False
        for field_name in self.fields:
            if field_name.startswith('include_') and cleaned_data.get(field_name):
                has_contribution = True
                # Check that points are provided for included contributions
                contrib_id = field_name.replace('include_', '')
                points_field = f'points_{contrib_id}'
                if points_field not in cleaned_data or cleaned_data[points_field] is None:
                    self.add_error(points_field, 'Points are required for included contributions.')
        
        if not has_contribution:
            raise ValidationError('At least one contribution type must be selected.')
        
        return cleaned_data
    
    def get_selected_contributions(self):
        """Get list of selected contribution types with their points."""
        if not self.is_valid():
            return []
        
        contributions = []
        for field_name in self.fields:
            if field_name.startswith('include_') and self.cleaned_data.get(field_name):
                contrib_id = int(field_name.replace('include_', ''))
                points = self.cleaned_data.get(f'points_{contrib_id}')
                if points is not None:
                    contributions.append({
                        'contribution_type_id': contrib_id,
                        'points': points
                    })
        
        return contributions