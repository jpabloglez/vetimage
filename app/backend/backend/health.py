"""
Health check endpoints for Docker orchestration and monitoring.
"""

from django.core.cache import cache
from django.db import connection
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status


@api_view(['GET'])
@permission_classes([AllowAny])
def health_liveness(request):
    """
    Liveness probe — confirms the Django process is running.
    GET /api/health/
    """
    return Response({'status': 'ok'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def health_readiness(request):
    """
    Readiness probe — checks database and Redis connectivity.
    GET /api/health/ready/
    """
    errors = {}

    # Check database
    try:
        connection.ensure_connection()
    except Exception as exc:
        errors['database'] = str(exc)

    # Check Redis / cache
    try:
        cache.set('health_check', 'ok', timeout=5)
        if cache.get('health_check') != 'ok':
            errors['cache'] = 'Cache read-back failed'
    except Exception as exc:
        errors['cache'] = str(exc)

    if errors:
        return Response(
            {'status': 'unavailable', 'errors': errors},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return Response({'status': 'ok'}, status=status.HTTP_200_OK)
