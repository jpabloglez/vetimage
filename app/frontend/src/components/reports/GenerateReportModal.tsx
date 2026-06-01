/**
 * Generate Report Modal
 *
 * Allows selecting a completed analysis task and creating a report from it.
 */

import React, { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { apiClient, type AnalysisTask } from '../../utils/api';

interface Props {
  onClose: () => void;
  onCreated: () => void;
}

const GenerateReportModal: React.FC<Props> = ({ onClose, onCreated }) => {
  const [tasks, setTasks] = useState<AnalysisTask[]>([]);
  const [selectedTaskId, setSelectedTaskId] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const load = async () => {
      try {
        const all = await apiClient.getAnalysisTasks({ status: 'COMPLETED' });
        setTasks(all);
      } catch {
        toast.error('Failed to load tasks');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const handleSubmit = async () => {
    if (!selectedTaskId) return;
    try {
      setSubmitting(true);
      await apiClient.createReport(selectedTaskId);
      onCreated();
    } catch {
      toast.error('Failed to generate report');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-xl w-full max-w-md mx-4 p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
            Generate Report
          </h2>
          <button onClick={onClose} className="p-1 hover:bg-slate-100 dark:hover:bg-slate-700 rounded">
            <X className="w-5 h-5 text-slate-500" />
          </button>
        </div>

        <p className="text-sm text-slate-600 dark:text-slate-400 mb-4">
          Select a completed analysis task to generate a structured report.
        </p>

        {loading ? (
          <div className="flex justify-center py-8">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-medical-600" />
          </div>
        ) : tasks.length === 0 ? (
          <p className="text-sm text-slate-500 dark:text-slate-400 py-4 text-center">
            No completed analysis tasks available.
          </p>
        ) : (
          <select
            value={selectedTaskId}
            onChange={(e) => setSelectedTaskId(e.target.value)}
            className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 text-sm mb-4"
          >
            <option value="">Select a task...</option>
            {tasks.map((task) => (
              <option key={task.id} value={task.id}>
                {task.model?.name ?? 'Unknown model'} — {new Date(task.created_at).toLocaleDateString()}
              </option>
            ))}
          </select>
        )}

        <div className="flex justify-end gap-3 mt-2">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-sm border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!selectedTaskId || submitting}
            className="px-4 py-2 rounded-lg text-sm bg-medical-600 text-white hover:bg-medical-700 transition-colors disabled:opacity-50"
          >
            {submitting ? 'Generating...' : 'Generate'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default GenerateReportModal;
