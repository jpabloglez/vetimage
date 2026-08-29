import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { DicomTagReviewStep } from '../DicomTagReviewStep';
import { apiClient } from '../../../utils/api';

vi.mock('../../../utils/api', async () => {
  const { createApiClientMock } = await import('../../../test/mockApiClient');
  return { apiClient: createApiClientMock() };
});

const renderStep = (props: Partial<React.ComponentProps<typeof DicomTagReviewStep>> = {}) =>
  render(
    <DicomTagReviewStep
      studyUID="1.2.3"
      onContinue={vi.fn()}
      onBack={vi.fn()}
      {...props}
    />,
  );

describe('DicomTagReviewStep', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (apiClient.getStudyTagReview as any).mockResolvedValue({
      patient_name: 'DOE^JOHN', patient_id: 'PAT001', accession_number: '',
    });
    (apiClient.updateStudyTagReview as any).mockResolvedValue({
      success: true, files_updated: 1, files_total: 1,
      patient_name: 'Rex', patient_id: 'REX-001', accession_number: '',
    });
  });

  it('loads and pre-fills the current study tags', async () => {
    renderStep();
    await waitFor(() => {
      expect(apiClient.getStudyTagReview).toHaveBeenCalledWith('1.2.3');
    });
    expect(await screen.findByDisplayValue('DOE^JOHN')).toBeInTheDocument();
    expect(screen.getByDisplayValue('PAT001')).toBeInTheDocument();
  });

  it('saves edits and calls onContinue', async () => {
    const onContinue = vi.fn();
    const user = userEvent.setup();
    renderStep({ onContinue });

    const nameInput = await screen.findByDisplayValue('DOE^JOHN');
    await user.clear(nameInput);
    await user.type(nameInput, 'Rex');

    await user.click(screen.getByRole('button', { name: /Continue/i }));

    await waitFor(() => {
      expect(apiClient.updateStudyTagReview).toHaveBeenCalledWith('1.2.3', {
        patient_name: 'Rex', patient_id: 'PAT001', accession_number: '',
      });
    });
    expect(onContinue).toHaveBeenCalled();
  });

  it('calls onBack without saving', async () => {
    const onBack = vi.fn();
    const user = userEvent.setup();
    renderStep({ onBack });

    await screen.findByDisplayValue('DOE^JOHN');
    await user.click(screen.getByText(/Back/i));

    expect(onBack).toHaveBeenCalled();
    expect(apiClient.updateStudyTagReview).not.toHaveBeenCalled();
  });
});
