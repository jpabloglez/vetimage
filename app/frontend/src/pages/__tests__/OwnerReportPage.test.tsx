import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import OwnerReportPage from '../OwnerReportPage';
import { apiClient } from '../../utils/api';

vi.mock('../../utils/api', async () => {
  const { createApiClientMock } = await import('../../test/mockApiClient');
  return { apiClient: createApiClientMock() };
});

const renderAt = (token: string) => render(
  <MemoryRouter initialEntries={[`/shared/${token}`]}>
    <Routes>
      <Route path="/shared/:token" element={<OwnerReportPage />} />
    </Routes>
  </MemoryRouter>,
);

const sharedReport = {
  title: 'Thoracic Radiograph Report',
  patient_info: { patient_name: 'Rex', species: 'Canine', breed: 'Labrador', owner: 'Jane Smith' },
  findings: ['Mild cardiomegaly noted', 'Lungs clear'],
  summary: 'Recheck in 3 months.',
  disclaimer: 'Reviewed and approved by your veterinarian.',
  approved_at: '2026-02-01T10:00:00Z',
  clinic: 'City Animal Clinic',
};

describe('OwnerReportPage (public share view)', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders an approved shared report with vet-reviewed framing', async () => {
    (apiClient.getSharedReport as any).mockResolvedValue(sharedReport);
    renderAt('tok-123');

    await waitFor(() => {
      expect(screen.getByText('Thoracic Radiograph Report')).toBeInTheDocument();
    });
    expect(apiClient.getSharedReport).toHaveBeenCalledWith('tok-123');
    expect(screen.getByText(/Reviewed by your veterinarian/i)).toBeInTheDocument();
    // Signalment + findings surfaced in plain language
    expect(screen.getByText('Rex')).toBeInTheDocument();
    expect(screen.getByText('Mild cardiomegaly noted')).toBeInTheDocument();
    // Owner is told to contact the clinic
    expect(screen.getByText(/contact your veterinary clinic/i)).toBeInTheDocument();
  });

  it('shows a friendly not-available message when the link is invalid/revoked', async () => {
    (apiClient.getSharedReport as any).mockRejectedValue(new Error('404'));
    renderAt('bad-token');

    await waitFor(() => {
      expect(screen.getByText(/Report not available/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/expired or been revoked/i)).toBeInTheDocument();
  });
});
