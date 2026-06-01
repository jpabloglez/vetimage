import secrets
import hashlib
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin
)

# Create your models here.
from django.contrib.auth.models import User

ROLES = (
    (1, 'User'),
    (2, 'Guest'),
    (3, 'Admin'),
    (4, 'Manager'),
    (5, 'Superuser')
)


class UserManager(BaseUserManager):

    def _create_user(self, email, password, is_active, is_staff, is_superuser, **extra_fields):
        if not email:
            raise ValueError('Users must have an email address')
        email = self.normalize_email(email)
        now = timezone.now()
        user = self.model(
            email=email,
            is_staff=is_staff,
            is_active=is_active,
            is_superuser=is_superuser,
            last_login=now,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        return self._create_user(email, password, True, False, False, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('role', 3)
        user = self._create_user(email, password, True, True, True, **extra_fields)
        return user

    def get_queryset(self):
        return super(UserManager, self).get_queryset()

class User(AbstractBaseUser):
    """ User Model """
    email = models.EmailField(unique=True)
    last_login = models.DateTimeField(default=timezone.now)
    role = models.PositiveBigIntegerField(choices=ROLES, default=1)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    #REQUIRED_FIELDS = []

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.email

    def has_perm(self, perm, obj=None):
        """ Does the user have a specific permission? """
        return True

    def has_module_perms(self, app_label):
        """ Does the user have permissions to view the app `app_label`? """
        return True

    # @property
    # def is_staff(self):
    #     """ Is the user a member of staff? """
    #     return self.is_staff

    # @property
    # def is_active(self):
    #     """ Is the user active? """
    #     return self.is_active

    # @property
    # def is_superuser(self):
    #     """ Is the user a admin member? """
    #     return self.is_superuser


class Organization(models.Model):
    """ 
    Organization to which users belong.
    Represents a company, institution, or group that users are associated with.

    Fields:
    - user: ForeignKey to the User model, indicating the owner or primary contact of the organization.
    - centre: CharField for the name of the organization or center.
    - address: CharField for the street address of the organization.
    - city: CharField for the city where the organization is located.
    - billing_address: CharField for the billing address of the organization.
    - billing_code: CharField for any billing or account code associated with the organization.
    - created_at: DateTimeField indicating when the organization record was created.
    - updated_at: DateTimeField indicating when the organization record was last updated.
    - deleted_at: DateTimeField indicating when the organization record was deleted (if applicable).

    """

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    centre = models.CharField(max_length=80)
    address = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    billing_address = models.CharField(max_length=100)
    billing_code = models.CharField(max_length=100)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.centre

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True)
    #organization = models.ForeignKey(
    #    Organization,
    #    on_delete=models.CASCADE,
    #    related_name='userprofile',
    #    null=True,)
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80, null=True)
    email = models.EmailField(max_length=80)
    phone = models.CharField(max_length=12, blank=True)
    address = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    zip = models.CharField(max_length=10, blank=True)
    language = models.CharField(
        max_length=24,
        default='en',
        choices=[('en', 'English'), ('es', 'Spanish'), ('pt', 'Portuguese')],
    )
    image = models.ImageField(upload_to='images/users', blank=True)

    # Monitor page: department/team organization
    department = models.CharField(
        max_length=100,
        blank=True,
        default='',
        db_index=True,
        help_text="Department or division (e.g., Radiology, Cardiology)"
    )
    job_title = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text="Job title or role (e.g., Radiologist, Technician)"
    )
    team_name = models.CharField(
        max_length=100,
        blank=True,
        default='',
        db_index=True,
        help_text="Team or group name for project-based work"
    )

    # Privacy control for job sharing
    is_sharing_jobs_with_colleagues = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Allow colleagues in same organization to view your analysis jobs"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['organization', 'is_sharing_jobs_with_colleagues', 'department']),
        ]

    def __str__(self):
        return f'{self.first_name} {self.last_name}'


class UserAPIKey(models.Model):
    """
    Long-lived API keys for service-to-service authentication (e.g., PACS connectors).

    Keys are hashed using SHA-256 before storage. Plaintext key is only shown once
    during creation via Django admin.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='api_keys',
        help_text='User that owns this API key'
    )
    name = models.CharField(
        max_length=100,
        help_text='Human-readable identifier (e.g., "Orthanc PACS Key")'
    )
    key_hash = models.CharField(
        max_length=64,
        unique=True,
        help_text='SHA-256 hash of the API key'
    )
    key_prefix = models.CharField(
        max_length=8,
        help_text='First 8 characters of key for display purposes'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Timestamp of last authentication with this key'
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Optional expiration date for key rotation'
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Inactive keys cannot be used for authentication'
    )

    class Meta:
        db_table = 'user_api_keys'
        ordering = ['-created_at']
        verbose_name = 'API Key'
        verbose_name_plural = 'API Keys'
        indexes = [
            models.Index(fields=['key_hash']),
            models.Index(fields=['user', 'is_active']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.name} ({self.key_prefix}...)"

    @staticmethod
    def generate_key() -> str:
        """
        Generate a cryptographically secure API key.

        Format: oml_<40 random characters>
        Total length: 44 characters
        """
        random_part = secrets.token_urlsafe(30)  # ~40 chars base64
        return f"oml_{random_part}"

    @staticmethod
    def hash_key(key: str) -> str:
        """Hash an API key using SHA-256."""
        return hashlib.sha256(key.encode()).hexdigest()

    @classmethod
    def create_key(cls, user, name: str, expires_at=None):
        """
        Create a new API key for a user.

        Returns tuple: (UserAPIKey instance, plaintext key)
        Plaintext key should be shown to admin ONCE and never stored.
        """
        plaintext_key = cls.generate_key()
        key_hash = cls.hash_key(plaintext_key)
        key_prefix = plaintext_key[:8]

        api_key = cls.objects.create(
            user=user,
            name=name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            expires_at=expires_at
        )

        return api_key, plaintext_key

    def verify_key(self, plaintext_key: str) -> bool:
        """Verify a plaintext key against this instance's hash."""
        return self.hash_key(plaintext_key) == self.key_hash

    def is_valid(self) -> bool:
        """Check if key is active and not expired."""
        if not self.is_active:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True

    def record_usage(self):
        """Update last_used_at timestamp."""
        self.last_used_at = timezone.now()
        self.save(update_fields=['last_used_at'])

