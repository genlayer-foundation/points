from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers
from .models import WorkingGroup, WorkingGroupParticipant


def feature_candidate_user_data(user, include_id=False):
    from social_connections.serializers import (
        PublicDiscordConnectionSerializer,
        PublicGitHubConnectionSerializer,
        PublicTwitterConnectionSerializer,
    )

    def _get(related_name, serializer_class):
        try:
            connection = getattr(user, related_name)
        except ObjectDoesNotExist:
            return None
        if connection is None:
            return None
        return serializer_class(connection).data

    data = {
        'name': user.name,
        'address': user.address,
        'profile_image_url': user.profile_image_url,
        'github_connection': _get('githubconnection', PublicGitHubConnectionSerializer),
        'twitter_connection': _get('twitterconnection', PublicTwitterConnectionSerializer),
        'discord_connection': _get('discordconnection', PublicDiscordConnectionSerializer),
    }
    if include_id:
        data['id'] = user.id
    return data


def feature_score_summary(scores):
    score_values = sorted(int(score) for score in scores)
    reviewer_count = len(score_values)
    if reviewer_count == 0:
        return {
            'median_score': None,
            'reviewer_count': 0,
            'spread': None,
            'decision': 'pending',
            'manual_review': False,
            'is_borderline': False,
        }

    midpoint = reviewer_count // 2
    if reviewer_count % 2:
        median_score = float(score_values[midpoint])
    else:
        median_score = (score_values[midpoint - 1] + score_values[midpoint]) / 2

    spread = score_values[-1] - score_values[0]
    manual_review = spread >= 3
    is_borderline = not manual_review and 1.5 <= median_score < 2

    if manual_review:
        decision = 'manual_review'
    elif median_score >= 2:
        decision = 'feature'
    else:
        decision = 'do_not_feature'

    return {
        'median_score': median_score,
        'reviewer_count': reviewer_count,
        'spread': spread,
        'decision': decision,
        'manual_review': manual_review,
        'is_borderline': is_borderline,
    }


class FeatureCandidateSubmissionSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    title = serializers.CharField(read_only=True)
    notes = serializers.CharField(read_only=True)
    state = serializers.CharField(read_only=True)
    contribution_date = serializers.DateTimeField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    own_score = serializers.SerializerMethodField()
    own_score_reason = serializers.SerializerMethodField()
    user_details = serializers.SerializerMethodField()
    contribution_type_details = serializers.SerializerMethodField()
    evidence_items = serializers.SerializerMethodField()

    def get_own_score(self, obj):
        review_map = self.context.get('own_review_map', {})
        return (review_map.get(obj.id) or {}).get('score')

    def get_own_score_reason(self, obj):
        review_map = self.context.get('own_review_map', {})
        return (review_map.get(obj.id) or {}).get('reason') or ''

    def get_user_details(self, obj):
        return feature_candidate_user_data(obj.user)

    def get_contribution_type_details(self, obj):
        contribution_type = obj.contribution_type
        category = contribution_type.category
        return {
            'id': contribution_type.id,
            'name': contribution_type.name,
            'slug': contribution_type.slug,
            'category': category.slug if category else None,
        }

    def get_evidence_items(self, obj):
        return [
            {
                'id': evidence.id,
                'description': evidence.description,
                'url': evidence.url,
                'url_type': {
                    'name': evidence.url_type.name,
                    'slug': evidence.url_type.slug,
                } if evidence.url_type else None,
                'file': evidence.file.url if evidence.file else None,
            }
            for evidence in obj.evidence_items.all()
        ]


class FeatureCandidateAdminSerializer(FeatureCandidateSubmissionSerializer):
    median_score = serializers.SerializerMethodField()
    reviewer_count = serializers.SerializerMethodField()
    spread = serializers.SerializerMethodField()
    decision = serializers.SerializerMethodField()
    manual_review = serializers.SerializerMethodField()
    is_borderline = serializers.SerializerMethodField()

    def get_user_details(self, obj):
        return feature_candidate_user_data(obj.user, include_id=True)

    def _summary(self, obj):
        summary_map = self.context.get('summary_map', {})
        return summary_map.get(obj.id) or feature_score_summary([])

    def get_median_score(self, obj):
        return self._summary(obj)['median_score']

    def get_reviewer_count(self, obj):
        return self._summary(obj)['reviewer_count']

    def get_spread(self, obj):
        return self._summary(obj)['spread']

    def get_decision(self, obj):
        return self._summary(obj)['decision']

    def get_manual_review(self, obj):
        return self._summary(obj)['manual_review']

    def get_is_borderline(self, obj):
        return self._summary(obj)['is_borderline']


class WorkingGroupParticipantSerializer(serializers.ModelSerializer):
    """
    Serializer for working group participant with user details.
    """
    id = serializers.IntegerField(source='user.id', read_only=True)
    name = serializers.CharField(source='user.name', read_only=True)
    address = serializers.CharField(source='user.address', read_only=True)
    profile_image_url = serializers.URLField(source='user.profile_image_url', read_only=True)

    class Meta:
        model = WorkingGroupParticipant
        fields = ['id', 'name', 'address', 'profile_image_url']


class WorkingGroupListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing working groups with participant count.
    """
    participant_count = serializers.IntegerField(read_only=True)
    is_member = serializers.SerializerMethodField()

    class Meta:
        model = WorkingGroup
        fields = ['id', 'name', 'icon', 'description', 'participant_count', 'is_member', 'created_at']

    def get_is_member(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.participants.filter(user=request.user).exists()
        return False


class WorkingGroupDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for working group detail with participants and conditional discord_url.
    """
    participant_count = serializers.SerializerMethodField()
    is_member = serializers.SerializerMethodField()
    discord_url = serializers.SerializerMethodField()
    participants = serializers.SerializerMethodField()

    class Meta:
        model = WorkingGroup
        fields = ['id', 'name', 'icon', 'description', 'discord_url', 'participant_count', 'is_member', 'participants', 'created_at']

    def get_participant_count(self, obj):
        return obj.participants.count()

    def get_is_member(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.participants.filter(user=request.user).exists()
        return False

    def get_discord_url(self, obj):
        """Only show discord_url if user is a member or a steward."""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None

        is_member = obj.participants.filter(user=request.user).exists()
        is_steward = hasattr(request.user, 'steward')

        if is_member or is_steward:
            return obj.discord_url
        return None

    def get_participants(self, obj):
        participants = obj.participants.select_related('user').all()
        return WorkingGroupParticipantSerializer(participants, many=True).data


class WorkingGroupCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a working group.
    """
    class Meta:
        model = WorkingGroup
        fields = ['name', 'icon', 'description', 'discord_url']


class WorkingGroupUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating a working group.
    """
    class Meta:
        model = WorkingGroup
        fields = ['name', 'icon', 'description', 'discord_url']
