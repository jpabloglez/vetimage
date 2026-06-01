/**
 * Monitor Settings Component
 *
 * Displays current tracking mode and allows configuration of poll intervals.
 * Shows WebSocket status when enabled, or allows poll interval adjustment for polling mode.
 */

import React, { useState } from 'react';
import { Settings, ChevronDown, ChevronUp, Wifi, RefreshCw, Info } from 'lucide-react';
import Card, { CardHeader, CardTitle, CardContent } from '../ui/Card';
import Button from '../ui/Button';

export interface MonitorSettingsProps {
  /** Current tracking mode */
  mode: 'websocket' | 'polling' | 'loading';
  /** WebSocket connection status */
  isConnected: boolean;
  /** Current monitor poll interval (seconds) */
  monitorInterval?: number;
  /** Current stats poll interval (seconds) */
  statsInterval?: number;
  /** Callback when intervals are updated */
  onIntervalsUpdate?: (monitor: number, stats: number) => void;
}

export const MonitorSettings: React.FC<MonitorSettingsProps> = ({
  mode,
  isConnected,
  monitorInterval = 10,
  statsInterval = 30,
  onIntervalsUpdate,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [localMonitorInterval, setLocalMonitorInterval] = useState(monitorInterval);
  const [localStatsInterval, setLocalStatsInterval] = useState(statsInterval);

  const handleApply = () => {
    if (onIntervalsUpdate) {
      onIntervalsUpdate(localMonitorInterval, localStatsInterval);
    }
  };

  const handleReset = () => {
    setLocalMonitorInterval(10);
    setLocalStatsInterval(30);
    if (onIntervalsUpdate) {
      onIntervalsUpdate(10, 30);
    }
  };

  return (
    <Card variant="default" className="border-dashed">
      <CardHeader
        className="cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Settings className="w-5 h-5 text-slate-600 dark:text-slate-400" />
            <CardTitle className="text-base">Monitoring Settings</CardTitle>
          </div>
          <div className="flex items-center gap-2">
            {/* Mode Badge */}
            <div
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
                mode === 'websocket' && isConnected
                  ? 'bg-success-100 text-success-700 dark:bg-success-900 dark:text-success-300'
                  : mode === 'polling'
                  ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
                  : 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300'
              }`}
            >
              {mode === 'websocket' && isConnected ? (
                <>
                  <Wifi className="w-3 h-3" />
                  <span>WebSocket</span>
                </>
              ) : mode === 'polling' ? (
                <>
                  <RefreshCw className="w-3 h-3" />
                  <span>Polling</span>
                </>
              ) : (
                <span>Loading...</span>
              )}
            </div>
            {isExpanded ? (
              <ChevronUp className="w-4 h-4 text-slate-400" />
            ) : (
              <ChevronDown className="w-4 h-4 text-slate-400" />
            )}
          </div>
        </div>
      </CardHeader>

      {isExpanded && (
        <CardContent className="space-y-4 pt-4 border-t border-slate-200 dark:border-slate-700">
          {/* Mode Information */}
          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3">
            <div className="flex items-start gap-2">
              <Info className="w-4 h-4 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" />
              <div className="text-sm text-blue-800 dark:text-blue-200">
                {mode === 'websocket' ? (
                  <>
                    <p className="font-medium mb-1">WebSocket Mode (Real-time)</p>
                    <p className="text-blue-700 dark:text-blue-300">
                      Updates are received instantly via WebSocket connection.
                      {isConnected ? ' Connection active.' : ' Connection lost.'}
                    </p>
                  </>
                ) : mode === 'polling' ? (
                  <>
                    <p className="font-medium mb-1">Polling Mode (Periodic Updates)</p>
                    <p className="text-blue-700 dark:text-blue-300">
                      Data is fetched at regular intervals. Polling pauses when tab is hidden to save resources.
                    </p>
                  </>
                ) : (
                  <p>Loading configuration from backend...</p>
                )}
              </div>
            </div>
          </div>

          {/* Polling Interval Settings (only shown in polling mode) */}
          {mode === 'polling' && (
            <div className="space-y-4">
              <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                Poll Interval Settings
              </h4>

              {/* Monitor Data Interval */}
              <div className="space-y-2">
                <label className="flex items-center justify-between text-sm">
                  <span className="text-slate-700 dark:text-slate-300">
                    Tasks/Transfers List
                  </span>
                  <span className="text-slate-500 dark:text-slate-400 text-xs">
                    Every {localMonitorInterval}s
                  </span>
                </label>
                <input
                  type="range"
                  min="5"
                  max="60"
                  step="5"
                  value={localMonitorInterval}
                  onChange={(e) => setLocalMonitorInterval(Number(e.target.value))}
                  className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer accent-medical-600"
                />
                <div className="flex justify-between text-xs text-slate-500 dark:text-slate-400">
                  <span>5s (Fast)</span>
                  <span>30s (Balanced)</span>
                  <span>60s (Slow)</span>
                </div>
              </div>

              {/* Statistics Interval */}
              <div className="space-y-2">
                <label className="flex items-center justify-between text-sm">
                  <span className="text-slate-700 dark:text-slate-300">
                    Statistics
                  </span>
                  <span className="text-slate-500 dark:text-slate-400 text-xs">
                    Every {localStatsInterval}s
                  </span>
                </label>
                <input
                  type="range"
                  min="10"
                  max="120"
                  step="10"
                  value={localStatsInterval}
                  onChange={(e) => setLocalStatsInterval(Number(e.target.value))}
                  className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer accent-medical-600"
                />
                <div className="flex justify-between text-xs text-slate-500 dark:text-slate-400">
                  <span>10s (Fast)</span>
                  <span>60s (Balanced)</span>
                  <span>120s (Slow)</span>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-2 pt-2">
                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleApply}
                  disabled={
                    localMonitorInterval === monitorInterval &&
                    localStatsInterval === statsInterval
                  }
                >
                  Apply Changes
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleReset}
                  disabled={localMonitorInterval === 10 && localStatsInterval === 30}
                >
                  Reset to Defaults
                </Button>
              </div>

              {/* Performance Note */}
              <div className="text-xs text-slate-500 dark:text-slate-400 bg-slate-50 dark:bg-slate-800 rounded p-2">
                <strong>Note:</strong> Lower intervals provide more frequent updates but increase server load.
                Recommended: 10s for tasks, 30s for statistics.
              </div>
            </div>
          )}

          {/* WebSocket Info (only shown in WebSocket mode) */}
          {mode === 'websocket' && (
            <div className="text-sm text-slate-600 dark:text-slate-400">
              <p className="mb-2">
                WebSocket provides instant updates without polling. No configuration needed.
              </p>
              {!isConnected && (
                <div className="bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded p-2 text-error-700 dark:text-error-300">
                  ⚠️ Connection lost. Attempting to reconnect...
                </div>
              )}
            </div>
          )}
        </CardContent>
      )}
    </Card>
  );
};

export default MonitorSettings;
