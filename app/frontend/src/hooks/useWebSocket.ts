/**
 * useWebSocket - React hook for WebSocket connections
 *
 * Provides a simple interface for establishing and managing WebSocket
 * connections with automatic reconnection and authentication.
 *
 * Features:
 * - Automatic connection on mount
 * - Auto-reconnection with exponential backoff
 * - Authentication via session (inherited from browser)
 * - Connection status tracking
 * - Message broadcasting to components
 *
 * @example
 * ```tsx
 * const { connected, lastMessage, send } = useWebSocket('/ws/monitor/tasks/');
 *
 * useEffect(() => {
 *   if (lastMessage?.type === 'task_updated') {
 *     console.log('Task updated:', lastMessage.task);
 *   }
 * }, [lastMessage]);
 * ```
 */

import { useState, useEffect, useRef, useCallback } from 'react';

// WebSocket base URL from environment
const WS_BASE_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:3081';

/**
 * WebSocket message types that can be received from the server
 */
export interface WebSocketMessage {
  type:
    | 'connection'
    | 'task_updated'
    | 'task_completed'
    | 'task_failed'
    | 'transfer_updated'
    | 'transfer_completed'
    | 'transfer_failed';
  status?: string;
  message?: string;
  task?: any;
  transfer?: any;
  notification?: {
    title: string;
    message: string;
    error?: string;
  };
}

export interface UseWebSocketReturn {
  /** Whether the WebSocket is currently connected */
  connected: boolean;
  /** The most recent message received */
  lastMessage: WebSocketMessage | null;
  /** Send a message to the WebSocket server */
  send: (data: any) => void;
  /** Manually disconnect the WebSocket */
  disconnect: () => void;
  /** Manually reconnect the WebSocket */
  reconnect: () => void;
}

interface UseWebSocketOptions {
  /** Whether to automatically connect on mount (default: true) */
  autoConnect?: boolean;
  /** Maximum reconnection attempts (default: Infinity) */
  maxReconnectAttempts?: number;
  /** Initial reconnection delay in ms (default: 1000) */
  reconnectDelay?: number;
  /** Maximum reconnection delay in ms (default: 30000) */
  maxReconnectDelay?: number;
  /** Callback when connection is established */
  onConnect?: () => void;
  /** Callback when connection is closed */
  onDisconnect?: (code: number) => void;
  /** Callback when a message is received */
  onMessage?: (message: WebSocketMessage) => void;
  /** Callback when an error occurs */
  onError?: (error: Event) => void;
}

/**
 * React hook for WebSocket connections with auto-reconnection
 *
 * @param path - WebSocket path (e.g., '/ws/monitor/tasks/')
 * @param options - Configuration options
 * @returns WebSocket connection state and methods
 */
export const useWebSocket = (
  path: string,
  options: UseWebSocketOptions = {}
): UseWebSocketReturn => {
  const {
    autoConnect = true,
    maxReconnectAttempts = Infinity,
    reconnectDelay = 1000,
    maxReconnectDelay = 30000,
    onConnect,
    onDisconnect,
    onMessage,
    onError,
  } = options;

  const [connected, setConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const currentDelayRef = useRef(reconnectDelay);
  const shouldConnectRef = useRef(autoConnect);

  /**
   * Clean up reconnection timeout
   */
  const clearReconnectTimeout = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
  }, []);

  /**
   * Establish WebSocket connection
   */
  const connect = useCallback(() => {
    // Don't connect if already connected or explicitly disconnected
    if (wsRef.current?.readyState === WebSocket.OPEN || !shouldConnectRef.current) {
      return;
    }

    // Get JWT access token from global (set by AuthContext)
    const token = (window as any).__auth_token__;

    // Construct full WebSocket URL with token query parameter
    const url = token
      ? `${WS_BASE_URL}${path}?token=${encodeURIComponent(token)}`
      : `${WS_BASE_URL}${path}`;

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        reconnectAttemptsRef.current = 0;
        currentDelayRef.current = reconnectDelay;
        console.log('[WebSocket] Connected:', path);
        onConnect?.();
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as WebSocketMessage;
          setLastMessage(message);
          onMessage?.(message);
        } catch (error) {
          console.error('[WebSocket] Failed to parse message:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('[WebSocket] Error:', error);
        onError?.(error);
      };

      ws.onclose = (event) => {
        setConnected(false);
        console.log('[WebSocket] Disconnected:', path, 'Code:', event.code);
        onDisconnect?.(event.code);

        // Attempt reconnection if not explicitly closed and under max attempts
        if (
          shouldConnectRef.current &&
          reconnectAttemptsRef.current < maxReconnectAttempts
        ) {
          reconnectAttemptsRef.current += 1;

          console.log(
            `[WebSocket] Reconnecting in ${currentDelayRef.current}ms ` +
            `(attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts})...`
          );

          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, currentDelayRef.current);

          // Exponential backoff with max delay cap
          currentDelayRef.current = Math.min(
            currentDelayRef.current * 2,
            maxReconnectDelay
          );
        } else if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
          console.error('[WebSocket] Max reconnection attempts reached');
        }
      };
    } catch (error) {
      console.error('[WebSocket] Failed to create connection:', error);
    }
  }, [path, maxReconnectAttempts, reconnectDelay, maxReconnectDelay, onConnect, onDisconnect, onMessage, onError]);

  /**
   * Send a message through the WebSocket
   */
  const send = useCallback((data: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    } else {
      console.warn('[WebSocket] Cannot send message: connection not open');
    }
  }, []);

  /**
   * Manually disconnect the WebSocket
   */
  const disconnect = useCallback(() => {
    shouldConnectRef.current = false;
    clearReconnectTimeout();

    if (wsRef.current) {
      wsRef.current.close(1000, 'Manual disconnect');
      wsRef.current = null;
    }
  }, [clearReconnectTimeout]);

  /**
   * Manually reconnect the WebSocket
   */
  const reconnect = useCallback(() => {
    disconnect();
    shouldConnectRef.current = true;
    reconnectAttemptsRef.current = 0;
    currentDelayRef.current = reconnectDelay;
    connect();
  }, [disconnect, connect, reconnectDelay]);

  // Connect on mount if autoConnect is true, but wait for token
  useEffect(() => {
    if (!autoConnect) return;

    let retryCount = 0;
    const maxRetries = 50; // 50 * 100ms = 5 seconds max wait
    let retryTimeout: NodeJS.Timeout | null = null;

    // Wait for token to be available before connecting
    const checkTokenAndConnect = () => {
      const token = (window as any).__auth_token__;
      if (token) {
        console.log('[WebSocket] Token available, connecting...');
        connect();
      } else if (retryCount < maxRetries) {
        retryCount++;
        // Retry after 100ms if no token yet
        retryTimeout = setTimeout(checkTokenAndConnect, 100);
      } else {
        console.warn('[WebSocket] Token not available after 5 seconds, connecting without token');
        connect();
      }
    };

    checkTokenAndConnect();

    // Cleanup on unmount
    return () => {
      shouldConnectRef.current = false;
      clearReconnectTimeout();
      if (retryTimeout) {
        clearTimeout(retryTimeout);
      }
      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmount');
      }
    };
  }, [connect, clearReconnectTimeout, autoConnect]);

  return {
    connected,
    lastMessage,
    send,
    disconnect,
    reconnect,
  };
};
