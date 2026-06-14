"""
Tests for the nnU-Net Universal Connector and run_nnunet_inference Celery task.

Covers:
- NNUNetConnector.prepare_input()      — DICOM → NIfTI layout
- NNUNetConnector.dispatch_job()       — schedules inference task
- NNUNetConnector.build_predict_command() — CLI construction
- NNUNetConnector.validate_parameters() — metadata guard
- run_nnunet_inference()               — full subprocess pipeline (mocked)
"""

import json
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

from ai_analysis.connectors.nnunet import NNUNetConnector


# ─── Fixtures ────────────────────────────────────────────────────────────────


def _make_model(tmp_path, dataset_id="Dataset010_Liver", extra_meta=None):
    """Return a lightweight AIModel mock configured for NNUNetConnector."""
    model = MagicMock()
    model.key = "stunet-s-v1"
    model.name = "STU-Net-S"
    model.timeout_seconds = 3600
    model.metadata = {"nnunet_dataset_id": dataset_id, **(extra_meta or {})}
    model.label_map = {"1": "liver", "2": "spleen"}
    return model


def _make_task(tmp_path, model=None, has_file=True):
    """Return an AnalysisTask mock with an optional input image file."""
    if model is None:
        model = _make_model(tmp_path)

    task = MagicMock()
    task.id = uuid.uuid4()
    task.model = model
    task.parameters = {}

    if has_file:
        dicom_file = tmp_path / "input.dcm"
        dicom_file.write_bytes(b"\x00" * 128)

        file_field = MagicMock()
        file_field.name = str(dicom_file.relative_to(tmp_path))

        image = MagicMock()
        image.file = file_field

        task.input_image = image
    else:
        task.input_image = None

    return task


# ─── NNUNetConnector.build_predict_command ────────────────────────────────────


class TestBuildPredictCommand:

    def test_basic_command_structure(self):
        cmd = NNUNetConnector.build_predict_command(
            input_dir=Path("/in"),
            output_dir=Path("/out"),
            dataset_id="Dataset010",
        )
        assert "nnUNetv2_predict" in cmd
        assert "-i" in cmd and "/in" in cmd
        assert "-o" in cmd and "/out" in cmd
        assert "-d" in cmd and "Dataset010" in cmd
        assert "-c" in cmd and "3d_fullres" in cmd
        assert "-f" in cmd and "all" in cmd

    def test_custom_config_and_folds(self):
        cmd = NNUNetConnector.build_predict_command(
            input_dir=Path("/in"),
            output_dir=Path("/out"),
            dataset_id="Dataset291",
            config="3d_lowres",
            folds="0 1 2",
        )
        assert "3d_lowres" in cmd
        # Folds split into individual args
        assert "0" in cmd
        assert "1" in cmd
        assert "2" in cmd

    def test_extra_args_appended(self):
        cmd = NNUNetConnector.build_predict_command(
            input_dir=Path("/in"),
            output_dir=Path("/out"),
            dataset_id="Dataset010",
            extra_args=["--save_probabilities"],
        )
        assert "--save_probabilities" in cmd

    def test_no_extra_args_by_default(self):
        cmd = NNUNetConnector.build_predict_command(
            input_dir=Path("/in"),
            output_dir=Path("/out"),
            dataset_id="Dataset010",
        )
        assert "--save_probabilities" not in cmd


# ─── NNUNetConnector.validate_parameters ─────────────────────────────────────


class TestValidateParameters:

    def test_passes_with_dataset_id_in_metadata(self, tmp_path):
        model = _make_model(tmp_path)
        connector = NNUNetConnector(model)
        assert connector.validate_parameters({}) is True

    def test_raises_when_dataset_id_missing(self, tmp_path):
        model = _make_model(tmp_path, dataset_id=None)
        model.metadata = {}
        connector = NNUNetConnector(model)
        with pytest.raises(ValueError, match="nnunet_dataset_id"):
            connector.validate_parameters({})

    def test_raises_when_metadata_is_none(self, tmp_path):
        model = _make_model(tmp_path)
        model.metadata = None
        connector = NNUNetConnector(model)
        with pytest.raises(ValueError, match="nnunet_dataset_id"):
            connector.validate_parameters({})


# ─── NNUNetConnector.prepare_input ───────────────────────────────────────────


class TestPrepareInput:

    def test_raises_when_no_input_image(self, tmp_path, settings):
        settings.MEDIA_ROOT = str(tmp_path)
        model = _make_model(tmp_path)
        connector = NNUNetConnector(model)
        task = _make_task(tmp_path, model=model, has_file=False)
        with pytest.raises(ValueError, match="no input image"):
            connector.prepare_input(task)

    def test_raises_when_dicom_file_missing(self, tmp_path, settings):
        settings.MEDIA_ROOT = str(tmp_path)
        model = _make_model(tmp_path)
        connector = NNUNetConnector(model)

        task = MagicMock()
        task.id = uuid.uuid4()
        task.model = model
        file_field = MagicMock()
        file_field.name = "nonexistent/file.dcm"
        task.input_image = MagicMock()
        task.input_image.file = file_field

        with pytest.raises(ValueError, match="not found"):
            connector.prepare_input(task)

    def test_raises_on_dcm2niix_failure(self, tmp_path, settings):
        settings.MEDIA_ROOT = str(tmp_path)
        model = _make_model(tmp_path)
        connector = NNUNetConnector(model)
        task = _make_task(tmp_path, model=model)

        fake_result = MagicMock()
        fake_result.returncode = 1
        fake_result.stderr = "dcm2niix error"

        with patch("subprocess.run", return_value=fake_result):
            with pytest.raises(RuntimeError, match="dcm2niix failed"):
                connector.prepare_input(task)

    def test_returns_nnunet_input_dir_and_case_id(self, tmp_path, settings):
        settings.MEDIA_ROOT = str(tmp_path)
        model = _make_model(tmp_path)
        connector = NNUNetConnector(model)
        task = _make_task(tmp_path, model=model)

        # Simulate dcm2niix producing converted.nii.gz
        def fake_dcm2niix(cmd, **kw):
            out_dir = None
            for i, arg in enumerate(cmd):
                if arg == "-o":
                    out_dir = Path(cmd[i + 1])
            (out_dir / "converted.nii.gz").write_bytes(b"\x00" * 64)
            r = MagicMock()
            r.returncode = 0
            return r

        with patch("subprocess.run", side_effect=fake_dcm2niix):
            result = connector.prepare_input(task)

        assert "nnunet_input_dir" in result
        assert "nnunet_case_id" in result
        case_id = result["nnunet_case_id"]
        renamed = Path(result["nnunet_input_dir"]) / f"{case_id}_0000.nii.gz"
        assert renamed.is_file(), f"Expected nnU-Net input file at {renamed}"

    def test_uses_fallback_when_primary_missing(self, tmp_path, settings):
        """When converted.nii.gz doesn't exist, falls back to first *.nii.gz."""
        settings.MEDIA_ROOT = str(tmp_path)
        model = _make_model(tmp_path)
        connector = NNUNetConnector(model)
        task = _make_task(tmp_path, model=model)

        def fake_dcm2niix(cmd, **kw):
            out_dir = None
            for i, arg in enumerate(cmd):
                if arg == "-o":
                    out_dir = Path(cmd[i + 1])
            # No "converted.nii.gz" — different naming
            (out_dir / "converteda.nii.gz").write_bytes(b"\x00" * 64)
            r = MagicMock()
            r.returncode = 0
            return r

        with patch("subprocess.run", side_effect=fake_dcm2niix):
            result = connector.prepare_input(task)

        case_id = result["nnunet_case_id"]
        renamed = Path(result["nnunet_input_dir"]) / f"{case_id}_0000.nii.gz"
        assert renamed.is_file()

    def test_raises_when_no_nifti_produced(self, tmp_path, settings):
        settings.MEDIA_ROOT = str(tmp_path)
        model = _make_model(tmp_path)
        connector = NNUNetConnector(model)
        task = _make_task(tmp_path, model=model)

        def fake_dcm2niix(cmd, **kw):
            r = MagicMock()
            r.returncode = 0
            return r  # No files written

        with patch("subprocess.run", side_effect=fake_dcm2niix):
            with pytest.raises(RuntimeError, match="no NIfTI file found"):
                connector.prepare_input(task)


# ─── NNUNetConnector.dispatch_job ─────────────────────────────────────────────


class TestDispatchJob:

    def test_raises_when_dataset_id_missing(self, tmp_path):
        model = _make_model(tmp_path)
        model.metadata = {}
        connector = NNUNetConnector(model)
        task = _make_task(tmp_path, model=model)
        with pytest.raises(ValueError, match="nnunet_dataset_id"):
            connector.dispatch_job(task)

    def test_schedules_inference_task_and_returns_job_id(self, tmp_path):
        model = _make_model(tmp_path)
        connector = NNUNetConnector(model)
        task = _make_task(tmp_path, model=model)

        with patch("ai_analysis.tasks.run_nnunet_inference.apply_async") as mock_apply:
            result = connector.dispatch_job(task)

        mock_apply.assert_called_once_with(
            args=[str(task.id)],
            queue="ai_jobs",
        )
        assert result["service_job_id"] == f"nnunet-{task.id}"
        assert result["status"] == "queued"


# ─── run_nnunet_inference Celery task ────────────────────────────────────────


@pytest.mark.django_db
class TestRunNnunetInference:

    def test_skips_nonexistent_task(self):
        from ai_analysis.tasks import run_nnunet_inference
        # Should not raise
        run_nnunet_inference(str(uuid.uuid4()))

    def test_fails_when_dataset_id_missing(self, completed_task):
        completed_task.model.metadata = {}
        completed_task.model.save()
        completed_task.parameters = {"nnunet_input_dir": "/some/dir", "nnunet_case_id": "abc"}
        completed_task.status = "DISPATCHED"
        completed_task.save()

        from ai_analysis.tasks import run_nnunet_inference
        run_nnunet_inference(str(completed_task.id))

        completed_task.refresh_from_db()
        assert completed_task.status == "FAILED"
        assert "nnunet_dataset_id" in completed_task.error_message

    def test_fails_when_input_dir_missing_from_parameters(self, completed_task):
        completed_task.model.metadata = {"nnunet_dataset_id": "Dataset010"}
        completed_task.model.save()
        completed_task.parameters = {}   # no nnunet_input_dir
        completed_task.status = "DISPATCHED"
        completed_task.save()

        from ai_analysis.tasks import run_nnunet_inference
        run_nnunet_inference(str(completed_task.id))

        completed_task.refresh_from_db()
        assert completed_task.status == "FAILED"
        assert "nnunet_input_dir" in completed_task.error_message

    def test_fails_on_nonzero_return_code(self, completed_task, tmp_path, settings):
        settings.MEDIA_ROOT = str(tmp_path)

        in_dir = tmp_path / "nnunet_inputs" / f"task_{completed_task.id}"
        in_dir.mkdir(parents=True)
        (in_dir / "abc_0000.nii.gz").write_bytes(b"\x00" * 64)

        completed_task.model.metadata = {"nnunet_dataset_id": "Dataset010"}
        completed_task.model.save()
        completed_task.parameters = {
            "nnunet_input_dir": str(in_dir),
            "nnunet_case_id":   "abc",
        }
        completed_task.status = "DISPATCHED"
        completed_task.save()

        fake_result = MagicMock()
        fake_result.returncode = 1
        fake_result.stdout = ""
        fake_result.stderr = "nnUNet error: model not found"

        with patch("subprocess.run", return_value=fake_result):
            from ai_analysis.tasks import run_nnunet_inference
            run_nnunet_inference(str(completed_task.id))

        completed_task.refresh_from_db()
        assert completed_task.status == "FAILED"
        assert "nnUNetv2_predict failed" in completed_task.error_message

    def test_completes_and_stores_result_path(self, completed_task, tmp_path, settings):
        settings.MEDIA_ROOT = str(tmp_path)

        in_dir = tmp_path / "nnunet_inputs" / f"task_{completed_task.id}"
        in_dir.mkdir(parents=True)
        case_id = str(completed_task.id)[:8]
        (in_dir / f"{case_id}_0000.nii.gz").write_bytes(b"\x00" * 64)

        completed_task.model.metadata = {
            "nnunet_dataset_id": "Dataset010",
            "nnunet_config":     "3d_fullres",
        }
        completed_task.model.save()
        completed_task.parameters = {
            "nnunet_input_dir": str(in_dir),
            "nnunet_case_id":   case_id,
        }
        completed_task.status = "DISPATCHED"
        completed_task.save()

        def fake_predict(cmd, **kw):
            # Find -o arg and write the mask
            out_dir = None
            for i, arg in enumerate(cmd):
                if arg == "-o":
                    out_dir = Path(cmd[i + 1])
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / f"{case_id}.nii.gz").write_bytes(b"\x00" * 128)
            r = MagicMock()
            r.returncode = 0
            r.stdout = r.stderr = ""
            return r

        with patch("subprocess.run", side_effect=fake_predict):
            from ai_analysis.tasks import run_nnunet_inference
            run_nnunet_inference(str(completed_task.id))

        completed_task.refresh_from_db()
        assert completed_task.status == "COMPLETED"
        assert completed_task.result_file_path.endswith(f"{case_id}.nii.gz")
        assert completed_task.result_metadata["nnunet_dataset_id"] == "Dataset010"
        assert f"{case_id}.nii.gz" in completed_task.result_metadata["output_keys"]

    def test_uses_fallback_mask_when_case_id_file_absent(self, completed_task, tmp_path, settings):
        """If <case_id>.nii.gz is missing, the first nii.gz in output is used."""
        settings.MEDIA_ROOT = str(tmp_path)

        in_dir = tmp_path / "nnunet_inputs" / f"task_{completed_task.id}"
        in_dir.mkdir(parents=True)
        case_id = "xxxxxxxx"

        completed_task.model.metadata = {"nnunet_dataset_id": "Dataset010"}
        completed_task.model.save()
        completed_task.parameters = {
            "nnunet_input_dir": str(in_dir),
            "nnunet_case_id":   case_id,
        }
        completed_task.status = "DISPATCHED"
        completed_task.save()

        def fake_predict(cmd, **kw):
            out_dir = None
            for i, arg in enumerate(cmd):
                if arg == "-o":
                    out_dir = Path(cmd[i + 1])
            out_dir.mkdir(parents=True, exist_ok=True)
            # Different filename than case_id
            (out_dir / "prediction.nii.gz").write_bytes(b"\x00" * 64)
            r = MagicMock()
            r.returncode = 0
            r.stdout = r.stderr = ""
            return r

        with patch("subprocess.run", side_effect=fake_predict):
            from ai_analysis.tasks import run_nnunet_inference
            run_nnunet_inference(str(completed_task.id))

        completed_task.refresh_from_db()
        assert completed_task.status == "COMPLETED"
        assert completed_task.result_file_path.endswith("prediction.nii.gz")


# ─── Seed model entries ───────────────────────────────────────────────────────


@pytest.mark.django_db
class TestNNUNetSeedModels:
    """Verify seed_ai_models creates nnU-Net model entries correctly."""

    def test_stunet_s_seeded(self):
        from django.core.management import call_command
        call_command("seed_ai_models", verbosity=0)

        from ai_analysis.models import AIModel
        m = AIModel.objects.get(key="stunet-s-v1")
        assert m.connector_class == "ai_analysis.connectors.nnunet.NNUNetConnector"
        assert m.use_orchestrator is False
        assert m.metadata["nnunet_dataset_id"] is not None
        assert "1" in m.label_map   # liver

    def test_stunet_b_and_l_seeded(self):
        from django.core.management import call_command
        call_command("seed_ai_models", verbosity=0)

        from ai_analysis.models import AIModel
        for key in ("stunet-b-v1", "stunet-l-v1"):
            m = AIModel.objects.get(key=key)
            assert m.use_orchestrator is False
            assert m.metadata.get("nnunet_dataset_id")

    def test_misfm_seeded(self):
        from django.core.management import call_command
        call_command("seed_ai_models", verbosity=0)

        from ai_analysis.models import AIModel
        m = AIModel.objects.get(key="misfm-v1")
        assert m.connector_class == "ai_analysis.connectors.nnunet.NNUNetConnector"
        assert m.use_orchestrator is False
        assert m.supported_modalities == ["CT", "MRI"]
        assert "1" in m.label_map   # liver
        assert "8" in m.label_map   # stomach
