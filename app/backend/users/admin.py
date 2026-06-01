from django.contrib import admin
from django.utils.html import format_html
from django.contrib import messages
from users.models import User, UserProfile, Organization, UserAPIKey


@admin.register(UserAPIKey)
class UserAPIKeyAdmin(admin.ModelAdmin):
    list_display = [
        'key_prefix_display',
        'name',
        'user_email',
        'created_at',
        'last_used_display',
        'expires_at',
        'is_active_badge',
    ]
    list_filter = ['is_active', 'created_at', 'user']
    search_fields = ['name', 'user__email', 'key_prefix']
    readonly_fields = [
        'key_hash',
        'key_prefix',
        'created_at',
        'last_used_at',
        'plaintext_key_display',
    ]

    fieldsets = (
        ('Key Information', {
            'fields': ('user', 'name', 'plaintext_key_display')
        }),
        ('Status', {
            'fields': ('is_active', 'expires_at')
        }),
        ('Audit', {
            'fields': ('key_prefix', 'key_hash', 'created_at', 'last_used_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['revoke_keys', 'activate_keys']

    def get_readonly_fields(self, request, obj=None):
        """Make user and name readonly after creation."""
        if obj:  # Editing existing
            return self.readonly_fields + ['user', 'name']
        return self.readonly_fields

    def key_prefix_display(self, obj):
        """Display key prefix with monospace font."""
        return format_html(
            '<code>{}</code>',
            f"{obj.key_prefix}..."
        )
    key_prefix_display.short_description = 'Key'

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User'
    user_email.admin_order_field = 'user__email'

    def last_used_display(self, obj):
        if obj.last_used_at:
            return obj.last_used_at.strftime('%Y-%m-%d %H:%M')
        return format_html('<span style="color: gray;">Never</span>')
    last_used_display.short_description = 'Last Used'

    def is_active_badge(self, obj):
        if obj.is_valid():
            return format_html('<span style="color: green;">✓ Active</span>')
        elif not obj.is_active:
            return format_html('<span style="color: red;">✗ Revoked</span>')
        else:
            return format_html('<span style="color: orange;">⚠ Expired</span>')
    is_active_badge.short_description = 'Status'

    def plaintext_key_display(self, obj):
        """
        Display plaintext key ONLY on creation.
        After save, it cannot be retrieved (only hash is stored).
        """
        if hasattr(obj, '_plaintext_key'):
            return format_html(
                '<div style="background: #ffe; padding: 10px; border: 2px solid #fa0; margin: 10px 0;">'
                '<strong>⚠️ COPY THIS KEY NOW - IT WILL NOT BE SHOWN AGAIN!</strong><br><br>'
                '<code style="font-size: 14px; user-select: all;">{}</code>'
                '</div>',
                obj._plaintext_key
            )
        return format_html(
            '<span style="color: gray;">Key is hashed and cannot be displayed. '
            'Generate a new key if needed.</span>'
        )
    plaintext_key_display.short_description = 'Plaintext API Key'

    def save_model(self, request, obj, form, change):
        """Generate API key on creation."""
        if not change:  # Creating new key
            api_key_obj, plaintext_key = UserAPIKey.create_key(
                user=obj.user,
                name=obj.name,
                expires_at=obj.expires_at
            )
            # Store plaintext key temporarily for display
            api_key_obj._plaintext_key = plaintext_key

            # Replace obj with the created one
            obj.pk = api_key_obj.pk
            obj.key_hash = api_key_obj.key_hash
            obj.key_prefix = api_key_obj.key_prefix
            obj._plaintext_key = plaintext_key

            messages.success(
                request,
                format_html(
                    'API Key created successfully. '
                    '<strong>Copy the key below and add it to the gateway configuration.</strong>'
                )
            )
        else:
            super().save_model(request, obj, form, change)

    def revoke_keys(self, request, queryset):
        """Revoke selected API keys."""
        count = queryset.update(is_active=False)
        self.message_user(request, f"Revoked {count} API key(s)")
    revoke_keys.short_description = "Revoke selected API keys"

    def activate_keys(self, request, queryset):
        """Activate selected API keys."""
        count = queryset.update(is_active=True)
        self.message_user(request, f"Activated {count} API key(s)")
    activate_keys.short_description = "Activate selected API keys"


class UserAPIKeyInline(admin.TabularInline):
    model = UserAPIKey
    extra = 0
    fields = ['key_prefix', 'name', 'is_active', 'created_at', 'last_used_at']
    readonly_fields = ['key_prefix', 'created_at', 'last_used_at']
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False  # Add via UserAPIKey admin to show plaintext key


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['email', 'role', 'is_active', 'is_staff', 'last_login']
    list_filter = ['role', 'is_active', 'is_staff']
    search_fields = ['email']
    inlines = [UserAPIKeyInline]


admin.site.register(UserProfile)
admin.site.register(Organization)


