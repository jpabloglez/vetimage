import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import MessageThread from '../MessageThread';
import { apiClient } from '../../../utils/api';

vi.mock('../../../utils/api', async () => {
  const { createApiClientMock } = await import('../../../test/mockApiClient');
  return { apiClient: createApiClientMock() };
});
vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
  toast: { success: vi.fn(), error: vi.fn() },
}));

const thread = [
  { id: 1, from_owner: false, body: 'Please bring Rex in Monday.', is_read: true, created_at: '2026-06-10T09:00:00Z' },
  { id: 2, from_owner: true, body: 'Will do, thanks!', is_read: true, created_at: '2026-06-10T09:05:00Z' },
];

describe('MessageThread', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (apiClient.getMessages as any).mockResolvedValue(thread);
    (apiClient.markMessagesRead as any).mockResolvedValue({ marked_read: 0 });
  });

  it('loads the thread and marks the other side read on open', async () => {
    render(<MessageThread animalId={10} />);
    await waitFor(() => expect(apiClient.getMessages).toHaveBeenCalledWith(10));
    expect(await screen.findByText('Please bring Rex in Monday.')).toBeInTheDocument();
    expect(screen.getByText('Will do, thanks!')).toBeInTheDocument();
    expect(apiClient.markMessagesRead).toHaveBeenCalledWith(10);
  });

  it('sends a message and appends it to the thread', async () => {
    (apiClient.sendMessage as any).mockResolvedValue({
      id: 3, from_owner: false, body: 'See you then.', is_read: false, created_at: '2026-06-10T10:00:00Z',
    });
    const user = userEvent.setup();
    render(<MessageThread animalId={10} />);
    await waitFor(() => expect(apiClient.getMessages).toHaveBeenCalled());

    await user.type(screen.getByPlaceholderText(/Type a message/i), 'See you then.');
    await user.click(screen.getByRole('button', { name: /Send/i }));

    await waitFor(() => expect(apiClient.sendMessage).toHaveBeenCalledWith(10, 'See you then.'));
    expect(await screen.findByText('See you then.')).toBeInTheDocument();
  });

  it('shows empty state when there are no messages', async () => {
    (apiClient.getMessages as any).mockResolvedValue([]);
    render(<MessageThread animalId={10} />);
    expect(await screen.findByText(/No messages yet/i)).toBeInTheDocument();
  });
});
