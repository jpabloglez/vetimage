import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import Navbar from '../Navbar';
import { apiClient } from '../../../utils/api';
import { useAuth } from '../../../contexts';

vi.mock('../../../utils/api', async () => {
  const { createApiClientMock } = await import('../../../test/mockApiClient');
  return { apiClient: createApiClientMock() };
});

vi.mock('../../../contexts', () => ({
  useAuth: vi.fn(),
  useTheme: () => ({ theme: 'light', toggleTheme: vi.fn() }),
}));

vi.mock('../../../hooks/useWebSocket', () => ({
  useWebSocket: () => ({
    connected: false, lastMessage: null, send: vi.fn(), disconnect: vi.fn(), reconnect: vi.fn(),
  }),
}));

const unreadNotifications = [
  { id: 1, message: 'Analysis failed', notification_type: 'error' as const, is_read: false, created_at: new Date().toISOString() },
  { id: 2, message: 'Report ready', notification_type: 'success' as const, is_read: false, created_at: new Date().toISOString() },
];

const renderNavbar = () =>
  render(<Navbar />, {
    wrapper: ({ children }) => (
      <MemoryRouter initialEntries={['/dashboard']}>{children}</MemoryRouter>
    ),
  });

describe('Navbar notifications', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (useAuth as any).mockReturnValue({
      user: { id: 1, email: 'vet@example.com', role: 1 },
      isAuthenticated: true,
      logout: vi.fn(),
    });
    (apiClient.getNotifications as any).mockResolvedValue(unreadNotifications);
  });

  it('shows the unread badge, then clears it when the bell is opened', async () => {
    const user = userEvent.setup();
    renderNavbar();

    const bell = await screen.findByRole('button', { name: /2 unread/i });
    expect(bell).toHaveTextContent('2');

    await user.click(bell);

    await waitFor(() => {
      expect(apiClient.markAllNotificationsRead).toHaveBeenCalled();
    });
    await waitFor(() => {
      expect(bell).not.toHaveTextContent('2');
    });
  });

  it('does not call mark-all-read when there is nothing unread', async () => {
    (apiClient.getNotifications as any).mockResolvedValue([]);
    const user = userEvent.setup();
    renderNavbar();

    const bell = await screen.findByRole('button', { name: 'Notifications' });
    await user.click(bell);

    expect(apiClient.markAllNotificationsRead).not.toHaveBeenCalled();
  });
});
