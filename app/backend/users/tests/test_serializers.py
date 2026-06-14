import pytest
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

from users.serializers import (
    UserRegistrationSerializer,
    CustomTokenObtainPairSerializer,
    UserAuthSerializer,
    ChangePasswordSerializer
)

User = get_user_model()


@pytest.mark.django_db
class TestUserRegistrationSerializer:
    """Test cases for UserRegistrationSerializer"""

    def test_valid_registration_data(self):
        """Test serializer with valid registration data"""
        data = {
            'email': 'newuser@example.com',
            'password': 'StrongPass123!',
            'password_confirm': 'StrongPass123!',
            'role': 1
        }
        serializer = UserRegistrationSerializer(data=data)
        assert serializer.is_valid()

    def test_password_mismatch(self):
        """Test that serializer rejects mismatched passwords"""
        data = {
            'email': 'user@example.com',
            'password': 'StrongPass123!',
            'password_confirm': 'DifferentPass456!',
            'role': 1
        }
        serializer = UserRegistrationSerializer(data=data)
        assert not serializer.is_valid()
        assert 'password' in serializer.errors

    def test_weak_password(self):
        """Test that serializer rejects weak passwords"""
        data = {
            'email': 'user@example.com',
            'password': '123',  # Too short
            'password_confirm': '123',
            'role': 1
        }
        serializer = UserRegistrationSerializer(data=data)
        assert not serializer.is_valid()
        assert 'password' in serializer.errors

    def test_invalid_email(self):
        """Test that serializer rejects invalid email"""
        data = {
            'email': 'not-an-email',
            'password': 'StrongPass123!',
            'password_confirm': 'StrongPass123!',
            'role': 1
        }
        serializer = UserRegistrationSerializer(data=data)
        assert not serializer.is_valid()
        assert 'email' in serializer.errors

    def test_create_user(self):
        """Test that serializer creates user correctly"""
        data = {
            'email': 'newuser@example.com',
            'password': 'StrongPass123!',
            'password_confirm': 'StrongPass123!',
            'role': 1
        }
        serializer = UserRegistrationSerializer(data=data)
        assert serializer.is_valid()
        user = serializer.save()

        assert user.email == 'newuser@example.com'
        assert user.check_password('StrongPass123!')
        assert user.role == 1
        assert user.is_active is True

    def test_default_role(self):
        """Test that default role is set if not provided"""
        data = {
            'email': 'user@example.com',
            'password': 'StrongPass123!',
            'password_confirm': 'StrongPass123!',
        }
        serializer = UserRegistrationSerializer(data=data)
        assert serializer.is_valid()


@pytest.mark.django_db
class TestCustomTokenObtainPairSerializer:
    """Test cases for CustomTokenObtainPairSerializer"""

    def test_token_contains_custom_claims(self):
        """Test that generated token contains custom claims"""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            role=1
        )
        # Use the custom serializer's get_token to include custom claims
        refresh = CustomTokenObtainPairSerializer.get_token(user)

        # Check custom claims in token
        assert refresh['email'] == 'test@example.com'
        assert refresh['role'] == 1

    def test_validate_adds_user_data(self):
        """Test that validate method adds user data to response"""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            role=1
        )

        serializer = CustomTokenObtainPairSerializer(data={
            'email': 'test@example.com',
            'password': 'testpass123'
        })

        assert serializer.is_valid()
        validated_data = serializer.validated_data

        assert 'access' in validated_data
        assert 'refresh' in validated_data
        assert 'user' in validated_data
        assert validated_data['user']['email'] == 'test@example.com'
        assert validated_data['user']['role'] == 1


@pytest.mark.django_db
class TestUserAuthSerializer:
    """Test cases for UserAuthSerializer"""

    def test_serializer_output(self):
        """Test that serializer outputs correct fields"""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            role=1
        )
        serializer = UserAuthSerializer(user)
        data = serializer.data

        assert 'id' in data
        assert 'email' in data
        assert 'role' in data
        assert data['email'] == 'test@example.com'
        assert data['role'] == 1
        assert 'password' not in data

    def test_read_only_fields(self):
        """Test that id field is read-only"""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            role=1
        )

        # Try to update id (should be ignored)
        serializer = UserAuthSerializer(
            user,
            data={'id': 999, 'email': 'test@example.com', 'role': 1},
            partial=True
        )
        assert serializer.is_valid()
        updated_user = serializer.save()
        assert updated_user.id == user.id  # ID should not change


@pytest.mark.django_db
class TestChangePasswordSerializer:
    """Test cases for ChangePasswordSerializer"""

    def test_valid_password_change(self):
        """Test serializer with valid password change data"""
        data = {
            'old_password': 'OldPass123!',
            'new_password': 'NewPass456!',
            'new_password_confirm': 'NewPass456!'
        }
        serializer = ChangePasswordSerializer(data=data)
        assert serializer.is_valid()

    def test_new_password_mismatch(self):
        """Test that serializer rejects mismatched new passwords"""
        data = {
            'old_password': 'OldPass123!',
            'new_password': 'NewPass456!',
            'new_password_confirm': 'DifferentPass789!'
        }
        serializer = ChangePasswordSerializer(data=data)
        assert not serializer.is_valid()
        assert 'new_password' in serializer.errors

    def test_weak_new_password(self):
        """Test that serializer rejects weak new passwords"""
        data = {
            'old_password': 'OldPass123!',
            'new_password': '123',
            'new_password_confirm': '123'
        }
        serializer = ChangePasswordSerializer(data=data)
        assert not serializer.is_valid()
        assert 'new_password' in serializer.errors
