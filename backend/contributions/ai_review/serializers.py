from rest_framework import serializers

from contributions.models import Evidence, SubmissionNote, SubmittedContribution
from stewards.models import ReviewTemplate


class AIReviewEvidenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Evidence
        fields = ['id', 'url', 'description']
        read_only_fields = fields


class LightAIReviewSubmissionSerializer(serializers.ModelSerializer):
    """Light serializer for list views — no nested queries."""

    contribution_type_name = serializers.CharField(
        source='contribution_type.name', read_only=True,
    )
    category_name = serializers.SerializerMethodField()
    has_proposal = serializers.SerializerMethodField()

    class Meta:
        model = SubmittedContribution
        fields = [
            'id',
            'contribution_type',
            'contribution_type_name',
            'category_name',
            'title',
            'notes',
            'state',
            'has_proposal',
            'created_at',
        ]
        read_only_fields = fields

    def get_category_name(self, obj):
        if obj.contribution_type and obj.contribution_type.category:
            return obj.contribution_type.category.name
        return None

    def get_has_proposal(self, obj):
        return obj.proposed_action is not None


class AIReviewSubmissionSerializer(serializers.ModelSerializer):
    """Full serializer for detail views — includes evidence and user history."""

    contribution_type_name = serializers.CharField(
        source='contribution_type.name', read_only=True,
    )
    contribution_type_slug = serializers.CharField(
        source='contribution_type.slug', read_only=True,
    )
    category_name = serializers.SerializerMethodField()
    min_points = serializers.IntegerField(
        source='contribution_type.min_points', read_only=True,
    )
    max_points = serializers.IntegerField(
        source='contribution_type.max_points', read_only=True,
    )
    evidence_items = AIReviewEvidenceSerializer(many=True, read_only=True)
    user_history = serializers.SerializerMethodField()
    has_proposal = serializers.SerializerMethodField()
    proposed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = SubmittedContribution
        fields = [
            'id',
            'contribution_type',
            'contribution_type_name',
            'contribution_type_slug',
            'category_name',
            'min_points',
            'max_points',
            'title',
            'notes',
            'state',
            'evidence_items',
            'user_history',
            'has_proposal',
            'proposed_action',
            'proposed_points',
            'proposed_staff_reply',
            'proposed_confidence',
            'proposed_template',
            'proposed_by_name',
            'proposed_at',
            'created_at',
        ]
        read_only_fields = fields

    def get_category_name(self, obj):
        if obj.contribution_type and obj.contribution_type.category:
            return obj.contribution_type.category.name
        return None

    def get_user_history(self, obj):
        from django.db.models import Count, Q
        stats = (
            SubmittedContribution.objects
            .filter(user=obj.user)
            .aggregate(
                accepted_count=Count('id', filter=Q(state='accepted')),
                rejected_count=Count('id', filter=Q(state='rejected')),
                pending_count=Count('id', filter=Q(state='pending')),
            )
        )
        return stats

    def get_has_proposal(self, obj):
        return obj.proposed_action is not None

    def get_proposed_by_name(self, obj):
        if obj.proposed_by:
            return obj.proposed_by.name or str(obj.proposed_by.id)
        return None


class AIReviewNoteSerializer(serializers.ModelSerializer):
    """Serializer for internal notes on reviewed submissions."""

    class Meta:
        model = SubmissionNote
        fields = ['message', 'is_proposal', 'data', 'created_at']
        read_only_fields = fields


class AIReviewReviewedSubmissionSerializer(serializers.ModelSerializer):
    """Serializer for reviewed submissions — includes review outcome and notes."""

    contribution_type_name = serializers.CharField(
        source='contribution_type.name', read_only=True,
    )
    contribution_type_slug = serializers.CharField(
        source='contribution_type.slug', read_only=True,
    )
    category_name = serializers.SerializerMethodField()
    evidence_items = AIReviewEvidenceSerializer(many=True, read_only=True)
    internal_notes = AIReviewNoteSerializer(many=True, read_only=True)

    class Meta:
        model = SubmittedContribution
        fields = [
            'id',
            'contribution_type',
            'contribution_type_name',
            'contribution_type_slug',
            'category_name',
            'notes',
            'state',
            'staff_reply',
            'reviewed_at',
            'evidence_items',
            'internal_notes',
            'created_at',
        ]
        read_only_fields = fields

    def get_category_name(self, obj):
        if obj.contribution_type and obj.contribution_type.category:
            return obj.contribution_type.category.name
        return None


class AIReviewProposeSerializer(serializers.Serializer):
    proposed_action = serializers.ChoiceField(
        choices=['accept', 'reject', 'more_info'],
    )
    proposed_points = serializers.IntegerField(required=False, allow_null=True)
    proposed_staff_reply = serializers.CharField(
        required=False, allow_blank=True, default='',
    )
    reasoning = serializers.CharField(required=False, allow_blank=True, default='')
    confidence = serializers.ChoiceField(
        choices=['high', 'medium', 'low'],
        required=False,
        default='medium',
    )
    template_id = serializers.PrimaryKeyRelatedField(
        queryset=ReviewTemplate.objects.all(), required=False, allow_null=True,
    )

    def validate(self, data):
        action = data['proposed_action']
        if action == 'accept' and not data.get('proposed_points'):
            raise serializers.ValidationError(
                {'proposed_points': 'Points are required when proposing accept.'}
            )
        if action in ('reject', 'more_info') and not data.get('proposed_staff_reply'):
            raise serializers.ValidationError(
                {'proposed_staff_reply': 'Staff reply is required when proposing reject or more_info.'}
            )
        return data


class AIReviewTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewTemplate
        fields = ['id', 'label', 'text']
        read_only_fields = fields
