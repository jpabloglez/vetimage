import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import ReferralPackagePage from '../ReferralPackagePage';
import { apiClient } from '../../utils/api';

vi.mock('../../utils/api', async () => {
  const { createApiClientMock } = await import('../../test/mockApiClient');
  return { apiClient: createApiClientMock() };
});

const renderAt = (token: string) =>
  render(
    <MemoryRouter initialEntries={[`/referral/${token}`]}>
      <Routes>
        <Route path="/referral/:token" element={<ReferralPackagePage />} />
      </Routes>
    </MemoryRouter>,
  );

const samplePackage = {
  patient: {
    name: 'Scout', species: 'Canine', breed: 'Border Collie', sex: 'Male',
    date_of_birth: '2021-03-01', microchip_id: '900012345678901',
  },
  referring_clinic_name: 'Downtown Vets',
  reason: 'Cardiology consult for suspected DCM.',
  history_summary: 'Murmur grade III/VI noted at annual exam.',
  urgency: 'urgent',
  study_instance_uid: '1.2.840.113619.2.55.12345',
  report: { title: 'Thoracic Radiograph', findings: ['Cardiomegaly', 'Mild pulmonary edema'], summary: 'Consistent with early CHF.' },
  disclaimer: 'Shared by the referring clinic for specialist review.',
  created_at: '2026-06-14T10:00:00Z',
};

describe('ReferralPackagePage', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders the referral bundle from a valid token', async () => {
    (apiClient.getPublicReferral as any).mockResolvedValue(samplePackage);
    renderAt('valid-token');
    await waitFor(() => expect(apiClient.getPublicReferral).toHaveBeenCalledWith('valid-token'));

    expect(await screen.findByText('Scout')).toBeInTheDocument();
    expect(screen.getByText('Downtown Vets')).toBeInTheDocument();
    expect(screen.getByText(/suspected DCM/i)).toBeInTheDocument();
    expect(screen.getByText('Cardiomegaly')).toBeInTheDocument();
    expect(screen.getByText('1.2.840.113619.2.55.12345')).toBeInTheDocument();
  });

  it('shows a not-available message when the token is invalid', async () => {
    (apiClient.getPublicReferral as any).mockRejectedValue(new Error('404'));
    renderAt('bad-token');
    expect(await screen.findByText(/Referral not available/i)).toBeInTheDocument();
  });
});
