import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import CalendarPage from '../CalendarPage';
import { apiClient } from '../../utils/api';

vi.mock('../../utils/api', async () => {
  const { createApiClientMock } = await import('../../test/mockApiClient');
  return { apiClient: createApiClientMock() };
});
vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
  toast: { success: vi.fn(), error: vi.fn() },
}));

const appointment = {
  id: 1,
  animal_name: 'Rex',
  owner_name: 'Jane Smith',
  appointment_type: 'consultation' as const,
  scheduled_at: new Date().toISOString().replace('T', 'T').slice(0, 16) + ':00Z',
  duration_minutes: 30,
  status: 'pending' as const,
};

const renderPage = () => render(<BrowserRouter><CalendarPage /></BrowserRouter>);

describe('CalendarPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (apiClient.getAppointments as any).mockResolvedValue([appointment]);
  });

  it('renders the page title and navigation controls', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText('Appointments')).toBeInTheDocument());
    expect(screen.getByRole('button', { name: /New appointment/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Month/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Week/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Today/i })).toBeInTheDocument();
  });

  it('shows appointment in the monthly grid', async () => {
    renderPage();
    await waitFor(() => expect(apiClient.getAppointments).toHaveBeenCalled());
    // appointment card shows time + animal name concatenated
    await waitFor(() => expect(screen.getByText(/Rex/)).toBeInTheDocument());
  });

  it('switches to week view when Week button is clicked', async () => {
    const user = userEvent.setup();
    renderPage();
    await waitFor(() => expect(screen.getByText('Appointments')).toBeInTheDocument());
    await user.click(screen.getByRole('button', { name: /Week/i }));
    await waitFor(() => expect(apiClient.getAppointments).toHaveBeenCalledTimes(2));
  });

  it('opens the new appointment modal when New appointment is clicked', async () => {
    const user = userEvent.setup();
    renderPage();
    await waitFor(() => expect(screen.getByText('Appointments')).toBeInTheDocument());
    await user.click(screen.getByRole('button', { name: /New appointment/i }));
    await waitFor(() => expect(screen.getByText('New Appointment')).toBeInTheDocument());
  });

  it('navigates to next month when next button is clicked', async () => {
    const user = userEvent.setup();
    renderPage();
    await waitFor(() => expect(screen.getByText('Appointments')).toBeInTheDocument());
    const header = screen.getByRole('heading', { level: 2 });
    const initialText = header.textContent;
    await user.click(screen.getByLabelText('Next'));
    await waitFor(() => expect(header.textContent).not.toBe(initialText));
  });

  it('Today button resets to current month', async () => {
    const user = userEvent.setup();
    renderPage();
    await waitFor(() => expect(screen.getByText('Appointments')).toBeInTheDocument());
    await user.click(screen.getByLabelText('Next'));
    await user.click(screen.getByRole('button', { name: /Today/i }));
    await waitFor(() => expect(apiClient.getAppointments).toHaveBeenCalledTimes(3));
  });
});
