from rest_framework import serializers

from .eligibility import evaluate_task_eligibility
from .models import SocialTask
from .verifiers import required_connection_for, requires_verification_for


class SocialTaskSerializer(serializers.ModelSerializer):
    """Public-facing task serializer.

    `status` is annotated by the view (`active` or `completed` for the
    request user). `points_awarded` and `completed_at` are populated from
    the user's completion if any.

    The internal `verification_type` slug is deliberately NOT exposed; the
    frontend stays decoupled through two derived flags instead:
    - `requires_verification`: "open-and-credit" vs "open-then-verify" UX.
    - `required_connection`: which social account ('twitter'/'discord'/...)
      must be linked before verification, or null.
    """

    category_slug = serializers.CharField(source='category.slug', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    status = serializers.SerializerMethodField()
    completed_at = serializers.SerializerMethodField()
    points_awarded = serializers.SerializerMethodField()
    requires_verification = serializers.SerializerMethodField()
    required_connection = serializers.SerializerMethodField()
    can_complete = serializers.SerializerMethodField()
    eligibility = serializers.SerializerMethodField()

    class Meta:
        model = SocialTask
        fields = [
            'slug',
            'name',
            'description',
            'points',
            'platform',
            'requires_verification',
            'required_connection',
            'action_url',
            'cta_text',
            'can_complete',
            'eligibility',
            'category_slug',
            'category_name',
            'order',
            'starts_at',
            'ends_at',
            'status',
            'completed_at',
            'points_awarded',
        ]

    def get_status(self, obj):
        completion = self._completion_for(obj)
        if completion:
            return 'completed'
        return 'active' if self._eligibility_for(obj).eligible else 'locked'

    def get_completed_at(self, obj):
        completion = self._completion_for(obj)
        return completion.completed_at if completion else None

    def get_points_awarded(self, obj):
        completion = self._completion_for(obj)
        return completion.points_awarded if completion else None

    def get_requires_verification(self, obj):
        return requires_verification_for(obj.verification_type)

    def get_required_connection(self, obj):
        return required_connection_for(obj.verification_type)

    def get_can_complete(self, obj):
        return self.get_status(obj) == 'active'

    def get_eligibility(self, obj):
        result = self._eligibility_for(obj)
        return {
            'eligible': result.eligible,
            'message': result.message,
            **(result.details or {}),
        }

    def _completion_for(self, obj):
        """Pull the prefetched completion for the request user (if any).

        The view annotates each task with `_user_completion` to keep this O(1).
        Falls back to a query when no prefetch is present (admin / test usage).
        """
        from .models import SocialTaskCompletion

        cached = getattr(obj, '_user_completion', None)
        if cached is not None:
            return cached if cached is not False else None
        request = self.context.get('request') if self.context else None
        if request is None or not request.user.is_authenticated:
            return None
        return SocialTaskCompletion.objects.filter(user=request.user, task=obj).first()

    def _eligibility_for(self, obj):
        cached = getattr(obj, '_eligibility_result', None)
        if cached is not None:
            return cached
        request = self.context.get('request') if self.context else None
        user = request.user if request and request.user.is_authenticated else None
        obj._eligibility_result = evaluate_task_eligibility(obj, user)
        return obj._eligibility_result
