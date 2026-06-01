/**
 * useMonitoring - Unified hook for real-time monitoring
 *
 * Automatically adapts between WebSocket and polling-based updates
 * based on backend configuration. Provides a consistent interface
 * regardless of the underlying mechanism.
 *
 * Features:
 * - Auto-detects tracking mode from backend
 * - WebSocket mode: Real-time updates via WebSocket
 * - Polling mode: Periodic HTTP requests (default)
 * - Unified interface for both modes
 * - Manual refresh capability
 *
 * @example
 * ```tsx
 * const { isConnected, monitorData, stats, refresh, mode } = useMonitoring({
 *   websocketPath: '/ws/monitor/tasks/',
 *   fetchMonitorData: () => apiClient.getMonitorTasks(filters),
 *   fetchStats: () => apiClient.getTaskStats(statsFilters),
 *   onMonitorUpdate: (data) => setTasks(data.results),
 *   onStatsUpdate: setStats,
 *   messageTypes: ['task_updated', 'task_completed', 'task_failed'],
 * });
 * ```
 */

import { useState, useEffect, useCallback } from 'react';
import { useWebSocket, WebSocketMessage } from './useWebSocket';
import { usePolling } from './usePolling';
import { apiClient } from '../utils/api';
import { FrontendConfig } from '../utils/api';

export interface UseMonitoringOptions {
  /** WebSocket path (if WebSocket mode) */
  websocketPath: string;
  /** Function to fetch monitor data */
  fetchMonitorData: () => Promise<any>;
  /** Function to fetch statistics */
  fetchStats: () => Promise<any>;
  /** Callback when monitor data updates */
  onMonitorUpdate?: (data: any) => void;
  /** Callback when stats update */
  onStatsUpdate?: (data: any) => void;
  /** WebSocket message types to handle */
  messageTypes?: string[];
}

export interface UseMonitoringReturn {
  /** Connection status (for WebSocket) or polling status */
  isConnected: boolean;
  /** Latest monitor data */
  monitorData: any | null;
  /** Latest statistics */
  stats: any | null;
  /** Manual refresh */
  refresh: () => Promise<void>;
  /** Tracking mode */
  mode: 'websocket' | 'polling' | 'loading';
  /** Current monitor poll interval (seconds) */
  monitorInterval: number;
  /** Current stats poll interval (seconds) */
  statsInterval: number;
  /** Update poll intervals (only works in polling mode) */
  updateIntervals: (monitor: number, stats: number) => void;
}

/**
 * Unified monitoring hook that adapts between WebSocket and polling
 *
 * @param options - Monitoring configuration
 * @returns Monitoring state and control methods
 */
export function useMonitoring({
  websocketPath,
  fetchMonitorData,
  fetchStats,
  onMonitorUpdate,
  onStatsUpdate,
  messageTypes = [],
}: UseMonitoringOptions): UseMonitoringReturn {
  const [config, setConfig] = useState<FrontendConfig | null>(null);
  const [monitorData, setMonitorData] = useState<any | null>(null);
  const [statsData, setStatsData] = useState<any | null>(null);

  // Custom intervals (overrides config if set)
  const [customMonitorInterval, setCustomMonitorInterval] = useState<number | null>(null);
  const [customStatsInterval, setCustomStatsInterval] = useState<number | null>(null);

  // Determine actual intervals to use (custom overrides config)
  const monitorInterval = customMonitorInterval ?? config?.monitor_poll_interval ?? 30;
  const statsInterval = customStatsInterval ?? config?.stats_poll_interval ?? 30;

  // Fetch configuration on mount
  useEffect(() => {
    apiClient
      .getFrontendConfig()
      .then((cfg) => {
        setConfig(cfg);
        console.log('[useMonitoring] Config loaded:', cfg);
      })
      .catch((error) => {
        console.error('[useMonitoring] Failed to load config:', error);
        // Fallback to polling if config fetch fails
        setConfig({
          websocket_based_tracking: false,
          monitor_poll_interval: 30,
          stats_poll_interval: 30,
          websocket_url: null,
        });
      });
  }, []);

  // WebSocket connection (only if enabled)
  const { connected: wsConnected, lastMessage } = useWebSocket(websocketPath, {
    autoConnect: config?.websocket_based_tracking ?? false,
  });

  // Polling for monitor data (only if WebSocket disabled)
  const { data: pollingMonitorData } = usePolling({
    fetchFn: fetchMonitorData,
    interval: monitorInterval * 1000,
    enabled: config?.websocket_based_tracking === false,
    onSuccess: onMonitorUpdate,
  });

  // Polling for stats (only if WebSocket disabled)
  const { data: pollingStatsData } = usePolling({
    fetchFn: fetchStats,
    interval: statsInterval * 1000,
    enabled: config?.websocket_based_tracking === false,
    onSuccess: onStatsUpdate,
  });

  // Handle WebSocket messages
  useEffect(() => {
    if (!config?.websocket_based_tracking || !lastMessage) return;

    if (messageTypes.includes(lastMessage.type)) {
      console.log('[useMonitoring] WebSocket update received:', lastMessage.type);
      // Trigger refresh on WebSocket update
      fetchMonitorData().then((data) => {
        setMonitorData(data);
        onMonitorUpdate?.(data);
      });
      fetchStats().then((data) => {
        setStatsData(data);
        onStatsUpdate?.(data);
      });
    }
  }, [lastMessage, config, messageTypes, fetchMonitorData, fetchStats, onMonitorUpdate, onStatsUpdate]);

  // Update monitor data based on mode
  useEffect(() => {
    if (config?.websocket_based_tracking === false && pollingMonitorData) {
      setMonitorData(pollingMonitorData);
    }
  }, [pollingMonitorData, config]);

  // Update stats based on mode
  useEffect(() => {
    if (config?.websocket_based_tracking === false && pollingStatsData) {
      setStatsData(pollingStatsData);
    }
  }, [pollingStatsData, config]);

  /**
   * Manual refresh - fetches both monitor data and stats
   */
  const refresh = useCallback(async () => {
    console.log('[useMonitoring] Manual refresh triggered');
    const [monitor, stats] = await Promise.all([fetchMonitorData(), fetchStats()]);
    setMonitorData(monitor);
    setStatsData(stats);
    onMonitorUpdate?.(monitor);
    onStatsUpdate?.(stats);
  }, [fetchMonitorData, fetchStats, onMonitorUpdate, onStatsUpdate]);

  /**
   * Update poll intervals (only works in polling mode)
   */
  const updateIntervals = useCallback((monitor: number, stats: number) => {
    console.log('[useMonitoring] Updating intervals:', { monitor, stats });
    setCustomMonitorInterval(monitor);
    setCustomStatsInterval(stats);
  }, []);

  // Determine current mode
  const mode = config === null
    ? 'loading'
    : config.websocket_based_tracking
      ? 'websocket'
      : 'polling';

  return {
    isConnected: config?.websocket_based_tracking ? wsConnected : true,
    monitorData,
    stats: statsData,
    refresh,
    mode,
    monitorInterval,
    statsInterval,
    updateIntervals,
  };
}
