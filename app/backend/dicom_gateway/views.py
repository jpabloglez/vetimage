"""
Views for DICOM Gateway Transfer Monitoring API.

This module provides REST API endpoints for monitoring DICOM transfers
at the study level with real-time statistics and filtering capabilities.
"""

from datetime import timedelta
from django.utils import timezone
from django.db.models import (
    Count, Sum, Avg, Min, Max, Q, F, Case, When, IntegerField
)
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, BasePermission
from rest_framework.pagination import PageNumberPagination

from .models import DICOMTransaction, PACSConfiguration
from dicom_images.models import MedicalStudy
from .serializers import (
    StudyTransferSerializer,
    TransferStatsSerializer,
    DICOMTransactionCreateSerializer
)


class TransferPagination(PageNumberPagination):
    """Custom pagination for transfer monitoring."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 200


class AllowInternalCreatePermission(BasePermission):
    """
    Allow POST requests without authentication (for internal service calls).
    Require authentication for GET/PUT/DELETE (admin access).
    """
    def has_permission(self, request, view):
        if request.method == 'POST':
            return True  # Allow internal service to create transactions
        return request.user and request.user.is_authenticated


class DICOMTransferViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API ViewSet for DICOM transfer monitoring.

    Provides study-level aggregation of DICOMTransaction records
    with privacy-aware organization filtering.

    Endpoints:
    - GET /api/dicom-gateway/transfers/monitor/ - Paginated transfer list
    - GET /api/dicom-gateway/transfers/stats/ - Transfer statistics

    Query Parameters (both endpoints):
    - date_from: ISO datetime (default: 24h ago)
    - date_to: ISO datetime (default: now)
    - status: success|partial|failed|in_progress
    - source_pacs: Filter by PACS AE title
    - modality: Filter by modality (CT, MR, etc.)
    - scope: own|colleagues|department|team (default: own)
    """

    permission_classes = [IsAuthenticated]
    pagination_class = TransferPagination

    def _parse_date_range(self, request):
        """Parse date_from and date_to query parameters."""
        date_to = request.query_params.get('date_to')
        date_from = request.query_params.get('date_from')

        if date_to:
            date_to = timezone.datetime.fromisoformat(date_to.replace('Z', '+00:00'))
        else:
            date_to = timezone.now()

        if date_from:
            date_from = timezone.datetime.fromisoformat(date_from.replace('Z', '+00:00'))
        else:
            date_from = date_to - timedelta(hours=24)

        return date_from, date_to

    def _get_base_queryset(self, request, date_from, date_to):
        """
        Get base queryset of DICOMTransaction records filtered by date range.

        Only includes incoming C-STORE transfers (received studies).
        """
        return DICOMTransaction.objects.filter(
            transaction_type='C-STORE',
            direction='incoming',
            started_at__gte=date_from,
            started_at__lte=date_to
        )

    def _aggregate_study_transfers(self, base_queryset):
        """
        Aggregate transactions by study_instance_uid.

        Returns study-level metrics including:
        - Instance counts (total, successful, failed, pending)
        - Size totals
        - Timing (first, last, average duration)
        - Source information
        """
        return base_queryset.values('study_instance_uid').annotate(
            # Instance counts
            total_instances=Count('id'),
            successful_instances=Count('id', filter=Q(status='success')),
            failed_instances=Count('id', filter=Q(status='failure')),
            pending_instances=Count('id', filter=Q(status='pending')),

            # Size
            total_size_bytes=Sum('file_size_bytes'),

            # Timing
            first_transfer_at=Min('started_at'),
            last_transfer_at=Max('completed_at'),
            avg_duration_ms=Avg('duration_ms'),

            # Source info (use first transaction's values)
            source_ae=F('source_ae'),
            source_ip=F('source_ip'),
            modality=F('modality'),
            patient_id_hash=F('patient_id_hash'),
        ).order_by('-first_transfer_at')

    def _calculate_transfer_status(self, transfer):
        """
        Calculate overall transfer status based on instance counts.

        Returns: 'success', 'partial', 'in_progress', or 'failed'
        """
        total = transfer['total_instances']
        successful = transfer['successful_instances']
        failed = transfer['failed_instances']
        pending = transfer['pending_instances']

        if pending > 0:
            return 'in_progress'
        elif failed == total and total > 0:
            return 'failed'
        elif failed > 0:
            return 'partial'
        else:
            return 'success'

    def _enrich_with_study_data(self, transfers):
        """
        Enrich transfer data with MedicalStudy information.

        Adds study_date, study_description, and uploaded_by information.
        """
        # Fetch all studies in one query
        study_uids = [t['study_instance_uid'] for t in transfers]
        studies = MedicalStudy.objects.filter(
            study_instance_uid__in=study_uids
        ).select_related('uploaded_by', 'uploaded_by__userprofile')

        # Create lookup dict
        study_lookup = {s.study_instance_uid: s for s in studies}

        # Enrich transfers
        for transfer in transfers:
            study = study_lookup.get(transfer['study_instance_uid'])

            if study:
                transfer['study_date'] = study.study_date
                transfer['study_description'] = study.study_description or ''
                transfer['uploaded_by'] = study.uploaded_by
            else:
                # Transfer in progress, study not created yet
                transfer['study_date'] = None
                transfer['study_description'] = 'In Progress'
                transfer['uploaded_by'] = None

            # Calculate total duration
            if transfer['last_transfer_at'] and transfer['first_transfer_at']:
                duration = transfer['last_transfer_at'] - transfer['first_transfer_at']
                transfer['total_duration_ms'] = int(duration.total_seconds() * 1000)
            else:
                transfer['total_duration_ms'] = None

            # Calculate status
            transfer['transfer_status'] = self._calculate_transfer_status(transfer)

            # Get PACS name
            try:
                if transfer['source_ae']:
                    pacs = PACSConfiguration.objects.filter(
                        ae_title=transfer['source_ae']
                    ).first()
                    transfer['source_pacs_name'] = pacs.name if pacs else transfer['source_ae']
                else:
                    transfer['source_pacs_name'] = 'Unknown'
            except:
                transfer['source_pacs_name'] = transfer['source_ae'] or 'Unknown'

        return transfers

    def _apply_organization_filter(self, transfers, request, scope):
        """
        Filter transfers based on organization scope.

        Scope options:
        - own: User's own transfers only (includes PACS transfers assigned to user)
        - colleagues: Organization colleagues who are sharing
        - department: Department members who are sharing
        - team: Team members who are sharing
        """
        if scope == 'own':
            # User's own transfers: uploaded by this user OR from PACS assigned to this user
            filtered = []
            for t in transfers:
                # Check direct upload
                if t.get('uploaded_by') and t['uploaded_by'].id == request.user.id:
                    filtered.append(t)
                    continue

                # Check PACS assignment
                source_ae = t.get('source_ae')
                if source_ae:
                    try:
                        pacs = PACSConfiguration.objects.filter(ae_title=source_ae).first()
                        if pacs and pacs.receiving_user_id == request.user.id:
                            filtered.append(t)
                    except:
                        pass
        elif scope in ['colleagues', 'department', 'team']:
            try:
                profile = request.user.userprofile
                org_id = profile.organization_id

                if not org_id:
                    # No organization, return only own
                    filtered = [t for t in transfers if t.get('uploaded_by') and t['uploaded_by'].id == request.user.id]
                else:
                    # Include own transfers and organization transfers
                    filtered = []
                    for t in transfers:
                        # Check direct upload by user
                        uploaded_by = t.get('uploaded_by')
                        if uploaded_by:
                            # Always include own
                            if uploaded_by.id == request.user.id:
                                filtered.append(t)
                                continue

                            # Check if user is sharing and in scope
                            try:
                                other_profile = uploaded_by.userprofile
                                if not other_profile.is_sharing_jobs_with_colleagues:
                                    continue

                                # Check organization match
                                if other_profile.organization_id != org_id:
                                    continue

                                # Check specific scope
                                if scope == 'colleagues':
                                    filtered.append(t)
                                    continue
                                elif scope == 'department' and other_profile.department == profile.department:
                                    filtered.append(t)
                                    continue
                                elif scope == 'team' and other_profile.team_name == profile.team_name:
                                    filtered.append(t)
                                    continue
                            except:
                                pass

                        # Check PACS-based organization membership
                        source_ae = t.get('source_ae')
                        if source_ae:
                            try:
                                pacs = PACSConfiguration.objects.filter(ae_title=source_ae).first()
                                if pacs and pacs.receiving_organization_id == org_id:
                                    # PACS belongs to same organization
                                    if scope == 'colleagues':
                                        filtered.append(t)
                                    elif scope == 'department' and pacs.receiving_user:
                                        # Check if PACS user is in same department
                                        pacs_profile = pacs.receiving_user.userprofile
                                        if pacs_profile.department == profile.department:
                                            filtered.append(t)
                                    elif scope == 'team' and pacs.receiving_user:
                                        # Check if PACS user is in same team
                                        pacs_profile = pacs.receiving_user.userprofile
                                        if pacs_profile.team_name == profile.team_name:
                                            filtered.append(t)
                            except:
                                pass
            except:
                # No profile, return only own
                filtered = [t for t in transfers if t.get('uploaded_by') and t['uploaded_by'].id == request.user.id]
        else:
            filtered = transfers

        return filtered

    @action(detail=False, methods=['get'])
    def monitor(self, request):
        """
        Study-level transfer monitoring with organization filtering.

        GET /api/dicom-gateway/transfers/monitor/

        Query Parameters:
        - date_from: ISO datetime (default: 24h ago)
        - date_to: ISO datetime (default: now)
        - status: success|partial|failed|in_progress
        - source_pacs: Filter by PACS AE title
        - modality: Filter by modality (CT, MR, etc.)
        - scope: own|colleagues|department|team (default: own)
        - page, page_size: Pagination

        Returns: Paginated list of study-level transfer aggregates
        """
        # Parse date range
        date_from, date_to = self._parse_date_range(request)

        # Get base queryset
        base_queryset = self._get_base_queryset(request, date_from, date_to)

        # Apply filters
        source_pacs = request.query_params.get('source_pacs')
        if source_pacs:
            base_queryset = base_queryset.filter(source_ae=source_pacs)

        modality = request.query_params.get('modality')
        if modality:
            base_queryset = base_queryset.filter(modality=modality)

        # Aggregate by study
        study_transfers = self._aggregate_study_transfers(base_queryset)

        # Convert to list for further processing
        transfers = list(study_transfers)

        # Enrich with study data
        transfers = self._enrich_with_study_data(transfers)

        # Apply status filter (after enrichment)
        status_filter = request.query_params.get('status')
        if status_filter:
            transfers = [t for t in transfers if t['transfer_status'] == status_filter]

        # Apply organization filter
        scope = request.query_params.get('scope', 'own')
        transfers = self._apply_organization_filter(transfers, request, scope)

        # Paginate
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(transfers, request)

        # Serialize
        serializer = StudyTransferSerializer(
            page,
            many=True,
            context={'request': request}
        )

        return paginator.get_paginated_response(serializer.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Transfer statistics for dashboard cards.

        GET /api/dicom-gateway/transfers/stats/

        Query Parameters:
        - date_from: ISO datetime (default: 24h ago)
        - date_to: ISO datetime (default: now)
        - scope: own|colleagues|department|team (default: own)

        Returns: Aggregate statistics including:
        - Total transfers, instances
        - Success/failure rates
        - Average transfer time
        - Total data received
        - Breakdowns by modality, source PACS, status
        """
        # Parse date range
        date_from, date_to = self._parse_date_range(request)

        # Get base queryset
        base_queryset = self._get_base_queryset(request, date_from, date_to)

        # Aggregate by study
        study_transfers = self._aggregate_study_transfers(base_queryset)
        transfers = list(study_transfers)

        # Enrich with study data
        transfers = self._enrich_with_study_data(transfers)

        # Apply organization filter
        scope = request.query_params.get('scope', 'own')
        transfers = self._apply_organization_filter(transfers, request, scope)

        # Calculate statistics
        total_transfers = len(transfers)
        total_instances = sum(t['total_instances'] for t in transfers)

        # Status counts
        successful_transfers = len([t for t in transfers if t['transfer_status'] == 'success'])
        failed_transfers = len([t for t in transfers if t['transfer_status'] == 'failed'])
        partial_transfers = len([t for t in transfers if t['transfer_status'] == 'partial'])
        in_progress_transfers = len([t for t in transfers if t['transfer_status'] == 'in_progress'])

        # Success rate
        success_rate = successful_transfers / total_transfers if total_transfers > 0 else 0.0

        # Average transfer time (only completed transfers)
        completed_transfers = [t for t in transfers if t['total_duration_ms'] is not None]
        if completed_transfers:
            avg_duration_ms = sum(t['total_duration_ms'] for t in completed_transfers) / len(completed_transfers)
            avg_transfer_time_seconds = avg_duration_ms / 1000.0
        else:
            avg_transfer_time_seconds = None

        # Total data received
        total_data_received_bytes = sum(t['total_size_bytes'] or 0 for t in transfers)

        # Breakdown by modality
        by_modality = {}
        for t in transfers:
            mod = t['modality'] or 'Unknown'
            by_modality[mod] = by_modality.get(mod, 0) + 1

        # Breakdown by source PACS
        by_source_pacs = {}
        for t in transfers:
            pacs = t['source_pacs_name'] or 'Unknown'
            by_source_pacs[pacs] = by_source_pacs.get(pacs, 0) + 1

        # Breakdown by status
        by_status = {
            'success': successful_transfers,
            'failed': failed_transfers,
            'partial': partial_transfers,
            'in_progress': in_progress_transfers,
        }

        # Serialize
        stats_data = {
            'total_transfers': total_transfers,
            'total_instances_received': total_instances,
            'successful_transfers': successful_transfers,
            'failed_transfers': failed_transfers,
            'partial_transfers': partial_transfers,
            'in_progress_transfers': in_progress_transfers,
            'success_rate': success_rate,
            'avg_transfer_time_seconds': avg_transfer_time_seconds,
            'total_data_received_bytes': total_data_received_bytes,
            'by_modality': by_modality,
            'by_source_pacs': by_source_pacs,
            'by_status': by_status,
        }

        serializer = TransferStatsSerializer(stats_data)
        return Response(serializer.data)


class DICOMTransactionViewSet(viewsets.ModelViewSet):
    """
    API ViewSet for creating DICOM transaction records.

    This endpoint is used by the DICOM gateway service to log
    individual DICOM transactions (C-STORE, C-FIND, etc.) for auditing
    and monitoring purposes.

    Endpoints:
    - POST /api/dicom-gateway/transactions/ - Create transaction record (no auth required - internal service)
    - GET /api/dicom-gateway/transactions/ - List transactions (admin only)
    - GET /api/dicom-gateway/transactions/{id}/ - Get transaction details (admin only)
    """

    queryset = DICOMTransaction.objects.all()
    serializer_class = DICOMTransactionCreateSerializer
    permission_classes = [AllowInternalCreatePermission]

    def get_queryset(self):
        """Filter transactions (admin can see all, others see own)"""
        user = self.request.user

        # Superusers can see all transactions
        if user.is_superuser:
            return DICOMTransaction.objects.all()

        # Regular users: placeholder for future filtering logic
        # For now, allow viewing all for debugging
        return DICOMTransaction.objects.all()

    def create(self, request, *args, **kwargs):
        """Create new DICOM transaction log entry with PACS config lookup."""

        # Extract source AE Title from request data
        source_ae = request.data.get('source_ae')

        # Lookup and populate pacs_config if available
        if source_ae:
            try:
                pacs_config = PACSConfiguration.objects.get(
                    ae_title=source_ae,
                    is_active=True
                )
                # Add to request data for serializer (use mutable copy)
                if hasattr(request.data, '_mutable'):
                    request.data._mutable = True
                request.data['pacs_config'] = str(pacs_config.id)
                if hasattr(request.data, '_mutable'):
                    request.data._mutable = False
            except PACSConfiguration.DoesNotExist:
                # No config found - that's OK, pacs_config will be null
                pass

        return super().create(request, *args, **kwargs)


@api_view(['GET'])
@permission_classes([AllowAny])  # Allow unauthenticated access from gateway
def pacs_lookup(request):
    """
    Lookup PACS configuration by AE Title and return node user API key confirmation.

    Query Parameters:
        ae_title: The DICOM AE Title to lookup

    Returns:
        200: {user_id: int, user_email: str, api_key_prefix: str, api_key_exists: bool,
              organization_id: int, pacs_name: str}
        404: PACS not configured or no node_user set
        400: Missing ae_title parameter

    Security Note:
        This endpoint confirms API key exists but doesn't return plaintext key.
        Admin must configure API key in gateway settings when generated.
    """
    from django.contrib.auth import get_user_model
    from users.models import UserAPIKey

    User = get_user_model()

    ae_title = request.query_params.get('ae_title')

    if not ae_title:
        return Response(
            {'error': 'ae_title parameter required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Lookup PACS configuration (use node_user instead of receiving_user)
        pacs_config = PACSConfiguration.objects.select_related('node_user').get(
            ae_title=ae_title,
            is_active=True
        )

        # Check if node_user is configured
        if not pacs_config.node_user:
            return Response(
                {'error': f'No node user configured for AE Title: {ae_title}'},
                status=status.HTTP_404_NOT_FOUND
            )

        user = pacs_config.node_user

        # Get active API key for this user
        try:
            api_key_obj = UserAPIKey.objects.filter(
                user=user,
                is_active=True
            ).order_by('-created_at').first()

            if not api_key_obj:
                return Response({
                    'error': f'No active API key found for user: {user.email}. '
                            f'Please generate an API key via Django admin.'
                }, status=status.HTTP_404_NOT_FOUND)

            # IMPORTANT: We can't return the plaintext key (only hash is stored)
            # Admin must configure the API key in gateway settings

            return Response({
                'user_id': user.id,
                'user_email': user.email,
                'api_key_prefix': api_key_obj.key_prefix,  # First 8 chars for verification
                'api_key_exists': True,
                'organization_id': pacs_config.receiving_organization_id,
                'pacs_name': pacs_config.name,
            })

        except Exception as e:
            return Response({
                'error': f'Error retrieving API key: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except PACSConfiguration.DoesNotExist:
        return Response(
            {'error': f'PACS configuration not found for AE Title: {ae_title}'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
