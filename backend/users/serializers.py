from rest_framework import serializers
from .models import User


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating user profile.
    Only allows updating the name field.
    """
    class Meta:
        model = User
        fields = ['name']
        

class UserSerializer(serializers.ModelSerializer):
    leaderboard_entry = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'name', 'address', 'visible', 'leaderboard_entry', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_leaderboard_entry(self, obj):
        """
        Get the leaderboard entry for this user.
        Returns rank and total_points if the entry exists, otherwise returns None.
        """
        try:
            if hasattr(obj, 'leaderboard_entry'):
                return {
                    'rank': obj.leaderboard_entry.rank,
                    'total_points': obj.leaderboard_entry.total_points
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