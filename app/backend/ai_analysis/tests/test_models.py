"""
Tests for ai_analysis models.
"""

import pytest
from datetime import timedelta
from django.core.exceptions import ValidationError
from django.utils import timezone

from ai_analysis.models import AIModel, AnalysisTask


# ===========================================================================
# AIModel
# ===========================================================================


@pytest.mark.django_db
class TestAIModel:

    def test_creation(self, ai_model):
        assert ai_model.pk is not None
        assert ai_model.key == 'test-model-v1'
        assert ai_model.is_active is True

    def test_str_repr(self, ai_model):
        s = str(ai_model)
        assert 'Test Model' in s
        assert 'test-model-v1' in s

    def test_clean_invalid_connector_class(self, ai_model):
        ai_model.connector_class = 'NoDotsHere'
        with pytest.raises(ValidationError) as exc_info:
            ai_model.clean()
        assert 'connector_class' in exc_info.value.message_dict

    def test_clean_invalid_timeout(self, ai_model):
        ai_model.timeout_seconds = 0
        with pytest.raises(ValidationError) as exc_info:
            ai_model.clean()
        assert 'timeout_seconds' in exc_info.value.message_dict

    def test_clean_valid(self, ai_model):
        # Should not raise
        ai_model.clean()


# ===========================================================================
# AnalysisTask
# ===========================================================================


@pytest.mark.django_db
class TestAnalysisTask:

    def test_creation(self, analysis_task):
        assert analysis_task.pk is not None
        assert analysis_task.status == 'PENDING'

    def test_str_repr(self, analysis_task):
        s = str(analysis_task)
        assert 'Task' in s
        assert 'PENDING' in s

    @pytest.mark.parametrize('terminal_status', ['COMPLETED', 'FAILED', 'TIMEOUT', 'CANCELLED'])
    def test_is_terminal_true(self, analysis_task, terminal_status):
        analysis_task.status = terminal_status
        assert analysis_task.is_terminal is True

    @pytest.mark.parametrize('active_status', ['PENDING', 'QUEUED', 'DISPATCHED', 'PROCESSING'])
    def test_is_terminal_false(self, analysis_task, active_status):
        analysis_task.status = active_status
        assert analysis_task.is_terminal is False

    def test_can_retry_failed_under_limit(self, analysis_task):
        analysis_task.status = 'FAILED'
        analysis_task.retry_count = 0
        assert analysis_task.can_retry is True

    def test_can_retry_at_limit(self, analysis_task):
        analysis_task.status = 'FAILED'
        analysis_task.retry_count = analysis_task.model.max_retries
        assert analysis_task.can_retry is False

    def test_can_retry_pending(self, analysis_task):
        analysis_task.status = 'PENDING'
        assert analysis_task.can_retry is False

    def test_can_retry_no_model(self, analysis_task):
        analysis_task.model = None
        analysis_task.status = 'FAILED'
        assert analysis_task.can_retry is False

    def test_processing_duration_with_times(self, analysis_task):
        now = timezone.now()
        analysis_task.started_processing_at = now - timedelta(seconds=120)
        analysis_task.completed_at = now
        assert analysis_task.processing_duration == pytest.approx(120.0, abs=1)

    def test_processing_duration_without_times(self, analysis_task):
        assert analysis_task.processing_duration is None

    def test_total_duration(self, analysis_task):
        analysis_task.completed_at = analysis_task.created_at + timedelta(seconds=300)
        assert analysis_task.total_duration == pytest.approx(300.0, abs=1)

    def test_webhook_secret_auto_generation(self, analysis_task):
        assert analysis_task.webhook_secret
        assert len(analysis_task.webhook_secret) == 64  # 32 bytes hex = 64 chars
