"""
Celery configuration for MAIO (Medical AI Analysis Orchestrator)

This module configures Celery for asynchronous task processing.
It handles AI job dispatch, monitoring, and cleanup tasks.
"""

import os
from celery import Celery
from celery.schedules import crontab

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

# Create Celery app
app = Celery('backend')

# Load configuration from Django settings with CELERY_ prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all installed apps
app.autodiscover_tasks()

# Configure periodic tasks (Celery Beat)
app.conf.beat_schedule = {
    'check-task-timeouts': {
        'task': 'ai_analysis.tasks.check_task_timeouts',
        'schedule': 600.0,  # Every 10 minutes
    },
    'cleanup-old-tasks': {
        'task': 'ai_analysis.tasks.cleanup_old_tasks',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM UTC
    },
    'sync-orchestrator-status': {
        'task': 'ai_analysis.tasks.sync_orchestrator_status',
        'schedule': 5.0,  # Every 5 seconds (polling interval)
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task for testing Celery setup"""
    print(f'Request: {self.request!r}')
