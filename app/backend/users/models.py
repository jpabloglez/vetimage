import hashlib
import hmac
import secrets
import uuid
from datetime import timedelta
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager
)

# Create your models here.

ROLES = (
    (1, 'Veterinarian'),
    (2, 'Guest'),
    (3, 'Clinic Admin'),
    (4, 'Veterinary Radiologist'),
    (5, 'Superuser'),
    (6, 'Pet Owner'),
)

# Role id for pet-owner portal accounts (see patients/views_portal.py).
PET_OWNER_ROLE = 6

# Role id that may manage clinic membership — see core.permissions.IsClinicAdmin.
CLINIC_ADMIN_ROLE = 3


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


class Clinic(models.Model):
    """
    A veterinary clinic — the tenant every record belongs to.

    One clinic is one customer. Staff are attached via `UserProfile.clinic`,
    and that membership is what scopes access to patients, studies, reports
    and referrals (see `dicom_images.scoping`).

    `user` is the account that created the clinic (usually whoever registered
    first). It is a bookkeeping/ownership pointer only — it grants nothing and
    takes no part in access control; membership does that.
    """

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='owned_clinics',
        help_text='Account that created this clinic. Not used for access control.',
    )
    name = models.CharField(max_length=80)
    address = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    billing_address = models.CharField(max_length=100)
    billing_code = models.CharField(max_length=100)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['name']
        indexes = [models.Index(fields=['name'])]

    def __str__(self):
        return self.name

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    clinic = models.ForeignKey(
        Clinic, on_delete=models.CASCADE, null=True, related_name='staff',
    )
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

    # Monitor page: department/team clinic
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
        help_text="Allow colleagues in same clinic to view your analysis jobs"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['clinic', 'is_sharing_jobs_with_colleagues', 'department']),
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
        """Verify a plaintext key against this instance's hash (constant time)."""
        return hmac.compare_digest(self.hash_key(plaintext_key), self.key_hash)

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


class ClinicInvitation(models.Model):
    """
    An invitation for someone to join a clinic as a member of staff.

    Accepting one grants immediate access to every patient, study and report in
    that clinic, so this is a privilege grant rather than a notification. It is
    therefore issued only by a Clinic Admin, single-use, and expiring — the same
    properties the WebSocket tickets and share links rely on.

    `role` is constrained to clinical roles at the serializer. Platform access
    (`is_staff`) is never grantable here: an invitation must not become a route
    into every other clinic's data.
    """

    DEFAULT_TTL_DAYS = 7

    clinic = models.ForeignKey(
        Clinic, on_delete=models.CASCADE, related_name='invitations',
    )
    email = models.EmailField()
    role = models.PositiveBigIntegerField(choices=ROLES, default=1)
    token = models.UUIDField(unique=True, default=uuid.uuid4, db_index=True)
    invited_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='sent_invitations',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    # Set on redemption — this is what makes the token single-use.
    accepted_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['clinic', '-created_at']),
            models.Index(fields=['email']),
        ]

    def __str__(self):
        return f'Invitation for {self.email} to {self.clinic.name}'

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=self.DEFAULT_TTL_DAYS)
        super().save(*args, **kwargs)

    @property
    def is_pending(self):
        return (
            self.accepted_at is None
            and self.revoked_at is None
            and self.expires_at > timezone.now()
        )

    @property
    def status(self):
        if self.accepted_at:
            return 'accepted'
        if self.revoked_at:
            return 'revoked'
        if self.expires_at <= timezone.now():
            return 'expired'
        return 'pending'
