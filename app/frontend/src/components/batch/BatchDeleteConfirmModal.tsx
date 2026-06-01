/**
 * Batch Delete Confirmation Modal
 */

import React from 'react';
import { AlertTriangle, Loader2 } from 'lucide-react';

interface BatchDeleteConfirmModalProps {
  count: number;
  onConfirm: () => void;
  onCancel: () => void;
  loading: boolean;
}

const BatchDeleteConfirmModal: React.FC<BatchDeleteConfirmModalProps> = ({
  count,
  onConfirm,
  onCancel,
  loading,
}) => {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-xl p-6 max-w-md w-full mx-4">
        <div className="flex items-start gap-4">
          <div className="w-10 h-10 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center flex-shrink-0">
            <AlertTriangle className="w-5 h-5 text-red-600" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              Delete {count} {count === 1 ? 'study' : 'studies'}?
            </h3>
            <p className="text-sm text-slate-600 dark:text-slate-400 mt-2">
              This action cannot be undone. All DICOM files, series, and images
              associated with the selected {count === 1 ? 'study' : 'studies'} will
              be permanently removed.
            </p>
          </div>
        </div>

        <div className="flex justify-end gap-3 mt-6">
          <button
            onClick={onCancel}
            disabled={loading}
            className="px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-lg flex items-center gap-2 disabled:opacity-50"
          >
            {loading && <Loader2 className="w-4 h-4 animate-spin" />}
            Delete
          </button>
        </div>
      </div>
    </div>
  );
};

export default BatchDeleteConfirmModal;
