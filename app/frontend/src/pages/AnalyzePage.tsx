/**
 * Analyze Page
 *
 * Three-tab interface for medical image analysis:
 *  1. Worklist     — Patient/analysis history ordered by date (PACS-style)
 *  2. New Analysis — 4-step workflow: Upload → Select → Configure → Monitor
 *  3. Reports      — Generated reports list with PDF download
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  ChevronRight, Upload, Brain, Settings, CheckCircle,
  Search, RefreshCw, Clock, FileText, Download, Plus,
  ChevronDown, ChevronUp, GitCompare,
} from 'lucide-react';

import { MedicalImageUploader } from '../components/uploader/MedicalImageUploader';
import { DragDropUploadZone } from '../components/analyze/DragDropUploadZone';
import { MetadataViewer } from '../components/analysis/MetadataViewer';
import { ModelRecommendation } from '../components/analysis/ModelRecommendation';
import { ParameterConfigurator } from '../components/analysis/ParameterConfigurator';
import ReportViewer from '../components/reports/ReportViewer';
import GenerateReportModal from '../components/reports/GenerateReportModal';
import ComparisonSelector from '../components/reports/ComparisonSelector';
import ReportComparison from '../components/reports/ReportComparison';
import ModelCard from '../components/models/ModelCard';
import AiDisclaimer from '../components/AiDisclaimer';
import Card, { CardContent, CardHeader, CardTitle } from '../components/ui/Card';

import {
  UploadedMedicalImage, AIModel, AnalysisTask, Report, apiClient,
} from '../utils/api';
import Button from '../components/ui/Button';
import toast from 'react-hot-toast';

// ─── Types ────────────────────────────────────────────────────────────────────

type AnalyzePageTab = 'worklist' | 'new' | 'reports' | 'models';
type WorkflowStep = 'upload' | 'select' | 'configure';

interface StepConfig {
  key: WorkflowStep;
  number: number;
  titleKey: string;
  icon: React.ElementType;
  descriptionKey: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const WORKFLOW_STEPS: StepConfig[] = [
  { key: 'upload',    number: 1, titleKey: 'steps.upload',      icon: Upload,   descriptionKey: 'steps.uploadDesc' },
  { key: 'select',    number: 2, titleKey: 'steps.selectModel',  icon: Brain,    descriptionKey: 'steps.selectModelDesc' },
  { key: 'configure', number: 3, titleKey: 'steps.configure',    icon: Settings, descriptionKey: 'steps.configureDesc' },
];

const STATUS_COLORS: Record<AnalysisTask['status'], string> = {
  PENDING:    'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
  QUEUED:     'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300',
  DISPATCHED: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300',
  PROCESSING: 'bg-amber-100 text-amber-700 dark:bg-amber-900/50 dark:text-amber-300',
  COMPLETED:  'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300',
  FAILED:     'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300',
  TIMEOUT:    'bg-orange-100 text-orange-700 dark:bg-orange-900/50 dark:text-orange-300',
  CANCELLED:  'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-500',
};

const PAGE_SIZE = 20;

const INPUT_CLS =
  'w-full px-3 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-medical-500 focus:border-medical-500 outline-none';

function formatDuration(seconds?: number): string {
  if (!seconds) return '—';
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  return `${Math.floor(seconds / 60)}m ${(seconds % 60).toFixed(0)}s`;
}

// ─── StepIndicator ────────────────────────────────────────────────────────────

const StepIndicator: React.FC<{
  steps: StepConfig[];
  currentStep: WorkflowStep;
  completedSteps: Set<WorkflowStep>;
}> = ({ steps, currentStep, completedSteps }) => {
  const { t } = useTranslation('analyze');
  return (
    <div className="mb-8">
      <div className="flex items-center justify-between">
        {steps.map((step, index) => {
          const isActive = step.key === currentStep;
          const isCompleted = completedSteps.has(step.key);
          const Icon = step.icon;
          return (
            <React.Fragment key={step.key}>
              <div className="flex flex-col items-center flex-1">
                <div className={`w-12 h-12 rounded-full flex items-center justify-center mb-2 transition-colors ${
                  isCompleted ? 'bg-success-500 text-white' :
                  isActive    ? 'bg-medical-500 text-white' :
                                'bg-slate-200 dark:bg-slate-700 text-slate-400 dark:text-slate-500'
                }`}>
                  {isCompleted ? <CheckCircle className="h-6 w-6" /> : <Icon className="h-6 w-6" />}
                </div>
                <p className={`text-sm font-semibold text-center ${
                  isActive    ? 'text-medical-600 dark:text-medical-400' :
                  isCompleted ? 'text-success-600 dark:text-success-400' :
                                'text-slate-500 dark:text-slate-400'
                }`}>
                  {t(step.titleKey)}
                </p>
                <p className="text-xs text-slate-400 dark:text-slate-500 text-center mt-1 hidden md:block">
                  {t(step.descriptionKey)}
                </p>
              </div>
              {index < steps.length - 1 && (
                <div className="flex-shrink-0 w-12 mb-8">
                  <ChevronRight className={`h-5 w-5 mx-auto ${
                    completedSteps.has(step.key) ? 'text-success-500' : 'text-slate-300 dark:text-slate-600'
                  }`} />
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};

// ─── WorklistTab ──────────────────────────────────────────────────────────────

const WorklistTab: React.FC = () => {
  const { t } = useTranslation('analyze');
  const [tasks, setTasks]   = useState<AnalysisTask[]>([]);
  const [models, setModels] = useState<AIModel[]>([]);
  const [loading, setLoading] = useState(true);

  const [search, setSearch]           = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [modelFilter, setModelFilter]   = useState('');
  const [dateFrom, setDateFrom]         = useState('');
  const [dateTo, setDateTo]             = useState('');
  const [page, setPage] = useState(1);

  useEffect(() => {
    apiClient.getAIModels().then(setModels).catch(() => {});
  }, []);

  const fetchTasks = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiClient.getAnalysisTasks({
        ...(statusFilter && { status: statusFilter }),
        ...(modelFilter  && { model: modelFilter }),
        limit: 200,
      });
      setTasks(data);
    } catch {
      toast.error(t('common:errors.loadFailed'));
    } finally {
      setLoading(false);
    }
  }, [statusFilter, modelFilter, t]);

  useEffect(() => {
    fetchTasks();
    setPage(1);
  }, [fetchTasks]);

  // Client-side: search by filename, date range — then triage so STAT/urgent
  // cases surface at the top of the worklist.
  const PRIORITY_RANK: Record<string, number> = { stat: 0, urgent: 1, routine: 2 };
  const filtered = tasks
    .filter((task) => {
      const filename = (task.input_image as any)?.filename ?? '';
      if (search && !filename.toLowerCase().includes(search.toLowerCase())) return false;
      if (dateFrom && new Date(task.created_at) < new Date(dateFrom)) return false;
      if (dateTo   && new Date(task.created_at) > new Date(`${dateTo}T23:59:59`)) return false;
      return true;
    })
    .sort((a, b) => {
      const pa = PRIORITY_RANK[a.priority ?? 'routine'] ?? 2;
      const pb = PRIORITY_RANK[b.priority ?? 'routine'] ?? 2;
      if (pa !== pb) return pa - pb;
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    });

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const pageItems  = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const handleRetry = async (taskId: string) => {
    try {
      await apiClient.retryAnalysisTask(taskId);
      toast.success(t('worklist.retried'));
      fetchTasks();
    } catch {
      toast.error(t('common:errors.generic'));
    }
  };

  const handleGenerateReport = async (taskId: string) => {
    try {
      await apiClient.createReport(taskId);
      toast.success(t('worklist.reportCreated'));
    } catch {
      toast.error(t('common:errors.generic'));
    }
  };

  return (
    <div>
      {/* Filter Bar */}
      <div className="medical-card p-4 mb-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
            <input
              type="text"
              placeholder={t('worklist.searchPlaceholder')}
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              className={`${INPUT_CLS} pl-9`}
            />
          </div>

          {/* Status */}
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
            className={INPUT_CLS}
          >
            <option value="">{t('worklist.allStatuses')}</option>
            {(['PENDING','QUEUED','DISPATCHED','PROCESSING','COMPLETED','FAILED','TIMEOUT','CANCELLED'] as const).map((s) => (
              <option key={s} value={s}>{t(`progress.${s.toLowerCase()}`)}</option>
            ))}
          </select>

          {/* Model */}
          <select
            value={modelFilter}
            onChange={(e) => { setModelFilter(e.target.value); setPage(1); }}
            className={INPUT_CLS}
          >
            <option value="">{t('worklist.allModels')}</option>
            {models.map((m) => (
              <option key={m.key} value={m.key}>{m.name}</option>
            ))}
          </select>

          {/* Date From */}
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => { setDateFrom(e.target.value); setPage(1); }}
            className={INPUT_CLS}
          />

          {/* Date To */}
          <input
            type="date"
            value={dateTo}
            onChange={(e) => { setDateTo(e.target.value); setPage(1); }}
            className={INPUT_CLS}
          />
        </div>
      </div>

      {/* Toolbar */}
      <div className="flex justify-between items-center mb-4">
        <span className="text-sm text-slate-600 dark:text-slate-400">
          {!loading && filtered.length > 0 && t('common:pagination.showing', {
            from: Math.min((page - 1) * PAGE_SIZE + 1, filtered.length),
            to:   Math.min(page * PAGE_SIZE, filtered.length),
            total: filtered.length,
          })}
        </span>
        <button
          onClick={fetchTasks}
          className="flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          {t('common:buttons.refresh')}
        </button>
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex justify-center py-16">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-medical-600" />
        </div>
      ) : pageItems.length === 0 ? (
        <div className="medical-card p-12 text-center">
          <FileText className="w-12 h-12 text-slate-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">
            {t('worklist.noTasks')}
          </h3>
          <p className="text-slate-600 dark:text-slate-400">{t('worklist.noTasksHint')}</p>
        </div>
      ) : (
        <div className="medical-card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
                  {(['patient','model','status','created','duration','actions'] as const).map((col) => (
                    <th key={col} className="text-left px-4 py-3 font-medium text-slate-600 dark:text-slate-400">
                      {t(`worklist.columns.${col}`)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
                {pageItems.map((task) => {
                  const img = task.input_image as any;
                  const filename = img?.filename ?? `#${task.id.slice(0, 8)}`;
                  const statusColor = STATUS_COLORS[task.status] ?? STATUS_COLORS.PENDING;
                  const statusKey = task.status?.toLowerCase() ?? 'pending';
                  return (
                    <tr key={task.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                      {/* Patient / File */}
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <FileText className="w-4 h-4 text-medical-500 flex-shrink-0" />
                          <div className="min-w-0">
                            <div className="flex items-center gap-1.5">
                              <p className="font-medium text-slate-900 dark:text-slate-100 truncate max-w-[180px]">
                                {filename}
                              </p>
                              {task.priority && task.priority !== 'routine' && (
                                <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold uppercase ${
                                  task.priority === 'stat'
                                    ? 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300'
                                    : 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300'
                                }`}>
                                  {task.priority}
                                </span>
                              )}
                            </div>
                            {img?.format && (
                              <p className="text-xs text-slate-500 dark:text-slate-400 uppercase">{img.format}</p>
                            )}
                          </div>
                        </div>
                      </td>

                      {/* Model */}
                      <td className="px-4 py-3">
                        <p className="font-medium text-slate-900 dark:text-slate-100">{task.model?.name ?? '—'}</p>
                        <p className="text-xs text-slate-500 dark:text-slate-400">
                          {task.model?.model_type}{task.model?.version ? ` · v${task.model.version}` : ''}
                        </p>
                      </td>

                      {/* Status */}
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${statusColor}`}>
                          {t(`progress.${statusKey}`)}
                        </span>
                        {task.error_message && (
                          <p className="text-xs text-red-500 dark:text-red-400 mt-1 max-w-[160px] truncate" title={task.error_message}>
                            {task.error_message}
                          </p>
                        )}
                      </td>

                      {/* Created */}
                      <td className="px-4 py-3 text-slate-600 dark:text-slate-400 whitespace-nowrap">
                        <div className="flex items-center gap-1.5">
                          <Clock className="w-3.5 h-3.5 flex-shrink-0" />
                          <span>{new Date(task.created_at).toLocaleString()}</span>
                        </div>
                      </td>

                      {/* Duration */}
                      <td className="px-4 py-3 text-slate-600 dark:text-slate-400">
                        {formatDuration(task.processing_duration)}
                      </td>

                      {/* Actions */}
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          {task.status === 'FAILED' && (
                            <button
                              onClick={() => handleRetry(task.id)}
                              className="flex items-center gap-1 px-2 py-1 text-xs rounded border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                            >
                              <RefreshCw className="w-3 h-3" />
                              {t('worklist.retry')}
                            </button>
                          )}
                          {task.status === 'COMPLETED' && (
                            <button
                              onClick={() => handleGenerateReport(task.id)}
                              className="flex items-center gap-1 px-2 py-1 text-xs rounded border border-medical-300 dark:border-medical-700 text-medical-700 dark:text-medical-300 hover:bg-medical-50 dark:hover:bg-medical-950/30 transition-colors"
                            >
                              <FileText className="w-3 h-3" />
                              {t('worklist.generateReport')}
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-between items-center mt-4">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-4 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-600 disabled:opacity-40 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          >
            {t('common:pagination.previous')}
          </button>
          <span className="text-sm text-slate-600 dark:text-slate-400">
            {t('common:pagination.pageOf', { current: page, total: totalPages })}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-4 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-600 disabled:opacity-40 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          >
            {t('common:pagination.next')}
          </button>
        </div>
      )}
    </div>
  );
};

// ─── NewAnalysisTab ───────────────────────────────────────────────────────────

const NewAnalysisTab: React.FC = () => {
  const { t } = useTranslation('analyze');
  const [currentStep, setCurrentStep]     = useState<WorkflowStep>('upload');
  const [completedSteps, setCompletedSteps] = useState<Set<WorkflowStep>>(new Set());
  const [uploadedImages, setUploadedImages] = useState<UploadedMedicalImage[]>([]);
  const [selectedImage, setSelectedImage]   = useState<UploadedMedicalImage | null>(null);
  const [selectedModel, setSelectedModel]   = useState<AIModel | null>(null);
  const [parameters, setParameters]         = useState<Record<string, any>>({});
  const [parametersValid, setParametersValid] = useState(false);

  const handleUploadComplete = (images: UploadedMedicalImage[]) => {
    setUploadedImages(images);
    setSelectedImage(images[0]);
    setCompletedSteps((prev) => new Set(prev).add('upload'));
    toast.success(t('upload.uploadComplete'));
    setCurrentStep('select');
  };

  const dispatchAnalysis = async (model: AIModel, params: Record<string, any>) => {
    if (!selectedImage) return;
    try {
      const task = await apiClient.createAnalysisTask({
        model_key: model.key,
        input_image_id: selectedImage.id,
        parameters: params,
      });
      if (task.warning) toast(task.warning, { icon: '⚠️', duration: 6000 });
      toast.success(t('analysisSubmitted'), { duration: 5000 });
      setCurrentStep('upload');
      setUploadedImages([]);
      setSelectedImage(null);
      setSelectedModel(null);
      setParameters({});
      setParametersValid(false);
      setCompletedSteps(new Set());
    } catch (error: any) {
      toast.error(error.detail || error.message || 'Failed to create analysis task');
    }
  };

  const handleModelSelect = (model: AIModel, isRecommended: boolean = false) => {
    setSelectedModel(model);
    setCompletedSteps((prev) => new Set(prev).add('select'));

    const hasRequiredParams = Object.keys(model.required_parameters ?? {}).length > 0;

    if (isRecommended && !hasRequiredParams) {
      const defaultParams = model.default_parameters ?? {};
      setParameters(defaultParams);
      dispatchAnalysis(model, defaultParams);
    } else {
      setCurrentStep('configure');
      toast.success(`Selected ${model.name}`);
    }
  };

  const handleParametersChange = (params: Record<string, any>, isValid: boolean) => {
    setParameters(params);
    setParametersValid(isValid);
  };

  const handleStartAnalysis = async () => {
    if (!selectedImage || !selectedModel || !parametersValid) {
      toast.error('Please complete all required fields');
      return;
    }
    await dispatchAnalysis(selectedModel, parameters);
  };

  return (
    <div>
      <StepIndicator steps={WORKFLOW_STEPS} currentStep={currentStep} completedSteps={completedSteps} />

      <div className="space-y-6">
        {/* Step 1: Upload */}
        {currentStep === 'upload' && (
          <div className="space-y-6">
            <DragDropUploadZone onUploadComplete={handleUploadComplete} />

            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-slate-200 dark:border-slate-700" />
              </div>
              <div className="relative flex justify-center">
                <span className="px-3 bg-white dark:bg-slate-900 text-sm text-slate-500 dark:text-slate-400">
                  or use the standard uploader
                </span>
              </div>
            </div>

            <MedicalImageUploader onUploadComplete={handleUploadComplete} />

            {uploadedImages.length > 0 && (
              <>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <div>
                    <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">
                      {t('uploadedImages', { count: uploadedImages.length })}
                    </h3>
                    <div className="space-y-2">
                      {uploadedImages.map((image) => (
                        <button
                          key={image.id}
                          onClick={() => setSelectedImage(image)}
                          className={`w-full p-3 text-left rounded-lg border transition-colors ${
                            selectedImage?.id === image.id
                              ? 'border-medical-500 bg-medical-50 dark:bg-medical-900/20'
                              : 'border-slate-200 dark:border-slate-700 hover:border-medical-300 dark:hover:border-medical-600'
                          }`}
                        >
                          <p className="text-sm font-medium text-slate-900 dark:text-slate-100 truncate">
                            {image.filename}
                          </p>
                          <p className="text-xs text-slate-500 dark:text-slate-400">
                            {image.format.toUpperCase()} · {(image.size_bytes / 1024 / 1024).toFixed(2)} MB
                          </p>
                        </button>
                      ))}
                    </div>
                  </div>
                  {selectedImage && (
                    <MetadataViewer metadata={selectedImage.metadata} filename={selectedImage.filename} />
                  )}
                </div>
              </>
            )}
          </div>
        )}

        {/* Step 2: Select Model */}
        {currentStep === 'select' && selectedImage && (
          <div className="space-y-6">
            <Button variant="ghost" onClick={() => setCurrentStep('upload')}>{t('backToUpload')}</Button>
            <ModelRecommendation imageId={selectedImage.id} onModelSelect={handleModelSelect} />
          </div>
        )}

        {/* Step 3: Configure */}
        {currentStep === 'configure' && selectedModel && (
          <div className="space-y-6">
            <Button variant="ghost" onClick={() => setCurrentStep('select')}>{t('backToModel')}</Button>
            <div className="p-4 bg-medical-50 dark:bg-medical-900/20 border border-medical-200 dark:border-medical-800 rounded-lg">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-semibold text-medical-900 dark:text-medical-100">{t('selectedModel')}</p>
                  <p className="text-lg font-bold text-medical-700 dark:text-medical-300">
                    {selectedModel.name} v{selectedModel.version}
                  </p>
                </div>
                <Button variant="outline" size="sm" onClick={() => setCurrentStep('select')}>
                  {t('changeModel')}
                </Button>
              </div>
            </div>
            {selectedModel.requires_anonymization && (
              <div className="flex items-start gap-3 p-3 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 text-sm text-amber-800 dark:text-amber-300">
                <span className="text-amber-500 mt-0.5">⚠</span>
                <span>
                  This model requires the study to be anonymized first.
                  Run the <strong>Anonymizer</strong> tool with the <strong>Full</strong> or <strong>Research</strong> profile before submitting.
                </span>
              </div>
            )}
            <ParameterConfigurator
              model={selectedModel}
              onParametersChange={handleParametersChange}
              onSubmit={handleStartAnalysis}
            />
          </div>
        )}

      </div>
    </div>
  );
};

// ─── ReportsTab ───────────────────────────────────────────────────────────────

const ReportsTab: React.FC = () => {
  const { t } = useTranslation('reports');
  const [reports, setReports]     = useState<Report[]>([]);
  const [loading, setLoading]     = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [showModal, setShowModal]   = useState(false);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [compareMode, setCompareMode] = useState(false);
  const [compareA, setCompareA] = useState<string | null>(null);
  const [compareB, setCompareB] = useState<string | null>(null);

  const fetchReports = useCallback(async () => {
    try {
      setLoading(true);
      setReports(await apiClient.getReports());
    } catch {
      toast.error(t('common:errors.loadFailed'));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => { fetchReports(); }, [fetchReports]);

  const handleDownloadPdf = async (reportId: string) => {
    try {
      setDownloading(reportId);
      await apiClient.downloadReportPdf(reportId);
    } catch {
      toast.error(t('downloadError'));
    } finally {
      setDownloading(null);
    }
  };

  const handleReportCreated = () => {
    setShowModal(false);
    fetchReports();
    toast.success(t('generateSuccess'));
  };

  return (
    <div>
      {/* Header actions */}
      <div className="flex justify-end gap-3 mb-6">
        <button
          onClick={fetchReports}
          className="flex items-center gap-2 px-4 py-2 rounded-lg border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          {t('refresh')}
        </button>
        <button
          onClick={() => { setCompareMode(!compareMode); setCompareA(null); setCompareB(null); }}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-colors ${
            compareMode
              ? 'border-medical-500 text-medical-600 bg-medical-50 dark:bg-medical-950/20'
              : 'border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
          }`}
        >
          <GitCompare className="w-4 h-4" />
          {t('compare')}
        </button>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-medical-600 text-white hover:bg-medical-700 transition-colors"
        >
          <Plus className="w-4 h-4" />
          {t('generate')}
        </button>
      </div>

      {/* Comparison Mode */}
      {compareMode && (
        <div className="mb-6">
          <ComparisonSelector
            reports={reports}
            reportA={compareA}
            reportB={compareB}
            onSelectA={setCompareA}
            onSelectB={setCompareB}
          />
          {compareA && compareB && (
            <ReportComparison
              reportA={reports.find((r) => r.id === compareA)!}
              reportB={reports.find((r) => r.id === compareB)!}
            />
          )}
        </div>
      )}

      {/* Report List */}
      {loading ? (
        <div className="flex justify-center py-16">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-medical-600" />
        </div>
      ) : reports.length === 0 ? (
        <div className="medical-card p-12 text-center">
          <FileText className="w-12 h-12 text-slate-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">{t('noReports')}</h3>
          <p className="text-slate-600 dark:text-slate-400 mb-4">{t('noReportsHint')}</p>
          <button
            onClick={() => setShowModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-medical-600 text-white hover:bg-medical-700 transition-colors"
          >
            <Plus className="w-4 h-4" />
            {t('generate')}
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {reports.map((report) => (
            <div key={report.id} className="medical-card overflow-hidden">
              <div className="flex items-center justify-between p-4">
                <div className="flex items-center gap-4 flex-1 min-w-0">
                  <FileText className="w-5 h-5 text-medical-600 dark:text-medical-400 flex-shrink-0" />
                  <div className="min-w-0">
                    <h3 className="font-medium text-slate-900 dark:text-slate-100 truncate">{report.title}</h3>
                    <p className="text-sm text-slate-500 dark:text-slate-400">
                      {report.model_name} · {new Date(report.created_at).toLocaleDateString()}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`px-2 py-1 rounded text-xs font-medium ${
                    report.status === 'FINAL'
                      ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                      : 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200'
                  }`}>
                    {report.status}
                  </span>
                  <button
                    onClick={() => handleDownloadPdf(report.id)}
                    disabled={downloading === report.id}
                    className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors disabled:opacity-50"
                  >
                    <Download className="w-3.5 h-3.5" />
                    {t('downloadPdf')}
                  </button>
                  <button
                    onClick={() => setExpandedId(expandedId === report.id ? null : report.id)}
                    className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                  >
                    {expandedId === report.id
                      ? <ChevronUp className="w-4 h-4 text-slate-500" />
                      : <ChevronDown className="w-4 h-4 text-slate-500" />
                    }
                  </button>
                </div>
              </div>
              {expandedId === report.id && report.content && (
                <div className="border-t border-slate-200 dark:border-slate-700 p-4">
                  <ReportViewer content={report.content} />
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {showModal && (
        <GenerateReportModal onClose={() => setShowModal(false)} onCreated={handleReportCreated} />
      )}
    </div>
  );
};

// ─── ModelsTab ────────────────────────────────────────────────────────────────

const ModelsTab: React.FC = () => {
  const { t } = useTranslation('models');
  const [models, setModels]                 = useState<AIModel[]>([]);
  const [filteredModels, setFilteredModels] = useState<AIModel[]>([]);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState<string | null>(null);
  const [searchQuery, setSearchQuery]   = useState('');
  const [selectedType, setSelectedType] = useState('all');

  useEffect(() => {
    apiClient.getAIModels()
      .then((data) => { setModels(data); setFilteredModels(data); })
      .catch((err) => setError(err.detail || err.error || t('common:errors.loadFailed')))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    let filtered = models;
    if (selectedType !== 'all') {
      filtered = filtered.filter((m) => m.model_type === selectedType);
    }
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      filtered = filtered.filter((m) =>
        m.name.toLowerCase().includes(q) ||
        m.description.toLowerCase().includes(q) ||
        m.tags?.some((tag) => tag.toLowerCase().includes(q)) ||
        m.organization?.toLowerCase().includes(q)
      );
    }
    setFilteredModels(filtered);
  }, [models, searchQuery, selectedType]);

  const modelTypes = Array.from(new Set(models.map((m) => m.model_type)));

  if (loading) {
    return (
      <div className="flex justify-center py-16">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-medical-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="medical-card p-8 text-center">
        <p className="text-red-600 dark:text-red-400">{error}</p>
      </div>
    );
  }

  return (
    <div>
      {/* Search + Type filter */}
      <Card variant="medical" className="mb-6">
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Search */}
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                {t('search')}
              </label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                <input
                  type="text"
                  placeholder={t('searchPlaceholder')}
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className={`${INPUT_CLS} pl-9`}
                />
              </div>
            </div>
            {/* Type filter */}
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                {t('modelType')}
              </label>
              <select
                value={selectedType}
                onChange={(e) => setSelectedType(e.target.value)}
                className={INPUT_CLS}
              >
                <option value="all">{t('allTypes')}</option>
                {modelTypes.map((type) => (
                  <option key={type} value={type}>
                    {type.charAt(0).toUpperCase() + type.slice(1)}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-700">
            <p className="text-sm text-slate-600 dark:text-slate-400">
              {t('showing', { count: filteredModels.length, total: models.length })}
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Grid */}
      {filteredModels.length === 0 ? (
        <div className="medical-card p-12 text-center">
          <Brain className="w-12 h-12 text-slate-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">
            {t('noModels')}
          </h3>
          <p className="text-slate-600 dark:text-slate-400">{t('noModelsHint')}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
          {filteredModels.map((model) => (
            <ModelCard key={model.key} model={model} />
          ))}
        </div>
      )}

      {/* About section */}
      <Card variant="glass">
        <CardHeader>
          <CardTitle>{t('about.title')}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-slate-700 dark:text-slate-300 mb-4">{t('about.description')}</p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {(['validated', 'openSource', 'productionReady'] as const).map((key) => (
              <div key={key} className="flex items-start gap-2">
                <CheckCircle className="w-5 h-5 text-medical-500 flex-shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-semibold text-slate-900 dark:text-slate-100 mb-1">
                    {t(`about.${key}`)}
                  </h4>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

// ─── AnalyzePage (main export) ────────────────────────────────────────────────

export const AnalyzePage: React.FC = () => {
  const { t } = useTranslation('analyze');
  const [activeTab, setActiveTab] = useState<AnalyzePageTab>('worklist');

  const tabs: { key: AnalyzePageTab; label: string }[] = [
    { key: 'worklist', label: t('tabs.worklist') },
    { key: 'new',      label: t('tabs.newAnalysis') },
    { key: 'reports',  label: t('tabs.reports') },
    { key: 'models',   label: t('tabs.models') },
  ];

  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      {/* Page Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100 mb-2">
          {t('pageTitle')}
        </h1>
        <p className="text-slate-600 dark:text-slate-400">{t('pageSubtitle')}</p>
      </div>

      <AiDisclaimer className="mb-6" />

      {/* Tab Navigation */}
      <div className="mb-6 border-b border-slate-200 dark:border-slate-700">
        <nav className="flex gap-8">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`pb-4 px-2 font-medium transition-colors ${
                activeTab === tab.key
                  ? 'border-b-2 border-medical-500 text-medical-600 dark:text-medical-400'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'worklist' && <WorklistTab />}
      {activeTab === 'new'      && <NewAnalysisTab />}
      {activeTab === 'reports'  && <ReportsTab />}
      {activeTab === 'models'   && <ModelsTab />}
    </div>
  );
};

export default AnalyzePage;
