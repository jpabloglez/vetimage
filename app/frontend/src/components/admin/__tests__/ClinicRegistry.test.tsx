/**
 * The clinic registry is the platform's cross-tenant view, so these tests
 * cover what it must show accurately (per-clinic usage) and the one thing
 * registration must not do: hand the customer a password chosen by staff.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// test-utils registers the shared apiClient mock; re-mocking here would create
// a rival instance the component never sees.
import { renderWithProviders } from '../../../test-utils';
import { apiClient } from '../../../utils/api';
import ClinicRegistry from '../ClinicRegistry';

const api = apiClient as unknown as Record<string, any>;

const clinic = {
  id: 1,
  name: 'Clinica Norte',
  address: '',
  city: 'Madrid',
  created_at: '2026-01-05T10:00:00Z',
  founder_email: 'director@norte.test',
  members: 4,
  owners_count: 12,
  patients_count: 19,
  studies_count: 61,
  analyses_count: 47,
  last_activity: '2026-09-01T08:00:00Z',
};

beforeEach(() => {
  vi.clearAllMocks();
  api.getAdminClinics.mockResolvedValue([clinic]);
});

describe('ClinicRegistry', () => {
  it('shows each clinic with its usage counts', async () => {
    renderWithProviders(<ClinicRegistry />);

    expect(await screen.findByText('Clinica Norte')).toBeInTheDocument();
    expect(screen.getByText('Madrid')).toBeInTheDocument();
    expect(screen.getByText('61')).toBeInTheDocument();
    expect(screen.getByText('47')).toBeInTheDocument();
    expect(screen.getByText('director@norte.test')).toBeInTheDocument();
  });

  it('sorts by a numeric column when its header is clicked', async () => {
    const user = userEvent.setup();
    api.getAdminClinics.mockResolvedValue([
      { ...clinic, id: 1, name: 'Alpha', studies_count: 5 },
      { ...clinic, id: 2, name: 'Beta', studies_count: 90 },
    ]);
    renderWithProviders(<ClinicRegistry />);

    await screen.findByText('Alpha');
    await user.click(screen.getByRole('button', { name: /studies/i }));

    await waitFor(() => {
      const names = screen.getAllByRole('row').slice(1).map((r) => r.textContent ?? '');
      expect(names[0]).toContain('Beta');
    });
  });

  it('registers a clinic by inviting its administrator, not by setting a password', async () => {
    const user = userEvent.setup();
    api.createAdminClinic.mockResolvedValue({
      id: 9, name: 'Nueva', admin_email: 'boss@nueva.test',
      invitation_path: '/invite/tok-123',
    });
    renderWithProviders(<ClinicRegistry />);

    await user.click(await screen.findByRole('button', { name: /register clinic/i }));
    await user.type(screen.getByLabelText(/^Clinic name/i), 'Nueva');
    await user.type(screen.getByLabelText(/^Administrator email/i), 'Boss@Nueva.test');
    await user.click(screen.getByRole('button', { name: /register clinic/i }));

    await waitFor(() => expect(api.createAdminClinic).toHaveBeenCalled());
    const payload = api.createAdminClinic.mock.calls[0][0];
    expect(payload).toMatchObject({ name: 'Nueva', admin_email: 'boss@nueva.test' });
    // Staff never choose the customer's credentials.
    expect(payload).not.toHaveProperty('password');
  });

  it('surfaces the invitation link so onboarding survives a mail failure', async () => {
    const user = userEvent.setup();
    api.createAdminClinic.mockResolvedValue({
      id: 9, name: 'Nueva', admin_email: 'boss@nueva.test',
      invitation_path: '/invite/tok-123',
    });
    renderWithProviders(<ClinicRegistry />);

    await user.click(await screen.findByRole('button', { name: /register clinic/i }));
    await user.type(screen.getByLabelText(/^Clinic name/i), 'Nueva');
    await user.type(screen.getByLabelText(/^Administrator email/i), 'boss@nueva.test');
    await user.click(screen.getByRole('button', { name: /register clinic/i }));

    expect(await screen.findByText(/\/invite\/tok-123/)).toBeInTheDocument();
  });

  it('shows the backend reason when a name is taken', async () => {
    const user = userEvent.setup();
    api.createAdminClinic.mockRejectedValue({
      data: { name: ['A clinic with that name already exists.'] },
    });
    renderWithProviders(<ClinicRegistry />);

    await user.click(await screen.findByRole('button', { name: /register clinic/i }));
    await user.type(screen.getByLabelText(/^Clinic name/i), 'Clinica Norte');
    await user.type(screen.getByLabelText(/^Administrator email/i), 'x@x.test');
    await user.click(screen.getByRole('button', { name: /register clinic/i }));

    expect(await screen.findByText(/already exists/i)).toBeInTheDocument();
  });
});
