/**
 * The invitations panel hands out access to a whole clinic's records, so these
 * tests are mostly about what the UI must not let slip: an unnoticed pending
 * invitation, a role the backend would reject, or a revoke that fires without
 * confirmation.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// test-utils already registers vi.mock('./utils/api') with the full mock
// surface; re-mocking it here would create a rival module instance that the
// component never sees, so configure the shared one instead.
import { renderWithProviders } from '../../../test-utils';
import { apiClient } from '../../../utils/api';
import InvitationsSection from '../InvitationsSection';

const api = apiClient as unknown as Record<string, any>;

const pending = {
  id: 7,
  email: 'newvet@clinic.test',
  role: 1,
  status: 'pending' as const,
  created_at: '2026-09-01T10:00:00Z',
  expires_at: '2026-09-08T10:00:00Z',
  accepted_at: null,
  accept_path: '/invite/abc-123',
};

beforeEach(() => {
  vi.clearAllMocks();
  api.getClinicInvitations.mockResolvedValue([]);
});

describe('InvitationsSection', () => {
  it('lists pending invitations so none sits unnoticed', async () => {
    api.getClinicInvitations.mockResolvedValue([pending]);
    renderWithProviders(<InvitationsSection />);

    expect(await screen.findByText('newvet@clinic.test')).toBeInTheDocument();
    expect(screen.getByText('Pending')).toBeInTheDocument();
  });

  it('offers only roles the backend will accept', async () => {
    renderWithProviders(<InvitationsSection />);
    const select = await screen.findByLabelText(/^Role/i);
    const values = Array.from(select.querySelectorAll('option')).map((o) => o.value);
    // INVITABLE_ROLES — never 5 (vestigial Superuser) or 6 (Pet Owner).
    expect(values).toEqual(['1', '4', '3']);
  });

  it('sends the invitation and refreshes the list', async () => {
    const user = userEvent.setup();
    api.createClinicInvitation.mockResolvedValue(pending);
    renderWithProviders(<InvitationsSection />);

    await user.type(await screen.findByLabelText(/^Email address/i), 'New@Clinic.test');
    await user.click(screen.getByRole('button', { name: /send invitation/i }));

    await waitFor(() => {
      // Normalised before it leaves the client, so a capitalised address can't
      // slip past the backend's duplicate check.
      expect(api.createClinicInvitation).toHaveBeenCalledWith('new@clinic.test', 1);
    });
    expect(api.getClinicInvitations).toHaveBeenCalledTimes(2);
  });

  it('shows the backend reason when an address is rejected', async () => {
    const user = userEvent.setup();
    api.createClinicInvitation.mockRejectedValue({
      data: { email: ['That person is already in this clinic.'] },
    });
    renderWithProviders(<InvitationsSection />);

    await user.type(await screen.findByLabelText(/^Email address/i), 'vet@clinic.test');
    await user.click(screen.getByRole('button', { name: /send invitation/i }));

    expect(await screen.findByText(/already in this clinic/i)).toBeInTheDocument();
  });

  it('confirms before revoking, and does not revoke on cancel', async () => {
    const user = userEvent.setup();
    api.getClinicInvitations.mockResolvedValue([pending]);
    renderWithProviders(<InvitationsSection />);

    await user.click(await screen.findByLabelText(/revoke the invitation for newvet@clinic.test/i));
    expect(await screen.findByText(/stop working immediately/i)).toBeInTheDocument();
    expect(api.revokeClinicInvitation).not.toHaveBeenCalled();

    await user.click(screen.getByRole('button', { name: /cancel/i }));
    expect(api.revokeClinicInvitation).not.toHaveBeenCalled();
  });

  it('revokes once confirmed', async () => {
    const user = userEvent.setup();
    api.getClinicInvitations.mockResolvedValue([pending]);
    api.revokeClinicInvitation.mockResolvedValue(undefined);
    renderWithProviders(<InvitationsSection />);

    await user.click(await screen.findByLabelText(/revoke the invitation for newvet@clinic.test/i));
    await user.click(await screen.findByRole('button', { name: /^revoke$/i }));

    await waitFor(() => {
      expect(api.revokeClinicInvitation).toHaveBeenCalledWith(7);
    });
  });

  it('offers copy and revoke only while an invitation is still pending', async () => {
    api.getClinicInvitations.mockResolvedValue([
      { ...pending, id: 8, status: 'accepted' as const, accepted_at: '2026-09-02T09:00:00Z' },
    ]);
    renderWithProviders(<InvitationsSection />);

    expect(await screen.findByText('Accepted')).toBeInTheDocument();
    expect(screen.queryByLabelText(/revoke the invitation/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/copy the invitation link/i)).not.toBeInTheDocument();
  });
});
