from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.password_validation import validate_password
from users.models import (
    User,
    UserProfile
)
from datetime import datetime
from django.utils import timezone
from django.utils.timesince import timesince

LANGUAGE_CHOICES = (
    ('en', 'English'),
    ('es', 'Spanish'),
    ('pt', 'Portuguese'),
)


class UserSerializer(serializers.ModelSerializer):

    #time_since_joined = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        #fields = ('id', 'email')
        #fields = '__all__'
        exclude = ('id', 'password')

    # def get_time_since_joined(self, object):
    #     join_data = object.created_at
    #     return timesince(join_data, datetime.now())

# class UserManagerSerializer(serializers.ModelSerializer):

#     days_active = serializers.SerializerMethodField()

#     class Meta:
#         model = UserManager
#         fields = '__all__'

#     def get_days_active(self, object):
#         join_data = object.created_at
#         return timesince(join_data, datetime.now())

class UserProfileSerializer(serializers.ModelSerializer):

    user = serializers.StringRelatedField(read_only=True)
    email = serializers.StringRelatedField(read_only=True, source='user.email')
    # role = serializers.StringRelatedField(read_only=True, source='user.role')
    time_since_joined = serializers.SerializerMethodField()
        
    class Meta:
        model = UserProfile
        #fields = ('id', 'name', 'email', 'phone', 'address', 
        # 'city', 'state', 'country', 'zip', 'image', 'created_at', 'updated_at', 'deleted_at')
        exclude = ('id',)
        # fields = '__all__'

    def get_time_since_joined(self, object):
        join_data = object.created_at
        return timesince(join_data, timezone.now())

    # Add validation to the serializer
    def validate(self, data):
        """ Check the provided language is valid """
        if data['language'] not in dict(LANGUAGE_CHOICES).keys():
            raise serializers.ValidationError("The provided language is not valid.")
        return data


# ============================================================================
# JWT Authentication Serializers
# ============================================================================


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = ('email', 'password', 'password_confirm', 'role')
        extra_kwargs = {
            'role': {'default': 1}  # Default to User role
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                "password": "Password fields didn't match."
            })
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        # create_user already sets is_active=True by default
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            role=validated_data.get('role', 1)
        )
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom token serializer with additional user data"""
    username_field = 'email'  # Use email instead of username

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims
        token['email'] = user.email
        token['role'] = user.role

        return token

    def validate(self, attrs):
        data = super().validate(attrs)

        # Add extra user data to response
        user_data = {
            'id': self.user.id,
            'email': self.user.email,
            'role': self.user.role,
        }

        # Include language preference from profile
        try:
            user_data['language'] = self.user.userprofile.language
        except Exception:
            user_data['language'] = 'en'

        data['user'] = user_data

        return data


class UserAuthSerializer(serializers.ModelSerializer):
    """Serializer for authenticated user profile"""
    language = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'email', 'role', 'language', 'image_url')
        read_only_fields = ('id',)

    def get_language(self, obj):
        try:
            return obj.userprofile.language
        except Exception:
            return 'en'

    def get_image_url(self, obj):
        try:
            if obj.userprofile.image:
                request = self.context.get('request')
                url = obj.userprofile.image.url
                return request.build_absolute_uri(url) if request else url
        except Exception:
            pass
        return None


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change"""
    old_password = serializers.CharField(required=True, style={'input_type': 'password'})
    new_password = serializers.CharField(
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        required=True,
        style={'input_type': 'password'}
    )

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                "new_password": "Password fields didn't match."
            })
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for password reset request (forgot password)"""
    email = serializers.EmailField(required=True)


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for password reset confirmation"""
    uid = serializers.CharField(required=True)
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        required=True,
        style={'input_type': 'password'}
    )

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                "new_password": "Password fields didn't match."
            })
        return attrs