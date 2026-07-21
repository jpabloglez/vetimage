import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders } from '../../test-utils';
import { apiClient } from '../../utils/api';
import Dashboard from '../DashboardPage';

// No WebSocket server in jsdom — stub the live-updates hook.
vi.mock('../../hooks/useWebSocket', () => ({
  useWebSocket: () => ({
    connected: false,
    lastMessage: null,
    send: vi.fn(),
    disconnect: vi.fn(),
    reconnect: vi.fn(),
  }),
}));

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (apiClient.getReports as any).mockResolvedValue([]);
  });

  it('renders the two quick-access tiles linking to analyze tabs', async () => {
    renderWithProviders(<Dashboard />);
    const quick = await screen.findByRole('link', { name: /Quick Analysis/i });
    expect(quick).toHaveAttribute('href', '/analyze?tab=new');
    const models = screen.getByRole('link', { name: /Available Models/i });
    expect(models).toHaveAttribute('href', '/analyze?tab=models');
  });

  it('shows an empty state when there are no reports', async () => {
    renderWithProviders(<Dashboard />);
    expect(await screen.findByText('No reports yet')).toBeInTheDocument();
  });

  it('renders labeled columns and patient fields, linking to the detail page', async () => {
    (apiClient.getReports as any).mockResolvedValue([
      {
        id: 'r1',
        title: 'Thoracic Report — Rex',
        content: {},
        status: 'FINAL',
        model_name: 'Vet Thorax CR',
        is_approved: true,
        created_at: new Date().toISOString(),
        patient_info: {
          patient_name: 'Rex',
          patient_id: 'A-1024',
          owner: 'Jane Smith',
          study_description: 'Thorax CR',
        },
      },
    ]);
    renderWithProviders(<Dashboard />);

    // Column headers act as the per-field labels.
    expect(await screen.findByRole('columnheader', { name: 'Patient Name' })).toBeInTheDocument();
    ['Patient ID', 'Owner', 'Description', 'Date', 'Status'].forEach((h) =>
      expect(screen.getByRole('columnheader', { name: h })).toBeInTheDocument(),
    );

    // Patient fields rendered, name links to the embedded detail page.
    const link = screen.getByRole('link', { name: 'Rex' });
    expect(link).toHaveAttribute('href', '/reports/r1');
    expect(screen.getByText('A-1024')).toBeInTheDocument();
    expect(screen.getByText('Jane Smith')).toBeInTheDocument();
    expect(screen.getByText('Approved')).toBeInTheDocument();
  });

  it('orders reports newest-first', async () => {
    (apiClient.getReports as any).mockResolvedValue([
      { id: 'old', title: 'Older', content: {}, status: 'DRAFT', created_at: '2020-01-01T00:00:00Z', patient_info: { patient_name: 'Older Pet' } },
      { id: 'new', title: 'Newer', content: {}, status: 'DRAFT', created_at: '2026-01-01T00:00:00Z', patient_info: { patient_name: 'Newer Pet' } },
    ]);
    renderWithProviders(<Dashboard />);
    const newer = await screen.findByRole('link', { name: 'Newer Pet' });
    const older = screen.getByRole('link', { name: 'Older Pet' });
    // Newer must appear before older in the DOM.
    expect(newer.compareDocumentPosition(older) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });
});
