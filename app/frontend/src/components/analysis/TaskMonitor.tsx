/**
 * Task Monitor Component
 *
 * Real-time task status monitoring with automatic polling.
 * Displays status indicators, progress information, and action buttons.
 * Supports download on completion and retry on failure.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  Loader,
  Download,
  RefreshCw,
  X,
  PlayCircle,
  Zap,
} from 'lucide-react';
import { apiClient, AnalysisTask } from '../../utils/api';
import Card, { CardHeader, CardTitle, CardContent } from '../ui/Card';
import Button from '../ui/Button';
import toast from 'react-hot-toast';

interface TaskMonitorProps {
  taskId: string;
  onComplete?: (task: AnalysisTask) => void;
  onCancel?: () => void;
  pollInterval?: number; // milliseconds
}

const StatusBadge: React.FC<{ status: AnalysisTask['status'] }> = ({ status }) => {
  const config = {
    PENDING: {
      icon: Clock,
      label: 'Pending',
      color: 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300',
    },
    QUEUED: {
      icon: Clock,
      label: 'Queued',
      color: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
    },
    DISPATCHED: {
      icon: PlayCircle,
      label: 'Dispatched',
      color: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900 dark:text-indigo-300',
    },
    PROCESSING: {
      icon: Zap,
      label: 'Processing',
      color: 'bg-medical-100 text-medical-700 dark:bg-medical-900 dark:text-medical-300',
    },
    COMPLETED: {
      icon: CheckCircle,
      label: 'Completed',
      color: 'bg-success-100 text-success-700 dark:bg-success-900 dark:text-success-300',
    },
    FAILED: {
      icon: XCircle,
      label: 'Failed',
      color: 'bg-error-100 text-error-700 dark:bg-error-900 dark:text-error-300',
    },
    TIMEOUT: {
      icon: AlertCircle,
      label: 'Timeout',
      color: 'bg-warning-100 text-warning-700 dark:bg-warning-900 dark:text-warning-300',
    },
    CANCELLED: {
      icon: X,
      label: 'Cancelled',
      color: 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300',
    },
  };

  const { icon: Icon, label, color } = config[status] || config.PENDING;

  return (
    <div className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-semibold ${color}`}>
      <Icon className="h-4 w-4" />
      {label}
    </div>
  );
};

const formatDuration = (seconds?: number): string => {
  if (!seconds) return 'N/A';
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.floor(seconds % 60);
  return `${minutes}m ${remainingSeconds}s`;
};

const formatDateTime = (dateString?: string): string => {
  if (!dateString) return 'N/A';
  const date = new Date(dateString);
  return date.toLocaleString();
};

export const TaskMonitor: React.FC<TaskMonitorProps> = ({
  taskId,
  onComplete,
  onCancel,
  pollInterval = 5000, // 5 seconds default
}) => {
  const [task, setTask] = useState<AnalysisTask | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retrying, setRetrying] = useState(false);
  const [cancelling, setCancelling] = useState(false);

  const fetchTaskStatus = useCallback(async () => {
    try {
      const taskData = await apiClient.getAnalysisTask(taskId);
      setTask(taskData);
      setError(null);

      // Notify parent on completion
      if (taskData.status === 'COMPLETED' && onComplete) {
        onComplete(taskData);
      }
    } catch (err: any) {
      console.error('Failed to fetch task status:', err);
      setError(err.message || 'Failed to load task status');
    } finally {
      setLoading(false);
    }
  }, [taskId, onComplete]);

  // Initial fetch
  useEffect(() => {
    fetchTaskStatus();
  }, [fetchTaskStatus]);

  // Auto-polling for active tasks
  useEffect(() => {
    if (!task || task.status === 'COMPLETED' || task.status === 'FAILED' || task.status === 'TIMEOUT' || task.status === 'CANCELLED') {
      return; // Stop polling for terminal states
    }

    const interval = setInterval(() => {
      fetchTaskStatus();
    }, pollInterval);

    return () => clearInterval(interval);
  }, [task, pollInterval, fetchTaskStatus]);

  const handleRetry = async () => {
    if (!task) return;

    setRetrying(true);
    try {
      const newTask = await apiClient.retryAnalysisTask(task.id);
      setTask(newTask);
      toast.success('Task retry initiated');
    } catch (err: any) {
      console.error('Failed to retry task:', err);
      toast.error(err.message || 'Failed to retry task');
    } finally {
      setRetrying(false);
    }
  };

  const handleCancel = async () => {
    if (!task) return;

    setCancelling(true);
    try {
      await apiClient.cancelAnalysisTask(task.id);
      toast.success('Task cancelled');
      if (onCancel) {
        onCancel();
      }
      // Refresh task status
      await fetchTaskStatus();
    } catch (err: any) {
      console.error('Failed to cancel task:', err);
      toast.error(err.message || 'Failed to cancel task');
    } finally {
      setCancelling(false);
    }
  };

  const handleDownload = () => {
    if (!task || !task.result_file_path) return;

    // Construct download URL (assuming result files are served from the backend)
    const downloadUrl = `${apiClient.baseUrl}${task.result_file_path}`;
    window.open(downloadUrl, '_blank');
    toast.success('Download started');
  };

  if (loading && !task) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-medical-500 mx-auto mb-4" />
          <p className="text-slate-600 dark:text-slate-400">Loading task status...</p>
        </CardContent>
      </Card>
    );
  }

  if (error && !task) {
    return (
      <Card>
        <CardContent className="py-8 text-center">
          <XCircle className="h-12 w-12 text-error-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">
            Error Loading Task
          </h3>
          <p className="text-slate-600 dark:text-slate-400 mb-4">{error}</p>
          <Button onClick={fetchTaskStatus}>Retry</Button>
        </CardContent>
      </Card>
    );
  }

  if (!task) return null;

  const isActive = ['PENDING', 'QUEUED', 'DISPATCHED', 'PROCESSING'].includes(task.status);
  const isCompleted = task.status === 'COMPLETED';
  const isFailed = ['FAILED', 'TIMEOUT'].includes(task.status);
  const isCancelled = task.status === 'CANCELLED';

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <CardTitle>Analysis Task Status</CardTitle>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              Task ID: {task.id}
            </p>
          </div>
          <StatusBadge status={task.status} />
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Model Information */}
        <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                {task.model.name}
              </p>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {task.model.model_type} • v{task.model.version}
              </p>
            </div>
            {isActive && (
              <Loader className="h-5 w-5 text-medical-500 animate-spin" />
            )}
          </div>
        </div>

        {/* Progress Indicator for Active Tasks */}
        {isActive && (
          <div>
            <div className="flex justify-between text-xs text-slate-600 dark:text-slate-400 mb-2">
              <span>Processing...</span>
              <span>Task {task.status.toLowerCase()}</span>
            </div>
            <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2">
              <div className="bg-medical-500 h-2 rounded-full animate-pulse" style={{ width: '70%' }} />
            </div>
          </div>
        )}

        {/* Timestamps */}
        <div className="grid grid-cols-2 gap-4 text-xs">
          <div>
            <p className="text-slate-500 dark:text-slate-400">Created</p>
            <p className="font-semibold text-slate-900 dark:text-slate-100">
              {formatDateTime(task.created_at)}
            </p>
          </div>
          {task.started_processing_at && (
            <div>
              <p className="text-slate-500 dark:text-slate-400">Started</p>
              <p className="font-semibold text-slate-900 dark:text-slate-100">
                {formatDateTime(task.started_processing_at)}
              </p>
            </div>
          )}
          {task.completed_at && (
            <div>
              <p className="text-slate-500 dark:text-slate-400">Completed</p>
              <p className="font-semibold text-slate-900 dark:text-slate-100">
                {formatDateTime(task.completed_at)}
              </p>
            </div>
          )}
          {task.processing_duration !== undefined && (
            <div>
              <p className="text-slate-500 dark:text-slate-400">Processing Time</p>
              <p className="font-semibold text-slate-900 dark:text-slate-100">
                {formatDuration(task.processing_duration)}
              </p>
            </div>
          )}
        </div>

        {/* Error Message */}
        {task.error_message && (
          <div className="p-3 bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg">
            <div className="flex items-start gap-2">
              <AlertCircle className="h-5 w-5 text-error-500 mt-0.5 flex-shrink-0" />
              <div className="flex-1">
                <p className="text-sm font-semibold text-error-900 dark:text-error-100 mb-1">
                  Error Details
                </p>
                <p className="text-xs text-error-700 dark:text-error-300">
                  {task.error_message}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Result Metadata */}
        {isCompleted && task.result_metadata && Object.keys(task.result_metadata).length > 0 && (
          <div className="p-3 bg-success-50 dark:bg-success-900/20 border border-success-200 dark:border-success-800 rounded-lg">
            <p className="text-sm font-semibold text-success-900 dark:text-success-100 mb-2">
              Analysis Complete
            </p>
            <div className="grid grid-cols-2 gap-2 text-xs">
              {Object.entries(task.result_metadata).slice(0, 4).map(([key, value]) => (
                <div key={key}>
                  <p className="text-success-700 dark:text-success-400">{key}</p>
                  <p className="font-semibold text-success-900 dark:text-success-100">
                    {String(value)}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-2 pt-4 border-t border-slate-200 dark:border-slate-700">
          {/* Download Button (for completed tasks) */}
          {isCompleted && task.result_file_path && (
            <Button variant="medical" fullWidth onClick={handleDownload}>
              <Download className="h-4 w-4 mr-2" />
              Download Result
            </Button>
          )}

          {/* Retry Button (for failed tasks) */}
          {isFailed && (
            <Button variant="medical" fullWidth onClick={handleRetry} disabled={retrying}>
              {retrying ? (
                <>
                  <Loader className="h-4 w-4 mr-2 animate-spin" />
                  Retrying...
                </>
              ) : (
                <>
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Retry Task
                </>
              )}
            </Button>
          )}

          {/* Cancel Button (for active tasks) */}
          {isActive && (
            <Button variant="outline" fullWidth onClick={handleCancel} disabled={cancelling}>
              {cancelling ? (
                <>
                  <Loader className="h-4 w-4 mr-2 animate-spin" />
                  Cancelling...
                </>
              ) : (
                <>
                  <X className="h-4 w-4 mr-2" />
                  Cancel Task
                </>
              )}
            </Button>
          )}

          {/* Refresh Button (manual refresh for any state) */}
          <Button variant="ghost" onClick={fetchTaskStatus}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>

        {/* Retry Counter */}
        {task.retry_count > 0 && (
          <div className="text-xs text-slate-500 dark:text-slate-400 text-center">
            Retry attempt {task.retry_count}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default TaskMonitor;
