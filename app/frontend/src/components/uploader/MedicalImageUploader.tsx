/**
 * Medical Image Uploader Component
 *
 * Multi-format drag-and-drop file uploader supporting:
 * - DICOM (.dcm, .dicom)
 * - NIfTI (.nii, .nii.gz)
 * - Standard images (.jpg, .jpeg, .png)
 *
 * Features:
 * - Drag-and-drop interface
 * - File validation with detailed feedback
 * - Upload progress tracking
 * - Storage quota display
 * - Format detection and icons
 */

import React, { useState, useCallback, useRef } from 'react';
import { Upload, X, CheckCircle, AlertCircle, FileText, HardDrive, Image as ImageIcon } from 'lucide-react';
import toast from 'react-hot-toast';
import { apiClient, UploadedMedicalImage } from '../../utils/api';
import {
  validateFiles,
  detectFileFormat,
  getFormatName,
  getFormatIcon,
  formatFileSize,
  getAcceptedExtensions,
  FileFormat,
} from '../../utils/fileValidation';
import Button from '../ui/Button';

interface FileWithProgress {
  file: File;
  format: FileFormat;
  progress: number;
  status: 'pending' | 'uploading' | 'success' | 'error';
  error?: string;
  uploadedData?: UploadedMedicalImage;
}

interface MedicalImageUploaderProps {
  onUploadComplete: (uploadedImages: UploadedMedicalImage[]) => void;
  maxFileSize?: number; // in bytes
  maxTotalSize?: number; // in bytes
}

export const MedicalImageUploader: React.FC<MedicalImageUploaderProps> = ({
  onUploadComplete,
  maxFileSize = 100 * 1024 * 1024, // 100 MB
  maxTotalSize = 500 * 1024 * 1024, // 500 MB
}) => {
  const [files, setFiles] = useState<FileWithProgress[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const droppedFiles = Array.from(e.dataTransfer.files);
    addFiles(droppedFiles);
  }, [maxFileSize, maxTotalSize]);

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const selectedFiles = Array.from(e.target.files);
      addFiles(selectedFiles);
    }
  };

  const addFiles = (newFiles: File[]) => {
    // Validate files
    const validation = validateFiles(newFiles, maxFileSize, maxTotalSize);

    // Show warnings
    validation.warnings.forEach(warning => {
      toast(warning, { icon: '⚠️' });
    });

    // Show errors
    validation.errors.forEach(error => {
      toast.error(error);
    });

    // Add valid files to the list
    const validFiles = validation.files
      .filter(f => f.valid)
      .map(f => ({
        file: f.file,
        format: f.format,
        progress: 0,
        status: 'pending' as const,
      }));

    if (validFiles.length > 0) {
      setFiles(prev => [...prev, ...validFiles]);
      toast.success(`Added ${validFiles.length} file(s)`);
    }

    // Show individual file errors
    validation.files
      .filter(f => !f.valid)
      .forEach(f => {
        f.errors.forEach(error => toast.error(error));
      });
  };

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const clearFiles = () => {
    setFiles([]);
    setUploadProgress(0);
  };

  const uploadFiles = async () => {
    if (files.length === 0) {
      toast.error('No files to upload');
      return;
    }

    if (files.some(f => f.status === 'uploading')) {
      toast.error('Upload already in progress');
      return;
    }

    setIsUploading(true);
    setUploadProgress(0);

    try {
      // Mark all files as uploading
      setFiles(prev =>
        prev.map(f => ({
          ...f,
          status: 'uploading' as const,
          progress: 0,
        }))
      );

      // Upload all files
      const filesToUpload = files.map(f => f.file);

      const response = await apiClient.uploadMedicalImages(
        filesToUpload,
        (progress) => {
          setUploadProgress(progress);
          // Update progress for all files (simplified - in reality would be per-file)
          setFiles(prev =>
            prev.map(f =>
              f.status === 'uploading'
                ? { ...f, progress }
                : f
            )
          );
        }
      );

      // Mark files as successful and attach uploaded data
      const uploadedImages = response.uploaded_images;
      setFiles(prev =>
        prev.map((f, index) => ({
          ...f,
          status: 'success' as const,
          progress: 100,
          uploadedData: uploadedImages[index],
        }))
      );

      toast.success(
        `Successfully uploaded ${response.total_count} file(s) (${formatFileSize(response.total_size_bytes)})`
      );

      // Notify parent component
      onUploadComplete(uploadedImages);

    } catch (error: any) {
      console.error('Upload error:', error);
      toast.error(error.message || 'Upload failed');

      // Mark all uploading files as error
      setFiles(prev =>
        prev.map(f =>
          f.status === 'uploading'
            ? { ...f, status: 'error' as const, error: error.message }
            : f
        )
      );
    } finally {
      setIsUploading(false);
    }
  };

  const handleBrowseClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="space-y-4">
      {/* Drop Zone */}
      <div
        className={`
          relative border-2 border-dashed rounded-lg p-8 text-center transition-all
          ${isDragging
            ? 'border-medical-500 bg-medical-50 dark:bg-medical-900/20'
            : 'border-slate-300 dark:border-slate-600 hover:border-medical-400 dark:hover:border-medical-500'
          }
          ${isUploading ? 'opacity-50 pointer-events-none' : 'cursor-pointer'}
        `}
        onDragEnter={handleDragEnter}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleBrowseClick}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={getAcceptedExtensions()}
          onChange={handleFileInputChange}
          className="hidden"
        />

        <Upload
          className={`mx-auto h-12 w-12 mb-4 ${
            isDragging ? 'text-medical-500' : 'text-slate-400'
          }`}
        />

        <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">
          {isDragging ? 'Drop files here' : 'Upload Medical Images'}
        </h3>

        <p className="text-sm text-slate-600 dark:text-slate-400 mb-4">
          Drag and drop files or click to browse
        </p>

        <div className="flex flex-wrap justify-center gap-2 text-xs text-slate-500 dark:text-slate-400">
          <span className="px-2 py-1 bg-slate-100 dark:bg-slate-700 rounded">
            🏥 DICOM
          </span>
          <span className="px-2 py-1 bg-slate-100 dark:bg-slate-700 rounded">
            🧠 NIfTI
          </span>
          <span className="px-2 py-1 bg-slate-100 dark:bg-slate-700 rounded">
            🖼️ JPG/PNG
          </span>
        </div>

        <p className="text-xs text-slate-500 dark:text-slate-400 mt-4">
          Max file size: {formatFileSize(maxFileSize)} | Max total: {formatFileSize(maxTotalSize)}
        </p>
      </div>

      {/* File List */}
      {files.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              Files ({files.length})
            </h4>
            <Button
              variant="ghost"
              size="sm"
              onClick={clearFiles}
              disabled={isUploading}
            >
              Clear All
            </Button>
          </div>

          <div className="space-y-2 max-h-96 overflow-y-auto">
            {files.map((fileItem, index) => (
              <div
                key={index}
                className="flex items-center gap-3 p-3 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg"
              >
                {/* Format Icon */}
                <div className="text-2xl flex-shrink-0">
                  {getFormatIcon(fileItem.format)}
                </div>

                {/* File Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-medium text-slate-900 dark:text-slate-100 truncate">
                      {fileItem.file.name}
                    </p>
                    <span className="text-xs px-2 py-0.5 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400 rounded">
                      {getFormatName(fileItem.format)}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    {formatFileSize(fileItem.file.size)}
                  </p>

                  {/* Progress Bar */}
                  {fileItem.status === 'uploading' && (
                    <div className="mt-2">
                      <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2">
                        <div
                          className="bg-medical-500 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${fileItem.progress}%` }}
                        />
                      </div>
                      <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                        {Math.round(fileItem.progress)}%
                      </p>
                    </div>
                  )}

                  {/* Error Message */}
                  {fileItem.status === 'error' && fileItem.error && (
                    <p className="text-xs text-error-600 dark:text-error-400 mt-1">
                      {fileItem.error}
                    </p>
                  )}
                </div>

                {/* Status Icon */}
                <div className="flex-shrink-0">
                  {fileItem.status === 'success' && (
                    <CheckCircle className="h-5 w-5 text-success-500" />
                  )}
                  {fileItem.status === 'error' && (
                    <AlertCircle className="h-5 w-5 text-error-500" />
                  )}
                  {fileItem.status === 'pending' && !isUploading && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        removeFile(index);
                      }}
                      className="text-slate-400 hover:text-error-500"
                    >
                      <X className="h-5 w-5" />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Upload Button */}
          {files.some(f => f.status === 'pending') && (
            <Button
              variant="medical"
              fullWidth
              onClick={uploadFiles}
              disabled={isUploading}
            >
              {isUploading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                  Uploading... {Math.round(uploadProgress)}%
                </>
              ) : (
                `Upload ${files.filter(f => f.status === 'pending').length} File(s)`
              )}
            </Button>
          )}
        </div>
      )}
    </div>
  );
};

export default MedicalImageUploader;
