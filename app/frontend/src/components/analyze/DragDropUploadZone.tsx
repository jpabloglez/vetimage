/**
 * Drag & Drop Upload Zone
 *
 * Drop zone with file validation, upload progress, and multi-format support.
 */

import React, { useState, useRef, useCallback } from 'react';
import { Upload, FileUp, X, CheckCircle, AlertCircle } from 'lucide-react';
import { apiClient, formatFileSize, type UploadedMedicalImage } from '../../utils/api';
import toast from 'react-hot-toast';
import { useTranslation } from 'react-i18next';

interface DragDropUploadZoneProps {
  onUploadComplete: (images: UploadedMedicalImage[]) => void;
}

interface UploadingFile {
  file: File;
  progress: number;
  status: 'pending' | 'uploading' | 'complete' | 'error';
  error?: string;
}

const ACCEPTED_EXTENSIONS = ['.dcm', '.dicom', '.nii', '.nii.gz', '.jpg', '.jpeg', '.png'];

export const DragDropUploadZone: React.FC<DragDropUploadZoneProps> = ({ onUploadComplete }) => {
  const { t } = useTranslation('analyze');
  const [isDragOver, setIsDragOver] = useState(false);
  const [uploadingFiles, setUploadingFiles] = useState<UploadingFile[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateFile = (file: File): string | null => {
    const name = file.name.toLowerCase();
    const valid = ACCEPTED_EXTENSIONS.some((ext) => name.endsWith(ext));
    if (!valid) return `Unsupported format: ${file.name}`;
    if (file.size > 500 * 1024 * 1024) return `File too large: ${file.name} (max 500MB)`;
    return null;
  };

  const handleFiles = useCallback(async (files: File[]) => {
    const validFiles: File[] = [];
    const errors: string[] = [];

    for (const file of files) {
      const error = validateFile(file);
      if (error) {
        errors.push(error);
      } else {
        validFiles.push(file);
      }
    }

    if (errors.length > 0) {
      errors.forEach((e) => toast.error(e));
    }

    if (validFiles.length === 0) return;

    const uploadEntries: UploadingFile[] = validFiles.map((file) => ({
      file,
      progress: 0,
      status: 'pending',
    }));

    setUploadingFiles(uploadEntries);
    setIsUploading(true);

    try {
      // Update progress as files upload
      const progressFn = (pct: number) => {
        setUploadingFiles((prev) =>
          prev.map((f) => ({
            ...f,
            progress: Math.round(pct),
            status: pct >= 100 ? 'complete' : 'uploading',
          }))
        );
      };

      const result = await apiClient.uploadMedicalImages(validFiles, progressFn);

      setUploadingFiles((prev) =>
        prev.map((f) => ({ ...f, progress: 100, status: 'complete' }))
      );

      if (result.uploaded_images && result.uploaded_images.length > 0) {
        onUploadComplete(result.uploaded_images);
        toast.success(`${result.uploaded_images.length} image(s) uploaded successfully`);
      }
    } catch (err: any) {
      setUploadingFiles((prev) =>
        prev.map((f) => ({
          ...f,
          status: 'error',
          error: err.message || 'Upload failed',
        }))
      );
      toast.error('Upload failed: ' + (err.message || 'Unknown error'));
    } finally {
      setIsUploading(false);
    }
  }, [onUploadComplete]);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      const files = Array.from(e.dataTransfer.files);
      handleFiles(files);
    },
    [handleFiles]
  );

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    handleFiles(files);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const clearFiles = () => {
    setUploadingFiles([]);
  };

  const overallProgress =
    uploadingFiles.length > 0
      ? Math.round(
          uploadingFiles.reduce((sum, f) => sum + f.progress, 0) / uploadingFiles.length
        )
      : 0;

  return (
    <div className="space-y-4">
      {/* Drop Zone */}
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => fileInputRef.current?.click()}
        className={`
          relative border-2 border-dashed rounded-xl p-12 text-center cursor-pointer
          transition-all duration-200
          ${isDragOver
            ? 'border-medical-500 bg-medical-50 dark:bg-medical-900/20 scale-[1.02]'
            : 'border-slate-300 dark:border-slate-600 hover:border-medical-400 dark:hover:border-medical-500 bg-slate-50 dark:bg-slate-800/50'
          }
          ${isUploading ? 'pointer-events-none opacity-60' : ''}
        `}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".dcm,.dicom,.nii,.nii.gz,.jpg,.jpeg,.png"
          onChange={handleInputChange}
          className="hidden"
        />

        <div className="flex flex-col items-center gap-4">
          {isDragOver ? (
            <FileUp className="w-16 h-16 text-medical-500 animate-bounce" />
          ) : (
            <Upload className="w-16 h-16 text-slate-400 dark:text-slate-500" />
          )}

          <div>
            <p className="text-lg font-semibold text-slate-900 dark:text-white">
              {isDragOver ? t('upload.dragDrop') : t('upload.dragDrop')}
            </p>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
              {t('upload.supportedFormats')}
            </p>
          </div>
        </div>
      </div>

      {/* Upload Progress */}
      {uploadingFiles.length > 0 && (
        <div className="medical-card p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-medium text-slate-900 dark:text-white">
              {isUploading ? t('upload.uploading') : t('upload.uploadComplete')}
            </h4>
            {!isUploading && (
              <button
                onClick={clearFiles}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* Overall progress bar */}
          <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2">
            <div
              className="bg-medical-500 h-2 rounded-full transition-all duration-300"
              style={{ width: `${overallProgress}%` }}
            />
          </div>

          {/* Individual files */}
          <div className="space-y-2 max-h-40 overflow-y-auto">
            {uploadingFiles.map((f, idx) => (
              <div key={idx} className="flex items-center gap-3 text-sm">
                {f.status === 'complete' ? (
                  <CheckCircle className="w-4 h-4 text-success-500 flex-shrink-0" />
                ) : f.status === 'error' ? (
                  <AlertCircle className="w-4 h-4 text-error-500 flex-shrink-0" />
                ) : (
                  <div className="w-4 h-4 border-2 border-medical-500 border-t-transparent rounded-full animate-spin flex-shrink-0" />
                )}
                <span className="text-slate-700 dark:text-slate-300 truncate flex-1">
                  {f.file.name}
                </span>
                <span className="text-slate-500 dark:text-slate-400 text-xs flex-shrink-0">
                  {formatFileSize(f.file.size)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default DragDropUploadZone;
