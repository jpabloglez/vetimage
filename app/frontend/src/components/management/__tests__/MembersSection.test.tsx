/**
 * The roster is where a clinic's access is granted and taken away, so these
 * cover what the UI must not let happen quietly: a revoke without
 * confirmation, an unexplained refusal, or a removed member disappearing from
 * view so nobody can see or undo it.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// test-utils registers the shared apiClient mock; a second one here would be a
// rival instance the component never sees.
import { renderWithProviders } from '../../../test-utils';
import { apiClient } from '../../../utils/api';
import MembersSection from '../MembersSection';

const api = apiClient as unknown as Record<string, any>;

const vet = {
  user_id: 2,
  email: 'vet@clinic.test',
  first_name: 'Ana',
  last_name: 'Ruiz',
  role: 1,
  is_clinic_admin: false,
  is_active: true,
  last_login: '2026-09-01T09:00:00Z',
  department: 'Imaging',
  job_title: 'Radiologist',
};

beforeEach(() => {
  vi.clearAllMocks();
  api.getClinicMembers.mockResolvedValue([vet]);
});

describe('MembersSection', () => {
  it('lists who can see the clinic', async () => {
    renderWithProviders(<MembersSection />);
    expect(await screen.findByText('Ana Ruiz')).toBeInTheDocument();
    expect(screen.getByText('vet@clinic.test')).toBeInTheDocument();
  });

  it('offers only roles the backend will accept', async () => {
    renderWithProviders(<MembersSection />);
    const select = await screen.findByLabelText(/role for ana ruiz/i);
    const values = Array.from(select.querySelectorAll('option')).map((o) => o.value);
    // ASSIGNABLE_ROLES — never 5 (vestigial) or 6 (Pet Owner).
    expect(values).toEqual(['1', '4', '3']);
  });

  it('changes a role', async () => {
    const user = userEvent.setup();
    api.setClinicMemberRole.mockResolvedValue({ ...vet, role: 3 });
    renderWithProviders(<MembersSection />);

    await user.selectOptions(await screen.findByLabelText(/role for ana ruiz/i), '3');
    await waitFor(() => expect(api.setClinicMemberRole).toHaveBeenCalledWith(2, 3));
  });

  it('confirms before revoking, and does not revoke on cancel', async () => {
    const user = userEvent.setup();
    renderWithProviders(<MembersSection />);

    await user.click(await screen.findByLabelText(/revoke access for ana ruiz/i));
    expect(await screen.findByText(/no longer be able to sign in/i)).toBeInTheDocument();
    // The dialog says the records stay — the reason this is safe.
    expect(screen.getByText(/stays with the clinic/i)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /cancel/i }));
    expect(api.revokeClinicMember).not.toHaveBeenCalled();
  });

  it('revokes once confirmed', async () => {
    const user = userEvent.setup();
    api.revokeClinicMember.mockResolvedValue({ ...vet, is_active: false });
    renderWithProviders(<MembersSection />);

    await user.click(await screen.findByLabelText(/revoke access for ana ruiz/i));
    await user.click(await screen.findByRole('button', { name: /^revoke access$/i }));

    await waitFor(() => expect(api.revokeClinicMember).toHaveBeenCalledWith(2));
  });

  it('keeps a revoked member visible, with a way back', async () => {
    api.getClinicMembers.mockResolvedValue([{ ...vet, is_active: false }]);
    renderWithProviders(<MembersSection />);

    expect(await screen.findByText('Ana Ruiz')).toBeInTheDocument();
    expect(screen.getByText(/no access/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/restore access for ana ruiz/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/revoke access for/i)).not.toBeInTheDocument();
  });

  it('explains a refusal in the backend\'s own words', async () => {
    const user = userEvent.setup();
    const toast = await import('react-hot-toast');
    api.setClinicMemberRole.mockRejectedValue({
      data: { error: "You are the clinic's only administrator." },
    });
    renderWithProviders(<MembersSection />);

    await user.selectOptions(await screen.findByLabelText(/role for ana ruiz/i), '3');
    await waitFor(() => {
      expect(toast.default.error).toHaveBeenCalledWith(
        "You are the clinic's only administrator.",
      );
    });
  });
});
