import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TagEditorImagePicker } from '../TagEditorImagePicker';
import { apiClient } from '../../../utils/api';

vi.mock('../../../utils/api', async () => {
  const { createApiClientMock } = await import('../../../test/mockApiClient');
  return { apiClient: createApiClientMock() };
});

const study = {
  id: 1, StudyInstanceUID: '1.2.3', StudyDate: '20260101',
  PatientID: 'PAT001', PatientName: 'Rex', StudyDescription: 'Thorax',
};
const series = { SeriesInstanceUID: '1.2.3.1', SeriesNumber: 1, SeriesDescription: 'Axial', Modality: 'CR', NumberOfSeriesRelatedInstances: 1 };
const instance = { id: 42, SOPInstanceUID: '1.2.3.1.1', SOPClassUID: 'x', InstanceNumber: 1 };

describe('TagEditorImagePicker', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (apiClient.getStudies as any).mockResolvedValue([study]);
    (apiClient.getSeries as any).mockResolvedValue([series]);
    (apiClient.getInstances as any).mockResolvedValue([instance]);
  });

  it('cascades study -> series -> instance and reports the selected image id', async () => {
    const onSelect = vi.fn();
    const user = userEvent.setup();
    render(<TagEditorImagePicker onSelect={onSelect} />);

    await waitFor(() => expect(apiClient.getStudies).toHaveBeenCalled());

    await user.selectOptions(screen.getByLabelText('Study'), '1.2.3');
    await waitFor(() => expect(apiClient.getSeries).toHaveBeenCalledWith('1.2.3'));

    await user.selectOptions(await screen.findByLabelText('Series'), '1.2.3.1');
    await waitFor(() => expect(apiClient.getInstances).toHaveBeenCalledWith('1.2.3', '1.2.3.1'));

    await user.selectOptions(await screen.findByLabelText('Instance'), '42');

    expect(onSelect).toHaveBeenCalledWith(42);
  });

  it('resets to null when the study selection changes', async () => {
    const onSelect = vi.fn();
    const user = userEvent.setup();
    render(<TagEditorImagePicker onSelect={onSelect} />);

    await waitFor(() => expect(apiClient.getStudies).toHaveBeenCalled());
    await user.selectOptions(screen.getByLabelText('Study'), '1.2.3');
    await user.selectOptions(await screen.findByLabelText('Series'), '1.2.3.1');
    await user.selectOptions(await screen.findByLabelText('Instance'), '42');
    onSelect.mockClear();

    await user.selectOptions(screen.getByLabelText('Study'), '');

    expect(onSelect).toHaveBeenCalledWith(null);
  });
});
