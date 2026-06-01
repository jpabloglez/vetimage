/**
 * Format Conversion Panel
 *
 * Study/series selector, format dropdown, job status polling, download.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { FileOutput, Download, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { apiClient, type Study, type ConversionJob } from '../../utils/api';

const ConversionPanel: React.FC = () => {
  const [studies, setStudies] = useState<Study[]>([]);
  const [selectedStudyId, setSelectedStudyId] = useState<number | null>(null);
  const [targetFormat, setTargetFormat] = useState<string>('jpeg');
  const [jobs, setJobs] = useState<ConversionJob[]>([]);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    apiClient.getStudies().then(setStudies).catch(() => {});
    apiClient.getConversionJobs().then(setJobs).catch(() => {});
  }, []);

  // Poll for active jobs
  useEffect(() => {
    const hasActive = jobs.some(j => j.status === 'PENDING' || j.status === 'PROCESSING');
    if (!hasActive) return;

    const interval = setInterval(async () => {
      try {
        const updated = await apiClient.getConversionJobs();
        setJobs(updated);
      } catch { /* ignore */ }
    }, 3000);

    return () => clearInterval(interval);
  }, [jobs]);

  const handleCreate = async () => {
    if (!selectedStudyId) {
      toast.error('Please select a study');
      return;
    }

    setCreating(true);
    try {
      const job = await apiClient.createConversionJob({
        study_id: selectedStudyId,
        target_format: targetFormat,
      });
      setJobs(prev => [job, ...prev]);
      toast.success('Conversion job created');
    } catch {
      toast.error('Failed to create conversion job');
    } finally {
      setCreating(false);
    }
  };

  const handleDownload = async (jobId: string) => {
    try {
      await apiClient.downloadConversionResult(jobId);
    } catch {
      toast.error('Download failed');
    }
  };

  const statusBadge = (status: string) => {
    const colors: Record<string, string> = {
      PENDING: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
      PROCESSING: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
      COMPLETED: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
      FAILED: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
    };
    return (
      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${colors[status] || ''}`}>
        {status}
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* Create Job Form */}
      <div className="medical-card p-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <FileOutput className="w-5 h-5 text-medical-600" />
          Convert DICOM Files
        </h3>

        <div className="grid md:grid-cols-3 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium mb-1">Study</label>
            <select
              value={selectedStudyId || ''}
              onChange={(e) => setSelectedStudyId(Number(e.target.value) || null)}
              className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-sm"
            >
              <option value="">Select a study...</option>
              {studies.map(s => (
                <option key={s.StudyInstanceUID} value={(s as any).id || 0}>
                  {s.PatientID} - {s.StudyDescription || 'No description'}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Target Format</label>
            <select
              value={targetFormat}
              onChange={(e) => setTargetFormat(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-sm"
            >
              <option value="jpeg">JPEG</option>
              <option value="png">PNG</option>
              <option value="nifti">NIfTI</option>
            </select>
          </div>

          <div className="flex items-end">
            <button
              onClick={handleCreate}
              disabled={creating || !selectedStudyId}
              className="medical-button-primary w-full flex items-center justify-center gap-2 px-4 py-2"
            >
              {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileOutput className="w-4 h-4" />}
              Convert
            </button>
          </div>
        </div>
      </div>

      {/* Job History */}
      {jobs.length > 0 && (
        <div className="medical-card p-6">
          <h3 className="text-lg font-semibold mb-4">Conversion History</h3>
          <div className="space-y-3">
            {jobs.map(job => (
              <div key={job.id} className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
                <div className="flex items-center gap-3">
                  {statusBadge(job.status)}
                  <span className="text-sm font-medium">{job.target_format.toUpperCase()}</span>
                  <span className="text-xs text-slate-500">
                    {new Date(job.created_at).toLocaleString()}
                  </span>
                </div>
                {job.status === 'COMPLETED' && (
                  <button
                    onClick={() => handleDownload(job.id)}
                    className="flex items-center gap-1 text-sm text-medical-600 hover:text-medical-700"
                  >
                    <Download className="w-4 h-4" />
                    Download
                  </button>
                )}
                {(job.status === 'PENDING' || job.status === 'PROCESSING') && (
                  <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ConversionPanel;
