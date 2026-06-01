import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders } from '../../test-utils';
import MonitorPage from '../MonitorPage';

// Mock heavy child components
vi.mock('../../components/monitor/JobMonitorPanel', () => ({
  JobMonitorPanel: () => <div data-testid="job-monitor-panel">JobMonitor</div>,
}));
vi.mock('../../components/monitor/DicomTransferPanel', () => ({
  DicomTransferPanel: () => <div data-testid="dicom-transfer-panel">DicomTransfer</div>,
}));
vi.mock('../../components/monitor/ProfileCompletionModal', () => ({
  ProfileCompletionModal: () => <div>ProfileModal</div>,
}));

describe('MonitorPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders dashboard heading', async () => {
    renderWithProviders(<MonitorPage />);
    await waitFor(() => {
      expect(screen.getByText('Monitoring Dashboard')).toBeInTheDocument();
    });
  });

  it('shows both tabs', async () => {
    renderWithProviders(<MonitorPage />);
    await waitFor(() => {
      expect(screen.getByText('AI Analyses')).toBeInTheDocument();
      expect(screen.getByText('DICOM Transfers')).toBeInTheDocument();
    });
  });

  it('shows the AI Analyses panel by default', async () => {
    renderWithProviders(<MonitorPage />);
    await waitFor(() => {
      expect(screen.getByTestId('job-monitor-panel')).toBeInTheDocument();
    });
  });

  it('does not show DICOM Transfer panel by default', async () => {
    renderWithProviders(<MonitorPage />);
    await waitFor(() => {
      expect(screen.queryByTestId('dicom-transfer-panel')).not.toBeInTheDocument();
    });
  });

  it('shows subtitle text', async () => {
    renderWithProviders(<MonitorPage />);
    await waitFor(() => {
      expect(
        screen.getByText(/Real-time tracking of analysis jobs/),
      ).toBeInTheDocument();
    });
  });

  it('does not show profile modal by default', async () => {
    renderWithProviders(<MonitorPage />);
    await waitFor(() => {
      expect(screen.queryByText('ProfileModal')).not.toBeInTheDocument();
    });
  });
});
