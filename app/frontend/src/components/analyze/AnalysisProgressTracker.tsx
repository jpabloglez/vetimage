/**
 * Analysis Progress Tracker
 *
 * Visual step indicator for the analysis workflow:
 * upload -> processing -> complete
 */

import React from 'react';
import { Upload, Loader2, CheckCircle, XCircle } from 'lucide-react';
import { useTranslation } from 'react-i18next';

type AnalysisStage = 'uploading' | 'processing' | 'complete' | 'error';

interface AnalysisProgressTrackerProps {
  stage: AnalysisStage;
  uploadProgress?: number;
  taskStatus?: string;
  errorMessage?: string;
}

const stageKeys = [
  { key: 'uploading', labelKey: 'steps.upload', icon: Upload },
  { key: 'processing', labelKey: 'progress.processing', icon: Loader2 },
  { key: 'complete', labelKey: 'progress.completed', icon: CheckCircle },
];

export const AnalysisProgressTracker: React.FC<AnalysisProgressTrackerProps> = ({
  stage,
  uploadProgress = 0,
  taskStatus,
  errorMessage,
}) => {
  const { t } = useTranslation('analyze');
  const stageOrder = ['uploading', 'processing', 'complete'];
  const currentIdx = stageOrder.indexOf(stage === 'error' ? 'processing' : stage);

  return (
    <div className="medical-card p-6">
      <h3 className="text-sm font-medium text-slate-600 dark:text-slate-400 mb-4">
        {t('progress.processing')}
      </h3>

      <div className="flex items-center justify-between mb-6">
        {stageKeys.map((s, idx) => {
          const Icon = s.icon;
          const isComplete = idx < currentIdx;
          const isActive = idx === currentIdx;
          const isError = stage === 'error' && idx === currentIdx;

          return (
            <React.Fragment key={s.key}>
              <div className="flex flex-col items-center">
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center transition-colors ${
                    isError
                      ? 'bg-error-100 dark:bg-error-900/30 text-error-600 dark:text-error-400'
                      : isComplete
                      ? 'bg-success-100 dark:bg-success-900/30 text-success-600 dark:text-success-400'
                      : isActive
                      ? 'bg-medical-100 dark:bg-medical-900/30 text-medical-600 dark:text-medical-400'
                      : 'bg-slate-100 dark:bg-slate-800 text-slate-400 dark:text-slate-500'
                  }`}
                >
                  {isError ? (
                    <XCircle className="w-5 h-5" />
                  ) : isComplete ? (
                    <CheckCircle className="w-5 h-5" />
                  ) : isActive && s.key === 'processing' ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    <Icon className="w-5 h-5" />
                  )}
                </div>
                <span
                  className={`text-xs mt-2 font-medium ${
                    isError
                      ? 'text-error-600 dark:text-error-400'
                      : isComplete || isActive
                      ? 'text-slate-900 dark:text-white'
                      : 'text-slate-400 dark:text-slate-500'
                  }`}
                >
                  {t(s.labelKey)}
                </span>
              </div>

              {idx < stageKeys.length - 1 && (
                <div
                  className={`flex-1 h-0.5 mx-3 ${
                    idx < currentIdx
                      ? 'bg-success-400'
                      : 'bg-slate-200 dark:bg-slate-700'
                  }`}
                />
              )}
            </React.Fragment>
          );
        })}
      </div>

      {/* Progress detail */}
      {stage === 'uploading' && (
        <div>
          <div className="flex items-center justify-between text-sm text-slate-600 dark:text-slate-400 mb-2">
            <span>{t('upload.uploading')}</span>
            <span>{uploadProgress}%</span>
          </div>
          <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2">
            <div
              className="bg-medical-500 h-2 rounded-full transition-all duration-300"
              style={{ width: `${uploadProgress}%` }}
            />
          </div>
        </div>
      )}

      {stage === 'processing' && taskStatus && (
        <div className="text-sm text-slate-600 dark:text-slate-400 text-center">
          {t('common:labels.status')}: <span className="font-medium text-medical-600 dark:text-medical-400">{taskStatus}</span>
        </div>
      )}

      {stage === 'error' && errorMessage && (
        <div className="text-sm text-error-600 dark:text-error-400 text-center bg-error-50 dark:bg-error-900/20 rounded-lg p-3">
          {errorMessage}
        </div>
      )}

      {stage === 'complete' && (
        <div className="text-sm text-success-600 dark:text-success-400 text-center">
          {t('progress.completed')}
        </div>
      )}
    </div>
  );
};

export default AnalysisProgressTracker;
