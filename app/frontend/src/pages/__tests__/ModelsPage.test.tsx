import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import ModelsPage from '../ModelsPage';
import { apiClient } from '../../utils/api';

vi.mock('../../utils/api', async () => {
  const { createApiClientMock } = await import('../../test/mockApiClient');
  return { apiClient: createApiClientMock() };
});

const model = (over: Record<string, unknown>) => ({
  key: 'k', name: 'Model', description: 'desc', version: '1.0',
  model_type: 'classification', supported_modalities: ['CR'], is_active: true,
  required_parameters: {}, default_parameters: {}, timeout_seconds: 60,
  retry_count: 0, supported_species: [], tags: [], ...over,
});

const renderPage = () => render(<BrowserRouter><ModelsPage /></BrowserRouter>);

describe('ModelsPage species filter', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (apiClient.getAIModels as any).mockResolvedValue([
      model({ key: 'canine-thorax', name: 'Canine Thorax', supported_species: ['canine'] }),
      model({ key: 'img-qc', name: 'Image Quality', supported_species: [] }), // species-agnostic
      model({ key: 'feline-derm', name: 'Feline Derm', supported_species: ['feline'] }),
    ]);
  });

  it('lists all models initially', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText('Canine Thorax')).toBeInTheDocument());
    expect(screen.getByText('Image Quality')).toBeInTheDocument();
    expect(screen.getByText('Feline Derm')).toBeInTheDocument();
  });

  it('filters by species (agnostic models always match)', async () => {
    const user = userEvent.setup();
    renderPage();
    await waitFor(() => expect(screen.getByText('Canine Thorax')).toBeInTheDocument());

    // Select "Feline" in the species dropdown
    const speciesSelect = screen.getByLabelText(/Species/i);
    await user.selectOptions(speciesSelect, 'feline');

    await waitFor(() => {
      expect(screen.queryByText('Canine Thorax')).not.toBeInTheDocument();
    });
    // Feline-specific + species-agnostic remain
    expect(screen.getByText('Feline Derm')).toBeInTheDocument();
    expect(screen.getByText('Image Quality')).toBeInTheDocument();
  });

  it('shows canine + agnostic when canine is selected', async () => {
    const user = userEvent.setup();
    renderPage();
    await waitFor(() => expect(screen.getByText('Canine Thorax')).toBeInTheDocument());

    await user.selectOptions(screen.getByLabelText(/Species/i), 'canine');

    await waitFor(() => {
      expect(screen.queryByText('Feline Derm')).not.toBeInTheDocument();
    });
    expect(screen.getByText('Canine Thorax')).toBeInTheDocument();
    expect(screen.getByText('Image Quality')).toBeInTheDocument();
  });
});
