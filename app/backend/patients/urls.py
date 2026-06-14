from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    OwnerViewSet, AnimalPatientViewSet, VHSMeasurementViewSet,
    ClinicalVisitViewSet, VaccinationRecordViewSet,
    WeightRecordViewSet, AppointmentViewSet,
    PrescriptionViewSet, AllergyRecordViewSet,
    ClinicalPhotoViewSet, LabResultViewSet,
    ReproductiveEventViewSet,
    ReferringClinicViewSet, ReferralPackageViewSet, PublicReferralPackageView,
    MessageViewSet,
)

router = DefaultRouter()
router.register('owners',           OwnerViewSet,             basename='owner')
router.register('animals',          AnimalPatientViewSet,     basename='animal-patient')
router.register('vhs',              VHSMeasurementViewSet,    basename='vhs-measurement')
router.register('visits',           ClinicalVisitViewSet,     basename='clinical-visit')
router.register('vaccinations',     VaccinationRecordViewSet, basename='vaccination')
router.register('weights',          WeightRecordViewSet,      basename='weight-record')
router.register('appointments',     AppointmentViewSet,       basename='appointment')
router.register('prescriptions',    PrescriptionViewSet,      basename='prescription')
router.register('allergies',        AllergyRecordViewSet,     basename='allergy')
router.register('photos',           ClinicalPhotoViewSet,     basename='clinical-photo')
router.register('labs',             LabResultViewSet,         basename='lab-result')
router.register('reproductive',     ReproductiveEventViewSet, basename='reproductive-event')
router.register('referring-clinics', ReferringClinicViewSet,  basename='referring-clinic')
router.register('referral-packages', ReferralPackageViewSet,  basename='referral-package')
router.register('messages',          MessageViewSet,          basename='message')

urlpatterns = [
    # Public, unauthenticated referral landing — must precede the router so the
    # 'referrals' segment isn't shadowed by a viewset route.
    path('referrals/<uuid:token>/', PublicReferralPackageView.as_view(), name='public-referral'),
] + router.urls
