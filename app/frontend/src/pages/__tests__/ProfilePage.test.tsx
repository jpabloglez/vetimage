/**
 * ProfilePage prefill.
 *
 * The form posts every field it holds, so a blank prefill is not a cosmetic
 * bug — it writes those blanks back and wipes department, job title and team
 * on the next save. These fields live on the nested UserProfile, not the User
 * row, so reading them flat off the response is the failure mode to guard.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { renderWithProviders } from '../../test-utils';
import { apiClient } from '../../utils/api';
import { ProfilePage } from '../ProfilePage';

const api = apiClient as unknown as Record<string, any>;

const profileResponse = {
  id: 1,
  email: 'vet@clinic.test',
  role: 1,
  language: 'en',
  is_staff: false,
  clinic_name: 'Clinic A',
  profile: {
    first_name: 'Ana',
    last_name: 'Ruiz',
    phone: '',
    department: 'Radiology',
    job_title: 'Radiologist',
    team_name: 'MRI Team',
    is_sharing_jobs_with_colleagues: true,
  },
};

beforeEach(() => {
  vi.clearAllMocks();
  api.getProfile.mockResolvedValue(profileResponse);
  api.completeProfile.mockResolvedValue(profileResponse);
});

describe('ProfilePage', () => {
  it('prefills from the nested profile block', async () => {
    renderWithProviders(<ProfilePage />);

    await waitFor(() => {
      expect(screen.getByDisplayValue('Radiology')).toBeInTheDocument();
    });
    expect(screen.getByDisplayValue('Radiologist')).toBeInTheDocument();
    expect(screen.getByDisplayValue('MRI Team')).toBeInTheDocument();
  });

  it('does not blank existing fields when saving an unrelated change', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ProfilePage />);

    await waitFor(() => expect(screen.getByDisplayValue('Radiology')).toBeInTheDocument());
    const team = screen.getByPlaceholderText(/Imaging Team/i);
    await user.clear(team);
    await user.type(team, 'Ultrasound');
    await user.click(screen.getByRole('button', { name: /save/i }));

    await waitFor(() => expect(api.completeProfile).toHaveBeenCalled());
    expect(api.completeProfile).toHaveBeenCalledWith(
      expect.objectContaining({
        department: 'Radiology',
        job_title: 'Radiologist',
        team_name: 'Ultrasound',
      }),
    );
  });

  it('survives a response with no profile block', async () => {
    api.getProfile.mockResolvedValue({ id: 1, email: 'vet@clinic.test', role: 1, language: 'en' });
    renderWithProviders(<ProfilePage />);

    // Renders rather than throwing on the missing nested object.
    await waitFor(() => expect(api.getProfile).toHaveBeenCalled());
    expect(screen.getByRole('button', { name: /save/i })).toBeInTheDocument();
  });
});
