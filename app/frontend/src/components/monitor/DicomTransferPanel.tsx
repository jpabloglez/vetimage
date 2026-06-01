/**
 * DICOM Transfer Monitor Panel Component
 *
 * Real-time monitoring of DICOM study transfers with automatic mode detection.
 * Supports both WebSocket and polling-based updates.
 * Features stats cards, filters, and a table showing transfers from PACS/Orthanc.
 */

import React, { useState, useEffect, useCallback } from 'react';
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
  HardDrive,
  Server,
} from 'lucide-react';
import {
  apiClient,
  DicomTransfer,
  TransferStats,
  DicomTransferFilters,
} from '../../utils/api';
import { useMonitoring } from '../../hooks/useMonitoring';
import Card, { CardHeader, CardTitle, CardContent } from '../ui/Card';
import Button from '../ui/Button';
import MonitorSettings from './MonitorSettings';
import toast from 'react-hot-toast';

export const DicomTransferPanel: React.FC = () => {
  const [isLoading, setIsLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);

  // Filters
  const [filters, setFilters] = useState<DicomTransferFilters>({
    scope: 'own',
    page_size: 20,
  });

  /**
   * Fetch transfers from API
   */
  const fetchTransfers = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await apiClient.getMonitorTransfers({
        ...filters,
        page: currentPage,
      });
      setTotalCount(response.count);
      return response;
    } catch (error: any) {
      console.error('Failed to fetch transfers:', error);
      toast.error('Failed to load transfers');
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
      const statsData = await apiClient.getTransferStats({
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
    websocketPath: '/ws/monitor/transfers/',
    fetchMonitorData: fetchTransfers,
    fetchStats: fetchStatsData,
    onMonitorUpdate: (data) => {
      if (data && data.results) {
        // Update transfers from monitoring data
        setTotalCount(data.count);
      }
    },
    onStatsUpdate: (data) => {
      // Stats will be available via the stats property
    },
    messageTypes: ['transfer_updated', 'transfer_completed', 'transfer_failed'],
  });

  // Extract transfers from monitor data
  const transfers = monitorData?.results || [];

  /**
   * Format bytes to human-readable string
   */
  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
  };

  /**
   * Format duration to human-readable string
   */
  const formatDuration = (ms: number | null): string => {
    if (!ms) return '-';
    const seconds = ms / 1000;
    if (seconds < 60) return `${Math.round(seconds)}s`;
    if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
    return `${(seconds / 3600).toFixed(1)}h`;
  };

  /**
   * Format relative time
   */
  const formatRelativeTime = (dateString: string): string => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
    return `${Math.floor(diffMins / 1440)}d ago`;
  };

  /**
   * Get status badge color
   */
  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'success':
        return 'bg-success-100 text-success-600 dark:bg-success-900 dark:text-success-400';
      case 'failed':
        return 'bg-error-100 text-error-600 dark:bg-error-900 dark:text-error-400';
      case 'partial':
        return 'bg-warning-100 text-warning-600 dark:bg-warning-900 dark:text-warning-400';
      case 'in_progress':
        return 'bg-medical-100 text-medical-600 dark:bg-medical-900 dark:text-medical-400';
      default:
        return 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400';
    }
  };

  /**
   * Handle filter change
   */
  const handleFilterChange = (key: keyof DicomTransferFilters, value: any) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
    setCurrentPage(1); // Reset to first page
  };

  /**
   * Handle refresh
   */
  const handleRefresh = () => {
    refresh();
  };

  // Statistics cards
  const statsCards = [
    {
      title: 'Total Transfers',
      value: stats?.total_transfers || 0,
      icon: Activity,
      color: 'text-medical-600 dark:text-medical-400',
    },
    {
      title: 'Success Rate',
      value: stats ? `${(stats.success_rate * 100).toFixed(1)}%` : '0%',
      icon: CheckCircle,
      color: 'text-success-600 dark:text-success-400',
    },
    {
      title: 'Data Received',
      value: stats ? formatBytes(stats.total_data_received_bytes) : '0 B',
      icon: HardDrive,
      color: 'text-blue-600 dark:text-blue-400',
    },
    {
      title: 'Avg Transfer Time',
      value: stats?.avg_transfer_time_seconds
        ? `${stats.avg_transfer_time_seconds.toFixed(1)}s`
        : '-',
      icon: Clock,
      color: 'text-purple-600 dark:text-purple-400',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Connection Status and Refresh */}
      <div className="flex items-center justify-end gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={handleRefresh}
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
              <span>Live</span>
            </>
          ) : mode === 'polling' ? (
            <>
              <RefreshCw className="w-4 h-4" />
              <span>Polling</span>
            </>
          ) : mode === 'loading' ? (
            <>
              <Clock className="w-4 h-4" />
              <span>Loading...</span>
            </>
          ) : (
            <>
              <WifiOff className="w-4 h-4" />
              <span>Disconnected</span>
            </>
          )}
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

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {statsCards.map((card) => (
          <Card key={card.title} variant="medical">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-600 dark:text-slate-400">{card.title}</p>
                  <p className="text-2xl font-bold mt-2">{card.value}</p>
                </div>
                <card.icon className={`w-8 h-8 ${card.color}`} />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Filter className="w-5 h-5" />
            <CardTitle>Filters</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Scope Filter */}
            <div>
              <label className="block text-sm font-medium mb-2">
                <Users className="w-4 h-4 inline mr-1" />
                Scope
              </label>
              <select
                className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800"
                value={filters.scope || 'own'}
                onChange={(e) =>
                  handleFilterChange('scope', e.target.value as 'own' | 'colleagues' | 'department' | 'team')
                }
              >
                <option value="own">My Transfers</option>
                <option value="colleagues">Colleagues</option>
                <option value="department">Department</option>
                <option value="team">Team</option>
              </select>
            </div>

            {/* Status Filter */}
            <div>
              <label className="block text-sm font-medium mb-2">
                <Activity className="w-4 h-4 inline mr-1" />
                Status
              </label>
              <select
                className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800"
                value={filters.status || ''}
                onChange={(e) => handleFilterChange('status', e.target.value || undefined)}
              >
                <option value="">All Statuses</option>
                <option value="success">Success</option>
                <option value="partial">Partial</option>
                <option value="failed">Failed</option>
                <option value="in_progress">In Progress</option>
              </select>
            </div>

            {/* Time Range */}
            <div>
              <label className="block text-sm font-medium mb-2">
                <Calendar className="w-4 h-4 inline mr-1" />
                Time Range
              </label>
              <select
                className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800"
                onChange={(e) => {
                  const hours = parseInt(e.target.value);
                  if (hours > 0) {
                    const now = new Date();
                    const past = new Date(now.getTime() - hours * 60 * 60 * 1000);
                    handleFilterChange('date_from', past.toISOString());
                    handleFilterChange('date_to', now.toISOString());
                  } else {
                    handleFilterChange('date_from', undefined);
                    handleFilterChange('date_to', undefined);
                  }
                }}
              >
                <option value="24">Last 24 hours</option>
                <option value="48">Last 2 days</option>
                <option value="168">Last week</option>
                <option value="720">Last 30 days</option>
              </select>
            </div>

            {/* Refresh Button */}
            <div>
              <label className="block text-sm font-medium mb-2 opacity-0">Refresh</label>
              <Button
                onClick={handleRefresh}
                variant="outline"
                size="md"
                className="w-full"
              >
                <RefreshCw className="w-4 h-4 mr-2" />
                Refresh
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Transfers Table */}
      <Card>
        <CardHeader>
          <CardTitle>DICOM Transfers</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center items-center py-12">
              <Activity className="w-8 h-8 animate-spin text-medical-600" />
            </div>
          ) : transfers.length === 0 ? (
            <div className="text-center py-12 text-slate-600 dark:text-slate-400">
              <Server className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>No transfers found</p>
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-slate-50 dark:bg-slate-800">
                    <tr>
                      <th className="px-4 py-3 text-left text-sm font-medium">Study UID</th>
                      <th className="px-4 py-3 text-left text-sm font-medium">Source</th>
                      <th className="px-4 py-3 text-left text-sm font-medium">Modality</th>
                      <th className="px-4 py-3 text-left text-sm font-medium">Status</th>
                      <th className="px-4 py-3 text-left text-sm font-medium">Instances</th>
                      <th className="px-4 py-3 text-left text-sm font-medium">Size</th>
                      <th className="px-4 py-3 text-left text-sm font-medium">Duration</th>
                      <th className="px-4 py-3 text-left text-sm font-medium">Received</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
                    {transfers.map((transfer) => (
                      <tr
                        key={transfer.study_instance_uid}
                        className="hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                      >
                        <td className="px-4 py-3 text-sm">
                          <div className="font-mono text-xs truncate max-w-xs" title={transfer.study_instance_uid}>
                            {transfer.study_instance_uid.substring(0, 20)}...
                          </div>
                          <div className="text-xs text-slate-600 dark:text-slate-400 mt-1">
                            {transfer.study_description || 'No description'}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-sm">
                          <div className="font-medium">{transfer.source_pacs_name}</div>
                          <div className="text-xs text-slate-600 dark:text-slate-400">
                            {transfer.source_ae} • {transfer.source_ip}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-sm">
                          <span className="px-2 py-1 bg-slate-100 dark:bg-slate-800 rounded text-xs font-medium">
                            {transfer.modality || 'Unknown'}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm">
                          <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusBadge(transfer.transfer_status)}`}>
                            {transfer.transfer_status.replace('_', ' ').toUpperCase()}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm">
                          <div className="font-medium">
                            {transfer.successful_instances}/{transfer.total_instances}
                          </div>
                          {transfer.failed_instances > 0 && (
                            <div className="text-xs text-error-600 dark:text-error-400">
                              {transfer.failed_instances} failed
                            </div>
                          )}
                        </td>
                        <td className="px-4 py-3 text-sm">{formatBytes(transfer.total_size_bytes)}</td>
                        <td className="px-4 py-3 text-sm">{formatDuration(transfer.total_duration_ms)}</td>
                        <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-400">
                          {formatRelativeTime(transfer.first_transfer_at)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              <div className="mt-6 flex items-center justify-between">
                <div className="text-sm text-slate-600 dark:text-slate-400">
                  Showing {Math.min((currentPage - 1) * (filters.page_size || 20) + 1, totalCount)} -{' '}
                  {Math.min(currentPage * (filters.page_size || 20), totalCount)} of {totalCount} transfers
                </div>
                <div className="flex gap-2">
                  <Button
                    onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                    disabled={currentPage === 1}
                    variant="outline"
                    size="sm"
                  >
                    Previous
                  </Button>
                  <Button
                    onClick={() => setCurrentPage((p) => p + 1)}
                    disabled={currentPage * (filters.page_size || 20) >= totalCount}
                    variant="outline"
                    size="sm"
                  >
                    Next
                  </Button>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
};
