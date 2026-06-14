"""
Drive one vet-thorax analysis task end-to-end against the live reference
service (#44). Used by `make ai-demo`.

Flow:
  1. Ensure the vet-thorax-cr-v1 model is registered (run seed_vet_models first).
  2. Synthesize a minimal demo study/series/image if none exists (the fixture
     service ignores pixel data).
  3. Create an AnalysisTask and dispatch it synchronously through the real
     connector -> live vet-thorax-service -> webhook callbacks.
  4. Poll the DB until the task reaches a terminal state and print the findings.

This proves the full dispatch -> webhook -> findings lifecycle without GPUs.
"""
import time

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Run a vet-thorax analysis end-to-end against the live reference service."

    def add_arguments(self, parser):
        parser.add_argument('--timeout', type=int, default=30,
                            help='Seconds to wait for the webhook to complete the task.')

    def handle(self, *args, **opts):
        from ai_analysis.models import AIModel, AnalysisTask
        from ai_analysis.tasks import dispatch_ai_job
        from dicom_images.models import MedicalStudy, MedicalSeries, MedicalImage
        from users.models import User

        try:
            model = AIModel.objects.get(key='vet-thorax-cr-v1')
        except AIModel.DoesNotExist:
            raise CommandError("vet-thorax-cr-v1 not found — run: manage.py seed_vet_models")

        user = User.objects.order_by('id').first()
        if user is None:
            raise CommandError("No users exist — create one first.")

        image = MedicalImage.objects.filter(series__modality__in=['CR', 'DX']).first()
        if image is None:
            self.stdout.write("No CR/DX image found — synthesizing a demo study…")
            study = MedicalStudy.objects.create(
                study_instance_uid='1.2.demo.vetthorax.1',
                patient_id='DEMO', patient_name='DEMO^DOG',
                study_description='Demo thoracic', uploaded_by=user, total_size_bytes=256,
            )
            series = MedicalSeries.objects.create(
                study=study, series_instance_uid='1.2.demo.vetthorax.1.1',
                series_number=1, series_description='Lateral', modality='CR',
            )
            image = MedicalImage.objects.create(
                series=series, sop_instance_uid='1.2.demo.vetthorax.1.1.1',
                sop_class_uid='1.2.840.10008.5.1.4.1.1.1', instance_number=1,
                file=SimpleUploadedFile('demo.dcm', b'\x00' * 256, content_type='application/dicom'),
                original_filename='demo.dcm', file_size_bytes=256,
            )

        task = AnalysisTask.objects.create(
            input_image=image, model=model, created_by=user,
            status='PENDING', parameters={'species': 'canine'},
        )
        self.stdout.write(f"Created task {task.id}; dispatching to {model.endpoint_url} …")

        # Dispatch synchronously (not .delay) so we surface errors immediately.
        dispatch_ai_job(str(task.id))

        deadline = time.time() + opts['timeout']
        while time.time() < deadline:
            task.refresh_from_db()
            if task.status in ('COMPLETED', 'FAILED', 'TIMEOUT'):
                break
            time.sleep(1)

        task.refresh_from_db()
        self.stdout.write(f"Final status: {task.status}")
        if task.status == 'COMPLETED':
            findings = (task.result_metadata or {}).get('findings', [])
            self.stdout.write(self.style.SUCCESS(f"Findings ({len(findings)}):"))
            for f in findings:
                self.stdout.write(
                    f"  • {f.get('label')} ({f.get('region')}) — confidence {f.get('confidence')}"
                )
            self.stdout.write(self.style.SUCCESS("AI pipeline end-to-end: OK"))
        else:
            self.stdout.write(self.style.ERROR(f"Task did not complete: {task.error_message}"))
            raise CommandError("Pipeline demo did not reach COMPLETED.")
