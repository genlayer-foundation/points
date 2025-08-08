from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import render, redirect
from django.urls import path, reverse
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import datetime
from .models import Contribution, ContributionType
from .validator_forms import CreateValidatorForm

User = get_user_model()


class ValidatorAdmin:
    """Custom admin for creating validators with contributions."""
    
    def get_urls(self):
        """Add custom URL for validator creation."""
        return [
            path('create-validator/', self.admin_site.admin_view(self.create_validator_view), name='contributions_create_validator'),
        ]
    
    def create_validator_view(self, request):
        """View for creating a new validator."""
        if request.method == 'POST':
            form = CreateValidatorForm(request.POST)
            if form.is_valid():
                try:
                    user = self._process_validator_creation(form)
                    messages.success(request, f'Validator {user.email} created successfully with contributions.')
                    # Redirect to user detail page
                    return redirect(reverse('admin:users_user_change', args=[user.id]))
                except ValidationError as e:
                    messages.error(request, str(e))
                except Exception as e:
                    messages.error(request, f'Error creating validator: {str(e)}')
        else:
            form = CreateValidatorForm()
        
        # Get contribution types for display
        default_types = ContributionType.objects.filter(is_default=True).order_by('name')
        
        context = {
            'form': form,
            'title': 'Create Validator',
            'default_types': default_types,
            'opts': {'app_label': 'contributions'},
            'has_view_permission': True,
            'has_add_permission': True,
            'has_change_permission': True,
            'has_delete_permission': True,
        }
        
        return render(request, 'admin/contributions/create_validator.html', context)
    
    @transaction.atomic
    def _process_validator_creation(self, form):
        """Process the validator creation with contributions."""
        name = form.cleaned_data['name']
        blockchain_address = form.cleaned_data['blockchain_address']
        contribution_date = form.cleaned_data['contribution_date']
        
        # Look up or create user
        user, created = User.objects.get_or_create(
            blockchain_address=blockchain_address,
            defaults={
                'email': blockchain_address,  # Use address as email initially
                'username': blockchain_address,
                'visible': True,
            }
        )
        
        # Update name if provided (and different)
        if name and user.get_full_name() != name:
            # Split name into first and last
            name_parts = name.split(' ', 1)
            user.first_name = name_parts[0]
            user.last_name = name_parts[1] if len(name_parts) > 1 else ''
            user.save()
        
        # Get selected contributions
        contributions_data = form.get_selected_contributions()
        
        # Convert date to datetime
        contribution_datetime = datetime.combine(contribution_date, datetime.min.time())
        contribution_datetime = timezone.make_aware(contribution_datetime)
        
        # Create contributions
        created_contributions = []
        for contrib_data in contributions_data:
            contribution_type = ContributionType.objects.get(id=contrib_data['contribution_type_id'])
            
            # Check for duplicates
            existing = Contribution.objects.filter(
                user=user,
                contribution_type=contribution_type,
                contribution_date__date=contribution_date
            ).exists()
            
            if existing:
                raise ValidationError(
                    f'Contribution of type "{contribution_type.name}" already exists for user {user.email} on {contribution_date}'
                )
            
            # Create the contribution
            contribution = Contribution.objects.create(
                user=user,
                contribution_type=contribution_type,
                points=contrib_data['points'],
                contribution_date=contribution_datetime,
                notes=f'Created via validator creation on {timezone.now().strftime("%Y-%m-%d %H:%M")}'
            )
            created_contributions.append(contribution)
        
        return user