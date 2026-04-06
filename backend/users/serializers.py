from rest_framework import serializers
from disposable_email_domains import blocklist
from .models import BanAppeal, User
from validators.models import Validator, ValidatorWallet
from builders.models import Builder
from stewards.models import Steward
from creators.models import Creator
from contributions.node_upgrade.models import TargetNodeVersion
from leaderboard.models import LeaderboardEntry
from contributions.models import Category


# ============================================================================
# Lightweight Serializers for Optimized List Views
# ============================================================================
# These serializers provide minimal data for list views and nested relationships,
# significantly reducing database queries and response payload size.
# Use these in list views or when full detail is not needed.


class LightUserSerializer(serializers.Serializer):
    """
    Minimal user serializer for list views and nested relationships.
    Only includes essential display fields, no related objects or computed fields.
    """
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    address = serializers.CharField(read_only=True)
    profile_image_url = serializers.URLField(read_only=True)
    visible = serializers.BooleanField(read_only=True)


class LightValidatorSerializer(serializers.Serializer):
    """
    Minimal validator serializer without expensive stat calculations.
    Only includes node version and basic matching info per network.
    """
    node_version_asimov = serializers.CharField(read_only=True)
    node_version_bradbury = serializers.CharField(read_only=True)
    matches_target_asimov = serializers.SerializerMethodField()
    matches_target_bradbury = serializers.SerializerMethodField()
    target_version_asimov = serializers.SerializerMethodField()
    target_version_bradbury = serializers.SerializerMethodField()
    active_validators_count = serializers.SerializerMethodField()
    total_validators_count = serializers.SerializerMethodField()

    def get_matches_target_asimov(self, obj):
        from contributions.node_upgrade.models import TargetNodeVersion
        target = TargetNodeVersion.get_active(network='asimov')
        if target and obj.node_version_asimov:
            return obj.version_matches_or_higher(target.version, node_version=obj.node_version_asimov)
        return False

    def get_matches_target_bradbury(self, obj):
        from contributions.node_upgrade.models import TargetNodeVersion
        target = TargetNodeVersion.get_active(network='bradbury')
        if target and obj.node_version_bradbury:
            return obj.version_matches_or_higher(target.version, node_version=obj.node_version_bradbury)
        return False

    def get_target_version_asimov(self, obj):
        from contributions.node_upgrade.models import TargetNodeVersion
        target = TargetNodeVersion.get_active(network='asimov')
        return target.version if target else None

    def get_target_version_bradbury(self, obj):
        from contributions.node_upgrade.models import TargetNodeVersion
        target = TargetNodeVersion.get_active(network='bradbury')
        return target.version if target else None

    def get_active_validators_count(self, obj):
        """Get count of active validator wallets for this operator."""
        return ValidatorWallet.objects.filter(
            operator=obj,
            status='active'
        ).count()

    def get_total_validators_count(self, obj):
        """Get total count of validator wallets for this operator."""
        return ValidatorWallet.objects.filter(operator=obj).count()


class LightBuilderSerializer(serializers.Serializer):
    """
    Minimal builder serializer without expensive stat calculations.
    Just indicates the user is a builder.
    """
    created_at = serializers.DateTimeField(read_only=True)


class LightLeaderboardEntrySerializer(serializers.Serializer):
    """
    Minimal leaderboard entry for nested user data.
    Only includes rank and points, not full user details.
    """
    rank = serializers.IntegerField(read_only=True)
    total_points = serializers.IntegerField(read_only=True)


# ============================================================================
# Full Serializers
# ============================================================================


class ValidatorSerializer(serializers.ModelSerializer):
    """
    Serializer for Validator model.
    """
    matches_target_asimov = serializers.SerializerMethodField()
    matches_target_bradbury = serializers.SerializerMethodField()
    target_version_asimov = serializers.SerializerMethodField()
    target_version_bradbury = serializers.SerializerMethodField()
    target_date_asimov = serializers.SerializerMethodField()
    target_date_bradbury = serializers.SerializerMethodField()
    target_created_at_asimov = serializers.SerializerMethodField()
    target_created_at_bradbury = serializers.SerializerMethodField()
    total_points = serializers.SerializerMethodField()
    rank = serializers.SerializerMethodField()
    total_contributions = serializers.SerializerMethodField()
    contribution_types = serializers.SerializerMethodField()
    active_validators_count = serializers.SerializerMethodField()
    total_validators_count = serializers.SerializerMethodField()

    class Meta:
        model = Validator
        fields = ['node_version_asimov', 'node_version_bradbury',
                 'matches_target_asimov', 'matches_target_bradbury',
                 'target_version_asimov', 'target_version_bradbury',
                 'target_date_asimov', 'target_date_bradbury',
                 'target_created_at_asimov', 'target_created_at_bradbury',
                 'total_points', 'rank', 'total_contributions', 'contribution_types',
                 'active_validators_count', 'total_validators_count', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def _get_target(self, network):
        return TargetNodeVersion.get_active(network=network)

    def get_matches_target_asimov(self, obj):
        target = self._get_target('asimov')
        if target and obj.node_version_asimov:
            return obj.version_matches_or_higher(target.version, node_version=obj.node_version_asimov)
        return False

    def get_matches_target_bradbury(self, obj):
        target = self._get_target('bradbury')
        if target and obj.node_version_bradbury:
            return obj.version_matches_or_higher(target.version, node_version=obj.node_version_bradbury)
        return False

    def get_target_version_asimov(self, obj):
        target = self._get_target('asimov')
        return target.version if target else None

    def get_target_version_bradbury(self, obj):
        target = self._get_target('bradbury')
        return target.version if target else None

    def get_target_date_asimov(self, obj):
        target = self._get_target('asimov')
        return target.target_date if target else None

    def get_target_date_bradbury(self, obj):
        target = self._get_target('bradbury')
        return target.target_date if target else None

    def get_target_created_at_asimov(self, obj):
        target = self._get_target('asimov')
        return target.created_at if target else None

    def get_target_created_at_bradbury(self, obj):
        target = self._get_target('bradbury')
        return target.created_at if target else None
    
    def get_total_points(self, obj):
        """Get total points for validator leaderboard."""
        leaderboard = LeaderboardEntry.objects.filter(user=obj.user, type='validator').first()
        return leaderboard.total_points if leaderboard else 0
    
    def get_rank(self, obj):
        """Get rank in validator leaderboard."""
        leaderboard = LeaderboardEntry.objects.filter(user=obj.user, type='validator').first()
        return leaderboard.rank if leaderboard else None
    
    def get_total_contributions(self, obj):
        """Get total number of contributions in validator category."""
        from contributions.models import Contribution, ContributionType
        try:
            category = Category.objects.get(slug='validator')
            contribution_types = ContributionType.objects.filter(category=category)
            return Contribution.objects.filter(
                user=obj.user,
                contribution_type__in=contribution_types
            ).count()
        except Category.DoesNotExist:
            return 0
    
    def get_contribution_types(self, obj):
        """
        Get breakdown of contribution types for validator category.
        Skip for nested/list views to avoid N+1 queries.
        """
        # Skip expensive queries for nested/list views
        if self.context.get('use_light_serializers', False):
            return []

        from contributions.models import Contribution, ContributionType
        from django.db.models import Count, Sum

        try:
            category = Category.objects.get(slug='validator')
            contribution_types = ContributionType.objects.filter(category=category)

            # Get contribution stats grouped by type
            stats = Contribution.objects.filter(
                user=obj.user,
                contribution_type__in=contribution_types
            ).values('contribution_type__id', 'contribution_type__name').annotate(
                count=Count('id'),
                total_points=Sum('frozen_global_points')
            ).order_by('-total_points')

            # Calculate total points for percentage
            total_points = sum(s['total_points'] or 0 for s in stats)

            # Format the response
            result = []
            for stat in stats:
                points = stat['total_points'] or 0
                result.append({
                    'id': stat['contribution_type__id'],
                    'name': stat['contribution_type__name'],
                    'count': stat['count'],
                    'total_points': points,
                    'percentage': round((points / total_points * 100) if total_points > 0 else 0, 1)
                })

            return result
        except Category.DoesNotExist:
            return []

    def get_active_validators_count(self, obj):
        """Get count of active validator wallets for this operator."""
        return ValidatorWallet.objects.filter(
            operator=obj,
            status='active'
        ).count()

    def get_total_validators_count(self, obj):
        """Get total count of validator wallets for this operator."""
        return ValidatorWallet.objects.filter(operator=obj).count()


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating user profile.
    Allows updating name, profile fields, and validator node versions per network.
    """
    node_version_asimov = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, source='validator.node_version_asimov'
    )
    node_version_bradbury = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, source='validator.node_version_bradbury'
    )
    email = serializers.EmailField(required=False, allow_blank=True)
    website = serializers.CharField(required=False, allow_blank=True, max_length=200)

    class Meta:
        model = User
        fields = ['name', 'node_version_asimov', 'node_version_bradbury', 'email', 'description', 'website',
                  'telegram_handle', 'linkedin_handle']
    
    def validate_email(self, value):
        """Validate email with DNS checks and block disposable providers"""
        if not value:
            return value

        from email_validator import validate_email, EmailNotValidError

        try:
            # Validate email with DNS deliverability check
            valid = validate_email(
                value,
                check_deliverability=True,      # Check DNS MX records
                test_environment=False,         # Block test@test.com patterns
                globally_deliverable=True,      # Reject localhost, private IPs, .local domains
                allow_domain_literal=False,     # Block IP-based emails like user@[192.168.1.1]
                timeout=10                      # DNS timeout in seconds (prevent hanging)
            )

            # Get normalized email (lowercase domain, etc.)
            normalized_email = valid.normalized

            # Check if domain is in disposable email blocklist
            if valid.domain.lower() in blocklist:
                raise serializers.ValidationError(
                    "Temporary or disposable email addresses are not allowed. Please use a permanent email address."
                )

            return normalized_email

        except EmailNotValidError as e:
            # Convert email-validator errors to DRF validation errors
            error_message = str(e)

            # Provide user-friendly messages for common errors
            if "does not exist" in error_message.lower():
                raise serializers.ValidationError(
                    "This email domain does not exist. Please check for typos."
                )
            elif "does not accept email" in error_message.lower():
                raise serializers.ValidationError(
                    "This email domain cannot receive emails. Please use a different email address."
                )
            else:
                raise serializers.ValidationError(error_message)

    def validate_description(self, value):
        """Validate description length"""
        if value and len(value) > 500:
            raise serializers.ValidationError("Description must be 500 characters or less.")
        return value
    
    def validate_website(self, value):
        """Validate and format website URL"""
        if value:
            # If no protocol is specified, add https://
            if not value.startswith(('http://', 'https://')):
                value = 'https://' + value
            
            # Now validate it's a proper URL
            from django.core.validators import URLValidator
            from django.core.exceptions import ValidationError as DjangoValidationError
            
            validator = URLValidator()
            try:
                validator(value)
            except DjangoValidationError:
                raise serializers.ValidationError("Enter a valid URL.")
        return value
    
    def validate_twitter_handle(self, value):
        """Validate Twitter handle format"""
        if value:
            # Remove @ if provided
            value = value.lstrip('@')
            if len(value) > 15:  # Twitter username max length
                raise serializers.ValidationError("Twitter handle must be 15 characters or less.")
        return value
    
    def validate_telegram_handle(self, value):
        """Validate Telegram handle format"""
        if value:
            # Remove @ if provided
            value = value.lstrip('@')
        return value
    
    def validate_linkedin_handle(self, value):
        """Validate LinkedIn handle format"""
        if value:
            # Remove linkedin.com/in/ if provided as full URL
            if 'linkedin.com/in/' in value:
                value = value.split('linkedin.com/in/')[-1]
            # Remove trailing slashes
            value = value.rstrip('/')
            # Remove any remaining URL parts
            value = value.split('?')[0]
        return value
    
    def update(self, instance, validated_data):
        # Handle validator data if present
        validator_data = validated_data.pop('validator', {})

        # Handle email update
        if 'email' in validated_data:
            new_email = validated_data.pop('email')
            if new_email and new_email != instance.email:
                # Normalize the email (lowercase domain, etc.)
                from django.contrib.auth.models import UserManager
                new_email = UserManager.normalize_email(new_email)

                # Check if email is already taken (case-insensitive)
                if User.objects.filter(email__iexact=new_email).exclude(id=instance.id).exists():
                    raise serializers.ValidationError({'email': 'This email is already in use.'})
                instance.email = new_email
                instance.is_email_verified = True  # Mark as verified when user provides it
        
        # Update other user fields
        for field, value in validated_data.items():
            setattr(instance, field, value)
        
        instance.save()
        
        # Update or create validator if any node_version field is provided
        if 'node_version_asimov' in validator_data or 'node_version_bradbury' in validator_data:
            validator, created = Validator.objects.get_or_create(user=instance)
            if 'node_version_asimov' in validator_data:
                validator.node_version_asimov = validator_data['node_version_asimov']
            if 'node_version_bradbury' in validator_data:
                validator.node_version_bradbury = validator_data['node_version_bradbury']
            validator.save()

        return instance
        

class BuilderSerializer(serializers.ModelSerializer):
    """
    Serializer for Builder profile.
    """
    total_points = serializers.SerializerMethodField()
    rank = serializers.SerializerMethodField()
    total_contributions = serializers.SerializerMethodField()
    contribution_types = serializers.SerializerMethodField()
    
    class Meta:
        model = Builder
        fields = ['total_points', 'rank', 'total_contributions', 'contribution_types', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']
    
    def get_total_points(self, obj):
        """Get total points for builder leaderboard."""
        leaderboard = LeaderboardEntry.objects.filter(user=obj.user, type='builder').first()
        return leaderboard.total_points if leaderboard else 0
    
    def get_rank(self, obj):
        """Get rank in builder leaderboard."""
        leaderboard = LeaderboardEntry.objects.filter(user=obj.user, type='builder').first()
        return leaderboard.rank if leaderboard else None
    
    def get_total_contributions(self, obj):
        """Get total number of builder-related contributions."""
        from contributions.models import Contribution, ContributionType
        
        # Count all builder-related contributions
        builder_slugs = ['builder', 'builder-welcome', 'create-intelligent-contracts']
        contribution_types = ContributionType.objects.filter(slug__in=builder_slugs)
        
        return Contribution.objects.filter(
            user=obj.user,
            contribution_type__in=contribution_types
        ).count()
    
    def get_contribution_types(self, obj):
        """
        Get breakdown of contribution types for builder.
        Skip for nested/list views to avoid N+1 queries.
        """
        # Skip expensive queries for nested/list views
        if self.context.get('use_light_serializers', False):
            return []

        from contributions.models import Contribution, ContributionType
        from django.db.models import Count, Sum

        # Get all builder-related contribution types
        builder_slugs = ['builder', 'builder-welcome', 'create-intelligent-contracts']
        contribution_types = ContributionType.objects.filter(slug__in=builder_slugs)

        contributions = Contribution.objects.filter(
            user=obj.user,
            contribution_type__in=contribution_types
        ).values('contribution_type__id', 'contribution_type__name', 'contribution_type__slug').annotate(
            count=Count('id'),
            total_points=Sum('frozen_global_points')
        ).order_by('-total_points')

        # Calculate total points for percentage
        total_points = sum(c['total_points'] or 0 for c in contributions)

        # Format the response with percentage
        result = []
        for contrib in contributions:
            points = contrib['total_points'] or 0
            result.append({
                'id': contrib['contribution_type__id'],
                'name': contrib['contribution_type__name'],
                'slug': contrib['contribution_type__slug'],
                'count': contrib['count'],
                'total_points': points,
                'percentage': round((points / total_points * 100) if total_points > 0 else 0, 1)
            })

        return result


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
        """Get total points for user."""
        # Stewards are deprecated, but return 0 for compatibility
        return 0

    def get_rank(self, obj):
        """Get rank for user."""
        # Stewards are deprecated, return None for compatibility
        return None


class CreatorSerializer(serializers.ModelSerializer):
    """
    Serializer for Creator profile.
    """
    total_referrals = serializers.SerializerMethodField()
    referral_points = serializers.SerializerMethodField()

    class Meta:
        model = Creator
        fields = ['total_referrals', 'referral_points', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def get_total_referrals(self, obj):
        """Get total number of users referred by this creator."""
        return obj.user.referrals.count()

    def get_referral_points(self, obj):
        """Get total points earned from referrals."""
        from contributions.models import Contribution
        from django.db.models import Sum

        # Get all contributions from referred users
        referred_users = obj.user.referrals.all()
        if not referred_users.exists():
            return 0

        # Calculate 10% of points from referred users' contributions
        total_points = Contribution.objects.filter(
            user__in=referred_users
        ).aggregate(
            total=Sum('frozen_global_points')
        )['total'] or 0

        return int(total_points * 0.1)  # 10% of referred users' points


class UserSerializer(serializers.ModelSerializer):
    leaderboard_entry = serializers.SerializerMethodField()
    validator = serializers.SerializerMethodField()
    builder = serializers.SerializerMethodField()
    steward = StewardSerializer(read_only=True)
    creator = CreatorSerializer(read_only=True)
    has_validator_waitlist = serializers.SerializerMethodField()
    has_builder_welcome = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()

    # Referral system fields
    referred_by_info = serializers.SerializerMethodField()
    total_referrals = serializers.SerializerMethodField()
    referral_details = serializers.SerializerMethodField()

    # Working groups
    working_groups = serializers.SerializerMethodField()

    # Social connections
    github_connection = serializers.SerializerMethodField()
    twitter_connection = serializers.SerializerMethodField()
    discord_connection = serializers.SerializerMethodField()

    # Backward-compat computed fields for github
    github_username = serializers.SerializerMethodField()
    github_linked_at = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'name', 'address', 'visible', 'leaderboard_entry', 'validator', 'builder', 'steward',
                  'creator', 'has_validator_waitlist', 'has_builder_welcome', 'created_at', 'updated_at',
                  # Profile fields
                  'description', 'banner_image_url', 'profile_image_url', 'website',
                  'twitter_handle', 'discord_handle', 'telegram_handle', 'linkedin_handle',
                  'github_username', 'github_linked_at',
                  'email', 'is_email_verified',
                  # Ban status
                  'is_banned', 'ban_reason',
                  # Social connections
                  'github_connection', 'twitter_connection', 'discord_connection',
                  # Referral fields
                  'referral_code', 'referred_by_info', 'total_referrals', 'referral_details',
                  # Working groups
                  'working_groups']
        read_only_fields = ['id', 'created_at', 'updated_at', 'referral_code']
    
    def get_validator(self, obj):
        """
        Get validator info using lightweight or full serializer based on context.
        """
        if not hasattr(obj, 'validator'):
            return None

        # Use lightweight serializer for nested/list views
        use_light = self.context.get('use_light_serializers', False)
        if use_light:
            return LightValidatorSerializer(obj.validator).data
        return ValidatorSerializer(obj.validator, context=self.context).data

    def get_builder(self, obj):
        """
        Get builder info using lightweight or full serializer based on context.
        """
        if not hasattr(obj, 'builder'):
            return None

        # Use lightweight serializer for nested/list views
        use_light = self.context.get('use_light_serializers', False)
        if use_light:
            return LightBuilderSerializer(obj.builder).data
        return BuilderSerializer(obj.builder, context=self.context).data

    def get_leaderboard_entry(self, obj):
        """
        Get the global leaderboard entry for this user.
        Returns rank and total_points if the entry exists, otherwise returns None.
        Skip for nested/list views to avoid N+1 queries.
        """
        # Skip expensive queries for nested/list views
        if self.context.get('use_light_serializers', False):
            return None

        try:
            # Get the validator leaderboard entry (default leaderboard)
            entry = LeaderboardEntry.objects.filter(user=obj, type='validator').first()
            if entry:
                return {
                    'rank': entry.rank,
                    'total_points': entry.total_points
                }
        except:
            pass
        return None
    
    def get_has_validator_waitlist(self, obj):
        """
        Check if user has the validator waitlist badge (contribution).
        Skip for nested/list views to avoid N+1 queries.
        """
        # Skip expensive queries for nested/list views
        if self.context.get('use_light_serializers', False):
            return False

        from contributions.models import Contribution, ContributionType

        try:
            waitlist_type = ContributionType.objects.get(slug='validator-waitlist')
            return Contribution.objects.filter(user=obj, contribution_type=waitlist_type).exists()
        except ContributionType.DoesNotExist:
            return False

    def get_has_builder_welcome(self, obj):
        """
        Check if user has the builder welcome badge (contribution).
        Skip for nested/list views to avoid N+1 queries.
        """
        # Skip expensive queries for nested/list views
        if self.context.get('use_light_serializers', False):
            return False

        from contributions.models import Contribution, ContributionType

        try:
            welcome_type = ContributionType.objects.get(slug='builder-welcome')
            return Contribution.objects.filter(user=obj, contribution_type=welcome_type).exists()
        except ContributionType.DoesNotExist:
            return False
    
    def get_email(self, obj):
        """
        Return email only if it's verified, otherwise return empty string.
        This prevents exposing auto-generated emails.
        """
        if obj.is_email_verified:
            return obj.email
        return ''
    
    def get_referred_by_info(self, obj):
        """
        Get information about who referred this user.
        Returns None if user was not referred.
        """
        if obj.referred_by:
            return {
                'id': obj.referred_by.id,
                'name': obj.referred_by.name or 'Anonymous',
                'address': obj.referred_by.address,
                'referral_code': obj.referred_by.referral_code
            }
        return None
    
    def get_total_referrals(self, obj):
        """
        Get the total number of users referred by this user.
        """
        return User.objects.filter(referred_by=obj).count()

    def get_referral_details(self, obj):
        """Referral breakdown. Only included when include_referral_details=True."""
        if not self.context.get('include_referral_details', False):
            return None
        from leaderboard.models import get_referral_breakdown
        return get_referral_breakdown(obj)

    def get_working_groups(self, obj):
        """
        Get list of working groups the user belongs to.
        """
        from stewards.models import WorkingGroupParticipant
        memberships = WorkingGroupParticipant.objects.filter(
            user=obj
        ).select_related('working_group')
        return [
            {
                'id': m.working_group.id,
                'name': m.working_group.name,
                'icon': m.working_group.icon,
                'description': m.working_group.description,
                'participant_count': m.working_group.participants.count(),
                'joined_at': m.created_at
            }
            for m in memberships
        ]

    def _get_social_connection(self, obj, related_name, serializer_class):
        try:
            connection = getattr(obj, related_name)
            return serializer_class(connection).data
        except Exception:
            return None

    def get_github_connection(self, obj):
        from social_connections.serializers import GitHubConnectionSerializer
        return self._get_social_connection(obj, 'githubconnection', GitHubConnectionSerializer)

    def get_twitter_connection(self, obj):
        from social_connections.serializers import TwitterConnectionSerializer
        return self._get_social_connection(obj, 'twitterconnection', TwitterConnectionSerializer)

    def get_discord_connection(self, obj):
        from social_connections.serializers import DiscordConnectionSerializer
        return self._get_social_connection(obj, 'discordconnection', DiscordConnectionSerializer)

    def get_github_username(self, obj):
        """Backward compat: read from GitHubConnection if available."""
        try:
            return obj.githubconnection.platform_username
        except Exception:
            return obj.github_username or ''

    def get_github_linked_at(self, obj):
        """Backward compat: read from GitHubConnection if available."""
        try:
            return obj.githubconnection.linked_at
        except Exception:
            return obj.github_linked_at


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


class BanAppealSerializer(serializers.ModelSerializer):
    """Serializer for user ban appeals."""
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.name', read_only=True)
    user_address = serializers.CharField(source='user.address', read_only=True)
    reviewed_by_email = serializers.CharField(
        source='reviewed_by.email', read_only=True, default=None,
    )

    class Meta:
        model = BanAppeal
        fields = [
            'id', 'user', 'user_email', 'user_name', 'user_address',
            'appeal_text', 'status',
            'reviewed_by', 'reviewed_by_email', 'reviewed_at', 'review_notes',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'user', 'status', 'reviewed_by', 'reviewed_at',
            'review_notes', 'created_at', 'updated_at',
        ]


class BanAppealReviewSerializer(serializers.Serializer):
    """Serializer for steward review of ban appeals."""
    action = serializers.ChoiceField(choices=['approve', 'deny'])
    review_notes = serializers.CharField(required=False, default='', allow_blank=True)