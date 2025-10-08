from rest_framework import serializers
from disposable_email_domains import blocklist
from .models import User
from validators.models import Validator
from builders.models import Builder
from stewards.models import Steward
from creators.models import Creator
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
    total_contributions = serializers.SerializerMethodField()
    contribution_types = serializers.SerializerMethodField()
    
    class Meta:
        model = Validator
        fields = ['node_version', 'matches_target', 'target_version', 'target_date', 'target_created_at', 
                 'total_points', 'rank', 'total_contributions', 'contribution_types', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']
    
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
        """Get breakdown of contribution types for validator category."""
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


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating user profile.
    Allows updating name, profile fields, and validator node_version.
    """
    node_version = serializers.CharField(required=False, allow_blank=True, allow_null=True, source='validator.node_version')
    email = serializers.EmailField(required=False, allow_blank=True)
    website = serializers.CharField(required=False, allow_blank=True, max_length=200)

    class Meta:
        model = User
        fields = ['name', 'node_version', 'email', 'description', 'website',
                  'twitter_handle', 'discord_handle', 'telegram_handle', 'linkedin_handle',
                  'github_username']
    
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
        """Get breakdown of contribution types for builder."""
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
    validator = ValidatorSerializer(read_only=True)
    builder = BuilderSerializer(read_only=True)
    steward = StewardSerializer(read_only=True)
    creator = CreatorSerializer(read_only=True)
    has_validator_waitlist = serializers.SerializerMethodField()
    has_builder_welcome = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    
    # Referral system fields
    referred_by_info = serializers.SerializerMethodField()
    total_referrals = serializers.SerializerMethodField()
    referral_details = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'name', 'address', 'visible', 'leaderboard_entry', 'validator', 'builder', 'steward',
                  'creator', 'has_validator_waitlist', 'has_builder_welcome', 'created_at', 'updated_at',
                  # Profile fields
                  'description', 'banner_image_url', 'profile_image_url', 'website',
                  'twitter_handle', 'discord_handle', 'telegram_handle', 'linkedin_handle', 'github_username', 'github_linked_at',
                  'email', 'is_email_verified',
                  # Referral fields
                  'referral_code', 'referred_by_info', 'total_referrals', 'referral_details']
        read_only_fields = ['id', 'created_at', 'updated_at', 'referral_code', 'github_linked_at']
    
    def get_leaderboard_entry(self, obj):
        """
        Get the global leaderboard entry for this user.
        Returns rank and total_points if the entry exists, otherwise returns None.
        """
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
        """
        from contributions.models import Contribution, ContributionType
        
        try:
            waitlist_type = ContributionType.objects.get(slug='validator-waitlist')
            return Contribution.objects.filter(user=obj, contribution_type=waitlist_type).exists()
        except ContributionType.DoesNotExist:
            return False
    
    def get_has_builder_welcome(self, obj):
        """
        Check if user has the builder welcome badge (contribution).
        """
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
        """
        Get comprehensive referral information including list of referred users.
        Queries contribution points directly from Contribution table for accuracy.
        """
        from leaderboard.models import ReferralPoints
        from contributions.models import Contribution
        from django.db.models import Count, Sum

        # Get referrer's referral points
        try:
            rp = obj.referral_points
            builder_pts = rp.builder_points
            validator_pts = rp.validator_points
        except ReferralPoints.DoesNotExist:
            builder_pts = 0
            validator_pts = 0

        # Get all users referred by this user
        referred_users = User.objects.filter(
            referred_by=obj
        ).select_related('validator', 'builder').annotate(
            total_contributions=Count('contributions', distinct=True)
        )

        # Build the referral list with builder/validator breakdown
        # Optimize: bulk query all contributions instead of N+1 queries
        referred_user_ids = [u.id for u in referred_users]

        builder_points_by_user = {
            item['user_id']: item['total'] or 0
            for item in Contribution.objects.filter(
                user_id__in=referred_user_ids,
                contribution_type__category__slug='builder'
            ).values('user_id').annotate(total=Sum('frozen_global_points'))
        }

        validator_points_by_user = {
            item['user_id']: item['total'] or 0
            for item in Contribution.objects.filter(
                user_id__in=referred_user_ids,
                contribution_type__category__slug='validator'
            ).values('user_id').annotate(total=Sum('frozen_global_points'))
        }

        referral_list = []
        for referred_user in referred_users:
            builder_contribution_points = builder_points_by_user.get(referred_user.id, 0)
            validator_contribution_points = validator_points_by_user.get(referred_user.id, 0)
            total_points = builder_contribution_points + validator_contribution_points

            referral_list.append({
                'id': referred_user.id,
                'name': referred_user.name or 'Anonymous',
                'address': referred_user.address,
                'profile_image_url': referred_user.profile_image_url,
                'total_points': total_points,
                'builder_contribution_points': builder_contribution_points,
                'validator_contribution_points': validator_contribution_points,
                'created_at': referred_user.created_at,
                'total_contributions': referred_user.total_contributions,
                'is_validator': hasattr(referred_user, 'validator'),
                'is_builder': hasattr(referred_user, 'builder'),
            })

        # Sort by total points (highest first)
        referral_list.sort(key=lambda x: x['total_points'], reverse=True)

        return {
            'total_referrals': len(referral_list),
            'builder_points': builder_pts,
            'validator_points': validator_pts,
            'referrals': referral_list
        }


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