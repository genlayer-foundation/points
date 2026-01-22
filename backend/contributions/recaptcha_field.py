"""
Custom reCAPTCHA field for Django REST Framework serializers.

This module provides a serializer field that validates Google reCAPTCHA v2 tokens
submitted from the frontend.
"""

from rest_framework import serializers
from django_recaptcha.fields import ReCaptchaField as DjangoReCaptchaField
from django_recaptcha.widgets import ReCaptchaV2Checkbox

from tally.middleware.tracing import trace_external


class ReCaptchaField(serializers.Field):
    """
    A DRF serializer field for validating Google reCAPTCHA v2 responses.

    This field accepts a reCAPTCHA token from the frontend and validates it
    against Google's reCAPTCHA API using the django-recaptcha library.

    Usage in serializers:
        recaptcha = ReCaptchaField(write_only=True, required=True)

    The field expects a string token value from the frontend's grecaptcha.getResponse().
    """

    default_error_messages = {
        'required': 'Please complete the reCAPTCHA verification.',
        'invalid': 'Invalid reCAPTCHA. Please try again.',
        'network_error': 'Unable to verify reCAPTCHA. Please try again.',
    }

    def __init__(self, **kwargs):
        # Force write_only since we don't want to return this in responses
        kwargs['write_only'] = True
        super().__init__(**kwargs)
        # Create Django form field instance for validation
        self.django_field = DjangoReCaptchaField(widget=ReCaptchaV2Checkbox())

    def to_internal_value(self, data):
        """
        Validate the reCAPTCHA token.

        Args:
            data: The reCAPTCHA response token from the frontend

        Returns:
            str: The validated token (not used, but returned for consistency)

        Raises:
            ValidationError: If the reCAPTCHA validation fails
        """
        if not data:
            self.fail('required')

        try:
            # Use django-recaptcha's validation
            # The field expects the token value directly
            with trace_external('recaptcha', 'verify'):
                cleaned_value = self.django_field.clean(data)
            return cleaned_value
        except Exception as e:
            # Handle various validation errors
            error_message = str(e).lower()
            if 'required' in error_message or 'blank' in error_message:
                self.fail('required')
            elif 'network' in error_message or 'connection' in error_message:
                self.fail('network_error')
            else:
                self.fail('invalid')

    def to_representation(self, value):
        """
        This field is write-only, so we never need to serialize it.
        """
        return None
