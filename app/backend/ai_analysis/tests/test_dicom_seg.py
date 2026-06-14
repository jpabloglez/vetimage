"""
Tests for the DICOM SEG creation service.

Covers:
- build_dcmqi_metadata()   — correct JSON structure for dcmqi
- _make_segment_attribute() — SNOMED CT code lookup
- write_source_dicoms()    — copies DICOM files to temp dir
- run_itkimage2segimage()  — subprocess wrapper (mocked)
- create_dicom_seg()       — full pipeline (mocked subprocess + file I/O)
- upload_dicom_to_orthanc() — Orthanc REST upload (mocked requests)
- create_dicom_seg_task()  — Celery task integration (mocked service layer)
"""

import json
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

from ai_analysis.services.dicom_seg import (
    _lookup_anatomy,
    _normalise_label,
    build_dcmqi_metadata,
    create_dicom_seg,
    run_itkimage2segimage,
    write_source_dicoms,
)


# ---------------------------------------------------------------------------
# Label normalisation & anatomy lookup
# ---------------------------------------------------------------------------

class TestNormaliseLabel:
    def test_lowercase(self):
        assert _normalise_label("Liver") == "liver"

    def test_spaces_to_underscores(self):
        assert _normalise_label("Right Kidney") == "right_kidney"

    def test_hyphens_to_underscores(self):
        assert _normalise_label("left-lung") == "left_lung"

    def test_already_normalised(self):
        assert _normalise_label("spleen") == "spleen"


class TestLookupAnatomy:
    def test_known_anatomical_structure(self):
        type_code, category = _lookup_anatomy("liver")
        assert type_code[0] == "10200004"
        assert type_code[1] == "SCT"
        assert type_code[2] == "Liver"
        assert category["CodeValue"] == "91723000"  # Anatomical Structure

    def test_known_lesion_uses_morphological_category(self):
        type_code, category = _lookup_anatomy("tumor")
        assert type_code[0] == "108369006"
        assert category["CodeValue"] == "49755003"  # Morphologically Abnormal Structure

    def test_unknown_falls_back_to_tissue(self):
        type_code, category = _lookup_anatomy("unknown_organ_xyz")
        assert type_code[0] == "85756007"  # Tissue
        assert category["CodeValue"] == "91723000"  # Anatomical Structure (not lesion)

    def test_case_insensitive(self):
        type_code1, _ = _lookup_anatomy("Spleen")
        type_code2, _ = _lookup_anatomy("spleen")
        assert type_code1 == type_code2


# ---------------------------------------------------------------------------
# build_dcmqi_metadata
# ---------------------------------------------------------------------------

class TestBuildDcmqiMetadata:
    def test_schema_present(self):
        meta = build_dcmqi_metadata({"1": "liver"})
        assert "$schema" in meta
        assert "dcmqi" in meta["$schema"]

    def test_required_top_level_fields(self):
        meta = build_dcmqi_metadata({"1": "liver"})
        for field in ("ContentCreatorName", "SeriesDescription", "SeriesNumber",
                      "InstanceNumber", "segmentAttributes"):
            assert field in meta, f"Missing field: {field}"

    def test_series_number_is_string(self):
        meta = build_dcmqi_metadata({"1": "liver"}, series_number=300)
        assert meta["SeriesNumber"] == "300"

    def test_segment_attributes_structure(self):
        """segmentAttributes must be a list-of-lists (one outer per NIfTI file)."""
        meta = build_dcmqi_metadata({"1": "liver", "2": "spleen"})
        attrs = meta["segmentAttributes"]
        # Two labels → two outer entries, each containing one segment dict
        assert len(attrs) == 2
        for outer in attrs:
            assert isinstance(outer, list)
            assert len(outer) == 1

    def test_label_ids_match_map_keys(self):
        meta = build_dcmqi_metadata({"1": "liver", "3": "pancreas"})
        label_ids = [outer[0]["labelID"] for outer in meta["segmentAttributes"]]
        assert sorted(label_ids) == [1, 3]

    def test_segment_has_required_keys(self):
        meta = build_dcmqi_metadata({"1": "spleen"})
        seg = meta["segmentAttributes"][0][0]
        required = {
            "labelID", "SegmentDescription", "SegmentAlgorithmType",
            "SegmentAlgorithmName", "recommendedDisplayRGBValue",
            "SegmentedPropertyCategoryCodeSequence",
            "SegmentedPropertyTypeCodeSequence",
        }
        assert required.issubset(seg.keys())

    def test_colour_rgb_format(self):
        meta = build_dcmqi_metadata({"1": "liver"})
        colour = meta["segmentAttributes"][0][0]["recommendedDisplayRGBValue"]
        assert isinstance(colour, list)
        assert len(colour) == 3
        assert all(0 <= c <= 255 for c in colour)

    def test_algorithm_name_propagated(self):
        meta = build_dcmqi_metadata({"1": "liver"}, algorithm_name="MyModel")
        seg = meta["segmentAttributes"][0][0]
        assert seg["SegmentAlgorithmName"] == "MyModel"

    def test_empty_label_map_raises(self):
        with pytest.raises(ValueError):
            build_dcmqi_metadata({})

    def test_labels_sorted_by_id(self):
        meta = build_dcmqi_metadata({"3": "pancreas", "1": "liver", "2": "spleen"})
        label_ids = [outer[0]["labelID"] for outer in meta["segmentAttributes"]]
        assert label_ids == [1, 2, 3]

    def test_snomed_code_for_liver(self):
        meta = build_dcmqi_metadata({"1": "liver"})
        type_seq = meta["segmentAttributes"][0][0]["SegmentedPropertyTypeCodeSequence"]
        assert type_seq["CodeValue"] == "10200004"
        assert type_seq["CodingSchemeDesignator"] == "SCT"

    def test_json_serialisable(self):
        meta = build_dcmqi_metadata({"1": "liver", "2": "right_kidney"})
        # Should not raise
        json.dumps(meta)


# ---------------------------------------------------------------------------
# write_source_dicoms
# ---------------------------------------------------------------------------

class TestWriteSourceDicoms:
    def _make_series(self, tmp_path, num_images=3):
        """Create a mock MedicalSeries with real temp files."""
        tmp_path.mkdir(parents=True, exist_ok=True)
        images = []
        for i in range(1, num_images + 1):
            dcm_file = tmp_path / f"img_{i:04d}.dcm"
            dcm_file.write_bytes(b"\x00" * 256)  # dummy content
            img = MagicMock()
            img.instance_number = i
            img.original_filename = dcm_file.name
            img.file = MagicMock()
            img.file.path = str(dcm_file)
            images.append(img)

        series = MagicMock()
        series.series_instance_uid = "1.2.3.4.5"
        qs = MagicMock()
        qs.order_by.return_value = images
        series.images = qs
        return series

    def test_copies_files_to_dest(self, tmp_path):
        series = self._make_series(tmp_path / "src", num_images=3)
        dest = tmp_path / "dest"
        count = write_source_dicoms(series, dest)
        assert count == 3
        assert len(list(dest.iterdir())) == 3

    def test_raises_when_no_files(self, tmp_path):
        series = MagicMock()
        qs = MagicMock()
        qs.order_by.return_value = []
        series.images = qs
        series.series_instance_uid = "1.2.3"
        with pytest.raises(RuntimeError, match="No DICOM files found"):
            write_source_dicoms(series, tmp_path / "dest")

    def test_skips_missing_files(self, tmp_path):
        """Images whose file.path does not exist on disk are skipped."""
        img_ok = MagicMock()
        ok_file = tmp_path / "ok.dcm"
        ok_file.write_bytes(b"\x00" * 64)
        img_ok.file.path = str(ok_file)
        img_ok.original_filename = "ok.dcm"
        img_ok.instance_number = 1

        img_bad = MagicMock()
        img_bad.file.path = "/nonexistent/path/bad.dcm"
        img_bad.original_filename = "bad.dcm"
        img_bad.instance_number = 2

        series = MagicMock()
        series.series_instance_uid = "1.2.3"
        qs = MagicMock()
        qs.order_by.return_value = [img_ok, img_bad]
        series.images = qs

        dest = tmp_path / "dest"
        count = write_source_dicoms(series, dest)
        assert count == 1


# ---------------------------------------------------------------------------
# run_itkimage2segimage
# ---------------------------------------------------------------------------

class TestRunItkimage2segimage:
    def test_success(self, tmp_path):
        nifti = tmp_path / "seg.nii.gz"
        nifti.write_bytes(b"\x00" * 32)
        dicom_dir = tmp_path / "dcms"
        dicom_dir.mkdir()
        meta_json = tmp_path / "meta.json"
        meta_json.write_text("{}")
        output = tmp_path / "out.dcm"

        with patch("subprocess.run") as mock_run:
            # Simulate itkimage2segimage producing the output file
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            output.write_bytes(b"\x00" * 128)  # fake output

            result = run_itkimage2segimage(nifti, dicom_dir, meta_json, output)

        assert result == output
        call_args = mock_run.call_args[0][0]
        assert "itkimage2segimage" in call_args
        assert "--useLabelIDAsSegmentNumber" in call_args
        assert str(nifti) in call_args

    def test_raises_on_nonzero_return_code(self, tmp_path):
        nifti = tmp_path / "seg.nii.gz"
        nifti.write_bytes(b"\x00" * 32)
        dicom_dir = tmp_path / "dcms"
        dicom_dir.mkdir()
        meta_json = tmp_path / "meta.json"
        meta_json.write_text("{}")
        output = tmp_path / "out.dcm"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1, stdout="", stderr="conversion error"
            )
            with pytest.raises(RuntimeError, match="itkimage2segimage failed"):
                run_itkimage2segimage(nifti, dicom_dir, meta_json, output)

    def test_raises_when_nifti_missing(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="NIfTI mask not found"):
            run_itkimage2segimage(
                tmp_path / "nonexistent.nii.gz",
                tmp_path / "dcms",
                tmp_path / "meta.json",
                tmp_path / "out.dcm",
            )

    def test_raises_when_output_not_produced(self, tmp_path):
        """rc=0 but output file not created — should still raise."""
        nifti = tmp_path / "seg.nii.gz"
        nifti.write_bytes(b"\x00")
        meta_json = tmp_path / "meta.json"
        meta_json.write_text("{}")
        output = tmp_path / "out.dcm"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            # output file is NOT created
            with pytest.raises(RuntimeError):
                run_itkimage2segimage(nifti, tmp_path, meta_json, output)


# ---------------------------------------------------------------------------
# create_dicom_seg — full pipeline (mocked)
# ---------------------------------------------------------------------------

class TestCreateDicomSeg:
    def _make_series(self, tmp_path):
        dcm_file = tmp_path / "slice.dcm"
        dcm_file.write_bytes(b"\x00" * 256)
        img = MagicMock()
        img.instance_number = 1
        img.original_filename = "slice.dcm"
        img.file = MagicMock()
        img.file.path = str(dcm_file)

        series = MagicMock()
        series.series_instance_uid = "1.2.3.4.5"
        qs = MagicMock()
        qs.order_by.return_value = [img]
        series.images = qs
        return series

    def test_creates_output_file(self, tmp_path, settings):
        settings.MEDIA_ROOT = str(tmp_path)
        series = self._make_series(tmp_path)
        nifti = tmp_path / "seg.nii.gz"
        nifti.write_bytes(b"\x00" * 64)
        label_map = {"1": "liver", "2": "spleen"}

        fake_output = None

        def fake_run_itkimage2segimage(nifti_path, dicom_dir, meta_path, output_path, **kw):
            # Simulate tool producing the output file
            output_path.write_bytes(b"\x00" * 512)
            nonlocal fake_output
            fake_output = output_path
            return output_path

        with patch(
            "ai_analysis.services.dicom_seg.run_itkimage2segimage",
            side_effect=fake_run_itkimage2segimage,
        ):
            result = create_dicom_seg(nifti, series, label_map)

        assert result.is_file()
        assert result.suffix == ".dcm"
        assert result.parent == tmp_path / "dicom_seg"

    def test_cleans_up_work_dir_on_success(self, tmp_path, settings):
        settings.MEDIA_ROOT = str(tmp_path)
        series = self._make_series(tmp_path)
        nifti = tmp_path / "seg.nii.gz"
        nifti.write_bytes(b"\x00" * 64)

        captured_work_dirs = []

        def fake_run(nifti_path, dicom_dir, meta_path, output_path, **kw):
            # Capture the work_dir (parent of dicom_dir)
            captured_work_dirs.append(dicom_dir.parent)
            output_path.write_bytes(b"\x00" * 64)
            return output_path

        with patch(
            "ai_analysis.services.dicom_seg.run_itkimage2segimage",
            side_effect=fake_run,
        ):
            create_dicom_seg(nifti, series, {"1": "liver"})

        # work_dir should be removed after success
        for wd in captured_work_dirs:
            assert not wd.exists(), f"Work dir {wd} was not cleaned up"

    def test_cleans_up_work_dir_on_failure(self, tmp_path, settings):
        settings.MEDIA_ROOT = str(tmp_path)
        series = self._make_series(tmp_path)
        nifti = tmp_path / "seg.nii.gz"
        nifti.write_bytes(b"\x00" * 64)

        captured_work_dirs = []

        def fake_run(nifti_path, dicom_dir, meta_path, output_path, **kw):
            captured_work_dirs.append(dicom_dir.parent)
            raise RuntimeError("tool failed")

        with patch(
            "ai_analysis.services.dicom_seg.run_itkimage2segimage",
            side_effect=fake_run,
        ):
            with pytest.raises(RuntimeError):
                create_dicom_seg(nifti, series, {"1": "liver"})

        for wd in captured_work_dirs:
            assert not wd.exists(), f"Work dir {wd} was not cleaned up after failure"

    def test_metadata_json_written(self, tmp_path, settings):
        settings.MEDIA_ROOT = str(tmp_path)
        series = self._make_series(tmp_path)
        nifti = tmp_path / "seg.nii.gz"
        nifti.write_bytes(b"\x00" * 64)

        written_meta = {}

        def fake_run(nifti_path, dicom_dir, meta_path, output_path, **kw):
            with open(meta_path) as f:
                written_meta.update(json.load(f))
            output_path.write_bytes(b"\x00" * 64)
            return output_path

        with patch(
            "ai_analysis.services.dicom_seg.run_itkimage2segimage",
            side_effect=fake_run,
        ):
            create_dicom_seg(nifti, series, {"1": "liver"})

        assert "$schema" in written_meta
        assert written_meta["segmentAttributes"][0][0]["labelID"] == 1


# ---------------------------------------------------------------------------
# upload_dicom_to_orthanc
# ---------------------------------------------------------------------------

class TestUploadDicomToOrthanc:
    def test_success(self, tmp_path, settings):
        settings.ORTHANC_URL = "http://orthanc:8042"
        settings.ORTHANC_USERNAME = "orthanc"
        settings.ORTHANC_PASSWORD = "orthanc"

        dcm_file = tmp_path / "test.dcm"
        dcm_file.write_bytes(b"\x00" * 256)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ID": "abc123",
            "Path": "/instances/abc123",
            "Status": "Success",
        }
        mock_response.raise_for_status.return_value = None

        with patch("requests.post", return_value=mock_response) as mock_post:
            from ai_analysis.services.orthanc_client import upload_dicom_to_orthanc
            result = upload_dicom_to_orthanc(dcm_file)

        assert result["ID"] == "abc123"
        assert result["Status"] == "Success"
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert call_kwargs[0][0] == "http://orthanc:8042/instances"
        assert call_kwargs[1]["headers"] == {"Content-Type": "application/dicom"}
        assert call_kwargs[1]["auth"] == ("orthanc", "orthanc")

    def test_raises_file_not_found(self, settings):
        settings.ORTHANC_URL = "http://orthanc:8042"
        from ai_analysis.services.orthanc_client import upload_dicom_to_orthanc
        with pytest.raises(FileNotFoundError):
            upload_dicom_to_orthanc(Path("/nonexistent/file.dcm"))

    def test_raises_on_http_error(self, tmp_path, settings):
        settings.ORTHANC_URL = "http://orthanc:8042"
        settings.ORTHANC_USERNAME = ""
        settings.ORTHANC_PASSWORD = ""
        dcm_file = tmp_path / "test.dcm"
        dcm_file.write_bytes(b"\x00" * 64)

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("HTTP 500")

        with patch("requests.post", return_value=mock_response):
            from ai_analysis.services.orthanc_client import upload_dicom_to_orthanc
            with pytest.raises(Exception, match="HTTP 500"):
                upload_dicom_to_orthanc(dcm_file)


# ---------------------------------------------------------------------------
# create_dicom_seg_task — Celery task
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
class TestTriggerDicomSegSignal:
    """Signal fires create_dicom_seg_task.delay when a segmentation task completes."""

    def test_triggers_on_completion_with_label_map(self, completed_task):
        completed_task.result_file_path = "ai_results/seg.nii.gz"
        completed_task.result_metadata = {}
        completed_task.model.label_map = {"1": "liver"}
        completed_task.model.save()

        with patch("ai_analysis.tasks.create_dicom_seg_task") as mock_task:
            mock_task.delay = MagicMock()
            completed_task.save()  # triggers signal

        mock_task.delay.assert_called_once_with(str(completed_task.id))

    def test_no_trigger_when_label_map_empty(self, completed_task):
        completed_task.result_file_path = "ai_results/seg.nii.gz"
        completed_task.result_metadata = {}
        completed_task.model.label_map = {}
        completed_task.model.save()

        with patch("ai_analysis.tasks.create_dicom_seg_task") as mock_task:
            mock_task.delay = MagicMock()
            completed_task.save()

        mock_task.delay.assert_not_called()

    def test_no_trigger_when_no_result_file(self, completed_task):
        completed_task.result_file_path = ""
        completed_task.result_metadata = {}
        completed_task.model.label_map = {"1": "liver"}
        completed_task.model.save()

        with patch("ai_analysis.tasks.create_dicom_seg_task") as mock_task:
            mock_task.delay = MagicMock()
            completed_task.save()

        mock_task.delay.assert_not_called()

    def test_no_trigger_when_already_processed(self, completed_task):
        """Idempotency: don't re-trigger if dicom_seg_series_uid already present."""
        completed_task.result_file_path = "ai_results/seg.nii.gz"
        completed_task.result_metadata = {"dicom_seg_series_uid": "1.2.3.4"}
        completed_task.model.label_map = {"1": "liver"}
        completed_task.model.save()

        with patch("ai_analysis.tasks.create_dicom_seg_task") as mock_task:
            mock_task.delay = MagicMock()
            completed_task.save()

        mock_task.delay.assert_not_called()

    def test_no_trigger_for_non_completed_status(self, analysis_task):
        analysis_task.model.label_map = {"1": "liver"}
        analysis_task.model.save()
        analysis_task.result_file_path = "ai_results/seg.nii.gz"
        analysis_task.status = "PROCESSING"

        with patch("ai_analysis.tasks.create_dicom_seg_task") as mock_task:
            mock_task.delay = MagicMock()
            analysis_task.save()

        mock_task.delay.assert_not_called()


@pytest.mark.django_db
class TestCreateDicomSegTask:
    def test_skips_when_no_result_file(self, completed_task):
        """Task with no result_file_path logs and returns without error."""
        completed_task.result_file_path = ""
        completed_task.save()

        from ai_analysis.tasks import create_dicom_seg_task
        with patch("ai_analysis.services.dicom_seg.create_dicom_seg") as mock_seg:
            create_dicom_seg_task(str(completed_task.id))
            mock_seg.assert_not_called()

    def test_skips_when_no_label_map(self, completed_task, tmp_path):
        """Task whose model.label_map is empty logs and returns without error."""
        completed_task.result_file_path = "ai_results/test.nii.gz"
        completed_task.save()
        completed_task.model.label_map = {}
        completed_task.model.save()

        from ai_analysis.tasks import create_dicom_seg_task
        with patch("ai_analysis.services.dicom_seg.create_dicom_seg") as mock_seg:
            create_dicom_seg_task(str(completed_task.id))
            mock_seg.assert_not_called()

    def test_stores_metadata_on_success(self, completed_task, tmp_path, settings):
        """Successful run stores dicom_seg_series_uid in result_metadata."""
        settings.MEDIA_ROOT = str(tmp_path)

        # Create a real NIfTI stub so path resolution works
        nifti_rel = "ai_results/seg.nii.gz"
        nifti_abs = tmp_path / nifti_rel
        nifti_abs.parent.mkdir(parents=True, exist_ok=True)
        nifti_abs.write_bytes(b"\x00" * 64)

        completed_task.result_file_path = nifti_rel
        completed_task.save()
        completed_task.model.label_map = {"1": "liver"}
        completed_task.model.save()

        fake_dcm = tmp_path / "dicom_seg" / "seg_abc.dcm"
        fake_dcm.parent.mkdir(parents=True, exist_ok=True)
        fake_dcm.write_bytes(b"\x00" * 64)

        mock_ds = MagicMock()
        mock_ds.SeriesInstanceUID = "1.2.840.10008.99.1"

        from ai_analysis.tasks import create_dicom_seg_task
        with patch("ai_analysis.services.dicom_seg.create_dicom_seg", return_value=fake_dcm), \
             patch("ai_analysis.services.orthanc_client.upload_dicom_to_orthanc",
                   return_value={"ID": "orthanc-uuid-001", "Status": "Success"}), \
             patch("pydicom.dcmread", return_value=mock_ds):
            create_dicom_seg_task(str(completed_task.id))

        completed_task.refresh_from_db()
        assert completed_task.result_metadata.get("dicom_seg_series_uid") == "1.2.840.10008.99.1"
        assert completed_task.result_metadata.get("dicom_seg_orthanc_id") == "orthanc-uuid-001"

    def test_nonexistent_task_id_returns_gracefully(self):
        """Non-existent task ID logs and returns without raising."""
        from ai_analysis.tasks import create_dicom_seg_task
        # Should not raise
        create_dicom_seg_task(str(uuid.uuid4()))


# ---------------------------------------------------------------------------
# run_segimage2itkimage
# ---------------------------------------------------------------------------

class TestRunSegimage2itkimage:
    """Unit tests for the segimage2itkimage subprocess wrapper."""

    def test_raises_if_input_missing(self, tmp_path):
        from ai_analysis.services.dicom_seg import run_segimage2itkimage
        with pytest.raises(FileNotFoundError):
            run_segimage2itkimage(
                dicom_seg_path=tmp_path / "nonexistent.dcm",
                output_dir=tmp_path / "out",
            )

    def test_raises_on_nonzero_returncode(self, tmp_path):
        from ai_analysis.services.dicom_seg import run_segimage2itkimage
        dcm = tmp_path / "input.dcm"
        dcm.write_bytes(b"\x00" * 64)

        fake_result = MagicMock()
        fake_result.returncode = 1
        fake_result.stdout = ""
        fake_result.stderr = "segimage2itkimage error"

        with patch("subprocess.run", return_value=fake_result):
            with pytest.raises(RuntimeError, match="segimage2itkimage failed"):
                run_segimage2itkimage(dcm, tmp_path / "out")

    def test_raises_when_no_output_files(self, tmp_path):
        from ai_analysis.services.dicom_seg import run_segimage2itkimage
        dcm = tmp_path / "input.dcm"
        dcm.write_bytes(b"\x00" * 64)
        out_dir = tmp_path / "out"
        out_dir.mkdir()

        fake_result = MagicMock()
        fake_result.returncode = 0
        fake_result.stdout = ""
        fake_result.stderr = ""

        with patch("subprocess.run", return_value=fake_result):
            with pytest.raises(RuntimeError, match="no NIfTI output"):
                run_segimage2itkimage(dcm, out_dir)

    def test_returns_segment_list_with_metadata(self, tmp_path):
        from ai_analysis.services.dicom_seg import run_segimage2itkimage
        dcm = tmp_path / "input.dcm"
        dcm.write_bytes(b"\x00" * 64)
        out_dir = tmp_path / "out"
        out_dir.mkdir()

        meta = {"segmentAttributes": [[{"labelID": 1, "SegmentDescription": "liver"}]]}

        def fake_run(cmd, **kw):
            # Simulate tool output: one merged NIfTI + JSON
            (out_dir / "seg.nii").write_bytes(b"\x00" * 128)
            (out_dir / "seg.json").write_text(json.dumps(meta))
            r = MagicMock()
            r.returncode = 0
            r.stdout = r.stderr = ""
            return r

        with patch("subprocess.run", side_effect=fake_run):
            segments = run_segimage2itkimage(dcm, out_dir, prefix="seg")

        assert len(segments) == 1
        assert segments[0]["nifti_path"].name == "seg.nii"
        assert segments[0]["metadata"] == meta
        assert segments[0]["metadata_path"].name == "seg.json"
        assert segments[0]["segment_number"] is None  # no trailing _N in "seg"

    def test_extracts_segment_number_from_filename(self, tmp_path):
        from ai_analysis.services.dicom_seg import run_segimage2itkimage
        dcm = tmp_path / "input.dcm"
        dcm.write_bytes(b"\x00" * 64)
        out_dir = tmp_path / "out"
        out_dir.mkdir()

        def fake_run(cmd, **kw):
            for n in (1, 2):
                (out_dir / f"seg_{n}.nii").write_bytes(b"\x00" * 64)
                (out_dir / f"seg_{n}.json").write_text(json.dumps({"segment": n}))
            r = MagicMock()
            r.returncode = 0
            r.stdout = r.stderr = ""
            return r

        with patch("subprocess.run", side_effect=fake_run):
            segments = run_segimage2itkimage(dcm, out_dir, prefix="seg", merge_segments=False)

        assert len(segments) == 2
        assert segments[0]["segment_number"] == 1
        assert segments[1]["segment_number"] == 2

    def test_passes_merge_segments_flag(self, tmp_path):
        from ai_analysis.services.dicom_seg import run_segimage2itkimage
        dcm = tmp_path / "input.dcm"
        dcm.write_bytes(b"\x00" * 64)
        out_dir = tmp_path / "out"
        out_dir.mkdir()

        captured_cmd = []

        def fake_run(cmd, **kw):
            captured_cmd.extend(cmd)
            (out_dir / "seg.nii").write_bytes(b"\x00" * 64)
            (out_dir / "seg.json").write_text("{}")
            r = MagicMock()
            r.returncode = 0
            r.stdout = r.stderr = ""
            return r

        with patch("subprocess.run", side_effect=fake_run):
            run_segimage2itkimage(dcm, out_dir, merge_segments=True)

        assert "--mergeSegments" in captured_cmd

    def test_omits_merge_segments_flag_when_false(self, tmp_path):
        from ai_analysis.services.dicom_seg import run_segimage2itkimage
        dcm = tmp_path / "input.dcm"
        dcm.write_bytes(b"\x00" * 64)
        out_dir = tmp_path / "out"
        out_dir.mkdir()

        captured_cmd = []

        def fake_run(cmd, **kw):
            captured_cmd.extend(cmd)
            (out_dir / "seg.nii").write_bytes(b"\x00" * 64)
            (out_dir / "seg.json").write_text("{}")
            r = MagicMock()
            r.returncode = 0
            r.stdout = r.stderr = ""
            return r

        with patch("subprocess.run", side_effect=fake_run):
            run_segimage2itkimage(dcm, out_dir, merge_segments=False)

        assert "--mergeSegments" not in captured_cmd


# ---------------------------------------------------------------------------
# convert_dicom_seg_to_nifti
# ---------------------------------------------------------------------------

class TestConvertDicomSegToNifti:

    def test_returns_segments_and_output_dir(self, tmp_path, settings):
        from ai_analysis.services.dicom_seg import convert_dicom_seg_to_nifti
        settings.MEDIA_ROOT = str(tmp_path)
        dcm = tmp_path / "input.dcm"
        dcm.write_bytes(b"\x00" * 64)

        fake_nifti = None

        def fake_run_seg(dicom_seg_path, output_dir, **kw):
            nifti = output_dir / "seg.nii"
            nifti.write_bytes(b"\x00" * 64)
            nonlocal fake_nifti
            fake_nifti = nifti
            return [{"nifti_path": nifti, "metadata_path": None, "metadata": {}, "segment_number": None}]

        with patch("ai_analysis.services.dicom_seg.run_segimage2itkimage", side_effect=fake_run_seg):
            segments, out_dir = convert_dicom_seg_to_nifti(dcm)

        assert out_dir.is_dir()
        assert len(segments) == 1
        assert segments[0]["nifti_path"].is_file()

    def test_cleans_up_on_failure(self, tmp_path, settings):
        from ai_analysis.services.dicom_seg import convert_dicom_seg_to_nifti
        settings.MEDIA_ROOT = str(tmp_path)
        dcm = tmp_path / "input.dcm"
        dcm.write_bytes(b"\x00" * 64)

        with patch(
            "ai_analysis.services.dicom_seg.run_segimage2itkimage",
            side_effect=RuntimeError("tool failed"),
        ):
            with pytest.raises(RuntimeError):
                convert_dicom_seg_to_nifti(dcm)

        # Output dir should have been cleaned up
        base = tmp_path / "nifti_from_seg"
        if base.exists():
            remaining = list(base.iterdir())
            assert remaining == [], "Output directory not cleaned up on failure"


# ---------------------------------------------------------------------------
# download_dicom_instance
# ---------------------------------------------------------------------------

class TestDownloadDicomInstance:

    def test_downloads_to_dest_path(self, tmp_path, settings):
        settings.ORTHANC_URL = "http://orthanc:8042"
        settings.ORTHANC_USERNAME = "orthanc"
        settings.ORTHANC_PASSWORD = "orthanc"

        dest = tmp_path / "downloaded.dcm"
        fake_content = b"\xde\xad\xbe\xef" * 64

        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.iter_content.return_value = [fake_content]
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("requests.get", return_value=mock_resp) as mock_get:
            from ai_analysis.services.orthanc_client import download_dicom_instance
            result = download_dicom_instance("orthanc-abc123", dest)

        assert result == dest
        assert dest.read_bytes() == fake_content
        call_url = mock_get.call_args[0][0]
        assert "instances/orthanc-abc123/file" in call_url

    def test_raises_on_http_error(self, tmp_path, settings):
        settings.ORTHANC_URL = "http://orthanc:8042"
        settings.ORTHANC_USERNAME = ""
        settings.ORTHANC_PASSWORD = ""

        dest = tmp_path / "downloaded.dcm"

        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = Exception("HTTP 404")
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("requests.get", return_value=mock_resp):
            from ai_analysis.services.orthanc_client import download_dicom_instance
            with pytest.raises(Exception, match="HTTP 404"):
                download_dicom_instance("nonexistent", dest)


# ---------------------------------------------------------------------------
# DicomSegConvertView  (upload endpoint)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestDicomSegConvertView:

    def test_missing_file_returns_400(self, auth_client):
        from django.urls import reverse
        url = reverse("dicom-seg-convert")
        resp = auth_client.post(url, {}, format="multipart")
        assert resp.status_code == 400
        assert "error" in resp.data

    def test_conversion_failure_returns_422(self, auth_client, tmp_path):
        from django.urls import reverse
        import io as _io
        url = reverse("dicom-seg-convert")

        with patch(
            "ai_analysis.services.dicom_seg.convert_dicom_seg_to_nifti",
            side_effect=RuntimeError("bad DICOM SEG"),
        ):
            resp = auth_client.post(
                url,
                {"file": _io.BytesIO(b"\x00" * 64)},
                format="multipart",
            )

        assert resp.status_code == 422

    def test_successful_upload_returns_zip(self, auth_client, tmp_path):
        from django.urls import reverse
        import io as _io
        url = reverse("dicom-seg-convert")

        nifti_path = tmp_path / "seg.nii"
        nifti_path.write_bytes(b"\x00" * 64)
        meta_path = tmp_path / "seg.json"
        meta_path.write_text('{"segments": []}')

        fake_segments = [{
            "nifti_path": nifti_path,
            "metadata_path": meta_path,
            "metadata": {"segments": []},
            "segment_number": None,
        }]

        with patch(
            "ai_analysis.services.dicom_seg.convert_dicom_seg_to_nifti",
            return_value=(fake_segments, tmp_path),
        ):
            resp = auth_client.post(
                url,
                {"file": _io.BytesIO(b"\x00" * 64)},
                format="multipart",
            )

        assert resp.status_code == 200
        assert resp["Content-Type"] == "application/zip"
        # Verify ZIP contains expected files
        buf = _io.BytesIO(b"".join(resp.streaming_content))
        import zipfile as _zf
        with _zf.ZipFile(buf) as z:
            names = z.namelist()
        assert "seg.nii" in names
        assert "seg.json" in names

    def test_requires_authentication(self, api_client):
        from django.urls import reverse
        import io as _io
        url = reverse("dicom-seg-convert")
        resp = api_client.post(url, {"file": _io.BytesIO(b"\x00")}, format="multipart")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# TaskDicomSegToNiftiView  (task-based download endpoint)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTaskDicomSegToNiftiView:

    def _url(self, task_id):
        from django.urls import reverse
        return reverse("task-seg-to-nifti", kwargs={"task_id": str(task_id)})

    def test_task_not_completed_returns_400(self, auth_client, analysis_task):
        analysis_task.status = "PROCESSING"
        analysis_task.save()
        resp = auth_client.get(self._url(analysis_task.id))
        assert resp.status_code == 400

    def test_no_orthanc_id_returns_404(self, auth_client, completed_task):
        completed_task.result_metadata = {}
        completed_task.save()
        resp = auth_client.get(self._url(completed_task.id))
        assert resp.status_code == 404

    def test_orthanc_error_returns_502(self, auth_client, completed_task):
        completed_task.result_metadata = {"dicom_seg_orthanc_id": "abc123"}
        completed_task.save()

        with patch(
            "ai_analysis.services.orthanc_client.download_dicom_instance",
            side_effect=Exception("connection refused"),
        ):
            resp = auth_client.get(self._url(completed_task.id))

        assert resp.status_code == 502

    def test_successful_download_returns_zip(self, auth_client, completed_task, tmp_path):
        import io as _io
        completed_task.result_metadata = {"dicom_seg_orthanc_id": "abc123"}
        completed_task.save()

        nifti_path = tmp_path / "seg.nii"
        nifti_path.write_bytes(b"\x00" * 64)
        meta_path = tmp_path / "seg.json"
        meta_path.write_text('{}')

        fake_segments = [{
            "nifti_path": nifti_path,
            "metadata_path": meta_path,
            "metadata": {},
            "segment_number": None,
        }]

        with patch("ai_analysis.services.orthanc_client.download_dicom_instance"), \
             patch(
                 "ai_analysis.services.dicom_seg.convert_dicom_seg_to_nifti",
                 return_value=(fake_segments, tmp_path),
             ):
            resp = auth_client.get(self._url(completed_task.id))

        assert resp.status_code == 200
        assert resp["Content-Type"] == "application/zip"
        buf = _io.BytesIO(b"".join(resp.streaming_content))
        import zipfile as _zf
        with _zf.ZipFile(buf) as z:
            assert "seg.nii" in z.namelist()
