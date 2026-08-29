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
      studyUIDs={['1.2.3']}
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

  it('saves edits and calls onContinue for a single-study upload', async () => {
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

  it('steps through multiple studies before calling onContinue', async () => {
    const fieldsByStudy: Record<string, any> = {
      '1.2.3': { patient_name: 'DOE^JOHN', patient_id: 'PAT001', accession_number: '' },
      '4.5.6': { patient_name: 'CAT^JANE', patient_id: 'PAT002', accession_number: '' },
    };
    (apiClient.getStudyTagReview as any).mockImplementation(
      (uid: string) => Promise.resolve(fieldsByStudy[uid]),
    );
    const onContinue = vi.fn();
    const onBack = vi.fn();
    const user = userEvent.setup();
    renderStep({ studyUIDs: ['1.2.3', '4.5.6'], onContinue, onBack });

    expect(await screen.findByDisplayValue('DOE^JOHN')).toBeInTheDocument();
    expect(screen.getByText('Study 1 of 2')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /Next Study/i }));

    await waitFor(() => {
      expect(apiClient.updateStudyTagReview).toHaveBeenCalledWith('1.2.3', {
        patient_name: 'DOE^JOHN', patient_id: 'PAT001', accession_number: '',
      });
    });
    expect(onContinue).not.toHaveBeenCalled();
    expect(await screen.findByDisplayValue('CAT^JANE')).toBeInTheDocument();
    expect(screen.getByText('Study 2 of 2')).toBeInTheDocument();

    // Back from the second study returns to the first, not out of the step.
    await user.click(screen.getByText(/Back/i));
    expect(onBack).not.toHaveBeenCalled();
    expect(await screen.findByDisplayValue('DOE^JOHN')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /Next Study/i }));
    await screen.findByDisplayValue('CAT^JANE');
    await user.click(screen.getByRole('button', { name: /Continue/i }));

    await waitFor(() => {
      expect(apiClient.updateStudyTagReview).toHaveBeenCalledWith('4.5.6', {
        patient_name: 'CAT^JANE', patient_id: 'PAT002', accession_number: '',
      });
    });
    expect(onContinue).toHaveBeenCalled();
  });
});
