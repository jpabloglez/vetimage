/**
 * Batch Action Bar
 *
 * Floating bar that appears when studies are selected.
 * Provides Export, Delete, and Analyze batch actions.
 */

import React, { useState } from 'react';
import { Download, Trash2, Brain, X, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { apiClient } from '../../utils/api';
import BatchDeleteConfirmModal from './BatchDeleteConfirmModal';

interface BatchActionBarProps {
  selectedStudyIds: number[];
  onClearSelection: () => void;
  onBatchComplete: () => void;
}

const BatchActionBar: React.FC<BatchActionBarProps> = ({
  selectedStudyIds,
  onClearSelection,
  onBatchComplete,
}) => {
  const [loading, setLoading] = useState<string | null>(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);

  if (selectedStudyIds.length === 0) return null;

  const handleExport = async () => {
    setLoading('export');
    try {
      await apiClient.createBatchJob({
        study_ids: selectedStudyIds,
        operation: 'export',
      });
      toast.success('Export job created');
      onBatchComplete();
    } catch {
      toast.error('Failed to create export job');
    } finally {
      setLoading(null);
    }
  };

  const handleDelete = async () => {
    setLoading('delete');
    try {
      await apiClient.createBatchJob({
        study_ids: selectedStudyIds,
        operation: 'delete',
      });
      toast.success('Delete job created');
      onClearSelection();
      onBatchComplete();
    } catch {
      toast.error('Failed to create delete job');
    } finally {
      setLoading(null);
      setShowDeleteModal(false);
    }
  };

  return (
    <>
      <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-xl px-6 py-3 flex items-center gap-4">
        <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
          {selectedStudyIds.length} selected
        </span>

        <div className="h-6 w-px bg-slate-200 dark:bg-slate-700" />

        <button
          onClick={handleExport}
          disabled={loading !== null}
          className="flex items-center gap-1.5 text-sm font-medium text-medical-600 hover:text-medical-700 disabled:opacity-50"
        >
          {loading === 'export' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
          Export
        </button>

        <button
          onClick={() => setShowDeleteModal(true)}
          disabled={loading !== null}
          className="flex items-center gap-1.5 text-sm font-medium text-red-600 hover:text-red-700 disabled:opacity-50"
        >
          <Trash2 className="w-4 h-4" />
          Delete
        </button>

        <div className="h-6 w-px bg-slate-200 dark:bg-slate-700" />

        <button
          onClick={onClearSelection}
          className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {showDeleteModal && (
        <BatchDeleteConfirmModal
          count={selectedStudyIds.length}
          onConfirm={handleDelete}
          onCancel={() => setShowDeleteModal(false)}
          loading={loading === 'delete'}
        />
      )}
    </>
  );
};

export default BatchActionBar;
