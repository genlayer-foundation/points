from rest_framework import serializers
from .models import User
from validators.models import Validator
from builders.models import Builder
from stewards.models import Steward
from contributions.node_upgrade.models import TargetNodeVersion
from leaderboard.models import LeaderboardEntry
from contributions.models import Category


class ValidatorSerializer(serializers.ModelSerializer):
    """
    Serializer for Validator model.
    """
    matches_target = serializers.SerializerMethodField()
    target_version = serializers.SerializerMethodField()
    target_date = serializers.SerializerMethodField()
    target_created_at = serializers.SerializerMethodField()
    total_points = serializers.SerializerMethodField()
    rank = serializers.SerializerMethodField()
    
    class Meta:
        model = Validator
        fields = ['node_version', 'matches_target', 'target_version', 'target_date', 'target_created_at', 'total_points', 'rank', 'updated_at']
        read_only_fields = ['updated_at']
    
    def get_matches_target(self, obj):
        """
        Check if the validator's version matches or is higher than the target.
        """
        target = TargetNodeVersion.get_active()
        if target and obj.node_version:
            return obj.version_matches_or_higher(target.version)
        return False
    
    def get_target_version(self, obj):
        """
        Get the current target version.
        """
        target = TargetNodeVersion.get_active()
        return target.version if target else None
    
    def get_target_date(self, obj):
        """
        Get the target date.
        """
        target = TargetNodeVersion.get_active()
        return target.target_date if target else None
    
    def get_target_created_at(self, obj):
        """
        Get when the target was created (for points calculation).
        """
        target = TargetNodeVersion.get_active()
        return target.created_at if target else None
    
    def get_total_points(self, obj):
        """Get total points for validator category."""
        try:
            category = Category.objects.get(slug='validator')
            leaderboard = LeaderboardEntry.objects.filter(user=obj.user, category=category).first()
            return leaderboard.total_points if leaderboard else 0
        except Category.DoesNotExist:
            return 0
    
    def get_rank(self, obj):
        """Get rank in validator category."""
        try:
            category = Category.objects.get(slug='validator')
            leaderboard = LeaderboardEntry.objects.filter(user=obj.user, category=category).first()
            return leaderboard.rank if leaderboard else None
        except Category.DoesNotExist:
            return None


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating user profile.
    Allows updating name and validator node_version.
    """
    node_version = serializers.CharField(required=False, allow_blank=True, allow_null=True, source='validator.node_version')
    
    class Meta:
        model = User
        fields = ['name', 'node_version']
    
    def update(self, instance, validated_data):
        # Handle validator data if present
        validator_data = validated_data.pop('validator', {})
        
        # Update user fields
        instance.name = validated_data.get('name', instance.name)
        instance.save()
        
        # Update or create validator if node_version is provided
        if 'node_version' in validator_data:
            validator, created = Validator.objects.get_or_create(user=instance)
            validator.node_version = validator_data['node_version']
            validator.save()
        
        return instance
        

class BuilderSerializer(serializers.ModelSerializer):
    """
    Serializer for Builder profile.
    """
    total_points = serializers.SerializerMethodField()
    rank = serializers.SerializerMethodField()
    
    class Meta:
        model = Builder
        fields = ['total_points', 'rank', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']
    
    def get_total_points(self, obj):
        """Get total points for builder category."""
        try:
            category = Category.objects.get(slug='builder')
            leaderboard = LeaderboardEntry.objects.filter(user=obj.user, category=category).first()
            return leaderboard.total_points if leaderboard else 0
        except Category.DoesNotExist:
            return 0
    
    def get_rank(self, obj):
        """Get rank in builder category."""
        try:
            category = Category.objects.get(slug='builder')
            leaderboard = LeaderboardEntry.objects.filter(user=obj.user, category=category).first()
            return leaderboard.rank if leaderboard else None
        except Category.DoesNotExist:
            return None


class StewardSerializer(serializers.ModelSerializer):
    """
    Serializer for Steward profile.
    """
    total_points = serializers.SerializerMethodField()
    rank = serializers.SerializerMethodField()
    
    class Meta:
        model = Steward
        fields = ['total_points', 'rank', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']
    
    def get_total_points(self, obj):
        """Get total points for steward category."""
        try:
            category = Category.objects.get(slug='steward')
            leaderboard = LeaderboardEntry.objects.filter(user=obj.user, category=category).first()
            return leaderboard.total_points if leaderboard else 0
        except Category.DoesNotExist:
            return 0
    
    def get_rank(self, obj):
        """Get rank in steward category."""
        try:
            category = Category.objects.get(slug='steward')
            leaderboard = LeaderboardEntry.objects.filter(user=obj.user, category=category).first()
            return leaderboard.rank if leaderboard else None
        except Category.DoesNotExist:
            return None


class UserSerializer(serializers.ModelSerializer):
    leaderboard_entry = serializers.SerializerMethodField()
    validator = ValidatorSerializer(read_only=True)
    builder = BuilderSerializer(read_only=True)
    steward = StewardSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'name', 'address', 'visible', 'leaderboard_entry', 'validator', 'builder', 'steward', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_leaderboard_entry(self, obj):
        """
        Get the global leaderboard entry for this user.
        Returns rank and total_points if the entry exists, otherwise returns None.
        """
        try:
            # Get the global leaderboard entry (category=None)
            entry = LeaderboardEntry.objects.filter(user=obj, category=None).first()
            if entry:
                return {
                    'rank': entry.rank,
                    'total_points': entry.total_points
                }
        except:
            pass
        return None


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    password_confirm = serializers.CharField(write_only=True, style={'input_type': 'password'})
    
    class Meta:
        model = User
        fields = ['email', 'name', 'address', 'password', 'password_confirm']
    
    def validate(self, data):
        # Check that the two passwords match
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError("Passwords must match.")
        return data
    
    def create(self, validated_data):
        # Remove password_confirm as it's not needed anymore
        validated_data.pop('password_confirm')
        
        # Get the visible field from the context if provided
        visible = self.context.get('visible', True)
        
        # Create user
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            name=validated_data.get('name', ''),
            address=validated_data.get('address', ''),
            visible=visible
        )
        
        return user