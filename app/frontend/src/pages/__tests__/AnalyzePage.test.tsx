import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../../test-utils';
import AnalyzePage from '../AnalyzePage';

// Mock heavy child components to keep tests focused on the page shell.
vi.mock('../../components/uploader/MedicalImageUploader', () => ({
  MedicalImageUploader: () => <div data-testid="medical-image-uploader">Uploader</div>,
}));
vi.mock('../../components/analyze/DragDropUploadZone', () => ({
  DragDropUploadZone: () => <div data-testid="dragdrop-zone">DropZone</div>,
}));
vi.mock('../../components/analysis/MetadataViewer', () => ({ MetadataViewer: () => <div /> }));
vi.mock('../../components/analysis/ModelRecommendation', () => ({ ModelRecommendation: () => <div /> }));
vi.mock('../../components/analysis/ParameterConfigurator', () => ({ ParameterConfigurator: () => <div /> }));
vi.mock('../../components/analysis/TaskMonitor', () => ({ TaskMonitor: () => <div /> }));

describe('AnalyzePage (tabbed shell)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the page title and subtitle', async () => {
    renderWithProviders(<AnalyzePage />);
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Analysis' })).toBeInTheDocument();
    });
    expect(screen.getByText(/Manage your analysis history/i)).toBeInTheDocument();
  });

  it('shows the AI decision-support disclaimer', async () => {
    renderWithProviders(<AnalyzePage />);
    await waitFor(() => {
      expect(screen.getByText(/Decision support — not a diagnosis/i)).toBeInTheDocument();
    });
  });

  it('renders the four workflow tabs', async () => {
    renderWithProviders(<AnalyzePage />);
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Worklist' })).toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: 'New Analysis' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Reports' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'AI Models' })).toBeInTheDocument();
  });

  it('defaults to the Worklist tab (uploader not shown initially)', async () => {
    renderWithProviders(<AnalyzePage />);
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Analysis' })).toBeInTheDocument();
    });
    expect(screen.queryByTestId('medical-image-uploader')).not.toBeInTheDocument();
  });

  it('reveals the upload flow when the New Analysis tab is selected', async () => {
    const user = userEvent.setup();
    renderWithProviders(<AnalyzePage />);
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'New Analysis' })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: 'New Analysis' }));

    await waitFor(() => {
      expect(screen.getByTestId('medical-image-uploader')).toBeInTheDocument();
    });
  });
});
