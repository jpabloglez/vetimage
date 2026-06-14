/**
 * Centralized API Client for MedAI Platform with JWT Authentication
 *
 * This module provides typed API methods for interacting with the backend,
 * including authentication, DICOM operations, and file uploads.
 *
 * Features:
 * - JWT authentication with access + refresh tokens
 * - Automatic token refresh on expiration
 * - Access token stored in memory (not localStorage for security)
 * - Refresh token stored in HttpOnly secure cookies
 */

// API Base URL from environment or default
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:3081';

// Import all types for use within the ApiClient class below
import type {
  LoginCredentials,
  RegisterData,
  User,
  AuthResponse,
  PaginatedResponse,
  Study,
  Series,
  Instance,
  UploadResponse,
  StorageInfo,
  Owner,
  OwnerWrite,
  AnimalPatient,
  AnimalPatientListItem,
  AnimalPatientWrite,
  VHSMeasurement,
  VHSMeasurementWrite,
  ClinicalVisit,
  ClinicalVisitWrite,
  VaccinationRecord,
  VaccinationRecordWrite,
  WeightRecord,
  WeightRecordWrite,
  Appointment,
  AppointmentWrite,
  AppointmentStatus,
  Prescription,
  PrescriptionWrite,
  AllergyRecord,
  AllergyRecordWrite,
  LabResult,
  LabResultWrite,
  ClinicalPhoto,
  ReproductiveEvent,
  ReproductiveEventWrite,
  ReferringClinic,
  ReferringClinicWrite,
  ReferralPackage,
  ReferralPackageWrite,
  PublicReferralPackage,
  PortalDashboard,
  Message,
  StudyShareLink,
  StudyShareLinkWrite,
  Species,
  AIModel,
  TaskStatus,
  AnalysisTask,
  CreateTaskRequest,
  ScoredModel,
  ModelRecommendationResponse,
  UploadedMedicalImage,
  MedicalImageUploadResponse,
  MonitorTasksParams,
  MonitorTask,
  PaginatedMonitorTasks,
  TaskStats,
  DicomTransferFilters,
  DicomTransfer,
  PaginatedDicomTransfers,
  TransferStats,
  ProfileCompletionData,
  ColleagueProfile,
  StatisticsFilters,
  StatisticsTask,
  PaginatedStatisticsData,
  StatisticsAggregated,
  StatisticsFilterOptions,
  StudyAnalytics,
  ModelMetric,
  ModelTrend,
  UserActivity,
  PopulationInsights,
  Notification,
  Report,
  PublicSharedReport,
  AuditLogEntry,
  ReportTemplate,
  AnonymizationProfile,
  AnonymizationOutputFormat,
  AnonymizationJob,
  CreateAnonymizationJobRequest,
  DicomTag,
  TagUpdate,
  ConversionTargetFormat,
  ConversionJob,
  CreateConversionJobRequest,
  BatchOperation,
  BatchJob,
  CreateBatchJobRequest,
  AuditReportFilters,
  FrontendConfig,
  ApiError,
} from '../types/api';

// Re-export all shared types — backward-compatible for existing imports.
// Uses `export *` (not `export type *`) so that re-exported names shadow
// browser globals (e.g. Notification, Report) in importing files, matching
// the previous behaviour of inline `export interface` declarations.
export * from '../types/api';

/**
 * API Client Class with JWT Authentication
 */
class ApiClient {
  private baseUrl: string;
  private accessToken: string | null = null;
  private tokenRefreshPromise: Promise<string> | null = null;
  private proactiveRefreshTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  /**
   * Set access token (called by AuthContext after login/refresh, and internally
   * after every token update). Also (re)schedules a proactive refresh so the
   * token is renewed shortly before it expires instead of only reacting to 401s.
   */
  setAccessToken(token: string | null) {
    this.accessToken = token;
    this.scheduleProactiveRefresh();
  }

  /**
   * Get current access token
   */
  getAccessToken(): string | null {
    return this.accessToken;
  }

  /** Decode a JWT payload's `exp` (seconds) without a dependency. */
  private decodeExp(token: string): number | null {
    try {
      const payload = token.split('.')[1];
      const json = JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/')));
      return typeof json.exp === 'number' ? json.exp : null;
    } catch {
      return null;
    }
  }

  /**
   * Schedule a refresh ~60s before the current access token expires. The
   * reactive 401 path remains as a fallback. No-op outside the browser (tests).
   */
  private scheduleProactiveRefresh() {
    if (this.proactiveRefreshTimer) {
      clearTimeout(this.proactiveRefreshTimer);
      this.proactiveRefreshTimer = null;
    }
    if (!this.accessToken || typeof window === 'undefined') return;
    const exp = this.decodeExp(this.accessToken);
    if (!exp) return;
    const msUntilRefresh = exp * 1000 - Date.now() - 60_000; // 60s lead time
    const delay = Math.max(msUntilRefresh, 5_000); // never busy-loop
    this.proactiveRefreshTimer = setTimeout(() => {
      this.refreshToken().catch(() => {
        window.dispatchEvent(new CustomEvent('auth:token-expired'));
      });
    }, delay);
  }

  /**
   * Make authenticated request with automatic token refresh
   */
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;

    // Add access token to headers if available
    // Skip Content-Type for FormData so the browser sets multipart boundary automatically
    const headers: HeadersInit = {
      ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      ...options.headers,
    };

    if (this.accessToken) {
      headers['Authorization'] = `Bearer ${this.accessToken}`;
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers,
        credentials: 'include', // Include cookies for refresh token
      });

      // Handle 401 Unauthorized - attempt token refresh
      if (response.status === 401 && this.accessToken) {
        console.log('Access token expired, attempting refresh...');

        try {
          const newAccessToken = await this.refreshAccessToken();

          // Retry original request with new token
          headers['Authorization'] = `Bearer ${newAccessToken}`;
          const retryResponse = await fetch(url, {
            ...options,
            headers,
            credentials: 'include',
          });

          return this.handleResponse<T>(retryResponse);
        } catch (refreshError) {
          // Refresh failed - user needs to log in again
          console.error('Token refresh failed:', refreshError);
          this.setAccessToken(null);

          // Dispatch custom event for AuthContext to handle
          window.dispatchEvent(new CustomEvent('auth:token-expired'));

          throw new Error('Session expired. Please log in again.');
        }
      }

      return this.handleResponse<T>(response);
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  /**
   * Handle API response
   */
  private async handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
      const error: ApiError = {
        error: response.statusText,
        status: response.status,
      };

      try {
        const errorData = await response.json();
        error.detail = errorData.message
          || (typeof errorData.detail === 'string' ? errorData.detail : undefined)
          || (typeof errorData.error === 'string' ? errorData.error : undefined);
        if (errorData.details) {
          error.details = errorData.details;
        }
      } catch {
        // Response doesn't have JSON body
      }

      throw error;
    }

    // Handle empty responses
    if (response.status === 204) {
      return {} as T;
    }

    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      return response.json();
    }

    return {} as T;
  }

  /**
   * Refresh access token using refresh token cookie
   */
  private async refreshAccessToken(): Promise<string> {
    // Prevent multiple simultaneous refresh requests
    if (this.tokenRefreshPromise) {
      return this.tokenRefreshPromise;
    }

    this.tokenRefreshPromise = (async () => {
      try {
        const response = await fetch(`${this.baseUrl}/users/auth/refresh/`, {
          method: 'POST',
          credentials: 'include', // Send refresh token cookie
          headers: {
            'Content-Type': 'application/json',
          },
        });

        if (!response.ok) {
          throw new Error('Token refresh failed');
        }

        const data = await response.json();
        this.setAccessToken(data.access);

        // Notify AuthContext that token has been refreshed
        window.dispatchEvent(new Event('auth:token-refreshed'));

        return data.access;
      } finally {
        this.tokenRefreshPromise = null;
      }
    })();

    return this.tokenRefreshPromise;
  }

  /**
   * Public method to refresh access token
   * Used on app initialization to restore session from refresh token cookie
   *
   * @returns true if refresh succeeded, false if no valid refresh token
   */
  async refreshToken(): Promise<boolean> {
    try {
      await this.refreshAccessToken();
      return true;
    } catch (error) {
      // Refresh failed - no valid refresh token cookie
      return false;
    }
  }

  // ============================================================================
  // AUTHENTICATION ENDPOINTS
  // ============================================================================

  /**
   * Register new user
   * POST /users/auth/register/
   */
  async register(data: RegisterData): Promise<AuthResponse> {
    const response = await fetch(`${this.baseUrl}/users/auth/register/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include', // Receive refresh token cookie
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.message || 'Registration failed');
    }

    const result = await response.json();
    this.setAccessToken(result.access);

    // Notify AuthContext that token has been set
    window.dispatchEvent(new Event('auth:token-refreshed'));

    return result;
  }

  /**
   * Login user
   * POST /users/auth/login/
   */
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    const response = await fetch(`${this.baseUrl}/users/auth/login/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include', // Receive refresh token cookie
      body: JSON.stringify(credentials),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.message || 'Login failed');
    }

    const result = await response.json();
    this.setAccessToken(result.access);

    // Notify AuthContext that token has been set
    window.dispatchEvent(new Event('auth:token-refreshed'));

    return result;
  }

  /**
   * Logout user
   * POST /users/auth/logout/
   */
  async logout(): Promise<void> {
    try {
      await fetch(`${this.baseUrl}/users/auth/logout/`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.accessToken}`,
        },
        credentials: 'include', // Send refresh token cookie for blacklisting
      });
    } finally {
      this.setAccessToken(null);
    }
  }

  /**
   * Get current user profile
   * GET /users/auth/profile/
   */
  async getProfile(): Promise<User> {
    return this.request<User>('/users/auth/profile/');
  }

  /**
   * Upload user avatar image
   * PATCH /users/auth/profile/upload_avatar/
   */
  async uploadAvatar(file: File): Promise<{ image_url: string }> {
    const form = new FormData();
    form.append('image', file);
    return this.request<{ image_url: string }>('/users/auth/profile/upload_avatar/', {
      method: 'PATCH',
      body: form,
    });
  }

  /**
   * Change password
   * POST /users/auth/change-password/
   */
  async changePassword(data: {
    old_password: string;
    new_password: string;
    new_password_confirm: string;
  }): Promise<{ message: string }> {
    return this.request('/users/auth/change-password/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  /**
   * Request password reset email
   * POST /users/auth/forgot-password/
   */
  async forgotPassword(email: string): Promise<{ message: string }> {
    return this.request('/users/auth/forgot-password/', {
      method: 'POST',
      body: JSON.stringify({ email }),
    });
  }

  /**
   * Reset password with token
   * POST /users/auth/reset-password/
   */
  async resetPassword(uid: string, token: string, newPassword: string, newPasswordConfirm: string): Promise<{ message: string }> {
    return this.request('/users/auth/reset-password/', {
      method: 'POST',
      body: JSON.stringify({
        uid,
        token,
        new_password: newPassword,
        new_password_confirm: newPasswordConfirm,
      }),
    });
  }

  /**
   * Get frontend configuration
   * GET /api/config/
   */
  async getFrontendConfig(): Promise<FrontendConfig> {
    return this.request<FrontendConfig>('/api/config/');
  }

  // ============================================================================
  // DICOM WEB API METHODS
  // ============================================================================

  /**
   * Get list of studies
   * GET /api/dicom/dicom-web/studies
   */
  async getStudies(params?: {
    patientID?: string;
    studyDate?: string;
    modality?: string;
    limit?: number;
    offset?: number;
  }): Promise<Study[]> {
    const queryParams = new URLSearchParams();
    if (params) {
      if (params.patientID) queryParams.append('PatientID', params.patientID);
      if (params.studyDate) queryParams.append('StudyDate', params.studyDate);
      if (params.modality) queryParams.append('ModalitiesInStudy', params.modality);
      if (params.limit) queryParams.append('limit', params.limit.toString());
      if (params.offset) queryParams.append('offset', params.offset.toString());
    }

    return this.request<Study[]>(`/api/dicom/dicom-web/studies?${queryParams}`);
  }

  /**
   * Get series for a study
   * GET /api/dicom/dicom-web/studies/{studyUID}/series
   */
  async getSeries(studyUID: string): Promise<Series[]> {
    return this.request<Series[]>(`/api/dicom/dicom-web/studies/${studyUID}/series`);
  }

  /**
   * Get instances for a series
   * GET /api/dicom/dicom-web/studies/{studyUID}/series/{seriesUID}/instances
   */
  async getInstances(studyUID: string, seriesUID: string): Promise<Instance[]> {
    return this.request<Instance[]>(`/api/dicom/dicom-web/studies/${studyUID}/series/${seriesUID}/instances`);
  }

  /**
   * Upload DICOM files
   * POST /api/dicom/upload/
   */
  async uploadDicomFiles(
    files: File[],
    onProgress?: (progress: number) => void
  ): Promise<UploadResponse> {
    const formData = new FormData();

    // Append all files
    files.forEach((file, index) => {
      formData.append(`file_${index}`, file);
    });

    const url = `${this.baseUrl}/api/dicom/upload/`;

    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();

      // Track upload progress
      if (onProgress) {
        xhr.upload.addEventListener('progress', (e) => {
          if (e.lengthComputable) {
            const progress = (e.loaded / e.total) * 100;
            onProgress(progress);
          }
        });
      }

      // Handle completion
      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const response = JSON.parse(xhr.responseText);
            resolve(response);
          } catch (error) {
            reject({
              error: 'Invalid response format',
              status: xhr.status,
            });
          }
        } else {
          reject({
            error: xhr.statusText,
            status: xhr.status,
          });
        }
      });

      // Handle errors
      xhr.addEventListener('error', () => {
        reject({
          error: 'Network error',
          status: 0,
        });
      });

      // Open request first (must be before setRequestHeader)
      xhr.open('POST', url);

      // Set auth header with access token
      if (this.accessToken) {
        xhr.setRequestHeader('Authorization', `Bearer ${this.accessToken}`);
      }

      // Include credentials for cookie-based auth
      xhr.withCredentials = true;

      // Send request
      xhr.send(formData);
    });
  }

  /**
   * Get user storage information
   * GET /api/dicom/storage/
   */
  async getStorageInfo(): Promise<StorageInfo> {
    return this.request<StorageInfo>('/api/dicom/storage/');
  }

  /**
   * Delete a study
   * DELETE /api/dicom/studies/{studyUID}
   */
  async deleteStudy(studyUID: string): Promise<{ success: boolean }> {
    return this.request<{ success: boolean }>(`/api/dicom/studies/${studyUID}`, {
      method: 'DELETE',
    });
  }

  /**
   * Search studies
   * GET /api/dicom/studies/ with query parameters
   */
  async searchStudies(query: string): Promise<Study[]> {
    const queryParams = new URLSearchParams({ q: query });
    return this.request<Study[]>(`/api/dicom/studies/?${queryParams}`);
  }

  // ============================================================================
  // VETERINARY PATIENTS ENDPOINTS (Owner → AnimalPatient)
  // ============================================================================

  /** List owners (optionally filtered by search term). GET /api/patients/owners/ */
  async getOwners(search?: string): Promise<Owner[]> {
    const qs = search ? `?search=${encodeURIComponent(search)}` : '';
    const res = await this.request<PaginatedResponse<Owner> | Owner[]>(`/api/patients/owners/${qs}`);
    return Array.isArray(res) ? res : res.results;
  }

  /** Get a single owner (includes nested animals). GET /api/patients/owners/{id}/ */
  async getOwner(id: number): Promise<Owner> {
    return this.request<Owner>(`/api/patients/owners/${id}/`);
  }

  /** Create an owner (organization auto-assigned). POST /api/patients/owners/ */
  async createOwner(data: OwnerWrite): Promise<Owner> {
    return this.request<Owner>('/api/patients/owners/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  /** Update an owner. PATCH /api/patients/owners/{id}/ */
  async updateOwner(id: number, data: Partial<OwnerWrite>): Promise<Owner> {
    return this.request<Owner>(`/api/patients/owners/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  /** Delete an owner (cascades to their animals). DELETE /api/patients/owners/{id}/ */
  async deleteOwner(id: number): Promise<void> {
    return this.request<void>(`/api/patients/owners/${id}/`, { method: 'DELETE' });
  }

  /** List animal patients, optionally filtered by species/owner/search. */
  async getAnimals(params?: { species?: Species; owner?: number; search?: string }): Promise<AnimalPatientListItem[]> {
    const q = new URLSearchParams();
    if (params?.species) q.set('species', params.species);
    if (params?.owner) q.set('owner', String(params.owner));
    if (params?.search) q.set('search', params.search);
    const qs = q.toString() ? `?${q.toString()}` : '';
    const res = await this.request<PaginatedResponse<AnimalPatientListItem> | AnimalPatientListItem[]>(`/api/patients/animals/${qs}`);
    return Array.isArray(res) ? res : res.results;
  }

  /** Get a single animal patient (includes owner + linked studies). */
  async getAnimal(id: number): Promise<AnimalPatient> {
    return this.request<AnimalPatient>(`/api/patients/animals/${id}/`);
  }

  /** Create an animal patient. POST /api/patients/animals/ */
  async createAnimal(data: AnimalPatientWrite): Promise<AnimalPatient> {
    return this.request<AnimalPatient>('/api/patients/animals/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  /** Update an animal patient. PATCH /api/patients/animals/{id}/ */
  async updateAnimal(id: number, data: Partial<AnimalPatientWrite>): Promise<AnimalPatient> {
    return this.request<AnimalPatient>(`/api/patients/animals/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  /** Delete an animal patient. DELETE /api/patients/animals/{id}/ */
  async deleteAnimal(id: number): Promise<void> {
    return this.request<void>(`/api/patients/animals/${id}/`, { method: 'DELETE' });
  }

  /** Link (or unlink) a study to an animal patient. PATCH /api/dicom/studies/{uid} */
  async linkStudyToAnimal(studyUID: string, animalPatientId: number | null): Promise<unknown> {
    return this.request(`/api/dicom/studies/${studyUID}`, {
      method: 'PATCH',
      body: JSON.stringify({ animal_patient_id: animalPatientId }),
    });
  }

  /** List VHS measurements for an animal patient. GET /api/patients/vhs/?animal={id} */
  async getVHSMeasurements(animalId: number): Promise<VHSMeasurement[]> {
    const res = await this.request<PaginatedResponse<VHSMeasurement> | VHSMeasurement[]>(
      `/api/patients/vhs/?animal=${animalId}`,
    );
    return Array.isArray(res) ? res : res.results;
  }

  /** Create a VHS measurement (vhs computed server-side). POST /api/patients/vhs/ */
  async createVHSMeasurement(data: VHSMeasurementWrite): Promise<VHSMeasurement> {
    return this.request<VHSMeasurement>('/api/patients/vhs/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  /** Delete a VHS measurement. DELETE /api/patients/vhs/{id}/ */
  async deleteVHSMeasurement(id: number): Promise<void> {
    return this.request<void>(`/api/patients/vhs/${id}/`, { method: 'DELETE' });
  }

  // ============================================================================
  // CLINICAL VISITS  GET/POST /api/patients/visits/?animal=<id>
  // ============================================================================

  async getVisits(animalId: number): Promise<ClinicalVisit[]> {
    const res = await this.request<PaginatedResponse<ClinicalVisit> | ClinicalVisit[]>(
      `/api/patients/visits/?animal=${animalId}`,
    );
    return Array.isArray(res) ? res : res.results;
  }

  async createVisit(data: ClinicalVisitWrite): Promise<ClinicalVisit> {
    return this.request<ClinicalVisit>('/api/patients/visits/', {
      method: 'POST', body: JSON.stringify(data),
    });
  }

  async updateVisit(id: number, data: Partial<ClinicalVisitWrite>): Promise<ClinicalVisit> {
    return this.request<ClinicalVisit>(`/api/patients/visits/${id}/`, {
      method: 'PATCH', body: JSON.stringify(data),
    });
  }

  async deleteVisit(id: number): Promise<void> {
    return this.request<void>(`/api/patients/visits/${id}/`, { method: 'DELETE' });
  }

  // ============================================================================
  // VACCINATION RECORDS  GET/POST /api/patients/vaccinations/?animal=<id>
  // ============================================================================

  async getVaccinations(animalId: number): Promise<VaccinationRecord[]> {
    const res = await this.request<PaginatedResponse<VaccinationRecord> | VaccinationRecord[]>(
      `/api/patients/vaccinations/?animal=${animalId}`,
    );
    return Array.isArray(res) ? res : res.results;
  }

  async createVaccination(data: VaccinationRecordWrite): Promise<VaccinationRecord> {
    return this.request<VaccinationRecord>('/api/patients/vaccinations/', {
      method: 'POST', body: JSON.stringify(data),
    });
  }

  async deleteVaccination(id: number): Promise<void> {
    return this.request<void>(`/api/patients/vaccinations/${id}/`, { method: 'DELETE' });
  }

  // ============================================================================
  // WEIGHT RECORDS  GET/POST /api/patients/weights/?animal=<id>
  // ============================================================================

  async getWeightRecords(animalId: number): Promise<WeightRecord[]> {
    const res = await this.request<PaginatedResponse<WeightRecord> | WeightRecord[]>(
      `/api/patients/weights/?animal=${animalId}`,
    );
    return Array.isArray(res) ? res : res.results;
  }

  async createWeightRecord(data: WeightRecordWrite): Promise<WeightRecord> {
    return this.request<WeightRecord>('/api/patients/weights/', {
      method: 'POST', body: JSON.stringify(data),
    });
  }

  async deleteWeightRecord(id: number): Promise<void> {
    return this.request<void>(`/api/patients/weights/${id}/`, { method: 'DELETE' });
  }

  // ============================================================================
  // APPOINTMENTS  GET/POST /api/patients/appointments/
  // ============================================================================

  async getAppointments(params?: {
    animal?: number;
    status?: AppointmentStatus;
    date_from?: string;
    date_to?: string;
  }): Promise<Appointment[]> {
    const q = new URLSearchParams();
    if (params?.animal)    q.set('animal',    String(params.animal));
    if (params?.status)    q.set('status',    params.status);
    if (params?.date_from) q.set('date_from', params.date_from);
    if (params?.date_to)   q.set('date_to',   params.date_to);
    const qs = q.toString() ? `?${q.toString()}` : '';
    const res = await this.request<PaginatedResponse<Appointment> | Appointment[]>(
      `/api/patients/appointments/${qs}`,
    );
    return Array.isArray(res) ? res : res.results;
  }

  async createAppointment(data: AppointmentWrite): Promise<Appointment> {
    return this.request<Appointment>('/api/patients/appointments/', {
      method: 'POST', body: JSON.stringify(data),
    });
  }

  async updateAppointment(id: number, data: Partial<AppointmentWrite>): Promise<Appointment> {
    return this.request<Appointment>(`/api/patients/appointments/${id}/`, {
      method: 'PATCH', body: JSON.stringify(data),
    });
  }

  async deleteAppointment(id: number): Promise<void> {
    return this.request<void>(`/api/patients/appointments/${id}/`, { method: 'DELETE' });
  }

  async completeAppointment(id: number): Promise<{ visit_id: number }> {
    return this.request<{ visit_id: number }>(`/api/patients/appointments/${id}/complete/`, {
      method: 'POST',
    });
  }

  // ============================================================================
  // PRESCRIPTIONS  GET/POST /api/patients/prescriptions/?animal=<id>
  // ============================================================================

  async getPrescriptions(animalId: number): Promise<Prescription[]> {
    const res = await this.request<PaginatedResponse<Prescription> | Prescription[]>(
      `/api/patients/prescriptions/?animal=${animalId}`,
    );
    return Array.isArray(res) ? res : res.results;
  }

  async createPrescription(data: PrescriptionWrite): Promise<Prescription> {
    return this.request<Prescription>('/api/patients/prescriptions/', {
      method: 'POST', body: JSON.stringify(data),
    });
  }

  async deletePrescription(id: number): Promise<void> {
    return this.request<void>(`/api/patients/prescriptions/${id}/`, { method: 'DELETE' });
  }

  // ============================================================================
  // ALLERGIES  GET/POST /api/patients/allergies/?animal=<id>
  // ============================================================================

  async getAllergies(animalId: number): Promise<AllergyRecord[]> {
    const res = await this.request<PaginatedResponse<AllergyRecord> | AllergyRecord[]>(
      `/api/patients/allergies/?animal=${animalId}`,
    );
    return Array.isArray(res) ? res : res.results;
  }

  async createAllergy(data: AllergyRecordWrite): Promise<AllergyRecord> {
    return this.request<AllergyRecord>('/api/patients/allergies/', {
      method: 'POST', body: JSON.stringify(data),
    });
  }

  async deleteAllergy(id: number): Promise<void> {
    return this.request<void>(`/api/patients/allergies/${id}/`, { method: 'DELETE' });
  }

  // ============================================================================
  // LAB RESULTS  GET/POST /api/patients/labs/?animal=<id>
  // ============================================================================

  async getLabResults(animalId: number, resultType?: string): Promise<LabResult[]> {
    const q = new URLSearchParams({ animal: String(animalId) });
    if (resultType) q.set('result_type', resultType);
    const res = await this.request<PaginatedResponse<LabResult> | LabResult[]>(
      `/api/patients/labs/?${q.toString()}`,
    );
    return Array.isArray(res) ? res : res.results;
  }

  async createLabResult(data: LabResultWrite): Promise<LabResult> {
    return this.request<LabResult>('/api/patients/labs/', {
      method: 'POST', body: JSON.stringify(data),
    });
  }

  async deleteLabResult(id: number): Promise<void> {
    return this.request<void>(`/api/patients/labs/${id}/`, { method: 'DELETE' });
  }

  /** Import an HL7 v2 ORU^R01 message (raw text) as a LabResult. */
  async importLabHl7(animalId: number, message: string): Promise<LabResult> {
    return this.request<LabResult>('/api/patients/labs/import-hl7/', {
      method: 'POST',
      body: JSON.stringify({ animal_patient_id: animalId, message }),
    });
  }

  /** Import a FHIR R4 DiagnosticReport (JSON) as a LabResult. */
  async importLabFhir(animalId: number, report: unknown): Promise<LabResult> {
    return this.request<LabResult>('/api/patients/labs/import-fhir/', {
      method: 'POST',
      body: JSON.stringify({ animal_patient_id: animalId, report }),
    });
  }

  // ============================================================================
  // CLINICAL PHOTOS  GET/POST /api/patients/photos/?animal=<id>
  // ============================================================================

  async getClinicalPhotos(animalId: number): Promise<ClinicalPhoto[]> {
    const res = await this.request<PaginatedResponse<ClinicalPhoto> | ClinicalPhoto[]>(
      `/api/patients/photos/?animal=${animalId}`,
    );
    return Array.isArray(res) ? res : res.results;
  }

  async uploadClinicalPhoto(animalId: number, file: File, caption?: string, bodyRegion?: string, takenOn?: string): Promise<ClinicalPhoto> {
    const fd = new FormData();
    fd.append('animal_patient_id', String(animalId));
    fd.append('photo', file);
    fd.append('taken_on', takenOn ?? new Date().toISOString().slice(0, 10));
    if (caption) fd.append('caption', caption);
    if (bodyRegion) fd.append('body_region', bodyRegion);
    return this.request<ClinicalPhoto>('/api/patients/photos/', { method: 'POST', body: fd });
  }

  async deleteClinicalPhoto(id: number): Promise<void> {
    return this.request<void>(`/api/patients/photos/${id}/`, { method: 'DELETE' });
  }

  /** Download the pet passport PDF for an animal. GET /api/patients/animals/{id}/passport/ */
  async downloadPassport(animalId: number, animalName?: string): Promise<void> {
    const url = `${this.baseUrl}/api/patients/animals/${animalId}/passport/`;
    const headers: HeadersInit = {};
    if (this.accessToken) {
      headers['Authorization'] = `Bearer ${this.accessToken}`;
    }

    const response = await fetch(url, { headers, credentials: 'include' });
    if (!response.ok) throw new Error('Passport download failed');

    const blob = await response.blob();
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `passport_${(animalName ?? 'pet').replace(/\W+/g, '')}_${animalId}.pdf`;
    link.click();
    URL.revokeObjectURL(link.href);
  }

  // ============================================================================
  // REPRODUCTIVE EVENTS  GET/POST /api/patients/reproductive/?animal=<id>
  // ============================================================================

  async getReproductiveEvents(animalId: number): Promise<ReproductiveEvent[]> {
    const res = await this.request<PaginatedResponse<ReproductiveEvent> | ReproductiveEvent[]>(
      `/api/patients/reproductive/?animal=${animalId}`,
    );
    return Array.isArray(res) ? res : res.results;
  }

  async createReproductiveEvent(data: ReproductiveEventWrite): Promise<ReproductiveEvent> {
    return this.request<ReproductiveEvent>('/api/patients/reproductive/', {
      method: 'POST', body: JSON.stringify(data),
    });
  }

  async deleteReproductiveEvent(id: number): Promise<void> {
    return this.request<void>(`/api/patients/reproductive/${id}/`, { method: 'DELETE' });
  }

  // ============================================================================
  // REFERRAL NETWORK (#24)  /api/patients/referring-clinics/ + /referral-packages/
  // ============================================================================

  async getReferringClinics(): Promise<ReferringClinic[]> {
    const res = await this.request<PaginatedResponse<ReferringClinic> | ReferringClinic[]>(
      '/api/patients/referring-clinics/',
    );
    return Array.isArray(res) ? res : res.results;
  }

  async createReferringClinic(data: ReferringClinicWrite): Promise<ReferringClinic> {
    return this.request<ReferringClinic>('/api/patients/referring-clinics/', {
      method: 'POST', body: JSON.stringify(data),
    });
  }

  async getReferralPackages(animalId: number): Promise<ReferralPackage[]> {
    const res = await this.request<PaginatedResponse<ReferralPackage> | ReferralPackage[]>(
      `/api/patients/referral-packages/?animal=${animalId}`,
    );
    return Array.isArray(res) ? res : res.results;
  }

  async createReferralPackage(data: ReferralPackageWrite): Promise<ReferralPackage> {
    return this.request<ReferralPackage>('/api/patients/referral-packages/', {
      method: 'POST', body: JSON.stringify(data),
    });
  }

  async deleteReferralPackage(id: number): Promise<void> {
    return this.request<void>(`/api/patients/referral-packages/${id}/`, { method: 'DELETE' });
  }

  /** Public, unauthenticated referral landing fetch (token in URL). */
  async getPublicReferral(token: string): Promise<PublicReferralPackage> {
    return this.request<PublicReferralPackage>(`/api/patients/referrals/${token}/`);
  }

  // ============================================================================
  // PET-OWNER PORTAL (#21)  /api/portal/
  // ============================================================================

  /** Owner-scoped dashboard: my pets + shared reports (role=Pet Owner only). */
  async getPortalDashboard(): Promise<PortalDashboard> {
    return this.request<PortalDashboard>('/api/portal/dashboard/');
  }

  /** Clinic-side: provision an owner portal login for an existing Owner. */
  async provisionOwnerAccount(ownerId: number, password: string): Promise<{ id: number; email: string; role: number }> {
    return this.request(`/api/portal/owners/${ownerId}/account/`, {
      method: 'POST', body: JSON.stringify({ password }),
    });
  }

  // ============================================================================
  // OWNER ↔ CLINIC MESSAGING (#22)  /api/patients/messages/?animal=<id>
  // ============================================================================

  async getMessages(animalId: number): Promise<Message[]> {
    const res = await this.request<PaginatedResponse<Message> | Message[]>(
      `/api/patients/messages/?animal=${animalId}`,
    );
    return Array.isArray(res) ? res : res.results;
  }

  async sendMessage(animalId: number, body: string): Promise<Message> {
    return this.request<Message>('/api/patients/messages/', {
      method: 'POST', body: JSON.stringify({ animal_patient_id: animalId, body }),
    });
  }

  async markMessagesRead(animalId: number): Promise<{ marked_read: number }> {
    return this.request('/api/patients/messages/mark_read/', {
      method: 'POST', body: JSON.stringify({ animal: animalId }),
    });
  }

  // ============================================================================
  // STUDY SHARE LINKS  GET/POST /api/dicom/share-links/
  // ============================================================================

  async getStudyShareLinks(studyUid: string): Promise<StudyShareLink[]> {
    const res = await this.request<PaginatedResponse<StudyShareLink> | StudyShareLink[]>(
      `/api/dicom/share-links/?study=${encodeURIComponent(studyUid)}`,
    );
    return Array.isArray(res) ? res : res.results;
  }

  async createStudyShareLink(data: StudyShareLinkWrite): Promise<StudyShareLink> {
    return this.request<StudyShareLink>('/api/dicom/share-links/', {
      method: 'POST', body: JSON.stringify(data),
    });
  }

  async deleteStudyShareLink(id: number): Promise<void> {
    return this.request<void>(`/api/dicom/share-links/${id}/`, { method: 'DELETE' });
  }

  /** Export a study as a DICOM CD/USB ZIP. GET /api/dicom/studies/{uid}/export/ */
  async exportStudyCD(studyUid: string): Promise<void> {
    const url = `${this.baseUrl}/api/dicom/studies/${encodeURIComponent(studyUid)}/export/`;
    const headers: HeadersInit = {};
    if (this.accessToken) {
      headers['Authorization'] = `Bearer ${this.accessToken}`;
    }

    const response = await fetch(url, { headers, credentials: 'include' });
    if (!response.ok) throw new Error('CD export failed');

    const blob = await response.blob();
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `dicom_cd_${studyUid.slice(-12).replace(/\./g, '_')}.zip`;
    link.click();
    URL.revokeObjectURL(link.href);
  }

  // ============================================================================
  // AI ANALYSIS ENDPOINTS
  // ============================================================================

  /**
   * Get list of available AI models
   * GET /api/ai-analysis/models/
   */
  async getAIModels(): Promise<AIModel[]> {
    const res = await this.request<PaginatedResponse<AIModel> | AIModel[]>('/api/ai-analysis/models/');
    return Array.isArray(res) ? res : res.results;
  }

  /**
   * Get detailed information about a specific AI model
   * GET /api/ai-analysis/models/{key}/
   */
  async getAIModel(modelKey: string): Promise<AIModel> {
    return this.request<AIModel>(`/api/ai-analysis/models/${modelKey}/`);
  }

  /**
   * Get list of analysis tasks for current user
   * GET /api/ai-analysis/tasks/
   */
  async getAnalysisTasks(params?: {
    status?: string;
    model?: string;
    limit?: number;
    offset?: number;
  }): Promise<AnalysisTask[]> {
    const queryParams = new URLSearchParams();
    if (params) {
      if (params.status) queryParams.append('status', params.status);
      if (params.model) queryParams.append('model', params.model);
      if (params.limit) queryParams.append('limit', params.limit.toString());
      if (params.offset) queryParams.append('offset', params.offset.toString());
    }

    const endpoint = queryParams.toString()
      ? `/api/ai-analysis/tasks/?${queryParams}`
      : '/api/ai-analysis/tasks/';

    const res = await this.request<PaginatedResponse<AnalysisTask> | AnalysisTask[]>(endpoint);
    return Array.isArray(res) ? res : res.results;
  }

  /**
   * Get details of a specific analysis task
   * GET /api/ai-analysis/tasks/{taskId}/
   */
  async getAnalysisTask(taskId: string): Promise<AnalysisTask> {
    return this.request<AnalysisTask>(`/api/ai-analysis/tasks/${taskId}/`);
  }

  /**
   * Create a new analysis task
   * POST /api/ai-analysis/tasks/
   */
  async createAnalysisTask(data: CreateTaskRequest): Promise<AnalysisTask> {
    return this.request<AnalysisTask>('/api/ai-analysis/tasks/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  /**
   * Cancel an analysis task
   * DELETE /api/ai-analysis/tasks/{taskId}/
   */
  async cancelAnalysisTask(taskId: string): Promise<void> {
    return this.request<void>(`/api/ai-analysis/tasks/${taskId}/`, {
      method: 'DELETE',
    });
  }

  /**
   * Retry a failed analysis task
   * POST /api/ai-analysis/tasks/{taskId}/retry/
   */
  async retryAnalysisTask(taskId: string): Promise<AnalysisTask> {
    return this.request<AnalysisTask>(`/api/ai-analysis/tasks/${taskId}/retry/`, {
      method: 'POST',
    });
  }

  async getTaskResultFiles(taskId: string): Promise<{ task_id: string; result_base_dir: string; files: { key: string; rel_path: string }[] }> {
    return this.request(`/api/ai-analysis/tasks/${taskId}/results/`);
  }

  async downloadTaskResultFile(taskId: string, filename: string): Promise<void> {
    const url = `${this.baseUrl}/api/ai-analysis/tasks/${taskId}/results/?file=${encodeURIComponent(filename)}`;
    const headers: HeadersInit = {};
    if (this.accessToken) {
      headers['Authorization'] = `Bearer ${this.accessToken}`;
    }
    const response = await fetch(url, { headers, credentials: 'include' });
    if (!response.ok) throw new Error('File download failed');
    const blob = await response.blob();
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    link.click();
    URL.revokeObjectURL(link.href);
  }

  /**
   * Upload medical images in multiple formats (DICOM, NIfTI, JPG/PNG)
   * POST /api/dicom/upload/medical/
   */
  async uploadMedicalImages(
    files: File[],
    onProgress?: (progress: number) => void
  ): Promise<MedicalImageUploadResponse> {
    const formData = new FormData();

    // Append all files
    files.forEach((file, index) => {
      formData.append(`file_${index}`, file);
    });

    const url = `${this.baseUrl}/api/dicom/upload/medical/`;

    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();

      // Track upload progress
      if (onProgress) {
        xhr.upload.addEventListener('progress', (e) => {
          if (e.lengthComputable) {
            const progress = (e.loaded / e.total) * 100;
            onProgress(progress);
          }
        });
      }

      // Handle completion
      xhr.addEventListener('load', async () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const response = JSON.parse(xhr.responseText);
            resolve(response);
          } catch (error) {
            reject(new Error('Failed to parse server response'));
          }
        } else if (xhr.status === 401) {
          // Token expired - try to refresh and retry
          try {
            console.log('Upload got 401, refreshing token and retrying...');
            await this.refreshAccessToken();

            // Retry upload with new token
            this.uploadMedicalImages(files, onProgress)
              .then(resolve)
              .catch(reject);
          } catch (refreshError) {
            // Refresh failed
            this.setAccessToken(null);
            window.dispatchEvent(new CustomEvent('auth:token-expired'));
            reject(new Error('Session expired. Please log in again.'));
          }
        } else {
          try {
            const error = JSON.parse(xhr.responseText);
            reject(new Error(error.error || error.message || 'Upload failed'));
          } catch {
            reject(new Error(`Upload failed with status ${xhr.status}`));
          }
        }
      });

      // Handle errors
      xhr.addEventListener('error', () => {
        reject(new Error('Network error during upload'));
      });

      xhr.addEventListener('abort', () => {
        reject(new Error('Upload cancelled'));
      });

      // Set up and send request
      xhr.open('POST', url, true);

      // Add auth token if available
      const token = this.getAccessToken();
      if (token) {
        xhr.setRequestHeader('Authorization', `Bearer ${token}`);
      }

      xhr.send(formData);
    });
  }

  /**
   * Get AI model recommendations for an image
   * POST /api/ai-analysis/recommend/
   */
  async getModelRecommendations(
    imageId: number
  ): Promise<ModelRecommendationResponse> {
    return this.request<ModelRecommendationResponse>('/api/ai-analysis/recommend/', {
      method: 'POST',
      body: JSON.stringify({ image_id: imageId }),
    });
  }

  /**
   * Get AI model recommendations based on raw metadata
   * POST /api/ai-analysis/recommend/
   */
  async getModelRecommendationsByMetadata(
    metadata: Record<string, any>
  ): Promise<ModelRecommendationResponse> {
    return this.request<ModelRecommendationResponse>('/api/ai-analysis/recommend/', {
      method: 'POST',
      body: JSON.stringify({ metadata }),
    });
  }

  // ============================================================================
  // MONITOR PAGE ENDPOINTS
  // ============================================================================

  /**
   * Get tasks for Monitor page with colleague visibility
   * GET /api/ai-analysis/tasks/monitor/
   */
  async getMonitorTasks(params: MonitorTasksParams = {}): Promise<PaginatedMonitorTasks> {
    const queryParams = new URLSearchParams();

    if (params.date_from) queryParams.append('date_from', params.date_from);
    if (params.date_to) queryParams.append('date_to', params.date_to);
    if (params.status) queryParams.append('status', params.status);
    if (params.scope) queryParams.append('scope', params.scope);
    if (params.model_key) queryParams.append('model_key', params.model_key);
    if (params.page) queryParams.append('page', params.page.toString());
    if (params.page_size) queryParams.append('page_size', params.page_size.toString());

    const endpoint = queryParams.toString()
      ? `/api/ai-analysis/tasks/monitor/?${queryParams}`
      : '/api/ai-analysis/tasks/monitor/';

    return this.request<PaginatedMonitorTasks>(endpoint);
  }

  /**
   * Get aggregate statistics for Monitor page dashboard
   * GET /api/ai-analysis/tasks/stats/
   */
  async getTaskStats(params: {
    date_from?: string;
    date_to?: string;
    scope?: 'own' | 'colleagues' | 'department' | 'team';
  } = {}): Promise<TaskStats> {
    const queryParams = new URLSearchParams();

    if (params.date_from) queryParams.append('date_from', params.date_from);
    if (params.date_to) queryParams.append('date_to', params.date_to);
    if (params.scope) queryParams.append('scope', params.scope);

    const endpoint = queryParams.toString()
      ? `/api/ai-analysis/tasks/stats/?${queryParams}`
      : '/api/ai-analysis/tasks/stats/';

    return this.request<TaskStats>(endpoint);
  }

  /**
   * Get DICOM transfers for monitoring
   * GET /api/dicom-gateway/transfers/monitor/
   */
  async getMonitorTransfers(params: DicomTransferFilters = {}): Promise<PaginatedDicomTransfers> {
    const queryParams = new URLSearchParams();

    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        queryParams.append(key, String(value));
      }
    });

    const endpoint = queryParams.toString()
      ? `/api/dicom-gateway/transfers/monitor/?${queryParams}`
      : '/api/dicom-gateway/transfers/monitor/';

    return this.request<PaginatedDicomTransfers>(endpoint);
  }

  /**
   * Get DICOM transfer statistics
   * GET /api/dicom-gateway/transfers/stats/
   */
  async getTransferStats(params: {
    date_from?: string;
    date_to?: string;
    scope?: 'own' | 'colleagues' | 'department' | 'team';
  } = {}): Promise<TransferStats> {
    const queryParams = new URLSearchParams();

    if (params.date_from) queryParams.append('date_from', params.date_from);
    if (params.date_to) queryParams.append('date_to', params.date_to);
    if (params.scope) queryParams.append('scope', params.scope);

    const endpoint = queryParams.toString()
      ? `/api/dicom-gateway/transfers/stats/?${queryParams}`
      : '/api/dicom-gateway/transfers/stats/';

    return this.request<TransferStats>(endpoint);
  }

  /**
   * Complete user profile with department/team information
   * POST /users/profile/complete_profile/
   */
  async completeProfile(data: ProfileCompletionData): Promise<void> {
    return this.request<void>('/users/profile/complete_profile/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  /**
   * Get colleagues in same organization who share their work
   * GET /api/users/profile/colleagues/
   */
  async getColleagues(): Promise<ColleagueProfile[]> {
    return this.request<ColleagueProfile[]>('/api/users/profile/colleagues/');
  }

  // ============================================================================
  // Statistics API Methods
  // ============================================================================

  /**
   * Get filtered statistics data with patient demographics
   * GET /api/ai-analysis/statistics/data/
   *
   * IMPORTANT: Patient names are EXCLUDED from responses for privacy compliance.
   * Only patient IDs are returned.
   */
  async getStatisticsData(filters: StatisticsFilters = {}): Promise<PaginatedStatisticsData> {
    const queryParams = new URLSearchParams();

    // Date filters
    if (filters.date_from) queryParams.append('date_from', filters.date_from);
    if (filters.date_to) queryParams.append('date_to', filters.date_to);

    // Model filters
    if (filters.model_keys) {
      filters.model_keys.forEach((key) => queryParams.append('model_keys', key));
    }

    // Status filters
    if (filters.statuses) {
      filters.statuses.forEach((status) => queryParams.append('statuses', status));
    }

    // Patient filters
    if (filters.patient_ids) {
      filters.patient_ids.forEach((id) => queryParams.append('patient_ids', id));
    }
    if (filters.patient_sex) {
      filters.patient_sex.forEach((sex) => queryParams.append('patient_sex', sex));
    }
    if (filters.patient_age_min !== null && filters.patient_age_min !== undefined) {
      queryParams.append('patient_age_min', filters.patient_age_min.toString());
    }
    if (filters.patient_age_max !== null && filters.patient_age_max !== undefined) {
      queryParams.append('patient_age_max', filters.patient_age_max.toString());
    }

    // DICOM metadata filters
    if (filters.modalities) {
      filters.modalities.forEach((mod) => queryParams.append('modalities', mod));
    }
    if (filters.body_parts) {
      filters.body_parts.forEach((bp) => queryParams.append('body_parts', bp));
    }

    // Pagination
    if (filters.page) queryParams.append('page', filters.page.toString());
    if (filters.page_size) queryParams.append('page_size', filters.page_size.toString());

    const endpoint = queryParams.toString()
      ? `/api/ai-analysis/statistics/data/?${queryParams}`
      : '/api/ai-analysis/statistics/data/';

    return this.request<PaginatedStatisticsData>(endpoint);
  }

  /**
   * Get aggregated statistics (time series, distributions, summaries)
   * GET /api/ai-analysis/statistics/aggregated/
   */
  async getStatisticsAggregated(
    filters: StatisticsFilters = {},
    timeGrouping: 'day' | 'hour' = 'day'
  ): Promise<StatisticsAggregated> {
    const queryParams = new URLSearchParams();

    // Copy filters (same as getStatisticsData)
    if (filters.date_from) queryParams.append('date_from', filters.date_from);
    if (filters.date_to) queryParams.append('date_to', filters.date_to);
    if (filters.model_keys) {
      filters.model_keys.forEach((key) => queryParams.append('model_keys', key));
    }
    if (filters.statuses) {
      filters.statuses.forEach((status) => queryParams.append('statuses', status));
    }

    // Time grouping
    queryParams.append('time_grouping', timeGrouping);

    const endpoint = queryParams.toString()
      ? `/api/ai-analysis/statistics/aggregated/?${queryParams}`
      : '/api/ai-analysis/statistics/aggregated/';

    return this.request<StatisticsAggregated>(endpoint);
  }

  /**
   * Get available filter options for the user's organization
   * GET /api/ai-analysis/statistics/filters_options/
   *
   * Returns lists of available models, modalities, body parts, etc.
   * to populate filter dropdowns.
   */
  async getStatisticsFilterOptions(): Promise<StatisticsFilterOptions> {
    return this.request<StatisticsFilterOptions>('/api/ai-analysis/statistics/filters_options/');
  }

  /**
   * Study-level analytics: modality distribution, upload trends, storage usage
   * GET /api/ai-analysis/statistics/study_analytics/
   */
  async getStudyAnalytics(period: string = 'daily'): Promise<StudyAnalytics> {
    return this.request<StudyAnalytics>(
      `/api/ai-analysis/statistics/study_analytics/?period=${period}`
    );
  }

  /**
   * Population-level insights: age/gender distribution, common findings
   * GET /api/ai-analysis/statistics/population/
   */
  async getPopulationInsights(): Promise<PopulationInsights> {
    return this.request<PopulationInsights>('/api/ai-analysis/statistics/population/');
  }

  /**
   * Per-model performance metrics
   * GET /api/ai-analysis/model-metrics/
   */
  async getModelMetrics(): Promise<ModelMetric[]> {
    const res = await this.request<PaginatedResponse<ModelMetric> | ModelMetric[]>('/api/ai-analysis/model-metrics/');
    return Array.isArray(res) ? res : res.results;
  }

  /**
   * Per-model performance trends over time
   * GET /api/ai-analysis/model-metrics/trends/
   */
  async getModelTrends(modelKey?: string): Promise<ModelTrend[]> {
    const params = modelKey ? `?model_key=${modelKey}` : '';
    const res = await this.request<PaginatedResponse<ModelTrend> | ModelTrend[]>(`/api/ai-analysis/model-metrics/trends/${params}`);
    return Array.isArray(res) ? res : res.results;
  }

  /**
   * User activity analytics (admin: all users, user: own stats)
   * GET /api/credentials/user-activity/
   */
  async getUserActivity(): Promise<UserActivity[]> {
    const res = await this.request<PaginatedResponse<UserActivity> | UserActivity[]>('/api/credentials/user-activity/');
    return Array.isArray(res) ? res : res.results;
  }

  /**
   * Current user's activity stats
   * GET /api/credentials/user-activity/me/
   */
  async getMyActivity(): Promise<UserActivity> {
    return this.request<UserActivity>('/api/credentials/user-activity/me/');
  }

  /**
   * Get user's notifications
   * GET /api/credentials/notifications/
   */
  async getNotifications(): Promise<Notification[]> {
    const res = await this.request<PaginatedResponse<Notification> | Notification[]>('/api/credentials/notifications/');
    return Array.isArray(res) ? res : res.results;
  }

  /**
   * Mark a notification as read
   * POST /api/credentials/notifications/{id}/mark_read/
   */
  async markNotificationRead(id: number): Promise<void> {
    return this.request<void>(`/api/credentials/notifications/${id}/mark_read/`, {
      method: 'POST',
    });
  }

  /**
   * Mark all notifications as read
   * POST /api/credentials/notifications/mark_all_read/
   */
  async markAllNotificationsRead(): Promise<void> {
    return this.request<void>('/api/credentials/notifications/mark_all_read/', {
      method: 'POST',
    });
  }

  // ============================================================================
  // REPORTS ENDPOINTS
  // ============================================================================

  /**
   * Get list of user's reports
   * GET /api/reports/
   */
  async getReports(): Promise<Report[]> {
    const res = await this.request<PaginatedResponse<Report> | Report[]>('/api/reports/');
    return Array.isArray(res) ? res : res.results;
  }

  /**
   * Get report detail
   * GET /api/reports/{id}/
   */
  async getReport(reportId: string): Promise<Report> {
    return this.request<Report>(`/api/reports/${reportId}/`);
  }

  /**
   * Create a report from a completed analysis task
   * POST /api/reports/
   */
  async createReport(analysisTaskId: string): Promise<Report> {
    return this.request<Report>('/api/reports/', {
      method: 'POST',
      body: JSON.stringify({ analysis_task_id: analysisTaskId }),
    });
  }

  /**
   * Download report as PDF
   * GET /api/reports/{id}/pdf/
   */
  async downloadReportPdf(reportId: string): Promise<void> {
    const url = `${this.baseUrl}/api/reports/${reportId}/pdf/`;
    const headers: HeadersInit = {};
    if (this.accessToken) {
      headers['Authorization'] = `Bearer ${this.accessToken}`;
    }

    const response = await fetch(url, {
      headers,
      credentials: 'include',
    });

    if (!response.ok) throw new Error('PDF download failed');

    const blob = await response.blob();
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `report_${reportId.slice(0, 8)}.pdf`;
    link.click();
    URL.revokeObjectURL(link.href);
  }

  /** Veterinarian sign-off: approve a report (marks FINAL). POST .../approve/ */
  async approveReport(reportId: string): Promise<Report> {
    return this.request<Report>(`/api/reports/${reportId}/approve/`, { method: 'POST' });
  }

  /** Revert a report to DRAFT. POST .../unapprove/ */
  async unapproveReport(reportId: string): Promise<Report> {
    return this.request<Report>(`/api/reports/${reportId}/unapprove/`, { method: 'POST' });
  }

  /** Create an owner share link (approved reports only). POST .../share/ */
  async shareReport(reportId: string): Promise<{ share_token: string; share_path: string }> {
    return this.request(`/api/reports/${reportId}/share/`, { method: 'POST' });
  }

  /** Revoke an owner share link. POST .../unshare/ */
  async unshareReport(reportId: string): Promise<{ success: boolean }> {
    return this.request(`/api/reports/${reportId}/unshare/`, { method: 'POST' });
  }

  /** Public, read-only owner view of a shared report (no auth). */
  async getSharedReport(token: string): Promise<PublicSharedReport> {
    return this.request<PublicSharedReport>(`/api/reports/shared/${token}/`);
  }

  /** Audit log entries (org-wide for admins). GET /api/credentials/audit-logs/ */
  async getAuditLogs(params?: {
    event_type?: string; suspicious_only?: boolean; start_date?: string; end_date?: string;
  }): Promise<AuditLogEntry[]> {
    const q = new URLSearchParams();
    if (params?.event_type) q.set('event_type', params.event_type);
    if (params?.suspicious_only) q.set('suspicious_only', 'true');
    if (params?.start_date) q.set('start_date', params.start_date);
    if (params?.end_date) q.set('end_date', params.end_date);
    const qs = q.toString() ? `?${q.toString()}` : '';
    const res = await this.request<PaginatedResponse<AuditLogEntry> | AuditLogEntry[]>(
      `/api/credentials/audit-logs/${qs}`,
    );
    return Array.isArray(res) ? res : res.results;
  }

  // ============================================================================
  // ANONYMIZATION ENDPOINTS
  // ============================================================================

  /**
   * Get list of user's anonymization jobs
   * GET /api/dicom/anonymize/
   */
  async getAnonymizationJobs(): Promise<AnonymizationJob[]> {
    const res = await this.request<PaginatedResponse<AnonymizationJob> | AnonymizationJob[]>('/api/dicom/anonymize/');
    return Array.isArray(res) ? res : res.results;
  }

  /**
   * Create an anonymization job
   * POST /api/dicom/anonymize/
   */
  async createAnonymizationJob(data: CreateAnonymizationJobRequest): Promise<AnonymizationJob> {
    return this.request<AnonymizationJob>('/api/dicom/anonymize/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  /**
   * Download anonymized ZIP
   * GET /api/dicom/anonymize/{id}/download/
   */
  // ============================================================================
  // DICOM TAG EDITOR ENDPOINTS
  // ============================================================================

  async getDicomTags(imageId: number, search?: string): Promise<{ tags: Record<string, DicomTag> }> {
    const params = search ? `?search=${encodeURIComponent(search)}` : '';
    return this.request<{ tags: Record<string, DicomTag> }>(`/api/dicom/images/${imageId}/tags/${params}`);
  }

  async updateDicomTags(imageId: number, tags: TagUpdate[]): Promise<{ tags: Record<string, DicomTag> }> {
    return this.request<{ tags: Record<string, DicomTag> }>(`/api/dicom/images/${imageId}/tags/update/`, {
      method: 'PATCH',
      body: JSON.stringify({ tags }),
    });
  }

  // ============================================================================
  // FORMAT CONVERSION ENDPOINTS
  // ============================================================================

  async getConversionJobs(): Promise<ConversionJob[]> {
    const res = await this.request<PaginatedResponse<ConversionJob> | ConversionJob[]>('/api/dicom/convert/');
    return Array.isArray(res) ? res : res.results;
  }

  async createConversionJob(data: CreateConversionJobRequest): Promise<ConversionJob> {
    return this.request<ConversionJob>('/api/dicom/convert/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async downloadConversionResult(jobId: string): Promise<void> {
    const url = `${this.baseUrl}/api/dicom/convert/${jobId}/download/`;
    const headers: HeadersInit = {};
    if (this.accessToken) {
      headers['Authorization'] = `Bearer ${this.accessToken}`;
    }
    const response = await fetch(url, { headers, credentials: 'include' });
    if (!response.ok) throw new Error('Download failed');
    const blob = await response.blob();
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `converted_${jobId.slice(0, 8)}.zip`;
    link.click();
    URL.revokeObjectURL(link.href);
  }

  // ============================================================================
  // BATCH OPERATIONS ENDPOINTS
  // ============================================================================

  async getBatchJobs(): Promise<BatchJob[]> {
    const res = await this.request<PaginatedResponse<BatchJob> | BatchJob[]>('/api/dicom/batch/');
    return Array.isArray(res) ? res : res.results;
  }

  async createBatchJob(data: CreateBatchJobRequest): Promise<BatchJob> {
    return this.request<BatchJob>('/api/dicom/batch/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async downloadBatchExport(jobId: string): Promise<void> {
    const url = `${this.baseUrl}/api/dicom/batch/${jobId}/download/`;
    const headers: HeadersInit = {};
    if (this.accessToken) {
      headers['Authorization'] = `Bearer ${this.accessToken}`;
    }
    const response = await fetch(url, { headers, credentials: 'include' });
    if (!response.ok) throw new Error('Download failed');
    const blob = await response.blob();
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `export_${jobId.slice(0, 8)}.zip`;
    link.click();
    URL.revokeObjectURL(link.href);
  }

  // ============================================================================
  // REPORT TEMPLATE ENDPOINTS
  // ============================================================================

  async getReportTemplates(): Promise<ReportTemplate[]> {
    const res = await this.request<PaginatedResponse<ReportTemplate> | ReportTemplate[]>('/api/reports/templates/');
    return Array.isArray(res) ? res : res.results;
  }

  async getDefaultTemplates(): Promise<ReportTemplate[]> {
    const res = await this.request<PaginatedResponse<ReportTemplate> | ReportTemplate[]>('/api/reports/templates/defaults/');
    return Array.isArray(res) ? res : res.results;
  }

  async createReportTemplate(data: Partial<ReportTemplate>): Promise<ReportTemplate> {
    return this.request<ReportTemplate>('/api/reports/templates/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateReportTemplate(id: string, data: Partial<ReportTemplate>): Promise<ReportTemplate> {
    return this.request<ReportTemplate>(`/api/reports/templates/${id}/`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteReportTemplate(id: string): Promise<void> {
    return this.request<void>(`/api/reports/templates/${id}/`, {
      method: 'DELETE',
    });
  }

  // ============================================================================
  // AUDIT REPORT ENDPOINTS
  // ============================================================================

  async getAuditReportPreview(filters: AuditReportFilters = {}): Promise<Record<string, any>> {
    const params = new URLSearchParams();
    if (filters.date_from) params.append('date_from', filters.date_from);
    if (filters.date_to) params.append('date_to', filters.date_to);
    if (filters.event_type) params.append('event_type', filters.event_type);
    if (filters.risk_score_min !== undefined) params.append('risk_score_min', String(filters.risk_score_min));
    const query = params.toString() ? `?${params}` : '';
    return this.request<Record<string, any>>(`/api/credentials/audit-report/preview/${query}`);
  }

  async downloadAuditReportPdf(filters: AuditReportFilters = {}): Promise<void> {
    const params = new URLSearchParams();
    if (filters.date_from) params.append('date_from', filters.date_from);
    if (filters.date_to) params.append('date_to', filters.date_to);
    if (filters.event_type) params.append('event_type', filters.event_type);
    if (filters.risk_score_min !== undefined) params.append('risk_score_min', String(filters.risk_score_min));
    const query = params.toString() ? `?${params}` : '';

    const url = `${this.baseUrl}/api/credentials/audit-report/download/${query}`;
    const headers: HeadersInit = {};
    if (this.accessToken) {
      headers['Authorization'] = `Bearer ${this.accessToken}`;
    }
    const response = await fetch(url, { headers, credentials: 'include' });
    if (!response.ok) throw new Error('PDF download failed');
    const blob = await response.blob();
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'audit_report.pdf';
    link.click();
    URL.revokeObjectURL(link.href);
  }

  // ============================================================================
  // ANONYMIZATION ENDPOINTS
  // ============================================================================

  async downloadAnonymizedZip(jobId: string): Promise<void> {
    const url = `${this.baseUrl}/api/dicom/anonymize/${jobId}/download/`;
    const headers: HeadersInit = {};
    if (this.accessToken) {
      headers['Authorization'] = `Bearer ${this.accessToken}`;
    }

    const response = await fetch(url, {
      headers,
      credentials: 'include',
    });

    if (!response.ok) throw new Error('Download failed');

    const blob = await response.blob();
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `anonymized_${jobId.slice(0, 8)}.zip`;
    link.click();
    URL.revokeObjectURL(link.href);
  }
}

// Export singleton instance
export const apiClient = new ApiClient();

// Export class for custom instances
export default ApiClient;

/**
 * Utility functions
 */

/**
 * Format file size to human-readable string
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes';

  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Format date to DICOM format (YYYYMMDD)
 */
export function formatDicomDate(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}${month}${day}`;
}

/**
 * Parse DICOM date to JavaScript Date
 */
export function parseDicomDate(dicomDate: string): Date | null {
  if (!dicomDate || dicomDate.length !== 8) return null;

  const year = parseInt(dicomDate.substring(0, 4), 10);
  const month = parseInt(dicomDate.substring(4, 6), 10) - 1; // Month is 0-indexed
  const day = parseInt(dicomDate.substring(6, 8), 10);

  return new Date(year, month, day);
}

/**
 * Format DICOM date for display
 */
export function formatDicomDateDisplay(dicomDate: string): string {
  const date = parseDicomDate(dicomDate);
  if (!date) return 'Unknown';

  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

/**
 * Validate DICOM file extension
 */
export function isDicomFile(filename: string): boolean {
  const ext = filename.toLowerCase().split('.').pop();
  return ext === 'dcm' || ext === 'dicom';
}

/**
 * Get API base URL
 */
export function getApiBaseUrl(): string {
  return API_BASE_URL;
}
