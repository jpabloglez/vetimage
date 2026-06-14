"""
Report Template Views
"""

from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import ReportTemplate
from .serializers_templates import (
    ReportTemplateSerializer,
    CreateReportTemplateSerializer,
)


class ReportTemplateViewSet(viewsets.ModelViewSet):
    """CRUD ViewSet for report templates."""

    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        qs = ReportTemplate.objects.filter(
            Q(is_default=True) | Q(created_by=self.request.user)
        )
        species = self.request.query_params.get('species')
        if species:
            qs = qs.filter(
                Q(species_filter=[]) | Q(species_filter__contains=species)
            )
        modality = self.request.query_params.get('modality')
        if modality:
            qs = qs.filter(
                Q(modality_filter=[]) | Q(modality_filter__contains=modality)
            )
        return qs

    def get_serializer_class(self):
        if self.action == 'create':
            return CreateReportTemplateSerializer
        return ReportTemplateSerializer

    def create(self, request, *args, **kwargs):
        serializer = CreateReportTemplateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save(
            created_by=request.user, is_default=False,
        )
        return Response(
            ReportTemplateSerializer(instance).data,
            status=status.HTTP_201_CREATED,
        )

    def destroy(self, request, *args, **kwargs):
        template = self.get_object()
        if template.is_default:
            return Response(
                {'error': 'Cannot delete system default templates.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=['get'], url_path='defaults')
    def defaults(self, request):
        """Return system default templates."""
        defaults = ReportTemplate.objects.filter(is_default=True)
        serializer = ReportTemplateSerializer(defaults, many=True)
        return Response(serializer.data)
