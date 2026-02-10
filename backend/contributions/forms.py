from django import forms
from django.utils import timezone
from .models import SubmittedContribution, Contribution, Evidence, ContributionType
from leaderboard.models import GlobalLeaderboardMultiplier


class SubmissionReviewForm(forms.ModelForm):
    """Form for staff to review submitted contributions."""
    points = forms.IntegerField(
        required=False,
        min_value=0,
        help_text="Required when accepting the submission",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'style': 'width: 150px;'})
    )
    
    class Meta:
        model = SubmittedContribution
        fields = ['contribution_type', 'contribution_date', 'notes', 'state', 'staff_reply']
        widgets = {
            'contribution_type': forms.Select(attrs={'class': 'form-control'}),
            'contribution_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'state': forms.Select(attrs={'class': 'form-control'}),
            'staff_reply': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }
    
    def __init__(self, *args, **kwargs):
        self.request_user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Add help text for state field
        self.fields['state'].help_text = "Select action to take on this submission"
        
        # Pre-populate points if proposed_points exists
        if self.instance and self.instance.proposed_points:
            self.initial['points'] = self.instance.proposed_points
            self.fields['points'].help_text = f"Suggested: {self.instance.proposed_points} points (auto-calculated)"
        
    def clean(self):
        cleaned_data = super().clean()
        state = cleaned_data.get('state')
        points = cleaned_data.get('points')
        staff_reply = cleaned_data.get('staff_reply')
        
        # Validate points are provided when accepting
        if state == 'accepted':
            if not points:
                raise forms.ValidationError({
                    'points': 'Points are required when accepting a submission.'
                })
            
            # Validate points are within contribution type limits
            contribution_type = self.instance.contribution_type
            if points < contribution_type.min_points or points > contribution_type.max_points:
                raise forms.ValidationError({
                    'points': f'Points must be between {contribution_type.min_points} and {contribution_type.max_points} for {contribution_type.name}.'
                })
        
        # Validate staff reply is provided for rejection or more info
        if state in ['rejected', 'more_info_needed'] and not staff_reply:
            raise forms.ValidationError({
                'staff_reply': f'Staff reply is required when {"rejecting" if state == "rejected" else "requesting more information for"} a submission.'
            })
        
        return cleaned_data
    
    def save(self, commit=True):
        """Save the form and create a Contribution if accepted."""
        submission = super().save(commit=False)
        
        # Update review fields
        if self.request_user:
            submission.reviewed_by = self.request_user
            submission.reviewed_at = timezone.now()
        
        if submission.state == 'accepted' and not submission.converted_contribution:
            # Create the actual contribution
            points = self.cleaned_data['points']
            contribution = Contribution.objects.create(
                user=submission.user,
                contribution_type=submission.contribution_type,  # This now uses the potentially updated type
                points=points,
                contribution_date=submission.contribution_date,
                notes=submission.notes
            )
            submission.converted_contribution = contribution
            
            # Copy evidence items
            for evidence in submission.evidence_items.all():
                Evidence.objects.create(
                    contribution=contribution,
                    description=evidence.description,
                    url=evidence.url,
                    file=evidence.file
                )
        
        if commit:
            submission.save()
        
        return submission