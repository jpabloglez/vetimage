import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
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

// Capture the onMessage callback so tests can push a live WS event.
const wsHandlers: { onMessage?: (m: any) => void } = {};
vi.mock('../../../hooks/useWebSocket', () => ({
  useWebSocket: (_path: string, opts: any) => {
    wsHandlers.onMessage = opts?.onMessage;
    return { connected: true, lastMessage: null, send: vi.fn(), disconnect: vi.fn(), reconnect: vi.fn() };
  },
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

  it('appends a live message pushed over the WebSocket for this animal', async () => {
    (apiClient.getMessages as any).mockResolvedValue([]);
    render(<MessageThread animalId={10} isOwner />);
    await waitFor(() => expect(apiClient.getMessages).toHaveBeenCalledWith(10));

    act(() => {
      wsHandlers.onMessage?.({
        type: 'message_created',
        animal_patient_id: 10,
        message: { id: 77, from_owner: false, body: 'Live from clinic', is_read: false, created_at: '2026-06-14T12:00:00Z' },
      });
    });
    expect(await screen.findByText('Live from clinic')).toBeInTheDocument();
  });

  it('ignores live messages for a different animal', async () => {
    (apiClient.getMessages as any).mockResolvedValue([]);
    render(<MessageThread animalId={10} />);
    await waitFor(() => expect(apiClient.getMessages).toHaveBeenCalled());

    act(() => {
      wsHandlers.onMessage?.({
        type: 'message_created',
        animal_patient_id: 999,
        message: { id: 88, from_owner: true, body: 'Other animal', is_read: false, created_at: '2026-06-14T12:00:00Z' },
      });
    });
    expect(screen.queryByText('Other animal')).not.toBeInTheDocument();
  });
});
