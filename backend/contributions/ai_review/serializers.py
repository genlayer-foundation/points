from rest_framework import serializers

from contributions.models import Evidence, ProjectMilestoneReview, SubmissionNote, SubmittedContribution
from contributions.rubric_review import (
    normalize_rubric_review_payload,
    uses_project_rubric,
)
from stewards.models import ReviewTemplate


class AIReviewEvidenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Evidence
        fields = ['id', 'url', 'description']
        read_only_fields = fields


class AIReviewMissionSerializer(serializers.Serializer):
    """Minimal mission context for AI review payloads."""

    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    start_date = serializers.DateTimeField(read_only=True)
    end_date = serializers.DateTimeField(read_only=True)
    contribution_type = serializers.PrimaryKeyRelatedField(read_only=True)
    is_active = serializers.SerializerMethodField()

    def get_is_active(self, obj):
        return obj.is_active()


class LightAIReviewSubmissionSerializer(serializers.ModelSerializer):
    """Light serializer for list views — no nested queries."""

    contribution_type_name = serializers.CharField(
        source='contribution_type.name', read_only=True,
    )
    review_flow = serializers.CharField(
        source='contribution_type.review_flow', read_only=True,
    )
    category_name = serializers.SerializerMethodField()
    has_proposal = serializers.SerializerMethodField()
    mission = AIReviewMissionSerializer(read_only=True)

    class Meta:
        model = SubmittedContribution
        fields = [
            'id',
            'contribution_type',
            'contribution_type_name',
            'review_flow',
            'category_name',
            'title',
            'notes',
            'state',
            'mission',
            'has_appeal',
            'appeal_reason',
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


class AIReviewNoteSerializer(serializers.ModelSerializer):
    """Serializer for internal notes on AI review submissions."""

    class Meta:
        model = SubmissionNote
        fields = ['message', 'is_proposal', 'data', 'created_at']
        read_only_fields = fields


class AIReviewRubricReviewSerializer(serializers.ModelSerializer):
    proposer_name = serializers.SerializerMethodField()

    class Meta:
        model = ProjectMilestoneReview
        fields = [
            'id', 'review_flow', 'action', 'confidence', 'gate_failures',
            'sections', 'extras', 'overall_reason', 'proposer_name',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields

    def get_proposer_name(self, obj):
        if not obj.proposer:
            return None
        return obj.proposer.name or str(obj.proposer.id)


class AIReviewSubmissionSerializer(serializers.ModelSerializer):
    """Full serializer for detail views — includes evidence, notes, and user history."""

    contribution_type_name = serializers.CharField(
        source='contribution_type.name', read_only=True,
    )
    contribution_type_slug = serializers.CharField(
        source='contribution_type.slug', read_only=True,
    )
    review_flow = serializers.CharField(
        source='contribution_type.review_flow', read_only=True,
    )
    category_name = serializers.SerializerMethodField()
    min_points = serializers.IntegerField(
        source='contribution_type.min_points', read_only=True,
    )
    max_points = serializers.IntegerField(
        source='contribution_type.max_points', read_only=True,
    )
    evidence_items = AIReviewEvidenceSerializer(many=True, read_only=True)
    internal_notes = AIReviewNoteSerializer(many=True, read_only=True)
    mission = AIReviewMissionSerializer(read_only=True)
    user_history = serializers.SerializerMethodField()
    has_proposal = serializers.SerializerMethodField()
    proposed_by_name = serializers.SerializerMethodField()
    rubric_review = serializers.SerializerMethodField()

    class Meta:
        model = SubmittedContribution
        fields = [
            'id',
            'contribution_type',
            'contribution_type_name',
            'contribution_type_slug',
            'review_flow',
            'category_name',
            'min_points',
            'max_points',
            'title',
            'notes',
            'state',
            'staff_reply',
            'mission',
            'has_appeal',
            'appeal_reason',
            'evidence_items',
            'internal_notes',
            'user_history',
            'has_proposal',
            'proposed_action',
            'proposed_points',
            'proposed_staff_reply',
            'proposed_confidence',
            'proposed_template',
            'proposed_by_name',
            'proposed_at',
            'rubric_review',
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

    def get_rubric_review(self, obj):
        try:
            review = obj.project_milestone_review
        except ProjectMilestoneReview.DoesNotExist:
            return None
        return AIReviewRubricReviewSerializer(review).data


class AIReviewReviewedSubmissionSerializer(serializers.ModelSerializer):
    """Serializer for reviewed submissions — includes review outcome and notes."""

    contribution_type_name = serializers.CharField(
        source='contribution_type.name', read_only=True,
    )
    contribution_type_slug = serializers.CharField(
        source='contribution_type.slug', read_only=True,
    )
    review_flow = serializers.CharField(
        source='contribution_type.review_flow', read_only=True,
    )
    category_name = serializers.SerializerMethodField()
    evidence_items = AIReviewEvidenceSerializer(many=True, read_only=True)
    internal_notes = AIReviewNoteSerializer(many=True, read_only=True)
    mission = AIReviewMissionSerializer(read_only=True)
    rubric_review = serializers.SerializerMethodField()

    class Meta:
        model = SubmittedContribution
        fields = [
            'id',
            'contribution_type',
            'contribution_type_name',
            'contribution_type_slug',
            'review_flow',
            'category_name',
            'notes',
            'state',
            'staff_reply',
            'mission',
            'has_appeal',
            'appeal_reason',
            'reviewed_at',
            'evidence_items',
            'internal_notes',
            'rubric_review',
            'created_at',
        ]
        read_only_fields = fields

    def get_category_name(self, obj):
        if obj.contribution_type and obj.contribution_type.category:
            return obj.contribution_type.category.name
        return None

    def get_rubric_review(self, obj):
        try:
            review = obj.project_milestone_review
        except ProjectMilestoneReview.DoesNotExist:
            return None
        return AIReviewRubricReviewSerializer(review).data


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
    rubric_review = serializers.JSONField(required=False)

    def validate(self, data):
        submission = self.context.get('submission')
        action = data['proposed_action']
        requires_rubric = uses_project_rubric(
            submission.contribution_type if submission else None
        )

        if requires_rubric:
            data['rubric_review'] = normalize_rubric_review_payload(
                data.get('rubric_review'),
                action,
            )
        elif 'rubric_review' in data:
            raise serializers.ValidationError({
                'rubric_review': 'Rubric review is only accepted for Builder Project proposals.'
            })

        if action == 'accept' and not requires_rubric and data.get('proposed_points') is None:
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
