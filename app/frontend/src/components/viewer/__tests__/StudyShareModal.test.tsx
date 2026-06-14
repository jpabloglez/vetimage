import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import StudyShareModal from '../StudyShareModal';
import { apiClient } from '../../../utils/api';

vi.mock('../../../utils/api', async () => {
  const { createApiClientMock } = await import('../../../test/mockApiClient');
  return { apiClient: createApiClientMock() };
});
vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
  toast: { success: vi.fn(), error: vi.fn() },
}));

const study = {
  StudyInstanceUID: '1.2.840.113619.2.55.12345',
  PatientName: 'Rex',
  StudyDescription: 'Thorax',
} as any;

describe('StudyShareModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (apiClient.getStudyShareLinks as any).mockResolvedValue([]);
  });

  it('renders the share form and empty links state', async () => {
    render(<StudyShareModal study={study} onClose={() => {}} />);
    await waitFor(() => expect(apiClient.getStudyShareLinks).toHaveBeenCalledWith(study.StudyInstanceUID));
    expect(screen.getByRole('button', { name: /Create link/i })).toBeInTheDocument();
    expect(screen.getByText(/No active share links/i)).toBeInTheDocument();
  });

  it('creates a share link with the study UID', async () => {
    (apiClient.createStudyShareLink as any).mockResolvedValue({
      id: 1, token: 'tok', share_url: 'http://x/shared/tok/', is_valid: true, access_count: 0,
    });
    const user = userEvent.setup();
    render(<StudyShareModal study={study} onClose={() => {}} />);
    await waitFor(() => expect(apiClient.getStudyShareLinks).toHaveBeenCalled());

    await user.click(screen.getByRole('button', { name: /Create link/i }));

    await waitFor(() => {
      expect(apiClient.createStudyShareLink).toHaveBeenCalledWith(
        expect.objectContaining({ study_uid: study.StudyInstanceUID }),
      );
    });
  });

  it('lists existing links with copy and revoke actions', async () => {
    (apiClient.getStudyShareLinks as any).mockResolvedValue([
      { id: 1, token: 'abc', share_url: 'http://x/shared/abc/', is_valid: true, access_count: 2, expires_at: null },
    ]);
    render(<StudyShareModal study={study} onClose={() => {}} />);
    await waitFor(() => expect(screen.getByText('http://x/shared/abc/')).toBeInTheDocument());
    expect(screen.getByRole('button', { name: /Copy/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Revoke/i })).toBeInTheDocument();
  });

  it('revokes a link', async () => {
    (apiClient.getStudyShareLinks as any).mockResolvedValue([
      { id: 7, token: 'abc', share_url: 'http://x/shared/abc/', is_valid: true, access_count: 0, expires_at: null },
    ]);
    (apiClient.deleteStudyShareLink as any).mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(<StudyShareModal study={study} onClose={() => {}} />);
    await waitFor(() => expect(screen.getByText('http://x/shared/abc/')).toBeInTheDocument());
    await user.click(screen.getByRole('button', { name: /Revoke/i }));
    await waitFor(() => expect(apiClient.deleteStudyShareLink).toHaveBeenCalledWith(7));
  });
});
