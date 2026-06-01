/**
 * Job Monitor Panel Component
 *
 * Real-time monitoring of analysis jobs with automatic mode detection.
 * Supports both WebSocket and polling-based updates.
 * Features stats cards, filters, and a table showing jobs from user and colleagues.
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Activity,
  CheckCircle,
  XCircle,
  Clock,
  Users,
  Filter,
  Calendar,
  WifiOff,
  Wifi,
  RefreshCw,
  Download,
} from 'lucide-react';
import {
  apiClient,
  MonitorTask,
  TaskStats,
  MonitorTasksParams,
} from '../../utils/api';
import { useMonitoring } from '../../hooks/useMonitoring';
import Card, { CardHeader, CardTitle, CardContent } from '../ui/Card';
import Button from '../ui/Button';
import MonitorSettings from './MonitorSettings';
import toast from 'react-hot-toast';

export const JobMonitorPanel: React.FC = () => {
  const [isLoading, setIsLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);

  // Filters
  const [filters, setFilters] = useState<MonitorTasksParams>({
    scope: 'own',
    page_size: 20,
  });

  /**
   * Fetch tasks from API
   */
  const fetchTasks = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await apiClient.getMonitorTasks({
        ...filters,
        page: currentPage,
      });
      setTotalCount(response.count);
      return response;
    } catch (error: any) {
      console.error('Failed to fetch tasks:', error);
      return { results: [], count: 0, next: null, previous: null };
    } finally {
      setIsLoading(false);
    }
  }, [filters, currentPage]);

  /**
   * Fetch statistics
   */
  const fetchStatsData = useCallback(async () => {
    try {
      const statsData = await apiClient.getTaskStats({
        date_from: filters.date_from,
        date_to: filters.date_to,
        scope: filters.scope,
      });
      return statsData;
    } catch (error: any) {
      console.error('Failed to fetch stats:', error);
      return null;
    }
  }, [filters.date_from, filters.date_to, filters.scope]);

  // Unified monitoring hook (WebSocket or polling based on backend config)
  const {
    isConnected,
    monitorData,
    stats,
    refresh,
    mode,
    monitorInterval,
    statsInterval,
    updateIntervals,
  } = useMonitoring({
    websocketPath: '/ws/monitor/tasks/',
    fetchMonitorData: fetchTasks,
    fetchStats: fetchStatsData,
    onMonitorUpdate: (data) => {
      if (data && data.results) {
        // Update tasks from monitoring data
        setTotalCount(data.count);
      }
    },
    onStatsUpdate: (data) => {
      // Stats will be available via the stats property
    },
    messageTypes: ['task_updated', 'task_completed', 'task_failed'],
  });

  // Keep a stable ref to refresh so the mount effect doesn't need it as a dep
  const refreshRef = useRef(refresh);
  useEffect(() => { refreshRef.current = refresh; });

  // Trigger one immediate data load on component mount
  const didInitialLoad = useRef(false);
  useEffect(() => {
    if (!didInitialLoad.current) {
      didInitialLoad.current = true;
      refreshRef.current();
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Extract tasks from monitor data
  const tasks = monitorData?.results || [];

  /**
   * Format duration in seconds to human-readable format
   */
  const formatDuration = (seconds: number | null | undefined): string => {
    if (!seconds) return 'N/A';
    if (seconds < 60) return `${Math.round(seconds)}s`;
    if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
    return `${Math.round(seconds / 3600)}h`;
  };

  /**
   * Format date to relative time
   */
  const formatRelativeTime = (dateStr: string): string => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
    return `${Math.floor(diffMins / 1440)}d ago`;
  };

  return (
    <div className="space-y-6">
      {/* Connection Status Badge */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-slate-900 dark:text-white">
          Analysis Jobs Monitor
        </h2>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={refresh}
            className="flex items-center gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </Button>
          <div
            className={`flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium ${
              mode === 'websocket' && isConnected
                ? 'bg-success-100 text-success-700 dark:bg-success-900 dark:text-success-300'
                : mode === 'polling'
                ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
                : 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300'
            }`}
          >
            {mode === 'websocket' && isConnected ? (
              <>
                <Wifi className="w-4 h-4" />
                Live
              </>
            ) : mode === 'polling' ? (
              <>
                <RefreshCw className="w-4 h-4" />
                Polling
              </>
            ) : mode === 'loading' ? (
              <>
                <Clock className="w-4 h-4" />
                Loading...
              </>
            ) : (
              <>
                <WifiOff className="w-4 h-4" />
                Disconnected
              </>
            )}
          </div>
        </div>
      </div>

      {/* Monitor Settings */}
      <MonitorSettings
        mode={mode}
        isConnected={isConnected}
        monitorInterval={monitorInterval}
        statsInterval={statsInterval}
        onIntervalsUpdate={updateIntervals}
      />

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Total Jobs */}
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-600 dark:text-slate-400">
                    Total Jobs
                  </p>
                  <p className="text-3xl font-bold text-slate-900 dark:text-white mt-2">
                    {stats.total_jobs}
                  </p>
                </div>
                <Activity className="w-10 h-10 text-medical-500" />
              </div>
            </CardContent>
          </Card>

          {/* Completed */}
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-600 dark:text-slate-400">
                    Completed
                  </p>
                  <p className="text-3xl font-bold text-success-600 dark:text-success-400 mt-2">
                    {stats.by_status.COMPLETED || 0}
                  </p>
                </div>
                <CheckCircle className="w-10 h-10 text-success-500" />
              </div>
            </CardContent>
          </Card>

          {/* Failed */}
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-600 dark:text-slate-400">
                    Failed
                  </p>
                  <p className="text-3xl font-bold text-error-600 dark:text-error-400 mt-2">
                    {stats.by_status.FAILED || 0}
                  </p>
                </div>
                <XCircle className="w-10 h-10 text-error-500" />
              </div>
            </CardContent>
          </Card>

          {/* Processing */}
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-600 dark:text-slate-400">
                    Processing
                  </p>
                  <p className="text-3xl font-bold text-medical-600 dark:text-medical-400 mt-2">
                    {stats.by_status.PROCESSING || 0}
                  </p>
                </div>
                <Clock className="w-10 h-10 text-medical-500 animate-spin" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Filter className="w-5 h-5" />
            Filters
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Scope */}
            <div>
              <label className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2 block">
                Scope
              </label>
              <select
                value={filters.scope}
                onChange={(e) => {
                  setFilters({ ...filters, scope: e.target.value as any });
                  setCurrentPage(1);
                }}
                className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
              >
                <option value="own">My Jobs</option>
                <option value="colleagues">Colleagues</option>
                <option value="department">Department</option>
                <option value="team">Team</option>
              </select>
            </div>

            {/* Status */}
            <div>
              <label className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2 block">
                Status
              </label>
              <select
                value={filters.status || ''}
                onChange={(e) => {
                  setFilters({
                    ...filters,
                    status: e.target.value || undefined,
                  });
                  setCurrentPage(1);
                }}
                className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
              >
                <option value="">All Status</option>
                <option value="PENDING">Pending</option>
                <option value="QUEUED">Queued</option>
                <option value="PROCESSING">Processing</option>
                <option value="COMPLETED">Completed</option>
                <option value="FAILED">Failed</option>
              </select>
            </div>

            {/* Date Range (Simplified - defaults to 24h) */}
            <div>
              <label className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2 block">
                Time Range
              </label>
              <select
                onChange={(e) => {
                  const hours = parseInt(e.target.value);
                  const now = new Date();
                  const from = new Date(now.getTime() - hours * 60 * 60 * 1000);
                  setFilters({
                    ...filters,
                    date_from: from.toISOString(),
                    date_to: now.toISOString(),
                  });
                  setCurrentPage(1);
                }}
                className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
              >
                <option value="24">Last 24 hours</option>
                <option value="48">Last 2 days</option>
                <option value="168">Last week</option>
                <option value="720">Last 30 days</option>
              </select>
            </div>

            {/* Refresh Button */}
            <div className="flex items-end">
              <Button
                variant="outline"
                onClick={refresh}
                disabled={isLoading}
                className="w-full"
              >
                <RefreshCw className={`w-4 h-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
                Refresh
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Tasks Table */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Jobs ({totalCount})</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center py-12">
              <RefreshCw className="w-8 h-8 animate-spin mx-auto text-medical-500 mb-4" />
              <p className="text-slate-600 dark:text-slate-400">Loading tasks...</p>
            </div>
          ) : tasks.length === 0 ? (
            <div className="text-center py-12">
              <Activity className="w-12 h-12 mx-auto text-slate-300 dark:text-slate-600 mb-4" />
              <p className="text-slate-600 dark:text-slate-400">No tasks found</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="border-b border-slate-200 dark:border-slate-700">
                  <tr>
                    <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700 dark:text-slate-300">
                      Model
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700 dark:text-slate-300">
                      Status
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700 dark:text-slate-300">
                      User
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700 dark:text-slate-300">
                      Created
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700 dark:text-slate-300">
                      Duration
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700 dark:text-slate-300">
                      Results
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
                  {tasks.map((task) => {
                    const outputKeys: string[] = task.result_metadata?.output_keys ?? [];
                    const hasResults = task.status === 'COMPLETED' && task.result_file_path && outputKeys.length > 0;
                    return (
                    <tr
                      key={task.id}
                      className="hover:bg-slate-50 dark:hover:bg-slate-800 transition"
                    >
                      <td className="py-3 px-4">
                        <div>
                          <div className="font-medium text-slate-900 dark:text-white">
                            {task.model_name}
                          </div>
                          <div className="text-xs text-slate-500 dark:text-slate-400">
                            {task.model_key}
                          </div>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                            task.status === 'COMPLETED'
                              ? 'bg-success-100 text-success-800 dark:bg-success-900 dark:text-success-300'
                              : task.status === 'FAILED'
                              ? 'bg-error-100 text-error-800 dark:bg-error-900 dark:text-error-300'
                              : task.status === 'PROCESSING'
                              ? 'bg-medical-100 text-medical-800 dark:bg-medical-900 dark:text-medical-300'
                              : 'bg-slate-100 text-slate-800 dark:bg-slate-700 dark:text-slate-300'
                          }`}
                        >
                          {task.status}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <Users className="w-4 h-4 text-slate-400" />
                          <div>
                            <div className="text-sm text-slate-900 dark:text-white">
                              {task.created_by_name}
                            </div>
                            {task.created_by_department && (
                              <div className="text-xs text-slate-500 dark:text-slate-400">
                                {task.created_by_department}
                              </div>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
                          <Calendar className="w-4 h-4" />
                          {formatRelativeTime(task.created_at)}
                        </div>
                      </td>
                      <td className="py-3 px-4 text-sm text-slate-600 dark:text-slate-400">
                        {formatDuration(task.processing_duration)}
                      </td>
                      <td className="py-3 px-4">
                        {hasResults ? (
                          <div className="flex flex-col gap-1">
                            {outputKeys.map((key) => (
                              <button
                                key={key}
                                onClick={() =>
                                  apiClient.downloadTaskResultFile(task.id, key).catch(() =>
                                    toast.error(`Failed to download ${key}`)
                                  )
                                }
                                className="flex items-center gap-1 text-xs text-medical-600 dark:text-medical-400 hover:text-medical-800 dark:hover:text-medical-200 hover:underline"
                              >
                                <Download className="w-3 h-3 flex-shrink-0" />
                                {key}
                              </button>
                            ))}
                          </div>
                        ) : (
                          <span className="text-xs text-slate-400">—</span>
                        )}
                      </td>
                    </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          {totalCount > (filters.page_size || 20) && (
            <div className="flex items-center justify-between mt-4 pt-4 border-t border-slate-200 dark:border-slate-700">
              <p className="text-sm text-slate-600 dark:text-slate-400">
                Showing {(currentPage - 1) * (filters.page_size || 20) + 1} to{' '}
                {Math.min(currentPage * (filters.page_size || 20), totalCount)} of{' '}
                {totalCount} tasks
              </p>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  onClick={() => setCurrentPage((p) => p + 1)}
                  disabled={
                    currentPage * (filters.page_size || 20) >= totalCount
                  }
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};
