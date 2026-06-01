/**
 * DICOM Dropzone Component
 *
 * Drag-and-drop file uploader for DICOM medical images with:
 * - Multi-file upload support
 * - File validation (DICOM only)
 * - Upload progress tracking
 * - Storage quota display
 * - Preview and metadata display
 */

import React, { useState, useCallback, useRef } from 'react';
import { Upload, X, CheckCircle, AlertCircle, FileText, HardDrive } from 'lucide-react';
import toast from 'react-hot-toast';
import { apiClient, formatFileSize, isDicomFile } from '../../utils/api';
import Button from '../ui/Button';

interface FileWithProgress {
  file: File;
  progress: number;
  status: 'pending' | 'uploading' | 'success' | 'error';
  error?: string;
  studyUID?: string;
}

interface StorageQuota {
  used_bytes: number;
  quota_bytes: number;
  remaining_bytes: number;
  usage_percentage: number;
  is_over_quota: boolean;
}

export const DicomDropzone: React.FC<{ onUploadComplete?: () => void }> = ({ onUploadComplete }) => {
  const [files, setFiles] = useState<FileWithProgress[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [storageQuota, setStorageQuota] = useState<StorageQuota | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load storage quota on mount
  React.useEffect(() => {
    loadStorageQuota();
  }, []);

  const loadStorageQuota = async () => {
    try {
      const quota = await apiClient.getStorageInfo();
      setStorageQuota(quota);
    } catch (error) {
      console.error('Failed to load storage quota:', error);
    }
  };

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
  }, []);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const selectedFiles = Array.from(e.target.files);
      addFiles(selectedFiles);
    }
  }, []);

  const addFiles = (newFiles: File[]) => {
    // Validate files
    const validFiles: FileWithProgress[] = [];
    const invalidFiles: string[] = [];

    newFiles.forEach(file => {
      if (!isDicomFile(file.name)) {
        invalidFiles.push(file.name);
        return;
      }

      // Check if file already added
      if (files.some(f => f.file.name === file.name && f.file.size === file.size)) {
        return;
      }

      validFiles.push({
        file,
        progress: 0,
        status: 'pending',
      });
    });

    if (invalidFiles.length > 0) {
      toast.error(`Invalid files (not DICOM): ${invalidFiles.join(', ')}`);
    }

    if (validFiles.length > 0) {
      setFiles(prev => [...prev, ...validFiles]);
      toast.success(`Added ${validFiles.length} DICOM file(s)`);
    }
  };

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const clearAll = () => {
    setFiles([]);
  };

  const uploadFiles = async () => {
    if (files.length === 0) {
      toast.error('No files to upload');
      return;
    }

    // Check storage quota
    if (storageQuota?.is_over_quota) {
      toast.error('Storage quota exceeded. Please delete some studies first.');
      return;
    }

    setIsUploading(true);

    try {
      const filesToUpload = files.filter(f => f.status === 'pending').map(f => f.file);

      if (filesToUpload.length === 0) {
        toast.error('All files have already been uploaded');
        setIsUploading(false);
        return;
      }

      // Update status to uploading
      setFiles(prev => prev.map(f =>
        f.status === 'pending' ? { ...f, status: 'uploading' as const } : f
      ));

      // Upload with progress tracking
      const result = await apiClient.uploadDicomFiles(filesToUpload, (progress) => {
        setFiles(prev => prev.map(f =>
          f.status === 'uploading' ? { ...f, progress } : f
        ));
      });

      // Mark all as successful
      setFiles(prev => prev.map(f =>
        f.status === 'uploading' ? {
          ...f,
          status: 'success' as const,
          progress: 100,
          studyUID: result.studyUID
        } : f
      ));

      toast.success(`Successfully uploaded ${result.uploaded_count} DICOM file(s)`);

      // Reload storage quota
      await loadStorageQuota();

      // Notify parent
      if (onUploadComplete) {
        onUploadComplete();
      }

    } catch (error: any) {
      console.error('Upload error:', error);

      // Mark files as error
      setFiles(prev => prev.map(f =>
        f.status === 'uploading' ? {
          ...f,
          status: 'error' as const,
          error: error.error || error.detail || 'Upload failed'
        } : f
      ));

      toast.error(error.error || error.detail || 'Upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  const getStatusIcon = (status: FileWithProgress['status']) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="w-5 h-5 text-success-600 dark:text-success-400" />;
      case 'error':
        return <AlertCircle className="w-5 h-5 text-error-600 dark:text-error-400" />;
      case 'uploading':
        return (
          <div className="w-5 h-5 border-2 border-medical-600 border-t-transparent rounded-full animate-spin" />
        );
      default:
        return <FileText className="w-5 h-5 text-slate-400" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Storage Quota Display */}
      {storageQuota && (
        <div className="medical-card p-4">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <HardDrive className="w-5 h-5 text-medical-600 dark:text-medical-400" />
              <span className="font-semibold text-slate-900 dark:text-slate-100">Storage Quota</span>
            </div>
            <span className="text-sm text-slate-600 dark:text-slate-400">
              {formatFileSize(storageQuota.used_bytes)} / {formatFileSize(storageQuota.quota_bytes)}
            </span>
          </div>
          <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2">
            <div
              className={`h-2 rounded-full transition-all ${
                storageQuota.is_over_quota
                  ? 'bg-error-600'
                  : storageQuota.usage_percentage > 80
                  ? 'bg-warning-600'
                  : 'bg-medical-600'
              }`}
              style={{ width: `${Math.min(storageQuota.usage_percentage, 100)}%` }}
            />
          </div>
          <div className="mt-1 text-xs text-slate-500 dark:text-slate-400 text-right">
            {storageQuota.usage_percentage.toFixed(1)}% used
          </div>
        </div>
      )}

      {/* Dropzone */}
      <div
        onDragEnter={handleDragEnter}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`
          medical-card p-12 text-center cursor-pointer transition-all
          border-2 border-dashed
          ${isDragging
            ? 'border-medical-600 bg-medical-50 dark:bg-medical-900/20'
            : 'border-slate-300 dark:border-slate-600 hover:border-medical-400 dark:hover:border-medical-500'
          }
        `}
      >
        <Upload className={`w-16 h-16 mx-auto mb-4 ${
          isDragging ? 'text-medical-600' : 'text-slate-400'
        }`} />
        <h3 className="text-xl font-semibold mb-2 text-slate-900 dark:text-slate-100">
          {isDragging ? 'Drop DICOM files here' : 'Upload DICOM Files'}
        </h3>
        <p className="text-slate-600 dark:text-slate-400 mb-4">
          Drag and drop DICOM files or click to browse
        </p>
        <p className="text-sm text-slate-500 dark:text-slate-500">
          Supported formats: .dcm, .dicom • Max file size: 100 MB
        </p>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".dcm,.dicom"
          onChange={handleFileSelect}
          className="hidden"
        />
      </div>

      {/* File List */}
      {files.length > 0 && (
        <div className="medical-card p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              Files ({files.length})
            </h3>
            <div className="flex gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={clearAll}
                disabled={isUploading}
              >
                Clear All
              </Button>
              <Button
                variant="medical"
                size="sm"
                onClick={uploadFiles}
                disabled={isUploading || files.every(f => f.status !== 'pending')}
                loading={isUploading}
              >
                Upload {files.filter(f => f.status === 'pending').length} File(s)
              </Button>
            </div>
          </div>

          <div className="space-y-2 max-h-96 overflow-y-auto">
            {files.map((fileItem, index) => (
              <div
                key={`${fileItem.file.name}-${index}`}
                className="flex items-center gap-3 p-3 bg-slate-50 dark:bg-slate-800 rounded-lg"
              >
                {getStatusIcon(fileItem.status)}

                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-slate-900 dark:text-slate-100 truncate">
                      {fileItem.file.name}
                    </span>
                    <span className="text-xs text-slate-500 dark:text-slate-400 ml-2">
                      {formatFileSize(fileItem.file.size)}
                    </span>
                  </div>

                  {fileItem.status === 'uploading' && (
                    <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-1">
                      <div
                        className="h-1 bg-medical-600 rounded-full transition-all"
                        style={{ width: `${fileItem.progress}%` }}
                      />
                    </div>
                  )}

                  {fileItem.status === 'error' && fileItem.error && (
                    <p className="text-xs text-error-600 dark:text-error-400">
                      {fileItem.error}
                    </p>
                  )}

                  {fileItem.status === 'success' && (
                    <p className="text-xs text-success-600 dark:text-success-400">
                      Upload complete
                    </p>
                  )}
                </div>

                {fileItem.status !== 'uploading' && (
                  <button
                    onClick={() => removeFile(index)}
                    className="p-1 hover:bg-slate-200 dark:hover:bg-slate-700 rounded transition-colors"
                    disabled={isUploading}
                  >
                    <X className="w-4 h-4 text-slate-400" />
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default DicomDropzone;
