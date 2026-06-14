/**
 * Shared apiClient mock factory for component tests.
 *
 * The real ApiClient is a large singleton; tests that render components wrapped
 * in AuthProvider crash if any method AuthProvider/components call is missing
 * from an ad-hoc mock. This factory returns the FULL surface as vi.fn()s with
 * safe defaults (no network, logged-out session), so every test starts from a
 * robust, predictable baseline and overrides only what it cares about.
 *
 * Usage with Vitest hoisting:
 *
 *   const { mockApi } = vi.hoisted(() => ({ mockApi: undefined as any }));
 *   vi.mock('../../utils/api', async () => {
 *     const { createApiClientMock } = await import('../../test/mockApiClient');
 *     return { apiClient: (mockApi.value = createApiClientMock()) };
 *   });
 *
 * or simply import createApiClientMock inside a vi.mock factory.
 */
import { vi } from 'vitest';

export type ApiClientMock = Record<string, ReturnType<typeof vi.fn>>;

/**
 * Methods that, by default, should reject (no session / not found) so that
 * AuthProvider lands in a clean logged-out state on mount.
 */
const REJECTING_DEFAULTS = ['getProfile', 'refreshToken'];

/** Every apiClient method used across the app. Keep in sync as the API grows. */
const API_METHODS = [
  // Auth / session
  'login', 'register', 'logout', 'getProfile', 'refreshToken', 'getAccessToken',
  'setAccessToken', 'forgotPassword', 'resetPassword', 'changePassword',
  'uploadAvatar', 'getFrontendConfig',
  // DICOM studies
  'getStudies', 'getSeries', 'getInstances', 'getStorageInfo', 'deleteStudy',
  'searchStudies', 'linkStudyToAnimal',
  // Veterinary patients
  'getOwners', 'getOwner', 'createOwner', 'updateOwner', 'deleteOwner',
  'getAnimals', 'getAnimal', 'createAnimal', 'updateAnimal', 'deleteAnimal',
  'getVHSMeasurements', 'createVHSMeasurement', 'deleteVHSMeasurement',
  // Clinical visits
  'getVisits', 'createVisit', 'updateVisit', 'deleteVisit',
  // Vaccination records
  'getVaccinations', 'createVaccination', 'deleteVaccination',
  // Weight records
  'getWeightRecords', 'createWeightRecord', 'deleteWeightRecord',
  // Appointments
  'getAppointments', 'createAppointment', 'updateAppointment',
  'deleteAppointment', 'completeAppointment',
  // P2: prescriptions, allergies, labs, photos, share links
  'getPrescriptions', 'createPrescription', 'deletePrescription',
  'getAllergies', 'createAllergy', 'deleteAllergy',
  'getLabResults', 'createLabResult', 'deleteLabResult', 'importLabHl7', 'importLabFhir',
  'getClinicalPhotos', 'uploadClinicalPhoto', 'deleteClinicalPhoto',
  'getReproductiveEvents', 'createReproductiveEvent', 'deleteReproductiveEvent',
  'downloadPassport', 'exportStudyCD',
  'getReferringClinics', 'createReferringClinic', 'getReferralPackages',
  'createReferralPackage', 'deleteReferralPackage', 'getPublicReferral',
  'getPortalDashboard', 'provisionOwnerAccount',
  'getMessages', 'sendMessage', 'markMessagesRead',
  'getStudyShareLinks', 'createStudyShareLink', 'deleteStudyShareLink',
  // AI models & analysis
  'getAIModels', 'getAIModel', 'getAnalysisTasks', 'getAnalysisTask',
  'createAnalysisTask', 'cancelAnalysisTask', 'retryAnalysisTask',
  'getTaskResultFiles', 'getModelRecommendations', 'getModelRecommendationsByMetadata',
  'getStudyFindings',
  // Reports
  'getReports', 'createReport', 'downloadReportPdf', 'approveReport',
  'unapproveReport', 'shareReport', 'unshareReport', 'getSharedReport',
  // Monitoring
  'getMonitorTasks', 'getTaskStats', 'getDicomTransfers', 'getTransferStats',
];

/**
 * Build a complete apiClient mock. Pass overrides to customise individual
 * methods for a given test, e.g. createApiClientMock({ login: vi.fn(...) }).
 */
export function createApiClientMock(overrides: Partial<ApiClientMock> = {}): ApiClientMock {
  const mock: ApiClientMock = {};
  for (const name of API_METHODS) {
    mock[name] = vi.fn().mockResolvedValue(undefined);
  }
  // Logged-out defaults
  mock.getAccessToken = vi.fn().mockReturnValue(null);
  for (const name of REJECTING_DEFAULTS) {
    mock[name] = vi.fn().mockRejectedValue(new Error('No active session'));
  }
  // Sensible empty-collection defaults
  mock.getOwners = vi.fn().mockResolvedValue([]);
  mock.getAnimals = vi.fn().mockResolvedValue([]);
  mock.getVHSMeasurements = vi.fn().mockResolvedValue([]);
  mock.getVisits = vi.fn().mockResolvedValue([]);
  mock.getVaccinations = vi.fn().mockResolvedValue([]);
  mock.getWeightRecords = vi.fn().mockResolvedValue([]);
  mock.getAppointments = vi.fn().mockResolvedValue([]);
  mock.completeAppointment = vi.fn().mockResolvedValue({ visit_id: 1 });
  mock.getPrescriptions = vi.fn().mockResolvedValue([]);
  mock.getAllergies = vi.fn().mockResolvedValue([]);
  mock.getLabResults = vi.fn().mockResolvedValue([]);
  mock.getClinicalPhotos = vi.fn().mockResolvedValue([]);
  mock.getReproductiveEvents = vi.fn().mockResolvedValue([]);
  mock.getReferringClinics = vi.fn().mockResolvedValue([]);
  mock.getReferralPackages = vi.fn().mockResolvedValue([]);
  mock.getMessages = vi.fn().mockResolvedValue([]);
  mock.getStudyShareLinks = vi.fn().mockResolvedValue([]);
  mock.createStudyShareLink = vi.fn().mockResolvedValue({ id: '1', token: 'test-token', share_url: 'http://test/shared/test-token', is_valid: true, access_count: 0 });
  mock.getAIModels = vi.fn().mockResolvedValue([]);
  mock.getAnalysisTasks = vi.fn().mockResolvedValue([]);
  mock.getReports = vi.fn().mockResolvedValue([]);
  mock.getStudies = vi.fn().mockResolvedValue([]);

  return { ...mock, ...overrides };
}

export default createApiClientMock;
