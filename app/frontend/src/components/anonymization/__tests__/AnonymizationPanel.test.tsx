/**
 * Unit tests for AnonymizationPanel
 *
 * Covers:
 * - Initial render (header, input mode tabs, profile picker, output format picker)
 * - Input mode tab switching (library ↔ upload)
 * - Output format picker selection
 * - BIDS info callout visibility
 * - Start button disabled state
 * - Job history rendering with format badge
 * - handleUploadComplete auto-selects uploaded study
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import React from 'react';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from '../../../contexts/AuthContext';

// -----------------------------------------------------------------------
// Module mocks — declared before imports that use them
// -----------------------------------------------------------------------

vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
  toast: { success: vi.fn(), error: vi.fn() },
}));

vi.mock('../../../utils/api', () => ({
  apiClient: {
    // Auth provider setup
    getProfile: vi.fn().mockRejectedValue(new Error('No session')),
    refreshToken: vi.fn().mockRejectedValue(new Error('No token')),
    getAccessToken: vi.fn().mockReturnValue(null),
    // Component methods
    getStudies: vi.fn().mockResolvedValue([
      {
        id: 1,
        StudyInstanceUID: 'study-uid-001',
        PatientID: 'PAT001',
        StudyDescription: 'Brain MRI',
      },
      {
        id: 2,
        StudyInstanceUID: 'study-uid-002',
        PatientID: 'PAT002',
        StudyDescription: 'Chest CT',
      },
    ]),
    getAnonymizationJobs: vi.fn().mockResolvedValue([]),
    createAnonymizationJob: vi.fn().mockResolvedValue({ id: 'job-1', status: 'PENDING' }),
    downloadAnonymizedZip: vi.fn().mockResolvedValue(undefined),
  },
}));

vi.mock('../../analyze/DragDropUploadZone', () => ({
  DragDropUploadZone: ({ onUploadComplete }: { onUploadComplete: (imgs: unknown[]) => void }) => (
    <div data-testid="drag-drop-upload-zone">
      <button
        data-testid="simulate-upload"
        onClick={() => onUploadComplete([{ id: 10, study_id: 2 }])}
      >
        Simulate Upload
      </button>
    </div>
  ),
}));

// -----------------------------------------------------------------------
// Helpers
// -----------------------------------------------------------------------

import AnonymizationPanel from '../AnonymizationPanel';

function renderPanel() {
  return render(
    <BrowserRouter>
      <AuthProvider>
        <AnonymizationPanel />
      </AuthProvider>
    </BrowserRouter>
  );
}

// -----------------------------------------------------------------------
// Tests
// -----------------------------------------------------------------------

describe('AnonymizationPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ─── Rendering ──────────────────────────────────────────────────────

  it('renders the panel header', async () => {
    renderPanel();
    expect(screen.getByText('DICOM Anonymization')).toBeInTheDocument();
  });

  it('renders input mode tabs', async () => {
    renderPanel();
    expect(screen.getByText('From Library')).toBeInTheDocument();
    expect(screen.getByText('Upload Files')).toBeInTheDocument();
  });

  it('renders profile picker with three options', async () => {
    renderPanel();
    expect(screen.getByText('Basic')).toBeInTheDocument();
    expect(screen.getByText('Full')).toBeInTheDocument();
    expect(screen.getByText('Research')).toBeInTheDocument();
  });

  it('renders output format picker with three options', async () => {
    renderPanel();
    expect(screen.getByText('DICOM ZIP')).toBeInTheDocument();
    expect(screen.getByText('NIfTI + BIDS')).toBeInTheDocument();
    expect(screen.getByText('PNG + BIDS')).toBeInTheDocument();
  });

  it('populates study dropdown after load', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText('PAT001 — Brain MRI')).toBeInTheDocument();
      expect(screen.getByText('PAT002 — Chest CT')).toBeInTheDocument();
    });
  });

  // ─── Input mode switching ────────────────────────────────────────────

  it('shows study dropdown in library mode by default', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByRole('combobox')).toBeInTheDocument();
    });
  });

  it('switches to upload zone on Upload Files tab click', async () => {
    renderPanel();
    fireEvent.click(screen.getByText('Upload Files'));
    await waitFor(() => {
      expect(screen.getByTestId('drag-drop-upload-zone')).toBeInTheDocument();
    });
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument();
  });

  it('switches back to library mode on From Library tab click', async () => {
    renderPanel();
    fireEvent.click(screen.getByText('Upload Files'));
    fireEvent.click(screen.getByText('From Library'));
    await waitFor(() => {
      expect(screen.getByRole('combobox')).toBeInTheDocument();
    });
  });

  // ─── Output format picker ────────────────────────────────────────────

  it('hides BIDS info callout when DICOM ZIP is selected (default)', async () => {
    renderPanel();
    expect(
      screen.queryByText(/BIDS output requires a complete study/i)
    ).not.toBeInTheDocument();
  });

  it('shows BIDS info callout when NIfTI + BIDS is selected', async () => {
    renderPanel();
    fireEvent.click(screen.getByText('NIfTI + BIDS'));
    expect(
      screen.getByText(/BIDS output requires a complete study/i)
    ).toBeInTheDocument();
  });

  it('shows BIDS info callout when PNG + BIDS is selected', async () => {
    renderPanel();
    fireEvent.click(screen.getByText('PNG + BIDS'));
    expect(
      screen.getByText(/BIDS output requires a complete study/i)
    ).toBeInTheDocument();
  });

  it('hides BIDS info callout when switching back to DICOM ZIP', async () => {
    renderPanel();
    fireEvent.click(screen.getByText('NIfTI + BIDS'));
    fireEvent.click(screen.getByText('DICOM ZIP'));
    expect(
      screen.queryByText(/BIDS output requires a complete study/i)
    ).not.toBeInTheDocument();
  });

  // ─── Start button state ──────────────────────────────────────────────

  it('Start Anonymization button is disabled when no study selected', async () => {
    renderPanel();
    await waitFor(() => screen.getByRole('combobox'));
    const btn = screen.getByRole('button', { name: /Start Anonymization/i });
    expect(btn).toBeDisabled();
  });

  it('Start Anonymization button is enabled after selecting a study', async () => {
    const user = userEvent.setup();
    renderPanel();

    await waitFor(() => screen.getByRole('combobox'));
    await user.selectOptions(screen.getByRole('combobox'), 'study-uid-001');

    const btn = screen.getByRole('button', { name: /Start Anonymization/i });
    expect(btn).not.toBeDisabled();
  });

  // ─── handleUploadComplete auto-select ────────────────────────────────

  it('auto-selects uploaded study and switches to library mode', async () => {
    const { apiClient } = await import('../../../utils/api');
    (apiClient.getStudies as ReturnType<typeof vi.fn>).mockResolvedValue([
      {
        id: 2,
        StudyInstanceUID: 'study-uid-002',
        PatientID: 'PAT002',
        StudyDescription: 'Chest CT',
      },
    ]);

    renderPanel();
    // Switch to upload mode
    fireEvent.click(screen.getByText('Upload Files'));
    await waitFor(() => screen.getByTestId('drag-drop-upload-zone'));

    // Simulate upload completing with study_id=2
    fireEvent.click(screen.getByTestId('simulate-upload'));

    // Should switch back to library and the study should be selected
    await waitFor(() => {
      const select = screen.getByRole('combobox') as HTMLSelectElement;
      expect(select.value).toBe('study-uid-002');
    });
  });

  // ─── Job history ─────────────────────────────────────────────────────

  it('renders job history with format badge', async () => {
    const { apiClient } = await import('../../../utils/api');
    (apiClient.getAnonymizationJobs as ReturnType<typeof vi.fn>).mockResolvedValue([
      {
        id: 'job-abc',
        profile: 'full',
        output_format: 'nifti_bids',
        status: 'COMPLETED',
        created_at: new Date().toISOString(),
      },
    ]);

    renderPanel();
    await waitFor(() => {
      expect(screen.getByText('Full profile')).toBeInTheDocument();
      expect(screen.getByText('· NIfTI + BIDS')).toBeInTheDocument();
      expect(screen.getByText('COMPLETED')).toBeInTheDocument();
    });
  });

  it('shows download button only for COMPLETED jobs', async () => {
    const { apiClient } = await import('../../../utils/api');
    (apiClient.getAnonymizationJobs as ReturnType<typeof vi.fn>).mockResolvedValue([
      {
        id: 'job-pending',
        profile: 'basic',
        output_format: 'dicom_zip',
        status: 'PENDING',
        created_at: new Date().toISOString(),
      },
    ]);

    renderPanel();
    await waitFor(() => screen.getByText('PENDING'));
    // The download button text is exactly "ZIP" — the format picker has "DICOM ZIP" not "ZIP"
    expect(screen.queryByRole('button', { name: /^ZIP$/i })).not.toBeInTheDocument();
  });

  it('shows download button for COMPLETED jobs', async () => {
    const { apiClient } = await import('../../../utils/api');
    (apiClient.getAnonymizationJobs as ReturnType<typeof vi.fn>).mockResolvedValue([
      {
        id: 'job-done',
        profile: 'basic',
        output_format: 'dicom_zip',
        status: 'COMPLETED',
        created_at: new Date().toISOString(),
      },
    ]);

    renderPanel();
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /^ZIP$/i })).toBeInTheDocument();
    });
  });
});
