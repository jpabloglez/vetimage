import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import OwnerPortalPage from '../OwnerPortalPage';
import { apiClient } from '../../utils/api';
import { useAuth } from '../../contexts';

vi.mock('../../utils/api', async () => {
  const { createApiClientMock } = await import('../../test/mockApiClient');
  return { apiClient: createApiClientMock() };
});

vi.mock('../../contexts', () => ({ useAuth: vi.fn() }));

const setAuth = (role: number | null) =>
  (useAuth as any).mockReturnValue({
    user: role == null ? null : { id: 1, email: 'jane@example.com', role },
    isAuthenticated: role != null,
    isLoading: false,
  });

const renderPortal = () =>
  render(
    <MemoryRouter initialEntries={['/portal']}>
      <Routes>
        <Route path="/portal" element={<OwnerPortalPage />} />
        <Route path="/dashboard" element={<div>Staff Dashboard</div>} />
        <Route path="/auth/login" element={<div>Login Page</div>} />
      </Routes>
    </MemoryRouter>,
  );

const dashboard = {
  owner: { email: 'jane@example.com', pet_count: 1 },
  pets: [{
    id: 10, name: 'Rex', species: 'Canine', breed: 'Labrador', sex: 'Male',
    date_of_birth: '2020-01-01', profile_photo: null, clinic: 'Test Clinic',
    vaccinations: [{ vaccine_name: 'Rabies', administered_on: '2026-01-01', next_due_on: '2027-01-01', overdue: false }],
    upcoming_appointments: [{ appointment_type: 'consultation', scheduled_at: '2026-07-01T10:00:00Z', status: 'confirmed' }],
  }],
  shared_reports: [{ title: 'Thoracic Radiograph', pet_name: 'Rex', approved_at: '2026-06-01T00:00:00Z', share_path: '/shared/abc' }],
};

describe('OwnerPortalPage', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders the owner dashboard for a pet-owner account', async () => {
    setAuth(6);
    (apiClient.getPortalDashboard as any).mockResolvedValue(dashboard);
    renderPortal();
    await waitFor(() => expect(apiClient.getPortalDashboard).toHaveBeenCalled());
    expect(await screen.findByText('Rex')).toBeInTheDocument();
    expect(screen.getByText('Rabies')).toBeInTheDocument();
    expect(screen.getByText('Thoracic Radiograph')).toBeInTheDocument();
  });

  it('redirects staff accounts away from the portal', async () => {
    setAuth(1); // veterinarian
    renderPortal();
    expect(await screen.findByText('Staff Dashboard')).toBeInTheDocument();
    expect(apiClient.getPortalDashboard).not.toHaveBeenCalled();
  });

  it('redirects unauthenticated visitors to login', async () => {
    setAuth(null);
    renderPortal();
    expect(await screen.findByText('Login Page')).toBeInTheDocument();
  });
});
