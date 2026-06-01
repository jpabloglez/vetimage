/**
 * Shared TypeScript types for OpenMedLab API responses and requests.
 *
 * All types are re-exported from utils/api.ts for backward compatibility.
 * New code should import directly from this file:
 *
 *   import type { Study, AnalysisTask } from '../types/api';
 */

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  email: string;
  password: string;
  password_confirm: string;
  role?: number;
}

export interface User {
  id: number;
  email: string;
  role: number;
  language?: string;
  image_url?: string;
  created_at: string;
  updated_at: string;
}

export interface AuthResponse {
  access: string;
  user: User;
}

// ---------------------------------------------------------------------------
// Pagination
// ---------------------------------------------------------------------------

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

// ---------------------------------------------------------------------------
// DICOM metadata
// ---------------------------------------------------------------------------

export interface Study {
  id?: number;
  StudyInstanceUID: string;
  StudyDate: string;
  StudyTime?: string;
  PatientID: string;
  PatientName: string;
  PatientBirthDate?: string;
  PatientSex?: string;
  StudyDescription?: string;
  AccessionNumber?: string;
  Modality?: string;
  NumberOfStudyRelatedSeries?: number;
  NumberOfStudyRelatedInstances?: number;
}

export interface Series {
  SeriesInstanceUID: string;
  SeriesNumber: number;
  SeriesDescription?: string;
  Modality: string;
  NumberOfSeriesRelatedInstances: number;
}

export interface Instance {
  SOPInstanceUID: string;
  SOPClassUID: string;
  InstanceNumber: number;
}

export interface UploadResponse {
  success: boolean;
  message: string;
  studyUID?: string;
  seriesUID?: string;
  instanceUID?: string;
  uploaded_count?: number;
}

export interface StorageInfo {
  used: number;
  quota: number;
  remaining: number;
  percentage: number;
}

// ---------------------------------------------------------------------------
// AI Models & Analysis
// ---------------------------------------------------------------------------

export interface AIModel {
  key: string;
  name: string;
  description: string;
  version: string;
  model_type: string;
  supported_modalities: string[];
  required_parameters: Record<string, any>;
  default_parameters: Record<string, any>;
  timeout_seconds: number;
  is_active: boolean;

  // Authors & Attribution
  authors?: Array<{
    name: string;
    affiliation?: string;
    email?: string;
  }>;
  organization?: string;

  // Publications
  publication_title?: string;
  publication_journal?: string;
  publication_year?: number;
  publication_doi?: string;
  publication_url?: string;
  citation?: string;

  // Resources
  github_url?: string;
  paper_url?: string;
  demo_url?: string;
  model_card_url?: string;

  // Licensing
  license_name?: string;
  license_url?: string;

  // Characteristics
  tags?: string[];
  medical_domains?: string[];
  anatomical_regions?: string[];

  // Performance
  performance_metrics?: Record<string, number>;
  validation_dataset?: string;
  training_dataset?: string;

  // Use Cases
  use_cases?: string[];
  limitations?: string;
  example_images?: string[];

  // Community
  documentation_url?: string;
  support_url?: string;
  homepage_url?: string;

  // Statistics
  download_count?: number;
  rating?: number;

  // Data Governance
  requires_anonymization?: boolean;

  // Timestamps
  created_at?: string;
  updated_at?: string;
}

export type TaskStatus =
  | 'PENDING'
  | 'QUEUED'
  | 'DISPATCHED'
  | 'PROCESSING'
  | 'COMPLETED'
  | 'FAILED'
  | 'TIMEOUT'
  | 'CANCELLED';

export interface AnalysisTask {
  id: string;
  model: {
    key: string;
    name: string;
    model_type: string;
    version: string;
    is_active: boolean;
  };
  input_image: any;
  status: TaskStatus;
  parameters: Record<string, any>;
  created_at: string;
  dispatched_at?: string;
  started_processing_at?: string;
  completed_at?: string;
  processing_duration?: number;
  total_duration?: number;
  result_file_path?: string;
  result_metadata?: Record<string, any>;
  error_message?: string;
  retry_count: number;
  warning?: string;
}

export interface CreateTaskRequest {
  model_key: string;
  input_image_id: number;
  parameters: Record<string, any>;
}

export interface ScoredModel {
  model: AIModel;
  compatibility_score: number;
  match_reasons: string[];
  warnings: string[];
}

export interface ModelRecommendationResponse {
  recommended_models: ScoredModel[];
}

// ---------------------------------------------------------------------------
// Medical image upload
// ---------------------------------------------------------------------------

export interface UploadedMedicalImage {
  id: number;
  filename: string;
  format: 'dicom' | 'nifti' | 'image';
  size_bytes: number;
  metadata: Record<string, any>;
  study_id: number;
  series_id: number;
}

export interface MedicalImageUploadResponse {
  uploaded_images: UploadedMedicalImage[];
  total_count: number;
  total_size_bytes: number;
  quota_used_bytes: number;
  quota_total_bytes: number;
}

// ---------------------------------------------------------------------------
// Monitor
// ---------------------------------------------------------------------------

export interface MonitorTasksParams {
  date_from?: string;
  date_to?: string;
  status?: string;
  scope?: 'own' | 'colleagues' | 'department' | 'team';
  model_key?: string;
  page?: number;
  page_size?: number;
}

export interface MonitorTask {
  id: string;
  model_key: string;
  model_name: string;
  status: string;
  created_at: string;
  completed_at?: string;
  processing_duration?: number;
  created_by_name: string;
  created_by_department?: string;
  parameters: Record<string, any>;
  error_message?: string;
  result_file_path?: string;
  result_metadata?: Record<string, any>;
}

export interface PaginatedMonitorTasks {
  count: number;
  next: string | null;
  previous: string | null;
  results: MonitorTask[];
}

export interface TaskStats {
  total_jobs: number;
  by_status: Record<string, number>;
  by_model: Record<string, number>;
  avg_processing_time_seconds: number | null;
  success_rate: number;
}

// ---------------------------------------------------------------------------
// DICOM Transfer Monitoring
// ---------------------------------------------------------------------------

export interface DicomTransferFilters {
  date_from?: string;
  date_to?: string;
  status?: 'success' | 'partial' | 'failed' | 'in_progress';
  source_pacs?: string;
  modality?: string;
  scope?: 'own' | 'colleagues' | 'department' | 'team';
  page?: number;
  page_size?: number;
}

export interface DicomTransfer {
  study_instance_uid: string;
  patient_id_hash: string;
  study_date: string | null;
  study_description: string;

  source_pacs_name: string;
  source_ae: string;
  source_ip: string;

  total_instances: number;
  successful_instances: number;
  failed_instances: number;
  pending_instances: number;
  transfer_status: 'success' | 'partial' | 'in_progress' | 'failed';

  first_transfer_at: string;
  last_transfer_at: string | null;
  total_duration_ms: number | null;

  total_size_bytes: number;
  modality: string;

  uploaded_by_name: string;
  uploaded_by_department: string | null;
}

export interface PaginatedDicomTransfers {
  count: number;
  next: string | null;
  previous: string | null;
  results: DicomTransfer[];
}

export interface TransferStats {
  total_transfers: number;
  total_instances_received: number;
  successful_transfers: number;
  failed_transfers: number;
  partial_transfers: number;
  in_progress_transfers: number;
  success_rate: number;
  avg_transfer_time_seconds: number | null;
  total_data_received_bytes: number;
  by_modality: Record<string, number>;
  by_source_pacs: Record<string, number>;
  by_status: Record<string, number>;
}

// ---------------------------------------------------------------------------
// User / Profile
// ---------------------------------------------------------------------------

export interface ProfileCompletionData {
  department: string;
  job_title: string;
  team_name?: string;
  is_sharing_jobs_with_colleagues: boolean;
  language?: string;
}

export interface ColleagueProfile {
  id: number;
  first_name: string;
  last_name: string;
  department: string;
  job_title: string;
  team_name: string;
}

// ---------------------------------------------------------------------------
// Statistics
// ---------------------------------------------------------------------------

export interface StatisticsFilters {
  date_from?: string | null;
  date_to?: string | null;
  model_keys?: string[];
  statuses?: string[];
  patient_ids?: string[];
  patient_sex?: string[];
  patient_age_min?: number | null;
  patient_age_max?: number | null;
  modalities?: string[];
  body_parts?: string[];
  page?: number;
  page_size?: number;
}

export interface StatisticsTask {
  id: string;
  model_name: string;
  model_key: string;
  model_type: string;
  status: string;
  created_at: string;
  completed_at?: string;
  processing_duration?: number;
  /** Patient ID only — no patient_name for privacy */
  patient_id: string;
  patient_sex?: string;
  patient_age?: number;
  study_date?: string;
  study_description?: string;
  modality?: string;
  body_part?: string;
  organization_name?: string;
  ai_metrics?: Record<string, any>;
}

export interface PaginatedStatisticsData {
  count: number;
  next: string | null;
  previous: string | null;
  results: StatisticsTask[];
}

export interface StatisticsAggregated {
  time_series: Array<{ date: string; count: number }>;
  processing_time_distribution: number[];
  model_usage: Array<{ model_name: string; model_key: string; count: number }>;
  status_breakdown: Record<string, number>;
  total_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
  average_processing_time?: number;
}

export interface StatisticsFilterOptions {
  models: Array<{ key: string; name: string; type: string }>;
  modalities: string[];
  body_parts: string[];
  patient_sex: string[];
  statuses: string[];
}

export interface StudyAnalytics {
  modality_distribution: Array<{ modality: string; count: number }>;
  upload_trends: Array<{ date: string; count: number }>;
  storage_usage: Array<{ date: string; cumulative_bytes: number; period_bytes: number }>;
  total_studies: number;
  total_storage_bytes: number;
}

export interface ModelMetric {
  model__key: string;
  model__name: string;
  total: number;
  completed: number;
  failed: number;
  timeout: number;
  avg_processing_time: number | null;
  failure_rate: number;
}

export interface ModelTrend {
  date: string;
  model_key: string;
  model_name: string;
  total: number;
  completed: number;
  failed: number;
  success_rate: number;
}

export interface UserActivity {
  user_id: number;
  email: string;
  upload_count: number;
  analysis_count: number;
  completed_analyses: number;
  failed_analyses: number;
  total_storage_bytes: number;
  last_upload_at: string | null;
  last_analysis_at: string | null;
  last_active_at: string | null;
}

export interface PopulationInsights {
  age_histogram: Array<{ bracket: string; count: number }>;
  gender_distribution: Array<{ patient_sex: string; count: number }>;
  top_findings: Array<{ finding: string; count: number }>;
  total_patients: number;
}

// ---------------------------------------------------------------------------
// Notifications
// ---------------------------------------------------------------------------

export interface Notification {
  id: number;
  message: string;
  notification_type: 'info' | 'success' | 'warning' | 'error';
  is_read: boolean;
  created_at: string;
  link?: string;
}

// ---------------------------------------------------------------------------
// Reports
// ---------------------------------------------------------------------------

export interface Report {
  id: string;
  title: string;
  content: Record<string, any>;
  status: 'DRAFT' | 'FINAL';
  analysis_task_id?: string;
  study_uid?: string;
  model_name?: string;
  created_at: string;
  updated_at?: string;
}

export interface ReportTemplate {
  id: string;
  name: string;
  template_type: string;
  layout: Record<string, any>;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

// ---------------------------------------------------------------------------
// Tools — Anonymization
// ---------------------------------------------------------------------------

export type AnonymizationProfile = 'basic' | 'full' | 'research';
export type AnonymizationOutputFormat = 'dicom_zip' | 'nifti_bids' | 'png_bids';

export interface AnonymizationJob {
  id: string;
  study: number | null;
  image_ids: number[];
  profile: AnonymizationProfile;
  output_format: AnonymizationOutputFormat;
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
  result_file_path: string;
  error_message: string;
  created_at: string;
  updated_at: string;
}

export interface CreateAnonymizationJobRequest {
  study_id?: number;
  image_ids?: number[];
  profile: AnonymizationProfile;
  output_format?: AnonymizationOutputFormat;
}

// ---------------------------------------------------------------------------
// Tools — DICOM Tag Editor
// ---------------------------------------------------------------------------

export interface DicomTag {
  vr: string;
  name: string;
  value: string | string[] | null;
}

export interface TagUpdate {
  tag: string;
  value: string;
}

// ---------------------------------------------------------------------------
// Tools — Format Conversion
// ---------------------------------------------------------------------------

export type ConversionTargetFormat = 'jpeg' | 'png' | 'nifti';

export interface ConversionJob {
  id: string;
  study: number | null;
  series_ids: number[];
  target_format: ConversionTargetFormat;
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
  result_file_path: string;
  error_message: string;
  created_at: string;
  updated_at: string;
}

export interface CreateConversionJobRequest {
  study_id?: number;
  series_ids?: number[];
  target_format: string;
}

// ---------------------------------------------------------------------------
// Tools — Batch Operations
// ---------------------------------------------------------------------------

export type BatchOperation = 'export' | 'delete' | 'analyze';

export interface BatchJob {
  id: string;
  operation: BatchOperation;
  study_ids: number[];
  model_key: string;
  parameters: Record<string, any>;
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
  result_file_path: string;
  result_summary: Record<string, any>;
  error_message: string;
  created_at: string;
  updated_at: string;
}

export interface CreateBatchJobRequest {
  study_ids: number[];
  operation: BatchOperation;
  model_key?: string;
  parameters?: Record<string, any>;
}

// ---------------------------------------------------------------------------
// Audit
// ---------------------------------------------------------------------------

export interface AuditReportFilters {
  date_from?: string;
  date_to?: string;
  user_id?: number;
  event_type?: string;
  risk_score_min?: number;
}

// ---------------------------------------------------------------------------
// Frontend config & errors
// ---------------------------------------------------------------------------

export interface FrontendConfig {
  websocket_based_tracking: boolean;
  monitor_poll_interval: number;
  stats_poll_interval: number;
  websocket_url: string | null;
}

export interface ApiError {
  error: string;
  detail?: string;
  details?: Record<string, any>;
  status: number;
}
