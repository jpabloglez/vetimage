# Django Management Commands - Complete Guide

## Overview

This DICOM platform includes a comprehensive set of Django management commands for development, maintenance, diagnostics, and GDPR compliance. All commands feature beautiful Rich CLI formatting with colored output, tables, panels, and progress bars.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Development Commands](#development-commands)
3. [Diagnostic Commands](#diagnostic-commands)
4. [Maintenance Commands](#maintenance-commands)
5. [Command Reference](#command-reference)
6. [Service Layer](#service-layer)
7. [Automation with Cron](#automation-with-cron)
8. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Installation

Dependencies are already included in `setup/requirements.txt`:
```bash
rich==13.7.0           # Beautiful terminal formatting
faker==22.0.0          # Realistic fake data generation
```

Install in Docker container:
```bash
docker exec backend-xrays pip install -r /var/www/setup/requirements.txt
```

### First-Time Setup

For new developers, run this one command to set up everything:

```bash
docker exec backend-xrays python manage.py setup_project
```

This creates:
- Superuser account (admin@example.com / admin123)
- 3 demo users with realistic profiles
- Sample DICOM studies for each user

---

## Development Commands

### setup_project

**Purpose**: One-command setup for new developers

**Usage**:
```bash
# Default setup
docker exec backend-xrays python manage.py setup_project

# Custom superuser
docker exec backend-xrays python manage.py setup_project \
  --superuser-email=admin@mycompany.com \
  --superuser-password=SecurePass123

# Without sample data
docker exec backend-xrays python manage.py setup_project --skip-sample-data

# Dry run (preview only)
docker exec backend-xrays python manage.py setup_project --dry-run
```

**Options**:
- `--superuser-email`: Email for superuser (default: admin@example.com)
- `--superuser-password`: Password for superuser (default: admin123)
- `--demo-users`: Number of demo users (default: 3)
- `--skip-sample-data`: Don't create DICOM studies
- `--dry-run`: Preview without making changes

**Output Example**:
```
╭─────────────────────────────── Project Setup ────────────────────────────────╮
│ Setting up development environment                                           │
│ This will create users and sample data for testing                           │
╰──────────────────────────────────────────────────────────────────────────────╯
ℹ Creating superuser account...
✓ Created superuser: admin@example.com
ℹ   Password: admin123
```

---

### populate_db

**Purpose**: Generate large amounts of test data at scale

**Usage**:
```bash
# Default: 10 users, 5 studies each
docker exec backend-xrays python manage.py populate_db

# Large dataset
docker exec backend-xrays python manage.py populate_db \
  --users=100 \
  --studies-per-user=10 \
  --series-per-study=3 \
  --images-per-series=20

# Preview first
docker exec backend-xrays python manage.py populate_db --dry-run --users=50

# Skip confirmation
docker exec backend-xrays python manage.py populate_db --force
```

**Options**:
- `--users`: Number of users to create (default: 10)
- `--studies-per-user`: Studies per user (default: 5)
- `--series-per-study`: Series per study (default: 3)
- `--images-per-series`: Images per series (default: 10)
- `--force`: Skip confirmation prompt
- `--dry-run`: Preview totals without creating

**Calculation Example**:
```
10 users × 5 studies × 3 series × 10 images = 1,500 image records
```

**Note**: Creates database records only (no actual DICOM files). Perfect for testing search, pagination, and API performance.

---

## Diagnostic Commands

### check_data_integrity

**Purpose**: Verify database integrity and find orphaned records

**Usage**:
```bash
# Check only (read-only)
docker exec backend-xrays python manage.py check_data_integrity

# Check and fix automatically
docker exec backend-xrays python manage.py check_data_integrity --fix --force
```

**Options**:
- `--fix`: Automatically delete orphaned records
- `--force`: Skip confirmation when using --fix

**What It Checks**:
- Series without studies
- Images without series
- Annotations without images
- User profiles without users
- Missing files on disk
- Invalid file references

**Output Example**:
```
           Orphaned Records
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Type                       ┃ Count ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ Series without study       │ 0     │
│ Images without series      │ 3     │
│ Annotations without image  │ 0     │
│ User profiles without user │ 1     │
└────────────────────────────┴───────┘
```

---

### verify_storage

**Purpose**: Verify user storage quotas match actual usage

**Usage**:
```bash
# Check all users
docker exec backend-xrays python manage.py verify_storage

# Check specific user
docker exec backend-xrays python manage.py verify_storage \
  --user-email=user@example.com

# Fix discrepancies
docker exec backend-xrays python manage.py verify_storage --fix

# Dry run first
docker exec backend-xrays python manage.py verify_storage --fix --dry-run
```

**Options**:
- `--user-email`: Check specific user
- `--fix`: Recalculate and update quotas
- `--dry-run`: Preview changes

**Output Example**:
```
  Storage Quota Verification Results
┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━┓
┃ User Email          ┃ Reported ┃ Actual  ┃ Difference ┃ Status    ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━┩
│ user@example.com    │ 2.45 GB  │ 2.50 GB │ 50.00 MB   │ ⚠ Mismatch│
│ admin@example.com   │ 1.23 GB  │ 1.23 GB │ 0 B        │ ✓ Match   │
└─────────────────────┴──────────┴─────────┴────────────┴───────────┘
```

---

### check_dicom_metadata

**Purpose**: Validate DICOM files against database records

**Usage**:
```bash
# Check all files
docker exec backend-xrays python manage.py check_dicom_metadata

# Check limited number
docker exec backend-xrays python manage.py check_dicom_metadata --limit=100
```

**Options**:
- `--limit`: Maximum files to check (default: all)

**What It Validates**:
- File exists on disk
- File is valid DICOM
- SOP Instance UID matches
- Dimensions match database
- Required DICOM tags present

**Exit Code**: Returns 1 if invalid files found (useful for CI/CD)

---

## Maintenance Commands

### reset_demo_data

**Purpose**: Clear all data and restore clean demo state

**Usage**:
```bash
# Full reset (WARNING: DESTRUCTIVE)
docker exec backend-xrays python manage.py reset_demo_data --force

# Keep superusers
docker exec backend-xrays python manage.py reset_demo_data \
  --keep-superusers --force

# Preview first
docker exec backend-xrays python manage.py reset_demo_data --dry-run
```

**Options**:
- `--keep-superusers`: Don't delete superuser accounts
- `--force`: Skip confirmation
- `--dry-run`: Preview without deleting

**What It Does**:
1. Deletes all users (or non-superusers if --keep-superusers)
2. Deletes all studies, series, images (cascading)
3. Deletes storage quotas
4. Creates 3 new demo users
5. Generates sample DICOM data

**⚠️ WARNING**: This is destructive and cannot be undone!

---

### cleanup_old_logs

**Purpose**: Remove old Django sessions

**Usage**:
```bash
# Default: 30 days
docker exec backend-xrays python manage.py cleanup_old_logs

# Custom threshold
docker exec backend-xrays python manage.py cleanup_old_logs --days=60

# Dry run first
docker exec backend-xrays python manage.py cleanup_old_logs --days=30 --dry-run
```

**Options**:
- `--days`: Delete sessions older than this (default: 30)
- `--dry-run`: Preview without deleting

**Use Case**: Run periodically to prevent session table bloat

---

### delete_expired_tokens

**Purpose**: Clean up expired JWT refresh tokens

**Usage**:
```bash
# Delete expired tokens
docker exec backend-xrays python manage.py delete_expired_tokens

# Dry run first
docker exec backend-xrays python manage.py delete_expired_tokens --dry-run
```

**Options**:
- `--dry-run`: Preview without deleting

**What It Cleans**:
- Outstanding tokens past expiration
- Blacklisted tokens for expired tokens

**Note**: Requires `rest_framework_simplejwt.token_blacklist` in INSTALLED_APPS

---

### anonymize_data

**Purpose**: GDPR-compliant user data anonymization

**Usage**:
```bash
# Anonymize specific user
docker exec backend-xrays python manage.py anonymize_data \
  --email=user@example.com \
  --force

# Keep studies but anonymize patient names
docker exec backend-xrays python manage.py anonymize_data \
  --email=user@example.com \
  --keep-studies \
  --force

# Bulk anonymize inactive users
docker exec backend-xrays python manage.py anonymize_data \
  --inactive-days=365 \
  --force

# Preview first
docker exec backend-xrays python manage.py anonymize_data \
  --inactive-days=365 \
  --dry-run
```

**Options**:
- `--email`: Anonymize specific user
- `--inactive-days`: Anonymize users inactive for N days (default: 365)
- `--keep-studies`: Anonymize patient names instead of deleting studies
- `--force`: Skip confirmation
- `--dry-run`: Preview without anonymizing

**What It Does**:
- Replaces email with `anonymized_[id]@example.com`
- Sets user account as inactive
- Clears all PII from UserProfile (name, phone, address, etc.)
- Deletes profile image
- Deletes studies OR anonymizes patient names (if --keep-studies)

**⚠️ GDPR Compliance**:
- This operation is irreversible
- Log all anonymization actions
- Notify data protection officer
- Follow retention policies

---

## Command Reference

### Common Flags

All commands support these standard flags:

| Flag | Description |
|------|-------------|
| `--dry-run` | Preview changes without executing |
| `--force` | Skip confirmation prompts |
| `--no-color` | Disable colored output |
| `--verbosity` | Output detail level (0-3) |
| `--help` | Show command help |

### Command Summary Table

| Command | Category | Requires Confirmation | Supports Dry-Run | Atomic Transaction |
|---------|----------|----------------------|------------------|-------------------|
| setup_project | Development | No | Yes | Yes |
| populate_db | Development | Yes | Yes | Yes |
| check_data_integrity | Diagnostic | No (Yes with --fix) | No | No |
| verify_storage | Diagnostic | No | Yes | Yes |
| check_dicom_metadata | Diagnostic | No | No | No |
| reset_demo_data | Maintenance | Yes | Yes | Yes |
| cleanup_old_logs | Maintenance | No | Yes | Yes |
| delete_expired_tokens | Maintenance | No | Yes | Yes |
| anonymize_data | Maintenance | Yes | Yes | Yes |

---

## Service Layer

Commands use a **service layer pattern** where business logic lives in reusable service classes:

### Core Services (`core/services.py`)

**DataIntegrityService**:
- `check_orphaned_records()` - Find records with invalid FKs
- `check_invalid_file_references()` - Find missing files
- `fix_orphaned_records(dry_run)` - Delete orphaned data

**CleanupService**:
- `cleanup_old_sessions(days_old, dry_run)` - Remove old sessions
- `cleanup_blacklisted_tokens(dry_run)` - Clean JWT blacklist

### Users Services (`users/services.py`)

**UserCreationService**:
- `create_superuser(email, password, **kwargs)` - Create admin
- `create_demo_users(count)` - Generate test users with Faker

**AnonymizationService**:
- `anonymize_user(user_id, keep_studies)` - Single user anonymization
- `anonymize_inactive_users(inactive_days, dry_run)` - Bulk anonymization

### DICOM Services (`dicom_images/services.py`)

**DicomDataGenerationService**:
- `generate_study(user, modality, num_series, num_images_per_series)` - Create test data

**StorageVerificationService**:
- `verify_user_quota(user)` - Check single user
- `verify_all_quotas()` - Check all users
- `fix_user_quota(user, dry_run)` - Recalculate quota

**DicomMetadataValidationService**:
- `validate_dicom_file(image)` - Validate single file
- `validate_all_dicom_files(limit)` - Bulk validation

### Using Services Programmatically

```python
from users.services import UserCreationService
from dicom_images.services import DicomDataGenerationService

# Create a demo user
user = UserCreationService.create_demo_users(count=1)[0]

# Generate DICOM study
study = DicomDataGenerationService.generate_study(
    user=user,
    modality='CT',
    num_series=3,
    num_images_per_series=10
)
```

---

## Automation with Cron

### Recommended Cron Schedule

Add to server crontab for automated maintenance:

```bash
# Daily cleanup at 2 AM
0 2 * * * cd /app/backend && docker exec backend-xrays python manage.py cleanup_old_logs --days=30

# Weekly token cleanup on Sunday at 3 AM
0 3 * * 0 cd /app/backend && docker exec backend-xrays python manage.py delete_expired_tokens

# Monthly storage verification on 1st at 4 AM
0 4 1 * * cd /app/backend && docker exec backend-xrays python manage.py verify_storage --fix --force

# Weekly data integrity check on Monday at 5 AM
0 5 * * 1 cd /app/backend && docker exec backend-xrays python manage.py check_data_integrity

# Quarterly anonymization of 2-year inactive users
0 6 1 */3 * cd /app/backend && docker exec backend-xrays python manage.py anonymize_data --inactive-days=730 --force
```

### Monitoring Cron Jobs

Wrap commands with logging:

```bash
#!/bin/bash
# cleanup_cron.sh

LOG_FILE="/var/log/django_commands/cleanup.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$DATE] Starting cleanup..." >> $LOG_FILE
docker exec backend-xrays python manage.py cleanup_old_logs --days=30 >> $LOG_FILE 2>&1
EXIT_CODE=$?
echo "[$DATE] Finished with exit code: $EXIT_CODE" >> $LOG_FILE
```

---

## Troubleshooting

### Command Not Found

**Problem**: `Unknown command: 'setup_project'`

**Solution**:
1. Verify `'core'` is in `INSTALLED_APPS`:
   ```python
   # backend/settings.py
   INSTALLED_APPS = [
       # ...
       'core',
       'users',
       'dicom_images',
   ]
   ```

2. Check directory structure exists:
   ```bash
   ls app/backend/users/management/commands/
   ls app/backend/dicom_images/management/commands/
   ```

3. Ensure `__init__.py` files exist in all directories

---

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'rich'`

**Solution**:
```bash
docker exec backend-xrays pip install rich==13.7.0 faker==22.0.0
```

---

### Permission Denied

**Problem**: Cannot delete files or modify database

**Solution**: Ensure Django has appropriate permissions:
```bash
# Check media directory permissions
docker exec backend-xrays ls -la /var/www/app/backend/media/

# Fix if needed
docker exec backend-xrays chown -R www-data:www-data /var/www/app/backend/media/
```

---

### Transaction Errors

**Problem**: `TransactionManagementError` during command execution

**Solution**: Some commands set `use_atomic_transaction = False`. If you need transactions, modify the command:

```python
class Command(BaseRichCommand):
    use_atomic_transaction = True  # Enable transactions
```

---

### Memory Issues with Large Datasets

**Problem**: Out of memory when running `populate_db` with large numbers

**Solution**: Process in smaller batches:
```bash
# Instead of 1000 users at once
docker exec backend-xrays python manage.py populate_db --users=1000

# Do 10 batches of 100
for i in {1..10}; do
  docker exec backend-xrays python manage.py populate_db --users=100 --force
done
```

---

## Best Practices

### 1. Always Use --dry-run First

For destructive operations:
```bash
# See what will happen
docker exec backend-xrays python manage.py reset_demo_data --dry-run

# Then execute
docker exec backend-xrays python manage.py reset_demo_data --force
```

### 2. Keep Superusers Safe

When resetting data:
```bash
docker exec backend-xrays python manage.py reset_demo_data --keep-superusers --force
```

### 3. Regular Maintenance Schedule

- **Daily**: cleanup_old_logs
- **Weekly**: delete_expired_tokens, check_data_integrity
- **Monthly**: verify_storage --fix
- **Quarterly**: anonymize_data for GDPR compliance

### 4. Monitor Exit Codes

Commands return appropriate exit codes for automation:
```bash
docker exec backend-xrays python manage.py check_dicom_metadata
if [ $? -ne 0 ]; then
  echo "Validation failed! Alert administrator"
fi
```

### 5. Log All GDPR Actions

For compliance, log all anonymization:
```bash
docker exec backend-xrays python manage.py anonymize_data \
  --email=user@example.com \
  --force \
  | tee -a /var/log/gdpr_actions.log
```

---

## Examples

### Complete Development Setup

```bash
# 1. Initial setup
docker exec backend-xrays python manage.py setup_project

# 2. Add more test data
docker exec backend-xrays python manage.py populate_db \
  --users=20 \
  --studies-per-user=5 \
  --force

# 3. Verify everything
docker exec backend-xrays python manage.py check_data_integrity
docker exec backend-xrays python manage.py verify_storage
```

### Monthly Maintenance Routine

```bash
# 1. Clean up old data
docker exec backend-xrays python manage.py cleanup_old_logs --days=30
docker exec backend-xrays python manage.py delete_expired_tokens

# 2. Verify integrity
docker exec backend-xrays python manage.py check_data_integrity --fix --force
docker exec backend-xrays python manage.py verify_storage --fix --force

# 3. Anonymize inactive users (1+ year)
docker exec backend-xrays python manage.py anonymize_data \
  --inactive-days=365 \
  --dry-run  # Review first
```

### Fresh Start

```bash
# Complete reset to clean state
docker exec backend-xrays python manage.py reset_demo_data --force

# Or keep your superuser
docker exec backend-xrays python manage.py reset_demo_data \
  --keep-superusers \
  --force
```

---

## Support

For issues or questions:
1. Check command help: `python manage.py <command> --help`
2. Review logs: `docker-compose logs backend-xrays`
3. Verify configuration: `python manage.py check`
4. Run with verbosity: `python manage.py <command> --verbosity=3`

---

**Last Updated**: December 24, 2025
**Django Version**: 4.1
**Python Version**: 3.10+
