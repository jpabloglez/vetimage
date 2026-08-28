import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import ReportDetailPage from '../ReportDetailPage';
import { apiClient } from '../../utils/api';

vi.mock('../../utils/api', async () => {
  const { createApiClientMock } = await import('../../test/mockApiClient');
  return { apiClient: createApiClientMock() };
});

const renderAt = (id: string) =>
  render(
    <MemoryRouter initialEntries={[`/reports/${id}`]}>
      <Routes>
        <Route path="/reports/:id" element={<ReportDetailPage />} />
      </Routes>
    </MemoryRouter>,
  );

const report = {
  id: 'r1',
  title: 'Thoracic Report — Rex',
  content: {
    patient_info: { patient_name: 'Rex', patient_id: 'A-1024', owner: 'Jane Smith' },
  },
  status: 'FINAL',
  analysis_task_id: 'task-1',
  study_uid: '1.2.840.1',
  model_name: 'Vet Thorax CR',
  is_approved: true,
  created_at: '2026-02-01T10:00:00Z',
};

const task = {
  id: 'task-1',
  model: { key: 'vet-thorax-cr-v1', name: 'Vet Thorax CR', model_type: 'classification', version: '1', is_active: true },
  status: 'COMPLETED',
  priority: 'routine',
  parameters: {},
  created_at: '2026-02-01T09:59:00Z',
  completed_at: '2026-02-01T10:00:00Z',
  processing_duration: 4.2,
  retry_count: 0,
  result_metadata: {
    findings: [{ label: 'Cardiomegaly', region: 'Cardiac silhouette', confidence: 0.82 }],
  },
};

describe('ReportDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (apiClient.getReport as any).mockResolvedValue(report);
    (apiClient.getAnalysisTask as any).mockResolvedValue(task);
    (apiClient.getReportPdfObjectUrl as any).mockResolvedValue('blob:fake-pdf');
  });

  it('renders report title, analysis info, findings and embeds the PDF', async () => {
    const user = userEvent.setup();
    renderAt('r1');

    expect(await screen.findByText('Thoracic Report — Rex')).toBeInTheDocument();
    expect(apiClient.getReport).toHaveBeenCalledWith('r1');
    expect(apiClient.getReportPdfObjectUrl).toHaveBeenCalledWith('r1');

    // Patient signalment appears in the condensed analysis-detail grid.
    expect(screen.getByText('Patient Name')).toBeInTheDocument();
    expect(screen.getByText('Rex')).toBeInTheDocument();
    expect(screen.getByText('A-1024')).toBeInTheDocument();
    expect(screen.getByText('Jane Smith')).toBeInTheDocument();

    // Secondary fields (priority, duration, study UID) start collapsed.
    expect(screen.queryByText('1.2.840.1')).not.toBeInTheDocument();
    await user.click(await screen.findByRole('button', { name: /Show more/i }));
    expect(await screen.findByText('1.2.840.1')).toBeInTheDocument();

    // "Viewer" links to the OHIF viewer for this report's study.
    expect(screen.getByRole('link', { name: /Viewer/i })).toHaveAttribute(
      'href', '/tools?tab=viewer&study=1.2.840.1',
    );

    // Related analysis info + findings
    await waitFor(() => expect(screen.getByText('Cardiomegaly')).toBeInTheDocument());
    expect(screen.getByText('82%')).toBeInTheDocument();

    // Embedded PDF iframe points at the object URL
    const iframe = document.querySelector('iframe');
    expect(iframe).toHaveAttribute('src', 'blob:fake-pdf');
  });

  it('shows an error state when the report fails to load', async () => {
    (apiClient.getReport as any).mockRejectedValue(new Error('nope'));
    renderAt('r1');
    expect(await screen.findByText(/Couldn't load this report/i)).toBeInTheDocument();
  });
});
