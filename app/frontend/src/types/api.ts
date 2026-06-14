/**
 * Shared TypeScript types for VetImage API responses and requests.
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
  // Veterinary link (Owner → AnimalPatient → Study)
  AnimalPatientID?: number | null;
  AnimalPatientName?: string | null;
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
// Veterinary patients (Owner → AnimalPatient → Study)
// ---------------------------------------------------------------------------

export type Species =
  | 'canine' | 'feline' | 'equine' | 'bovine' | 'avian' | 'exotic' | 'other';

export type AnimalSex = 'M' | 'F' | 'MN' | 'FS' | 'U' | '';

export interface OwnerSummary {
  id: number;
  first_name: string;
  last_name: string;
  email?: string;
  phone?: string;
}

export interface AnimalPatientListItem {
  id: number;
  name: string;
  species: Species;
  breed?: string;
  sex?: AnimalSex;
  owner_name: string;
  profile_photo?: string | null;
}

export interface AnimalPatientStudyRef {
  study_instance_uid: string;
  study_description?: string;
  study_date?: string | null;
}

export type VHSInterpretation = 'within_range' | 'above_range' | 'below_range' | 'unknown';

export interface VHSTrendPoint {
  id: number;
  measured_on: string;
  vhs: number;
  long_axis_vertebrae: number;
  short_axis_vertebrae: number;
  interpretation: VHSInterpretation;
  method: 'manual' | 'ai_assisted';
  notes?: string;
}

export interface VHSMeasurement {
  id: number;
  study_instance_uid?: string;
  sop_instance_uid?: string;
  measured_on: string;
  long_axis_vertebrae: string;
  short_axis_vertebrae: string;
  vhs: string;
  method: 'manual' | 'ai_assisted';
  landmark_points?: Record<string, unknown>;
  notes?: string;
  interpretation: VHSInterpretation;
  reference_range?: { low: number; high: number } | null;
  created_by_email?: string;
  created_at?: string;
  updated_at?: string;
}

export interface VHSMeasurementWrite {
  animal_patient_id: number;
  study_instance_uid?: string;
  sop_instance_uid?: string;
  measured_on: string;
  long_axis_vertebrae: number | string;
  short_axis_vertebrae: number | string;
  method?: 'manual' | 'ai_assisted';
  notes?: string;
}

export type VisitType =
  | 'consultation' | 'follow_up' | 'vaccination' | 'surgery' | 'imaging' | 'emergency';

export type AppointmentStatus =
  | 'pending' | 'confirmed' | 'completed' | 'cancelled' | 'no_show';

export interface WeightTrendPoint {
  id: number;
  measured_on: string;
  weight_kg: number;
  bcs?: number | null;
  notes?: string;
}

export interface VaccinationSummary {
  id: number;
  vaccine_name: string;
  administered_on: string;
  next_due_on?: string | null;
  batch_number?: string;
  notes?: string;
}

export interface AppointmentSummary {
  id: number;
  appointment_type: VisitType;
  scheduled_at: string;
  status: AppointmentStatus;
  duration_minutes: number;
}

export type ReproductiveEventType =
  | 'heat' | 'mating' | 'pregnancy_confirmed' | 'whelping'
  | 'litter_registration' | 'spay_neuter' | 'other';

export interface ReproductiveEvent {
  id: number;
  event_type: ReproductiveEventType;
  event_date: string;
  partner_id?: string;
  litter_count?: number | null;
  notes?: string;
  created_at?: string;
}

export interface ReproductiveEventWrite {
  animal_patient_id: number;
  event_type: ReproductiveEventType;
  event_date: string;
  partner_id?: string;
  litter_count?: number | null;
  notes?: string;
}

export interface AnimalPatient {
  id: number;
  owner: OwnerSummary;
  name: string;
  species: Species;
  breed?: string;
  date_of_birth?: string | null;
  sex?: AnimalSex;
  weight_kg?: string | null;
  microchip_id?: string;
  color?: string;
  profile_photo?: string | null;
  insurance_provider?: string;
  insurance_policy_number?: string;
  insurance_expiry?: string | null;
  visits_count?: number;
  studies?: AnimalPatientStudyRef[];
  vhs_trend?: VHSTrendPoint[];
  weight_trend?: WeightTrendPoint[];
  vaccinations?: VaccinationSummary[];
  upcoming_appointments?: AppointmentSummary[];
  created_at?: string;
  updated_at?: string;
}

export interface AnimalPatientWrite {
  owner_id: number;
  name: string;
  species: Species;
  breed?: string;
  date_of_birth?: string | null;
  sex?: AnimalSex;
  weight_kg?: string | null;
  microchip_id?: string;
  color?: string;
  insurance_provider?: string;
  insurance_policy_number?: string;
  insurance_expiry?: string | null;
}

export interface Owner {
  id: number;
  organization?: number;
  first_name: string;
  last_name: string;
  email?: string;
  phone?: string;
  address?: string;
  city?: string;
  country?: string;
  animals_count?: number;
  animals?: AnimalPatientListItem[];
  created_at?: string;
  updated_at?: string;
}

export interface OwnerWrite {
  first_name: string;
  last_name: string;
  email?: string;
  phone?: string;
  address?: string;
  city?: string;
  country?: string;
}

export interface ClinicalVisit {
  id: number;
  visit_date: string;
  visit_type: VisitType;
  attending_vet_email?: string;
  chief_complaint?: string;
  subjective?: string;
  objective?: string;
  assessment?: string;
  plan?: string;
  weight_kg?: string | null;
  temperature_celsius?: string | null;
  heart_rate_bpm?: number | null;
  respiratory_rate?: number | null;
  linked_study?: number | null;
  linked_report?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface ClinicalVisitWrite {
  animal_patient_id: number;
  visit_date: string;
  visit_type: VisitType;
  chief_complaint?: string;
  subjective?: string;
  objective?: string;
  assessment?: string;
  plan?: string;
  weight_kg?: string | null;
  temperature_celsius?: string | null;
  heart_rate_bpm?: number | null;
  respiratory_rate?: number | null;
  linked_study?: number | null;
  linked_report?: string | null;
}

export interface VaccinationRecord {
  id: number;
  vaccine_name: string;
  administered_on: string;
  next_due_on?: string | null;
  batch_number?: string;
  administered_by_email?: string;
  notes?: string;
  created_at?: string;
}

export interface VaccinationRecordWrite {
  animal_patient_id: number;
  vaccine_name: string;
  administered_on: string;
  next_due_on?: string | null;
  batch_number?: string;
  notes?: string;
}

export interface WeightRecord {
  id: number;
  measured_on: string;
  weight_kg: string;
  bcs?: number | null;
  notes?: string;
  created_at?: string;
}

export interface WeightRecordWrite {
  animal_patient_id: number;
  measured_on: string;
  weight_kg: string;
  bcs?: number | null;
  notes?: string;
}

export interface Appointment {
  id: number;
  animal_name: string;
  owner_name: string;
  appointment_type: VisitType;
  scheduled_at: string;
  duration_minutes: number;
  status: AppointmentStatus;
  notes?: string;
  linked_visit?: number | null;
  created_at?: string;
}

export interface AppointmentWrite {
  animal_patient_id: number;
  appointment_type: VisitType;
  scheduled_at: string;
  duration_minutes?: number;
  attending_vet?: number | null;
  notes?: string;
}

// ---------------------------------------------------------------------------
// P2: Prescription, AllergyRecord, LabResult, ClinicalPhoto, StudyShareLink
// ---------------------------------------------------------------------------

export type AllergenType = 'drug' | 'food' | 'environmental' | 'contact';
export type AllergySeverity = 'mild' | 'moderate' | 'severe' | 'life_threatening';
export type LabResultType =
  | 'hematology' | 'biochemistry' | 'urinalysis' | 'cytology'
  | 'serology' | 'microbiology' | 'other';

export interface Prescription {
  id: number;
  visit?: number | null;
  prescribed_on: string;
  medication_name: string;
  dose?: string;
  route?: string;
  frequency?: string;
  duration_days?: number | null;
  refills_remaining?: number;
  notes?: string;
  prescribed_by_email?: string;
  created_at?: string;
}

export interface PrescriptionWrite {
  animal_patient_id: number;
  visit?: number | null;
  prescribed_on: string;
  medication_name: string;
  dose?: string;
  route?: string;
  frequency?: string;
  duration_days?: number | null;
  notes?: string;
}

export interface AllergyRecord {
  id: number;
  allergen: string;
  allergen_type: AllergenType;
  reaction?: string;
  severity: AllergySeverity;
  first_observed?: string | null;
  is_high_severity: boolean;
  created_at?: string;
}

export interface AllergyRecordWrite {
  animal_patient_id: number;
  allergen: string;
  allergen_type: AllergenType;
  reaction?: string;
  severity: AllergySeverity;
  first_observed?: string | null;
}

export interface LabAnalyte {
  value: number;
  unit: string;
  ref_low?: number | null;
  ref_high?: number | null;
  flag?: 'N' | 'H' | 'L' | 'CRITICAL' | string;
}

export interface LabResult {
  id: number;
  visit?: number | null;
  result_type: LabResultType;
  panel_name: string;
  result_date: string;
  result_data: Record<string, LabAnalyte>;
  lab_name?: string;
  pdf_url?: string | null;
  created_at?: string;
}

export interface LabResultWrite {
  animal_patient_id: number;
  visit?: number | null;
  result_type: LabResultType;
  panel_name: string;
  result_date: string;
  result_data: Record<string, LabAnalyte>;
  lab_name?: string;
}

export interface ClinicalPhoto {
  id: number;
  visit?: number | null;
  photo_url?: string | null;
  caption?: string;
  body_region?: string;
  taken_on: string;
  created_at?: string;
}

export interface StudyShareLink {
  id: number;
  study: number;
  study_instance_uid?: string;
  recipient_email?: string;
  token: string;
  expires_at?: string | null;
  access_count: number;
  max_accesses?: number | null;
  is_valid: boolean;
  share_url?: string;
  created_at?: string;
}

export interface StudyShareLinkWrite {
  study_uid: string;
  recipient_email?: string;
  expires_at?: string | null;
  max_accesses?: number | null;
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
  supported_species?: string[];

  // Performance
  performance_metrics?: Record<string, number | string>;
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
  metadata?: Record<string, unknown>;

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
  priority?: TaskPriority;
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

export type TaskPriority = 'routine' | 'urgent' | 'stat';

/** A single AI decision-support finding (from result_metadata.findings). */
export interface Finding {
  label?: string;
  region?: string;
  confidence?: number;
  description?: string;
  /** Normalized [x, y, w, h] in [0,1] image coordinates, when the model provides it. */
  bbox?: [number, number, number, number] | null;
  task_id?: string;
  model?: string | null;
}

export interface CreateTaskRequest {
  model_key: string;
  input_image_id: number;
  parameters: Record<string, any>;
  priority?: TaskPriority;
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
  is_approved?: boolean;
  approved_by_email?: string;
  approved_at?: string | null;
  is_shared?: boolean;
  created_at: string;
  updated_at?: string;
}

export interface AuditLogEntry {
  id: number;
  user_email?: string | null;
  username_attempted?: string;
  event_type: string;
  event_type_display: string;
  event_timestamp: string;
  ip_address: string;
  user_agent?: string;
  request_path?: string;
  request_method?: string;
  is_suspicious: boolean;
  risk_score?: number;
}

export interface PublicSharedReport {
  title: string;
  patient_info: Record<string, string>;
  findings: string[];
  summary: string;
  disclaimer: string;
  approved_at: string | null;
  clinic: string | null;
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
// Referral network (#24)
// ---------------------------------------------------------------------------

export type ReferralUrgency = 'routine' | 'urgent' | 'emergency';

export interface ReferringClinic {
  id: number;
  name: string;
  contact_name?: string;
  contact_email?: string;
  contact_phone?: string;
  address?: string;
  notes?: string;
  created_at?: string;
}

export interface ReferringClinicWrite {
  name: string;
  contact_name?: string;
  contact_email?: string;
  contact_phone?: string;
  address?: string;
  notes?: string;
}

export interface ReferralPackage {
  id: number;
  animal_name: string;
  referring_clinic?: number | null;
  referring_clinic_name?: string | null;
  study_instance_uid?: string | null;
  report?: number | null;
  report_title?: string | null;
  reason?: string;
  history_summary?: string;
  urgency: ReferralUrgency;
  token: string;
  recipient_email?: string;
  expires_at?: string | null;
  access_count: number;
  share_path: string;
  is_valid: boolean;
  created_at?: string;
}

export interface ReferralPackageWrite {
  animal_patient_id: number;
  referring_clinic?: number | null;
  study_uid?: string;
  report?: number | null;
  reason?: string;
  history_summary?: string;
  urgency?: ReferralUrgency;
  recipient_email?: string;
  expires_at?: string | null;
}

// ---------------------------------------------------------------------------
// Owner ↔ clinic messaging (#22)
// ---------------------------------------------------------------------------

export interface Message {
  id: number;
  sender_email?: string;
  from_owner: boolean;
  body: string;
  is_read: boolean;
  created_at: string;
}

// ---------------------------------------------------------------------------
// Pet-owner portal (#21)
// ---------------------------------------------------------------------------

export interface PortalPet {
  id: number;
  name: string;
  species: string;
  breed: string;
  sex: string;
  date_of_birth: string | null;
  profile_photo: string | null;
  clinic: string | null;
  vaccinations: Array<{
    vaccine_name: string;
    administered_on: string;
    next_due_on: string | null;
    overdue: boolean;
  }>;
  upcoming_appointments: Array<{
    appointment_type: string;
    scheduled_at: string;
    status: string;
  }>;
}

export interface PortalSharedReport {
  title: string;
  pet_name: string;
  approved_at: string | null;
  share_path: string;
}

export interface PortalDashboard {
  owner: { email: string; pet_count: number };
  pets: PortalPet[];
  shared_reports: PortalSharedReport[];
}

export interface PublicReferralPackage {
  patient: {
    name: string;
    species: string;
    breed: string;
    sex: string;
    date_of_birth: string | null;
    microchip_id: string;
  };
  referring_clinic_name: string | null;
  reason: string;
  history_summary: string;
  urgency: ReferralUrgency;
  study_instance_uid: string | null;
  report: { title: string; findings: string[]; summary: string } | null;
  disclaimer: string;
  created_at: string;
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
