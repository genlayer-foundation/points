from rest_framework import serializers

from contributions.models import Contribution
from contributions.serializers import LightContributionSerializer
from users.serializers import LightUserSerializer
from users.models import User

from .models import Project


class ProjectListSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    user_address = serializers.SerializerMethodField()
    user_profile_image_url = serializers.SerializerMethodField()
    owner_profile_image_url = serializers.SerializerMethodField()
    featured_profile_image_url = serializers.CharField(
        source='user_profile_image_url',
        read_only=True,
    )
    link = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            'id',
            'slug',
            'title',
            'description',
            'author',
            'hero_image_url',
            'hero_image_url_tablet',
            'hero_image_url_mobile',
            'view_url',
            'url',
            'github_url',
            'x_url',
            'telegram_url',
            'discord_url',
            'demo_url',
            'details',
            'link',
            'user',
            'user_name',
            'user_address',
            'user_profile_image_url',
            'owner_profile_image_url',
            'featured_profile_image_url',
            'status',
            'show_in_overview',
            'order',
            'created_at',
            'can_edit',
        ]
        read_only_fields = fields

    def get_user_name(self, obj):
        return obj.user.name if obj.user else ''

    def get_user_address(self, obj):
        return obj.user.address if obj.user else ''

    def get_user_profile_image_url(self, obj):
        if obj.user_profile_image_url:
            return obj.user_profile_image_url
        if obj.user and obj.user.profile_image_url:
            return obj.user.profile_image_url
        return ''

    def get_owner_profile_image_url(self, obj):
        if obj.user and obj.user.profile_image_url:
            return obj.user.profile_image_url
        return ''

    def get_link(self, obj):
        return obj.get_link()

    def get_can_edit(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        return obj.can_be_edited_by(user)


class ProjectDetailSerializer(ProjectListSerializer):
    related_contributions = LightContributionSerializer(many=True, read_only=True)
    participants = LightUserSerializer(many=True, read_only=True)

    class Meta(ProjectListSerializer.Meta):
        fields = ProjectListSerializer.Meta.fields + ['participants', 'related_contributions']
        read_only_fields = fields


class ProjectProfileUpdateSerializer(serializers.Serializer):
    description = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True, max_length=2000)
    details = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True, max_length=12000)
    url = serializers.URLField(required=False, allow_blank=True, max_length=500)
    github_url = serializers.URLField(required=False, allow_blank=True, max_length=500)
    x_url = serializers.URLField(required=False, allow_blank=True, max_length=500)
    telegram_url = serializers.URLField(required=False, allow_blank=True, max_length=500)
    discord_url = serializers.URLField(required=False, allow_blank=True, max_length=500)
    demo_url = serializers.URLField(required=False, allow_blank=True, max_length=500)
    hero_image_url = serializers.URLField(required=False, allow_blank=True, max_length=500)
    hero_image_url_tablet = serializers.URLField(required=False, allow_blank=True, max_length=500)
    hero_image_url_mobile = serializers.URLField(required=False, allow_blank=True, max_length=500)
    user_profile_image_url = serializers.URLField(required=False, allow_blank=True, max_length=500)
    participant_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        allow_empty=True,
        max_length=30,
    )
    related_contribution_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        allow_empty=True,
        max_length=100,
    )

    def validate_participant_ids(self, value):
        user_ids = list(dict.fromkeys(value))
        users = User.objects.filter(id__in=user_ids, visible=True)
        found_ids = set(users.values_list('id', flat=True))
        missing_ids = [user_id for user_id in user_ids if user_id not in found_ids]
        if missing_ids:
            raise serializers.ValidationError(f"Unknown participant id(s): {', '.join(map(str, missing_ids))}.")
        return user_ids

    def validate_related_contribution_ids(self, value):
        contribution_ids = list(dict.fromkeys(value))
        contributions = Contribution.objects.filter(id__in=contribution_ids, user__visible=True)
        found_ids = set(contributions.values_list('id', flat=True))
        missing_ids = [contribution_id for contribution_id in contribution_ids if contribution_id not in found_ids]
        if missing_ids:
            raise serializers.ValidationError(f"Unknown contribution id(s): {', '.join(map(str, missing_ids))}.")
        return contribution_ids

    def validate(self, attrs):
        related_contribution_ids = attrs.get('related_contribution_ids')
        if related_contribution_ids is None:
            return attrs

        participant_ids = attrs.get(
            'participant_ids',
            list(self.instance.participants.values_list('id', flat=True)) if self.instance else [],
        )
        allowed_user_ids = set(participant_ids)
        if self.instance and self.instance.user_id:
            allowed_user_ids.add(self.instance.user_id)

        if allowed_user_ids:
            unrelated = (
                Contribution.objects
                .filter(id__in=related_contribution_ids, user__visible=True)
                .exclude(user_id__in=allowed_user_ids)
                .values_list('id', flat=True)
            )
            unrelated_ids = list(unrelated)
            if unrelated_ids:
                raise serializers.ValidationError({
                    'related_contribution_ids': [
                        f"Contribution id(s) must belong to selected participants: {', '.join(map(str, unrelated_ids))}."
                    ]
                })

        return attrs

    def update(self, instance, validated_data):
        participant_ids = validated_data.pop('participant_ids', None)
        related_contribution_ids = validated_data.pop('related_contribution_ids', None)
        for field_name, value in validated_data.items():
            setattr(instance, field_name, value)
        instance.save(update_fields=[*validated_data.keys(), 'updated_at'] if validated_data else None)
        if participant_ids is not None:
            instance.participants.set(User.objects.filter(id__in=participant_ids, visible=True))
        if related_contribution_ids is not None:
            instance.related_contributions.set(
                Contribution.objects.filter(id__in=related_contribution_ids, user__visible=True)
            )
        return instance
