/**
 * usePolling - Generic React hook for polling-based data fetching
 *
 * Provides automatic periodic data fetching with smart features:
 * - Configurable polling interval
 * - Automatic pause when page is hidden
 * - Error handling with callbacks
 * - Manual refetch capability
 * - Start/stop controls
 *
 * @example
 * ```tsx
 * const { data, isLoading, error, refetch } = usePolling({
 *   fetchFn: () => apiClient.getTasks(),
 *   interval: 10000, // 10 seconds
 *   onSuccess: (data) => console.log('Data updated:', data),
 * });
 * ```
 */

import { useState, useEffect, useRef, useCallback } from 'react';

export interface UsePollingOptions<T> {
  /** Function that fetches the data */
  fetchFn: () => Promise<T>;
  /** Polling interval in milliseconds */
  interval: number;
  /** Whether to start polling immediately (default: true) */
  enabled?: boolean;
  /** Callback when data is successfully fetched */
  onSuccess?: (data: T) => void;
  /** Callback when fetch fails */
  onError?: (error: Error) => void;
  /** Whether to pause polling when page is hidden (default: true) */
  pauseWhenHidden?: boolean;
}

export interface UsePollingReturn<T> {
  /** The most recent data */
  data: T | null;
  /** Whether currently fetching */
  isLoading: boolean;
  /** The most recent error */
  error: Error | null;
  /** Manually trigger a fetch */
  refetch: () => Promise<void>;
  /** Start polling */
  start: () => void;
  /** Stop polling */
  stop: () => void;
}

/**
 * Hook for periodic data fetching with smart features
 *
 * @param options - Polling configuration options
 * @returns Polling state and control methods
 */
export function usePolling<T>({
  fetchFn,
  interval,
  enabled = true,
  onSuccess,
  onError,
  pauseWhenHidden = true,
}: UsePollingOptions<T>): UsePollingReturn<T> {
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  // Manual start/stop control — starts enabled so `enabled` prop is the sole gate
  const [manualEnabled, setManualEnabled] = useState(true);

  // Combine external prop with manual control — both must be true to poll
  const isActive = enabled && manualEnabled;

  // Use refs for callbacks to prevent them from triggering fetch identity changes
  // (inline callbacks in parent components recreate on every render)
  const onSuccessRef = useRef(onSuccess);
  useEffect(() => { onSuccessRef.current = onSuccess; });
  const onErrorRef = useRef(onError);
  useEffect(() => { onErrorRef.current = onError; });

  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const isMountedRef = useRef(true);

  /**
   * Fetch data from the provided fetchFn.
   * Only depends on fetchFn and pauseWhenHidden — callbacks are accessed via refs
   * so changing them never causes the interval to restart.
   */
  const fetch = useCallback(async () => {
    if (pauseWhenHidden && document.visibilityState === 'hidden') {
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const result = await fetchFn();

      if (isMountedRef.current) {
        setData(result);
        setError(null);
        onSuccessRef.current?.(result);
      }
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err));

      if (isMountedRef.current) {
        setError(error);
        onErrorRef.current?.(error);
      }
    } finally {
      if (isMountedRef.current) {
        setIsLoading(false);
      }
    }
  }, [fetchFn, pauseWhenHidden]);

  /**
   * Start polling
   */
  const start = useCallback(() => {
    setManualEnabled(true);
  }, []);

  /**
   * Stop polling
   */
  const stop = useCallback(() => {
    setManualEnabled(false);
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  // Initial fetch and setup interval — fires when isActive or fetch changes
  useEffect(() => {
    if (!isActive) return;

    // Initial fetch
    fetch();

    // Setup polling interval
    intervalRef.current = setInterval(fetch, interval);

    // Cleanup
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [fetch, interval, isActive]);

  // Handle page visibility changes
  useEffect(() => {
    if (!pauseWhenHidden) return;

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible' && isActive) {
        fetch();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [fetch, isActive, pauseWhenHidden]);

  // Track mount status
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  return {
    data,
    isLoading,
    error,
    refetch: fetch,
    start,
    stop,
  };
}
