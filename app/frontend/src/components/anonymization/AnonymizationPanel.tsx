/**
 * Anonymization Panel
 *
 * Two input modes: "From Library" (study dropdown) or "Upload Files" (drag-and-drop).
 * Three output formats: DICOM ZIP | NIfTI + BIDS | PNG + BIDS.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  ShieldCheck,
  Download,
  Loader2,
  Library,
  Upload,
  Archive,
  FolderOpen,
  Image,
  Info,
} from 'lucide-react';
import { toast } from 'react-hot-toast';
import {
  apiClient,
  type Study,
  type AnonymizationJob,
  type UploadedMedicalImage,
} from '../../utils/api';
import { DragDropUploadZone } from '../analyze/DragDropUploadZone';

type InputMode = 'library' | 'upload';
type OutputFormat = 'dicom_zip' | 'nifti_bids' | 'png_bids';

const PROFILE_OPTIONS = [
  {
    value: 'basic',
    label: 'Basic',
    description: 'Removes critical identifiers (patient name, ID, birth date)',
  },
  {
    value: 'full',
    label: 'Full',
    description: 'Removes all ~30 PHI tags per DICOM PS3.15',
  },
  {
    value: 'research',
    label: 'Research',
    description: 'Full removal + UID replacement + date shifting',
  },
] as const;

const OUTPUT_FORMAT_OPTIONS: {
  value: OutputFormat;
  label: string;
  icon: React.ElementType;
  description: string;
}[] = [
  {
    value: 'dicom_zip',
    label: 'DICOM ZIP',
    icon: Archive,
    description: 'Anonymized DICOM files in ZIP archive',
  },
  {
    value: 'nifti_bids',
    label: 'NIfTI + BIDS',
    icon: FolderOpen,
    description: 'NIfTI volumes with BIDS JSON sidecars',
  },
  {
    value: 'png_bids',
    label: 'PNG + BIDS',
    icon: Image,
    description: 'PNG slices with BIDS JSON sidecars',
  },
];

const AnonymizationPanel: React.FC = () => {
  const [studies, setStudies] = useState<Study[]>([]);
  const [selectedStudyUID, setSelectedStudyUID] = useState('');
  const [profile, setProfile] = useState<'basic' | 'full' | 'research'>('basic');
  const [outputFormat, setOutputFormat] = useState<OutputFormat>('dicom_zip');
  const [inputMode, setInputMode] = useState<InputMode>('library');
  const [submitting, setSubmitting] = useState(false);
  const [jobs, setJobs] = useState<AnonymizationJob[]>([]);
  const [loadingStudies, setLoadingStudies] = useState(true);

  const fetchStudies = useCallback(async () => {
    try {
      const data = await apiClient.getStudies();
      setStudies(data);
    } catch {
      toast.error('Failed to load studies');
    } finally {
      setLoadingStudies(false);
    }
  }, []);

  const fetchJobs = useCallback(async () => {
    try {
      const data = await apiClient.getAnonymizationJobs();
      setJobs(data);
    } catch {
      // silent
    }
  }, []);

  useEffect(() => {
    fetchStudies();
    fetchJobs();
  }, [fetchStudies, fetchJobs]);

  // Poll for job status updates
  useEffect(() => {
    const hasActive = jobs.some(
      (j) => j.status === 'PENDING' || j.status === 'PROCESSING'
    );
    if (!hasActive) return;
    const interval = setInterval(fetchJobs, 3000);
    return () => clearInterval(interval);
  }, [jobs, fetchJobs]);

  const handleUploadComplete = useCallback(
    (images: UploadedMedicalImage[]) => {
      if (!images.length) return;
      const uploadedStudyId = (images[0] as any).study_id ?? (images[0] as any).study;
      apiClient
        .getStudies()
        .then((fresh: Study[]) => {
          setStudies(fresh);
          const match = fresh.find((s) => s.id === uploadedStudyId);
          if (match) {
            setSelectedStudyUID(match.StudyInstanceUID);
            setInputMode('library');
            toast.success('Files uploaded — study auto-selected');
          } else {
            setInputMode('library');
            toast.success('Upload complete — select the study from the dropdown');
          }
        })
        .catch(() => toast.error('Upload complete but could not refresh studies'));
    },
    []
  );

  const handleStart = async () => {
    if (!selectedStudyUID) return;

    const study = studies.find((s) => s.StudyInstanceUID === selectedStudyUID);
    if (!study) return;

    try {
      setSubmitting(true);
      await apiClient.createAnonymizationJob({
        study_id: study.id,
        profile,
        output_format: outputFormat,
      });
      toast.success('Anonymization job started');
      fetchJobs();
    } catch {
      toast.error('Failed to start anonymization');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDownload = async (jobId: string) => {
    try {
      await apiClient.downloadAnonymizedZip(jobId);
    } catch {
      toast.error('Failed to download');
    }
  };

  const formatLabel = (fmt: OutputFormat) =>
    OUTPUT_FORMAT_OPTIONS.find((o) => o.value === fmt)?.label ?? fmt;

  return (
    <div className="space-y-6">
      {/* Start Job Card */}
      <div className="medical-card p-6">
        {/* Header */}
        <div className="flex items-center gap-3 mb-2">
          <ShieldCheck className="w-5 h-5 text-medical-600 dark:text-medical-400" />
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
            DICOM Anonymization
          </h3>
        </div>
        <p className="text-sm text-slate-600 dark:text-slate-400 mb-5">
          Remove Protected Health Information (PHI) from DICOM datasets for research use.
        </p>

        {/* Input mode tabs */}
        <div className="flex rounded-lg border border-slate-200 dark:border-slate-700 overflow-hidden mb-4 w-fit">
          {(
            [
              { mode: 'library' as InputMode, label: 'From Library', icon: Library },
              { mode: 'upload' as InputMode, label: 'Upload Files', icon: Upload },
            ] as const
          ).map(({ mode, label, icon: Icon }) => (
            <button
              key={mode}
              onClick={() => setInputMode(mode)}
              className={`flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors ${
                inputMode === mode
                  ? 'bg-medical-600 text-white'
                  : 'bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700'
              }`}
            >
              <Icon className="w-4 h-4" />
              {label}
            </button>
          ))}
        </div>

        {/* Study selector or upload zone */}
        {inputMode === 'library' ? (
          <>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              Select Study
            </label>
            {loadingStudies ? (
              <div className="flex items-center gap-2 text-sm text-slate-500 py-2">
                <Loader2 className="w-4 h-4 animate-spin" /> Loading studies...
              </div>
            ) : (
              <select
                value={selectedStudyUID}
                onChange={(e) => setSelectedStudyUID(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 text-sm mb-4"
              >
                <option value="">Select a study...</option>
                {studies.map((s) => (
                  <option key={s.StudyInstanceUID} value={s.StudyInstanceUID}>
                    {s.PatientID} — {s.StudyDescription || s.StudyInstanceUID}
                  </option>
                ))}
              </select>
            )}
          </>
        ) : (
          <div className="mb-4">
            <DragDropUploadZone onUploadComplete={handleUploadComplete} />
          </div>
        )}

        {/* Profile Picker */}
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
          Anonymization Profile
        </label>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4">
          {PROFILE_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setProfile(opt.value)}
              className={`text-left p-3 rounded-lg border-2 transition-colors ${
                profile === opt.value
                  ? 'border-medical-500 bg-medical-50 dark:bg-medical-950/20'
                  : 'border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'
              }`}
            >
              <div className="text-sm font-medium text-slate-900 dark:text-slate-100">
                {opt.label}
              </div>
              <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                {opt.description}
              </div>
            </button>
          ))}
        </div>

        {/* Output Format Picker */}
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
          Output Format
        </label>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4">
          {OUTPUT_FORMAT_OPTIONS.map((opt) => {
            const Icon = opt.icon;
            return (
              <button
                key={opt.value}
                onClick={() => setOutputFormat(opt.value)}
                className={`text-left p-3 rounded-lg border-2 transition-colors ${
                  outputFormat === opt.value
                    ? 'border-medical-500 bg-medical-50 dark:bg-medical-950/20'
                    : 'border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'
                }`}
              >
                <div className="flex items-center gap-2 mb-0.5">
                  <Icon className="w-4 h-4 text-medical-600 dark:text-medical-400" />
                  <span className="text-sm font-medium text-slate-900 dark:text-slate-100">
                    {opt.label}
                  </span>
                </div>
                <div className="text-xs text-slate-500 dark:text-slate-400">
                  {opt.description}
                </div>
              </button>
            );
          })}
        </div>

        {/* BIDS info callout */}
        {outputFormat !== 'dicom_zip' && (
          <div className="flex items-start gap-2 p-3 rounded-lg bg-blue-50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-800 mb-4">
            <Info className="w-4 h-4 text-blue-600 dark:text-blue-400 mt-0.5 shrink-0" />
            <p className="text-xs text-blue-700 dark:text-blue-300">
              BIDS output requires a complete study. PHI is removed before conversion.
              Technical parameters are preserved.
            </p>
          </div>
        )}

        <button
          onClick={handleStart}
          disabled={!selectedStudyUID || submitting}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-medical-600 text-white hover:bg-medical-700 transition-colors disabled:opacity-50"
        >
          {submitting ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <ShieldCheck className="w-4 h-4" />
          )}
          {submitting ? 'Starting...' : 'Start Anonymization'}
        </button>
      </div>

      {/* Job History */}
      {jobs.length > 0 && (
        <div className="medical-card p-6">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">
            Job History
          </h3>
          <div className="space-y-2">
            {jobs.map((job) => (
              <div
                key={job.id}
                className="flex items-center justify-between p-3 rounded-lg bg-slate-50 dark:bg-slate-800/50"
              >
                <div>
                  <span className="text-sm text-slate-900 dark:text-slate-100">
                    {job.profile.charAt(0).toUpperCase() + job.profile.slice(1)} profile
                  </span>
                  <span className="text-xs text-slate-500 dark:text-slate-400 ml-1">
                    · {formatLabel(job.output_format ?? 'dicom_zip')}
                  </span>
                  <span className="text-xs text-slate-500 dark:text-slate-400 ml-2">
                    {new Date(job.created_at).toLocaleString()}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className={`px-2 py-0.5 rounded text-xs font-medium ${
                      job.status === 'COMPLETED'
                        ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                        : job.status === 'FAILED'
                        ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                        : 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200'
                    }`}
                  >
                    {job.status}
                  </span>
                  {job.status === 'COMPLETED' && (
                    <button
                      onClick={() => handleDownload(job.id)}
                      className="flex items-center gap-1 px-2 py-1 rounded text-xs border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                    >
                      <Download className="w-3 h-3" />
                      ZIP
                    </button>
                  )}
                  {(job.status === 'PENDING' || job.status === 'PROCESSING') && (
                    <Loader2 className="w-4 h-4 text-medical-500 animate-spin" />
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default AnonymizationPanel;
