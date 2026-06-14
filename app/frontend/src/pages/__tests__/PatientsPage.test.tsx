import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import PatientsPage from '../PatientsPage';
import { apiClient } from '../../utils/api';

vi.mock('../../utils/api', async () => {
  const { createApiClientMock } = await import('../../test/mockApiClient');
  return { apiClient: createApiClientMock() };
});
vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
  toast: { success: vi.fn(), error: vi.fn() },
}));
// recharts needs real layout; stub to lightweight elements for jsdom.
vi.mock('recharts', () => {
  const Stub = ({ children }: any) => <div>{children}</div>;
  return {
    ResponsiveContainer: Stub, LineChart: Stub, Line: Stub, XAxis: Stub,
    YAxis: Stub, Tooltip: Stub, ReferenceArea: Stub, CartesianGrid: Stub,
  };
});

const owner = {
  id: 1, first_name: 'Jane', last_name: 'Smith', email: 'jane@example.com',
  phone: '555-0100', animals_count: 1,
  animals: [{ id: 10, name: 'Rex', species: 'canine', breed: 'Labrador', sex: 'M', owner_name: 'Jane Smith' }],
};

const animalDetail = {
  id: 10, name: 'Rex', species: 'canine', breed: 'Labrador', sex: 'M',
  owner: { id: 1, first_name: 'Jane', last_name: 'Smith' },
  studies: [],
  vhs_trend: [
    { id: 1, measured_on: '2026-01-01', vhs: 10.2, long_axis_vertebrae: 5.5, short_axis_vertebrae: 4.7, interpretation: 'within_range', method: 'manual' },
  ],
};

const renderPage = () => render(<BrowserRouter><PatientsPage /></BrowserRouter>);

describe('PatientsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (apiClient.getOwners as any).mockResolvedValue([owner]);
    (apiClient.getAnimal as any).mockResolvedValue(animalDetail);
  });

  it('switches to the All patients view and lists animals across owners', async () => {
    const user = userEvent.setup();
    (apiClient.getAnimals as any).mockResolvedValue([
      { id: 10, name: 'Rex', species: 'canine', breed: 'Labrador', sex: 'M', owner_name: 'Jane Smith' },
      { id: 11, name: 'Whiskers', species: 'feline', breed: 'Siamese', sex: 'FS', owner_name: 'Carlos Ruiz' },
    ]);
    renderPage();
    await waitFor(() => expect(screen.getByText('Jane Smith')).toBeInTheDocument());

    await user.click(screen.getByRole('button', { name: 'All patients' }));

    await waitFor(() => expect(screen.getByText('Whiskers')).toBeInTheDocument());
    expect(screen.getByText('Rex')).toBeInTheDocument();
    expect(apiClient.getAnimals).toHaveBeenCalled();
    // The action button switches to "New patient" in this view.
    expect(screen.getByRole('button', { name: /New patient/i })).toBeInTheDocument();
  });

  it('lists owners and expands to show their animals', async () => {
    const user = userEvent.setup();
    renderPage();
    await waitFor(() => expect(screen.getByText('Jane Smith')).toBeInTheDocument());
    expect(screen.getByText(/1 patient/i)).toBeInTheDocument();

    // Expand the owner to reveal the animal
    await user.click(screen.getByText('Jane Smith'));
    await waitFor(() => expect(screen.getByText('Rex')).toBeInTheDocument());
  });

  it('creates a new owner with pet', async () => {
    const user = userEvent.setup();
    (apiClient.createOwner as any).mockResolvedValue({ ...owner, id: 2 });
    (apiClient.createAnimal as any).mockResolvedValue({ id: 20 });
    renderPage();
    await waitFor(() => expect(screen.getByText('Jane Smith')).toBeInTheDocument());

    await user.click(screen.getByRole('button', { name: /New owner/i }));
    await user.type(screen.getByLabelText(/First name/i), 'Carlos');
    await user.type(screen.getByLabelText(/Last name/i), 'Ruiz');
    await user.type(screen.getByLabelText(/^Email/i), 'carlos@example.com');
    await user.type(screen.getByLabelText(/^Phone/i), '555-9988');
    await user.type(screen.getByLabelText(/^Pet name/i), 'Buddy');
    await user.click(screen.getByRole('button', { name: /Create owner/i }));

    await waitFor(() => {
      expect(apiClient.createOwner).toHaveBeenCalledWith(
        expect.objectContaining({ first_name: 'Carlos', last_name: 'Ruiz', email: 'carlos@example.com', phone: '555-9988' }),
      );
    });
    await waitFor(() => {
      expect(apiClient.createAnimal).toHaveBeenCalledWith(
        expect.objectContaining({ owner_id: 2, name: 'Buddy', species: 'canine' }),
      );
    });
  });

  it('opens a patient detail with the VHS panel and latest score', async () => {
    const user = userEvent.setup();
    renderPage();
    await waitFor(() => expect(screen.getByText('Jane Smith')).toBeInTheDocument());

    await user.click(screen.getByText('Jane Smith'));      // expand owner
    await waitFor(() => expect(screen.getByText('Rex')).toBeInTheDocument());
    await user.click(screen.getByText('Rex'));              // open detail

    await waitFor(() => expect(apiClient.getAnimal).toHaveBeenCalledWith(10));
    // VHS section + latest value rendered (appears in summary and history row)
    expect(await screen.findByText(/Vertebral Heart Score/i)).toBeInTheDocument();
    expect(screen.getAllByText('10.2').length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Within range/i).length).toBeGreaterThan(0);
  });

  it('records a new VHS measurement (computed live)', async () => {
    const user = userEvent.setup();
    (apiClient.createVHSMeasurement as any).mockResolvedValue({ id: 2 });
    renderPage();
    await waitFor(() => expect(screen.getByText('Jane Smith')).toBeInTheDocument());
    await user.click(screen.getByText('Jane Smith'));
    await waitFor(() => expect(screen.getByText('Rex')).toBeInTheDocument());
    await user.click(screen.getByText('Rex'));
    await screen.findByText(/Vertebral Heart Score/i);

    await user.click(screen.getByRole('button', { name: /Add VHS/i }));
    await user.type(screen.getByLabelText(/Long axis/i), '5.5');
    await user.type(screen.getByLabelText(/Short axis/i), '4.5');
    await user.click(screen.getByRole('button', { name: /Save measurement/i }));

    await waitFor(() => {
      expect(apiClient.createVHSMeasurement).toHaveBeenCalledWith(
        expect.objectContaining({
          animal_patient_id: 10, long_axis_vertebrae: 5.5, short_axis_vertebrae: 4.5,
        }),
      );
    });
  });

  it('renders tabs in animal detail modal', async () => {
    const user = userEvent.setup();
    renderPage();
    await waitFor(() => expect(screen.getByText('Jane Smith')).toBeInTheDocument());
    await user.click(screen.getByText('Jane Smith'));
    await waitFor(() => expect(screen.getByText('Rex')).toBeInTheDocument());
    await user.click(screen.getByText('Rex'));
    await waitFor(() => expect(apiClient.getAnimal).toHaveBeenCalledWith(10));
    // All 5 tabs should be visible
    expect(await screen.findByRole('button', { name: /Visits/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Vaccinations/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Weight/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Appointments/i })).toBeInTheDocument();
  });

  it('vaccinations tab shows empty state when no records', async () => {
    const user = userEvent.setup();
    renderPage();
    await waitFor(() => expect(screen.getByText('Jane Smith')).toBeInTheDocument());
    await user.click(screen.getByText('Jane Smith'));
    await waitFor(() => expect(screen.getByText('Rex')).toBeInTheDocument());
    await user.click(screen.getByText('Rex'));
    await waitFor(() => expect(apiClient.getAnimal).toHaveBeenCalledWith(10));
    await user.click(await screen.findByRole('button', { name: /Vaccinations/i }));
    await waitFor(() => expect(apiClient.getVaccinations).toHaveBeenCalledWith(10));
    expect(await screen.findByText(/No vaccinations recorded/i)).toBeInTheDocument();
  });

  it('weight tab shows empty state and loads records', async () => {
    const user = userEvent.setup();
    renderPage();
    await waitFor(() => expect(screen.getByText('Jane Smith')).toBeInTheDocument());
    await user.click(screen.getByText('Jane Smith'));
    await waitFor(() => expect(screen.getByText('Rex')).toBeInTheDocument());
    await user.click(screen.getByText('Rex'));
    await waitFor(() => expect(apiClient.getAnimal).toHaveBeenCalledWith(10));
    await user.click(await screen.findByRole('button', { name: /^Weight$/i }));
    await waitFor(() => expect(apiClient.getWeightRecords).toHaveBeenCalledWith(10));
    expect(await screen.findByText(/No weight records/i)).toBeInTheDocument();
  });

  it('appointments tab shows empty state', async () => {
    const user = userEvent.setup();
    renderPage();
    await waitFor(() => expect(screen.getByText('Jane Smith')).toBeInTheDocument());
    await user.click(screen.getByText('Jane Smith'));
    await waitFor(() => expect(screen.getByText('Rex')).toBeInTheDocument());
    await user.click(screen.getByText('Rex'));
    await waitFor(() => expect(apiClient.getAnimal).toHaveBeenCalledWith(10));
    await user.click(await screen.findByRole('button', { name: /Appointments/i }));
    await waitFor(() => expect(apiClient.getAppointments).toHaveBeenCalledWith({ animal: 10 }));
    expect(await screen.findByText(/No upcoming appointments/i)).toBeInTheDocument();
  });

  // --- Phase 2 features ---

  it('renders all P2 tabs in the animal detail modal', async () => {
    const user = userEvent.setup();
    renderPage();
    await waitFor(() => expect(screen.getByText('Jane Smith')).toBeInTheDocument());
    await user.click(screen.getByText('Jane Smith'));
    await waitFor(() => expect(screen.getByText('Rex')).toBeInTheDocument());
    await user.click(screen.getByText('Rex'));
    await waitFor(() => expect(apiClient.getAnimal).toHaveBeenCalledWith(10));
    expect(await screen.findByRole('button', { name: /Prescriptions/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Allergies/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Lab Results/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Photos/i })).toBeInTheDocument();
  });

  it('shows allergy alert banner for high-severity allergies', async () => {
    (apiClient.getAllergies as any).mockResolvedValue([
      { id: 1, allergen: 'Penicillin', allergen_type: 'drug', severity: 'severe', is_high_severity: true },
    ]);
    const user = userEvent.setup();
    renderPage();
    await waitFor(() => expect(screen.getByText('Jane Smith')).toBeInTheDocument());
    await user.click(screen.getByText('Jane Smith'));
    await waitFor(() => expect(screen.getByText('Rex')).toBeInTheDocument());
    await user.click(screen.getByText('Rex'));
    await waitFor(() => expect(apiClient.getAllergies).toHaveBeenCalledWith(10));
    expect(await screen.findByRole('alert')).toHaveTextContent(/Penicillin/);
  });

  it('prescriptions tab creates a new prescription', async () => {
    (apiClient.createPrescription as any).mockResolvedValue({ id: 1 });
    const user = userEvent.setup();
    renderPage();
    await waitFor(() => expect(screen.getByText('Jane Smith')).toBeInTheDocument());
    await user.click(screen.getByText('Jane Smith'));
    await waitFor(() => expect(screen.getByText('Rex')).toBeInTheDocument());
    await user.click(screen.getByText('Rex'));
    await user.click(await screen.findByRole('button', { name: /Prescriptions/i }));
    await waitFor(() => expect(apiClient.getPrescriptions).toHaveBeenCalledWith(10));

    await user.click(await screen.findByRole('button', { name: /New prescription/i }));
    await user.type(screen.getByLabelText(/Medication name/i), 'Amoxicillin');
    await user.click(screen.getByRole('button', { name: /Save prescription/i }));

    await waitFor(() => {
      expect(apiClient.createPrescription).toHaveBeenCalledWith(
        expect.objectContaining({ animal_patient_id: 10, medication_name: 'Amoxicillin' }),
      );
    });
  });

  it('lab results tab shows empty state and loads records', async () => {
    const user = userEvent.setup();
    renderPage();
    await waitFor(() => expect(screen.getByText('Jane Smith')).toBeInTheDocument());
    await user.click(screen.getByText('Jane Smith'));
    await waitFor(() => expect(screen.getByText('Rex')).toBeInTheDocument());
    await user.click(screen.getByText('Rex'));
    await user.click(await screen.findByRole('button', { name: /Lab Results/i }));
    await waitFor(() => expect(apiClient.getLabResults).toHaveBeenCalledWith(10));
    expect(await screen.findByText(/No lab results recorded/i)).toBeInTheDocument();
  });

  // --- Phase 3 features ---

  it('reproductive tab creates an event', async () => {
    (apiClient.createReproductiveEvent as any).mockResolvedValue({ id: 1 });
    const user = userEvent.setup();
    renderPage();
    await waitFor(() => expect(screen.getByText('Jane Smith')).toBeInTheDocument());
    await user.click(screen.getByText('Jane Smith'));
    await waitFor(() => expect(screen.getByText('Rex')).toBeInTheDocument());
    await user.click(screen.getByText('Rex'));
    await user.click(await screen.findByRole('button', { name: /Reproductive/i }));
    await waitFor(() => expect(apiClient.getReproductiveEvents).toHaveBeenCalledWith(10));

    await user.click(await screen.findByRole('button', { name: /Record event/i }));
    await user.click(screen.getByRole('button', { name: /^Save$/i }));

    await waitFor(() => {
      expect(apiClient.createReproductiveEvent).toHaveBeenCalledWith(
        expect.objectContaining({ animal_patient_id: 10, event_type: 'heat' }),
      );
    });
  });

  it('shows insurance block in overview when on file', async () => {
    (apiClient.getAnimal as any).mockResolvedValue({
      ...animalDetail,
      insurance_provider: 'PetPlan',
      insurance_policy_number: 'PP-12345',
      insurance_expiry: '2027-01-01',
    });
    const user = userEvent.setup();
    renderPage();
    await waitFor(() => expect(screen.getByText('Jane Smith')).toBeInTheDocument());
    await user.click(screen.getByText('Jane Smith'));
    await waitFor(() => expect(screen.getByText('Rex')).toBeInTheDocument());
    await user.click(screen.getByText('Rex'));
    await waitFor(() => expect(apiClient.getAnimal).toHaveBeenCalledWith(10));
    expect(await screen.findByText('PetPlan')).toBeInTheDocument();
    expect(screen.getByText(/PP-12345/)).toBeInTheDocument();
  });

  it('imports an HL7 lab result from the labs tab', async () => {
    (apiClient.importLabHl7 as any).mockResolvedValue({ id: 99 });
    const user = userEvent.setup();
    renderPage();
    await waitFor(() => expect(screen.getByText('Jane Smith')).toBeInTheDocument());
    await user.click(screen.getByText('Jane Smith'));
    await waitFor(() => expect(screen.getByText('Rex')).toBeInTheDocument());
    await user.click(screen.getByText('Rex'));
    await user.click(await screen.findByRole('button', { name: /Lab Results/i }));

    await user.click(await screen.findByRole('button', { name: /^Import$/i }));
    const box = await screen.findByPlaceholderText(/HL7 ORU/i);
    await user.type(box, 'MSH|^~\\&|IDEXX|Lab|VetImage|Clinic');
    await user.click(screen.getByRole('button', { name: /Import result/i }));

    await waitFor(() => expect(apiClient.importLabHl7).toHaveBeenCalledWith(
      10, expect.stringContaining('MSH|')));
  });

  it('pet passport button downloads the PDF', async () => {
    (apiClient.downloadPassport as any).mockResolvedValue(undefined);
    const user = userEvent.setup();
    renderPage();
    await waitFor(() => expect(screen.getByText('Jane Smith')).toBeInTheDocument());
    await user.click(screen.getByText('Jane Smith'));
    await waitFor(() => expect(screen.getByText('Rex')).toBeInTheDocument());
    await user.click(screen.getByText('Rex'));
    await waitFor(() => expect(apiClient.getAnimal).toHaveBeenCalledWith(10));

    await user.click(await screen.findByRole('button', { name: /Pet passport/i }));
    await waitFor(() => expect(apiClient.downloadPassport).toHaveBeenCalledWith(10, 'Rex'));
  });
});
