/**
 * File Validation Utilities for Medical Image Uploads
 *
 * Provides client-side validation for multi-format medical image uploads.
 */

// Supported medical image formats
export const SUPPORTED_FORMATS = {
  dicom: ['.dcm', '.dicom'],
  nifti: ['.nii', '.nii.gz'],
  image: ['.jpg', '.jpeg', '.png'],
} as const;

// All supported extensions in a flat array
export const ALL_SUPPORTED_EXTENSIONS = Object.values(SUPPORTED_FORMATS).flat();

// File format type
export type FileFormat = 'dicom' | 'nifti' | 'image' | null;

/**
 * Check if a file is a medical image file based on extension
 */
export const isMedicalImageFile = (filename: string): boolean => {
  const filenameLower = filename.toLowerCase();

  return ALL_SUPPORTED_EXTENSIONS.some(ext => filenameLower.endsWith(ext));
};

/**
 * Detect file format from filename extension
 */
export const detectFileFormat = (filename: string): FileFormat => {
  const filenameLower = filename.toLowerCase();

  // Check DICOM
  if (SUPPORTED_FORMATS.dicom.some(ext => filenameLower.endsWith(ext))) {
    return 'dicom';
  }

  // Check NIfTI (check .nii.gz before .nii)
  if (filenameLower.endsWith('.nii.gz')) {
    return 'nifti';
  }
  if (SUPPORTED_FORMATS.nifti.some(ext => filenameLower.endsWith(ext))) {
    return 'nifti';
  }

  // Check standard images
  if (SUPPORTED_FORMATS.image.some(ext => filenameLower.endsWith(ext))) {
    return 'image';
  }

  return null;
};

/**
 * Get human-readable format name
 */
export const getFormatName = (format: FileFormat): string => {
  switch (format) {
    case 'dicom':
      return 'DICOM';
    case 'nifti':
      return 'NIfTI';
    case 'image':
      return 'Image';
    default:
      return 'Unknown';
  }
};

/**
 * Get icon emoji for file format
 */
export const getFormatIcon = (format: FileFormat): string => {
  switch (format) {
    case 'dicom':
      return '🏥';
    case 'nifti':
      return '🧠';
    case 'image':
      return '🖼️';
    default:
      return '📄';
  }
};

/**
 * Validate file size
 */
export const isValidFileSize = (file: File, maxSizeBytes: number = 100 * 1024 * 1024): boolean => {
  return file.size <= maxSizeBytes;
};

/**
 * Format file size for display
 */
export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';

  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
};

/**
 * Validate multiple files
 */
export interface FileValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
  files: {
    file: File;
    format: FileFormat;
    valid: boolean;
    errors: string[];
  }[];
}

export const validateFiles = (
  files: File[],
  maxFileSize: number = 100 * 1024 * 1024,
  maxTotalSize: number = 500 * 1024 * 1024
): FileValidationResult => {
  const result: FileValidationResult = {
    valid: true,
    errors: [],
    warnings: [],
    files: [],
  };

  if (files.length === 0) {
    result.valid = false;
    result.errors.push('No files selected');
    return result;
  }

  let totalSize = 0;

  for (const file of files) {
    const fileResult = {
      file,
      format: detectFileFormat(file.name),
      valid: true,
      errors: [] as string[],
    };

    // Check format
    if (!fileResult.format) {
      fileResult.valid = false;
      fileResult.errors.push(`Unsupported file type: ${file.name}`);
      result.valid = false;
    }

    // Check file size
    if (!isValidFileSize(file, maxFileSize)) {
      fileResult.valid = false;
      fileResult.errors.push(
        `File too large: ${formatFileSize(file.size)} (max: ${formatFileSize(maxFileSize)})`
      );
      result.valid = false;
    }

    totalSize += file.size;
    result.files.push(fileResult);
  }

  // Check total size
  if (totalSize > maxTotalSize) {
    result.valid = false;
    result.errors.push(
      `Total upload size ${formatFileSize(totalSize)} exceeds limit of ${formatFileSize(maxTotalSize)}`
    );
  }

  // Add warnings for mixed formats
  const formats = new Set(result.files.map(f => f.format).filter(f => f !== null));
  if (formats.size > 1) {
    result.warnings.push(
      'Multiple file formats detected. Consider uploading similar formats together for better organization.'
    );
  }

  return result;
};

/**
 * Get accepted file extensions for HTML input element
 */
export const getAcceptedExtensions = (): string => {
  return ALL_SUPPORTED_EXTENSIONS.join(',');
};
