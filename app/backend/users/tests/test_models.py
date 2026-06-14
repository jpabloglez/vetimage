import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

User = get_user_model()


@pytest.mark.django_db
class TestUserModel:
    """Test cases for User model"""

    def test_create_user(self):
        """Test creating a user with email and password"""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            role=1
        )
        assert user.email == 'test@example.com'
        assert user.is_active is True
        assert user.is_staff is False
        assert user.is_superuser is False
        assert user.role == 1
        assert user.check_password('testpass123')

    def test_create_user_default_role(self):
        """Test creating a user with default role"""
        user = User.objects.create_user(
            email='user@example.com',
            password='testpass123'
        )
        assert user.role == 1  # Default role is User

    def test_create_superuser(self):
        """Test creating a superuser"""
        admin = User.objects.create_superuser(
            email='admin@example.com',
            password='adminpass123'
        )
        assert admin.email == 'admin@example.com'
        assert admin.is_active is True
        assert admin.is_staff is True
        assert admin.is_superuser is True
        assert admin.role == 3  # Admin role
        assert admin.check_password('adminpass123')

    def test_user_email_unique(self):
        """Test that user email must be unique"""
        User.objects.create_user(
            email='unique@example.com',
            password='testpass123'
        )
        with pytest.raises(IntegrityError):
            User.objects.create_user(
                email='unique@example.com',
                password='otherpass456'
            )

    def test_user_email_normalization(self):
        """Test that email is normalized (lowercase domain)"""
        email = 'test@EXAMPLE.COM'
        user = User.objects.create_user(
            email=email,
            password='testpass123'
        )
        assert user.email == 'test@example.com'

    def test_user_str_representation(self):
        """Test the string representation of user"""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        assert str(user) == 'test@example.com'

    def test_user_without_email_raises_error(self):
        """Test that creating user without email raises error"""
        with pytest.raises(ValueError):
            User.objects.create_user(
                email='',
                password='testpass123'
            )

    def test_password_hashing(self):
        """Test that password is hashed, not stored in plain text"""
        password = 'testpass123'
        user = User.objects.create_user(
            email='test@example.com',
            password=password
        )
        assert user.password != password
        assert user.password.startswith('pbkdf2_sha256$')
        assert user.check_password(password)

    def test_user_roles(self):
        """Test different user roles"""
        admin = User.objects.create_user(
            email='admin@example.com',
            password='testpass123',
            role=0
        )
        user = User.objects.create_user(
            email='user@example.com',
            password='testpass123',
            role=1
        )
        doctor = User.objects.create_user(
            email='doctor@example.com',
            password='testpass123',
            role=2
        )

        assert admin.role == 0
        assert user.role == 1
        assert doctor.role == 2

    def test_username_field_is_email(self):
        """Test that USERNAME_FIELD is set to email"""
        assert User.USERNAME_FIELD == 'email'
