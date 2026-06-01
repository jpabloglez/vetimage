"""
File Path Handler

Secure validation and parsing of S3 URIs and local file paths.
"""

import re
import logging
from pathlib import Path
from typing import Tuple


logger = logging.getLogger(__name__)


class FilePathHandler:
    """Handle S3 URIs and local file paths securely"""

    # S3 URI pattern: s3://bucket/key
    S3_URI_PATTERN = re.compile(r'^s3://([^/]+)/(.+)$')

    # Allowed local path prefixes (whitelist)
    ALLOWED_LOCAL_PATHS = [
        '/app/data',
        '/app/MIRAGE/__datasets',
        '/app/MIRAGE/_test_data',
        '/tmp',
        '/app/local_images',
        '/var/www/app/backend/media',  # OpenMedLab shared media volume (DICOM input + AI results)
    ]

    @staticmethod
    def detect_source_type(source: str) -> str:
        """
        Detect if source is S3 URI or local path

        Args:
            source: Input path or URI

        Returns:
            's3' or 'local'

        Raises:
            ValueError: If source format is invalid
        """
        if not source:
            raise ValueError("Source path cannot be empty")

        if source.startswith('s3://'):
            return 's3'
        elif source.startswith('/') or source.startswith('./') or source.startswith('../'):
            return 'local'
        else:
            raise ValueError(f"Invalid source format: {source}. Must be S3 URI (s3://) or absolute/relative path")

    @staticmethod
    def validate_s3_uri(uri: str) -> Tuple[str, str]:
        """
        Validate S3 URI and extract bucket/key

        Args:
            uri: S3 URI in format s3://bucket/key

        Returns:
            Tuple of (bucket, key)

        Raises:
            ValueError: If URI is invalid
        """
        match = FilePathHandler.S3_URI_PATTERN.match(uri)
        if not match:
            raise ValueError(f"Invalid S3 URI format: {uri}. Expected s3://bucket/key")

        bucket = match.group(1)
        key = match.group(2)

        # Validate bucket name (AWS rules)
        if not (3 <= len(bucket) <= 63):
            raise ValueError(f"Invalid S3 bucket name length: {bucket}. Must be 3-63 characters")

        if not re.match(r'^[a-z0-9][a-z0-9.-]*[a-z0-9]$', bucket):
            raise ValueError(
                f"Invalid S3 bucket name format: {bucket}. "
                "Must start and end with lowercase letter or number, "
                "can contain lowercase letters, numbers, hyphens, and periods"
            )

        # Validate key (not empty, no trailing slash for files)
        if not key:
            raise ValueError(f"Invalid S3 key: empty key in {uri}")

        # Check for directory-style key (ends with /)
        if key.endswith('/') and not uri.endswith('//'):
            # This is okay for output destinations (directories)
            pass

        logger.debug(f"Validated S3 URI: bucket={bucket}, key={key}")
        return bucket, key

    @staticmethod
    def validate_local_path(path: str, allow_relative: bool = False) -> Path:
        """
        Validate local file path and prevent path traversal

        Security checks:
        - Prevent directory traversal (../)
        - Ensure path is within allowed directories
        - Resolve to absolute path

        Args:
            path: Local file path
            allow_relative: Whether to allow relative paths

        Returns:
            Resolved absolute Path object

        Raises:
            ValueError: If path is invalid or not in allowed directories
        """
        if not path:
            raise ValueError("Path cannot be empty")

        path_obj = Path(path)

        # Resolve to absolute path
        if not path_obj.is_absolute():
            if not allow_relative:
                raise ValueError(f"Relative paths not allowed: {path}")
            path_obj = path_obj.resolve()

        # Check for path traversal attempts in original path
        if '..' in Path(path).parts:
            raise ValueError(f"Path traversal detected: {path}. '..' not allowed in paths")

        # Resolve path and check again
        try:
            resolved_path = path_obj.resolve()
            path_str = str(resolved_path)
        except Exception as e:
            raise ValueError(f"Invalid path: {path}. Error: {e}")

        # Ensure no .. components remain after resolution
        if '..' in resolved_path.parts:
            raise ValueError(f"Path traversal detected after resolution: {path}")

        # Whitelist check: ensure path is within allowed base directories
        is_allowed = any(
            path_str.startswith(base) for base in FilePathHandler.ALLOWED_LOCAL_PATHS
        )

        if not is_allowed:
            raise ValueError(
                f"Path not in allowed directories: {path_str}. "
                f"Allowed bases: {', '.join(FilePathHandler.ALLOWED_LOCAL_PATHS)}"
            )

        logger.debug(f"Validated local path: {path_str}")
        return resolved_path

    @staticmethod
    def sanitize_output_path(destination: str, job_id: str) -> str:
        """
        Sanitize output destination and append job_id

        Args:
            destination: Output destination (S3 URI or local path)
            job_id: Job UUID to append

        Returns:
            Sanitized path with job_id appended

        Examples:
            s3://bucket/prefix -> s3://bucket/prefix/{job_id}
            /app/data/results -> /app/data/results/{job_id}
        """
        source_type = FilePathHandler.detect_source_type(destination)

        if source_type == 's3':
            bucket, key = FilePathHandler.validate_s3_uri(destination)
            # Remove trailing slash
            key = key.rstrip('/')
            sanitized = f"s3://{bucket}/{key}/{job_id}"
            logger.debug(f"Sanitized S3 output path: {sanitized}")
            return sanitized
        else:
            path = FilePathHandler.validate_local_path(destination, allow_relative=True)
            sanitized = str(path / job_id)
            logger.debug(f"Sanitized local output path: {sanitized}")
            return sanitized

    @staticmethod
    def validate_input_sources(sources: list) -> bool:
        """
        Validate a list of input sources

        Args:
            sources: List of source paths/URIs

        Returns:
            True if all sources are valid

        Raises:
            ValueError: If any source is invalid
        """
        if not sources:
            raise ValueError("Input sources list cannot be empty")

        for source in sources:
            source_type = FilePathHandler.detect_source_type(source)

            if source_type == 's3':
                FilePathHandler.validate_s3_uri(source)
            else:
                FilePathHandler.validate_local_path(source, allow_relative=True)

        logger.info(f"Validated {len(sources)} input sources")
        return True

    @staticmethod
    def validate_output_destination(destination: str) -> bool:
        """
        Validate output destination

        Args:
            destination: Output destination path/URI

        Returns:
            True if valid

        Raises:
            ValueError: If destination is invalid
        """
        if not destination:
            raise ValueError("Output destination cannot be empty")

        source_type = FilePathHandler.detect_source_type(destination)

        if source_type == 's3':
            FilePathHandler.validate_s3_uri(destination)
        else:
            FilePathHandler.validate_local_path(destination, allow_relative=True)

        logger.debug(f"Validated output destination: {destination}")
        return True
