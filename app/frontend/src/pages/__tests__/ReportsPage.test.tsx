import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import ReportsPage from '../ReportsPage';
import { apiClient } from '../../utils/api';

vi.mock('../../utils/api', async () => {
  const { createApiClientMock } = await import('../../test/mockApiClient');
  return { apiClient: createApiClientMock() };
});
vi.mock('react-hot-toast', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
  default: { success: vi.fn(), error: vi.fn() },
}));

const draft = {
  id: 'r-draft', title: 'Draft Report', content: {}, status: 'DRAFT',
  is_approved: false, is_shared: false, created_at: '2026-02-01T00:00:00Z',
};
const approved = {
  id: 'r-approved', title: 'Approved Report', content: {}, status: 'FINAL',
  is_approved: true, is_shared: false, approved_by_email: 'vet@clinic.com',
  created_at: '2026-02-02T00:00:00Z',
};

const renderPage = () => render(<BrowserRouter><ReportsPage /></BrowserRouter>);

describe('ReportsPage sign-off & sharing', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (apiClient.getReports as any).mockResolvedValue([draft, approved]);
  });

  it('shows Approve on drafts and Approved on signed-off reports', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText('Draft Report')).toBeInTheDocument());

    expect(screen.getByRole('button', { name: /^Approve$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Approved/i })).toBeInTheDocument();
  });

  it('only offers a Share link for approved reports', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText('Approved Report')).toBeInTheDocument());
    // Exactly one Share button (for the approved report)
    const shareButtons = screen.getAllByRole('button', { name: /Share|Copy link/i });
    expect(shareButtons).toHaveLength(1);
  });

  it('calls approveReport when Approve is clicked', async () => {
    const user = userEvent.setup();
    (apiClient.approveReport as any).mockResolvedValue({ ...draft, is_approved: true, status: 'FINAL' });
    renderPage();
    await waitFor(() => expect(screen.getByText('Draft Report')).toBeInTheDocument());

    await user.click(screen.getByRole('button', { name: /^Approve$/i }));
    await waitFor(() => expect(apiClient.approveReport).toHaveBeenCalledWith('r-draft'));
  });

  it('creates and copies an owner share link', async () => {
    const user = userEvent.setup();
    (apiClient.shareReport as any).mockResolvedValue({
      share_token: 'tok-xyz', share_path: '/shared/tok-xyz',
    });
    const writeText = vi.spyOn(navigator.clipboard, 'writeText').mockResolvedValue(undefined);
    renderPage();
    await waitFor(() => expect(screen.getByText('Approved Report')).toBeInTheDocument());

    await user.click(screen.getByRole('button', { name: /Share|Copy link/i }));
    await waitFor(() => expect(apiClient.shareReport).toHaveBeenCalledWith('r-approved'));
    expect(writeText).toHaveBeenCalledWith(expect.stringContaining('/shared/tok-xyz'));
  });
});
