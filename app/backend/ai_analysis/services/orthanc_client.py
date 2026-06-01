"""
Orthanc REST API Client

Provides a minimal interface for uploading DICOM files to the Orthanc PACS
server configured in settings (ORTHANC_URL / ORTHANC_USERNAME / ORTHANC_PASSWORD).

Orthanc REST API reference:
  https://orthanc.uclouvain.be/book/users/rest.html
"""

import logging
from pathlib import Path

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# Default connection timeout (connect, read) in seconds
_TIMEOUT = (10, 60)


def _orthanc_auth() -> tuple[str, str] | None:
    """Return (username, password) tuple if credentials are configured."""
    username = getattr(settings, "ORTHANC_USERNAME", "")
    password = getattr(settings, "ORTHANC_PASSWORD", "")
    if username and password:
        return (username, password)
    return None


def upload_dicom_to_orthanc(file_path: Path) -> dict:
    """
    Upload a DICOM file to Orthanc via the ``/instances`` REST endpoint.

    Args:
        file_path: Absolute path to the DICOM file to upload.

    Returns:
        Orthanc response dict, typically::

            {
                "ID":     "<orthanc-instance-id>",
                "Path":   "/instances/<id>",
                "Status": "Success",          # or "AlreadyStored"
                "ParentPatient":  "...",
                "ParentStudy":    "...",
                "ParentSeries":   "...",
            }

    Raises:
        FileNotFoundError: If *file_path* does not exist.
        requests.HTTPError: If Orthanc returns a non-2xx status.
    """
    if not file_path.is_file():
        raise FileNotFoundError(f"DICOM file not found: {file_path}")

    url = f"{settings.ORTHANC_URL}/instances"
    auth = _orthanc_auth()

    logger.info("Uploading DICOM SEG to Orthanc: %s → %s", file_path.name, url)

    with open(file_path, "rb") as fh:
        response = requests.post(
            url,
            data=fh,
            headers={"Content-Type": "application/dicom"},
            auth=auth,
            timeout=_TIMEOUT,
        )

    response.raise_for_status()
    data = response.json()
    logger.info(
        "Orthanc upload complete: ID=%s Status=%s",
        data.get("ID"), data.get("Status"),
    )
    return data


def download_dicom_instance(orthanc_instance_id: str, dest_path: Path) -> Path:
    """
    Download a DICOM instance from Orthanc by its internal instance UUID.

    Args:
        orthanc_instance_id: Orthanc internal instance UUID (the ``ID`` field
                             returned by upload or series metadata).
        dest_path:           Absolute path where the downloaded file is saved.

    Returns:
        *dest_path* on success.

    Raises:
        requests.HTTPError: If Orthanc returns a non-2xx status.
    """
    url = f"{settings.ORTHANC_URL}/instances/{orthanc_instance_id}/file"
    logger.info("Downloading DICOM from Orthanc: %s → %s", url, dest_path.name)

    dest_path.parent.mkdir(parents=True, exist_ok=True)

    with requests.get(url, auth=_orthanc_auth(), timeout=_TIMEOUT, stream=True) as resp:
        resp.raise_for_status()
        with open(dest_path, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=65536):
                fh.write(chunk)

    logger.info("Downloaded %d bytes to %s", dest_path.stat().st_size, dest_path)
    return dest_path


def get_series_metadata(orthanc_series_id: str) -> dict:
    """
    Fetch metadata for an Orthanc series (optional utility).

    Args:
        orthanc_series_id: The Orthanc internal series UUID.

    Returns:
        Orthanc series metadata dict.
    """
    url = f"{settings.ORTHANC_URL}/series/{orthanc_series_id}"
    response = requests.get(url, auth=_orthanc_auth(), timeout=_TIMEOUT)
    response.raise_for_status()
    return response.json()
