from django.contrib import admin
from .models import Owner, AnimalPatient, VHSMeasurement

admin.site.register(Owner)
admin.site.register(AnimalPatient)
admin.site.register(VHSMeasurement)
