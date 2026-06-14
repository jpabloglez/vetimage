import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ReferralModal from '../ReferralModal';
import { apiClient } from '../../../utils/api';

vi.mock('../../../utils/api', async () => {
  const { createApiClientMock } = await import('../../../test/mockApiClient');
  return { apiClient: createApiClientMock() };
});
vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
  toast: { success: vi.fn(), error: vi.fn() },
}));

const linkedStudy = {
  StudyInstanceUID: '1.2.840.113619.2.55.12345',
  PatientName: 'Rex',
  AnimalPatientID: 10,
  AnimalPatientName: 'Rex',
} as any;

const unlinkedStudy = {
  StudyInstanceUID: '1.2.840.113619.2.55.99999',
  PatientName: 'Unknown',
  AnimalPatientID: null,
} as any;

describe('ReferralModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (apiClient.getReferralPackages as any).mockResolvedValue([]);
  });

  it('prompts to assign a patient when the study is not linked', async () => {
    render(<ReferralModal study={unlinkedStudy} onClose={() => {}} />);
    expect(await screen.findByText(/Assign this study to a patient first/i)).toBeInTheDocument();
    expect(apiClient.getReferralPackages).not.toHaveBeenCalled();
  });

  it('renders the form and loads existing referrals for the linked animal', async () => {
    render(<ReferralModal study={linkedStudy} onClose={() => {}} />);
    await waitFor(() => expect(apiClient.getReferralPackages).toHaveBeenCalledWith(10));
    expect(screen.getByRole('button', { name: /Create referral/i })).toBeInTheDocument();
    expect(screen.getByText(/No referrals yet/i)).toBeInTheDocument();
  });

  it('creates a referral package with study UID and animal id', async () => {
    (apiClient.createReferralPackage as any).mockResolvedValue({
      id: 1, token: 'tok', share_path: '/referral/tok', urgency: 'routine',
      access_count: 0, is_valid: true, animal_name: 'Rex',
    });
    const user = userEvent.setup();
    render(<ReferralModal study={linkedStudy} onClose={() => {}} />);
    await waitFor(() => expect(apiClient.getReferralPackages).toHaveBeenCalled());

    await user.click(screen.getByRole('button', { name: /Create referral/i }));

    await waitFor(() => {
      expect(apiClient.createReferralPackage).toHaveBeenCalledWith(
        expect.objectContaining({
          animal_patient_id: 10,
          study_uid: linkedStudy.StudyInstanceUID,
          urgency: 'routine',
        }),
      );
    });
  });

  it('lists existing referrals with copy and revoke actions', async () => {
    (apiClient.getReferralPackages as any).mockResolvedValue([
      { id: 5, token: 'abc', share_path: '/referral/abc', urgency: 'urgent', access_count: 3, is_valid: true, expires_at: null },
    ]);
    (apiClient.deleteReferralPackage as any).mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(<ReferralModal study={linkedStudy} onClose={() => {}} />);
    await waitFor(() => expect(screen.getByText(/\/referral\/abc/)).toBeInTheDocument());

    await user.click(screen.getByRole('button', { name: /Revoke/i }));
    await waitFor(() => expect(apiClient.deleteReferralPackage).toHaveBeenCalledWith(5));
  });
});
