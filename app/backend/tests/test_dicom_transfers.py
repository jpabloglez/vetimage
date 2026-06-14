from dicom_gateway.models import DICOMTransaction
from django.utils import timezone
from datetime import timedelta

recent = DICOMTransaction.objects.filter(
    started_at__gte=timezone.now() - timedelta(minutes=5)
).count()
print(f'New transactions in last 5 minutes: {recent}')
