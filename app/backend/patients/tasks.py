"""
Celery tasks for the patients app.

Currently: vaccination due-date reminders.
"""
from celery import shared_task
from datetime import date, timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task(name='patients.tasks.send_vaccination_reminders')
def send_vaccination_reminders():
    """
    Run daily (scheduled via Celery beat at 08:00 UTC).

    Finds VaccinationRecords whose next_due_on falls exactly 14, 7, or 1 day
    from today and creates a Notification for the vet who last administered the
    vaccine — so they can reach out to the owner in time.

    Deduplication: a separate reminder_sent flag per window is not tracked yet;
    the task is idempotent per day (same due-date hit once per run window).
    """
    from patients.models import VaccinationRecord
    from credentials.models import Notification

    today = date.today()
    created_total = 0

    for window_days in (14, 7, 1):
        target = today + timedelta(days=window_days)
        records = (
            VaccinationRecord.objects
            .filter(next_due_on=target)
            .select_related('animal_patient__owner', 'administered_by')
        )

        for record in records:
            vet = record.administered_by
            if vet is None:
                continue

            animal = record.animal_patient
            message = (
                f"{animal.name}'s {record.vaccine_name} is due in "
                f"{window_days} day{'s' if window_days > 1 else ''} "
                f"({target.isoformat()})."
            )
            Notification.objects.create(
                user=vet,
                message=message,
                notification_type='warning',
                link=f'/patients?animal={animal.id}',
            )
            created_total += 1

    logger.info('send_vaccination_reminders: created %d notifications for %s', created_total, today)
    return created_total
