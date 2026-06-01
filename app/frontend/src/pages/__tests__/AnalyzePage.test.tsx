import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders } from '../../test-utils';
import AnalyzePage from '../AnalyzePage';

// Mock heavy child components to keep tests focused on the page shell
vi.mock('../../components/uploader/MedicalImageUploader', () => ({
  MedicalImageUploader: () => <div data-testid="medical-image-uploader">Uploader</div>,
}));
vi.mock('../../components/analysis/MetadataViewer', () => ({
  MetadataViewer: () => <div>MetadataViewer</div>,
}));
vi.mock('../../components/analysis/ModelRecommendation', () => ({
  ModelRecommendation: () => <div>ModelRecommendation</div>,
}));
vi.mock('../../components/analysis/ParameterConfigurator', () => ({
  ParameterConfigurator: () => <div>ParameterConfigurator</div>,
}));
vi.mock('../../components/analysis/TaskMonitor', () => ({
  TaskMonitor: () => <div>TaskMonitor</div>,
}));

describe('AnalyzePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders page heading', async () => {
    renderWithProviders(<AnalyzePage />);
    await waitFor(() => {
      expect(screen.getByText('Medical Image Analysis')).toBeInTheDocument();
    });
  });

  it('shows upload step description', async () => {
    renderWithProviders(<AnalyzePage />);
    await waitFor(() => {
      expect(screen.getByText('Upload Images')).toBeInTheDocument();
    });
  });

  it('renders all four step titles', async () => {
    renderWithProviders(<AnalyzePage />);
    await waitFor(() => {
      expect(screen.getByText('Upload Images')).toBeInTheDocument();
      expect(screen.getByText('Select Model')).toBeInTheDocument();
      expect(screen.getByText('Configure')).toBeInTheDocument();
      expect(screen.getByText('Monitor')).toBeInTheDocument();
    });
  });

  it('shows the uploader component on initial render', async () => {
    renderWithProviders(<AnalyzePage />);
    await waitFor(() => {
      expect(screen.getByTestId('medical-image-uploader')).toBeInTheDocument();
    });
  });

  it('shows subtitle text', async () => {
    renderWithProviders(<AnalyzePage />);
    await waitFor(() => {
      expect(
        screen.getByText(/Upload medical images, select an AI model/),
      ).toBeInTheDocument();
    });
  });

  it('does not show monitor content initially', async () => {
    renderWithProviders(<AnalyzePage />);
    await waitFor(() => {
      expect(screen.queryByText('Start New Analysis')).not.toBeInTheDocument();
    });
  });
});
