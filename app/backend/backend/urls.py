"""backend URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from files.views import ImageUploadView
from backend.views import get_frontend_config
from backend.health import health_liveness, health_readiness
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)


urlpatterns = [
    # API Schema and Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='api-schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='api-schema'), name='api-docs'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='api-schema'), name='api-redoc'),

    # Frontend Configuration
    path('api/config/', get_frontend_config, name='frontend-config'),

    # Health checks
    path('api/health/', health_liveness, name='health-liveness'),
    path('api/health/ready/', health_readiness, name='health-readiness'),

    # Admin and App URLs
    path('admin/', admin.site.urls),
    path('users/', include('users.urls')),
    path('files/', ImageUploadView.as_view()),
    path('api/dicom/', include('dicom_images.urls')),
    path('api/dicom-gateway/', include('dicom_gateway.urls')),  # DICOM Gateway Transfer Monitoring
    path('api/ai-analysis/', include('ai_analysis.urls')),  # AI Analysis Orchestrator
    path('api/credentials/', include('credentials.urls')),  # Enhanced Authentication & Session Tracking
    path('api/reports/', include('reports.urls')),  # Structured Reports & PDF Export
    path('api/patients/', include('patients.urls')),  # Veterinary patient registry
    path('api/portal/', include('patients.urls_portal')),  # Pet-owner portal (#21)
]

from django.conf.urls.static import static
from django.conf import settings

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)