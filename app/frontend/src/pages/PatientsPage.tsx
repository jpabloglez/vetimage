/**
 * PatientsPage — Veterinary Owner & Animal Patient registry.
 *
 * Surfaces the Owner → AnimalPatient → Study hierarchy that the backend
 * (patients app) exposes at /api/patients/. Lets clinic staff create and edit
 * owners and their animals, and view a patient's signalment + study timeline.
 * Fully internationalised via the `patients` namespace.
 */
import React, { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import toast from 'react-hot-toast';
import { PawPrint, Plus, Search, ChevronDown, ChevronRight, Pencil, Trash2, User, Heart, FileDown, Upload } from 'lucide-react';
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceArea, CartesianGrid,
} from 'recharts';

import {
  apiClient,
  type Owner,
  type AnimalPatient,
  type AnimalPatientListItem,
  type OwnerWrite,
  type AnimalPatientWrite,
  type VHSMeasurementWrite,
  type ClinicalVisit,
  type ClinicalVisitWrite,
  type VaccinationRecord,
  type VaccinationRecordWrite,
  type WeightRecord,
  type WeightRecordWrite,
  type Appointment,
  type AppointmentWrite,
  type Prescription,
  type PrescriptionWrite,
  type AllergyRecord,
  type AllergyRecordWrite,
  type LabResult,
  type ClinicalPhoto,
  type ReproductiveEvent,
  type ReproductiveEventWrite,
  type ReproductiveEventType,
  type Species,
  type AnimalSex,
  type VisitType,
  type AllergenType,
  type AllergySeverity,
} from '../utils/api';
import { Button, Input, Card, CardContent, Modal, ModalContent, ModalFooter } from '../components/ui';
import AiDisclaimer from '../components/AiDisclaimer';
import ConfirmDialog from '../components/ui/ConfirmDialog';
import {
  ownerSchema, ownerAnimalSchema, animalPatientSchema, vhsSchema,
  clinicalVisitSchema, vaccinationSchema, weightRecordSchema, appointmentSchema,
  prescriptionSchema, allergySchema, labResultSchema, reproductiveEventSchema,
  zodFieldErrors,
} from '../utils/validation';

const REPRO_EVENT_VALUES: ReproductiveEventType[] = [
  'heat', 'mating', 'pregnancy_confirmed', 'whelping', 'litter_registration', 'spay_neuter', 'other',
];
import CountrySelect from '../components/ui/CountrySelect';
import OwnerPicker from '../components/patients/OwnerPicker';
import MessageThread from '../components/patients/MessageThread';

const VISIT_TYPE_VALUES: VisitType[] = ['consultation', 'follow_up', 'vaccination', 'surgery', 'imaging', 'emergency'];

const SPECIES_VALUES: Species[] = ['canine', 'feline', 'equine', 'bovine', 'avian', 'exotic', 'other'];
const SPECIES_EMOJI: Record<string, string> = {
  canine: '🐕', feline: '🐈', equine: '🐎', bovine: '🐄', avian: '🦜', exotic: '🦎', other: '🐾',
};
const SEX_VALUES: AnimalSex[] = ['', 'M', 'F', 'MN', 'FS', 'U'];
const emojiFor = (s: string) => SPECIES_EMOJI[s] ?? '🐾';

// ---------------------------------------------------------------------------
// Owner form modal
// ---------------------------------------------------------------------------
const OwnerFormModal: React.FC<{
  open: boolean;
  initial?: Owner | null;
  onClose: () => void;
  onSaved: () => void;
}> = ({ open, initial, onClose, onSaved }) => {
  const { t } = useTranslation('patients');
  const [form, setForm] = useState<OwnerWrite>({ first_name: '', last_name: '', email: '', phone: '' });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [animalForm, setAnimalForm] = useState({ name: '', species: 'canine' as Species, breed: '' });
  const [animalErrors, setAnimalErrors] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const isNew = !initial;

  useEffect(() => {
    if (open) {
      setErrors({});
      setAnimalErrors({});
      setAnimalForm({ name: '', species: 'canine', breed: '' });
      setForm({
        first_name: initial?.first_name ?? '',
        last_name: initial?.last_name ?? '',
        email: initial?.email ?? '',
        phone: initial?.phone ?? '',
        address: initial?.address ?? '',
        city: initial?.city ?? '',
        country: initial?.country ?? '',
      });
    }
  }, [open, initial]);

  const set = (k: keyof OwnerWrite) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm((f) => ({ ...f, [k]: e.target.value }));
    setErrors((prev) => (prev[k] ? { ...prev, [k]: '' } : prev));
  };

  const setAnimal = (k: keyof typeof animalForm) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
      setAnimalForm((f) => ({ ...f, [k]: e.target.value }));
      setAnimalErrors((prev) => (prev[k] ? { ...prev, [k]: '' } : prev));
    };

  const selectClass =
    'w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-medical bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-medical-500';

  const submit = async () => {
    const ownerErrs = zodFieldErrors(ownerSchema, form);
    const petErrs = isNew ? zodFieldErrors(ownerAnimalSchema, animalForm) : {};
    if (Object.keys(ownerErrs).length || Object.keys(petErrs).length) {
      setErrors(ownerErrs);
      setAnimalErrors(petErrs);
      return;
    }
    setSaving(true);
    try {
      if (initial) {
        await apiClient.updateOwner(initial.id, form);
        toast.success(t('ownerForm.updated'));
      } else {
        const newOwner = await apiClient.createOwner(form);
        await apiClient.createAnimal({
          owner_id: newOwner.id,
          name: animalForm.name,
          species: animalForm.species,
          breed: animalForm.breed || undefined,
        });
        toast.success(t('ownerForm.created'));
      }
      onSaved();
      onClose();
    } catch {
      toast.error(t('ownerForm.failed'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal isOpen={open} onClose={onClose} title={initial ? t('ownerForm.editTitle') : t('ownerForm.newTitle')} size="lg">
      <ModalContent>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Input label={t('ownerForm.firstName')} required value={form.first_name} onChange={set('first_name')} error={errors.first_name} />
          <Input label={t('ownerForm.lastName')} required value={form.last_name} onChange={set('last_name')} error={errors.last_name} />
          <Input label={t('ownerForm.email')} required type="email" value={form.email ?? ''} onChange={set('email')} error={errors.email} />
          <Input label={t('ownerForm.phone')} required value={form.phone ?? ''} onChange={set('phone')} error={errors.phone} />
          <Input label={t('ownerForm.address')} value={form.address} onChange={set('address')} />
          <Input label={t('ownerForm.city')} value={form.city} onChange={set('city')} />
          <CountrySelect
            label={t('ownerForm.country')}
            value={form.country}
            onChange={(code) => setForm((f) => ({ ...f, country: code }))}
          />
        </div>

        {isNew && (
          <>
            <div className="mt-5 mb-3 flex items-center gap-2">
              <div className="flex-1 border-t border-slate-200 dark:border-slate-700" />
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-400 px-2">{t('ownerForm.petSection')}</span>
              <div className="flex-1 border-t border-slate-200 dark:border-slate-700" />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input label={t('ownerForm.petName')} required value={animalForm.name} onChange={setAnimal('name')} error={animalErrors.name} />
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  {t('ownerForm.petSpecies')} <span className="text-error-500">*</span>
                </label>
                <select className={selectClass} value={animalForm.species} onChange={setAnimal('species')}>
                  {SPECIES_VALUES.map((s) => (
                    <option key={s} value={s}>{emojiFor(s)} {t(`species.${s}`)}</option>
                  ))}
                </select>
              </div>
              <Input label={t('ownerForm.petBreed')} value={animalForm.breed} onChange={setAnimal('breed')} error={animalErrors.breed} />
            </div>
          </>
        )}
      </ModalContent>
      <ModalFooter>
        <Button variant="ghost" onClick={onClose} disabled={saving}>{t('ownerForm.cancel')}</Button>
        <Button variant="medical" onClick={submit} disabled={saving}>
          {saving ? t('ownerForm.saving') : initial ? t('ownerForm.save') : t('ownerForm.create')}
        </Button>
      </ModalFooter>
    </Modal>
  );
};

// ---------------------------------------------------------------------------
// Animal form modal
// ---------------------------------------------------------------------------
const AnimalFormModal: React.FC<{
  open: boolean;
  ownerId: number | null;
  ownerName?: string;
  initial?: AnimalPatient | null;
  onClose: () => void;
  onSaved: () => void;
}> = ({ open, ownerId, ownerName, initial, onClose, onSaved }) => {
  const { t } = useTranslation('patients');
  const [form, setForm] = useState<AnimalPatientWrite>({
    owner_id: ownerId ?? 0, name: '', species: 'canine',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  // Standalone "new patient" flow: pick the owner inline when none is preset.
  const [pickedOwnerName, setPickedOwnerName] = useState<string>('');
  const needsOwnerPick = !initial && !ownerId;

  useEffect(() => {
    if (open) {
      setErrors({});
      setPickedOwnerName('');
      setForm({
        owner_id: initial?.owner?.id ?? ownerId ?? 0,
        name: initial?.name ?? '',
        species: (initial?.species as Species) ?? 'canine',
        breed: initial?.breed ?? '',
        date_of_birth: initial?.date_of_birth ?? '',
        sex: (initial?.sex as AnimalSex) ?? '',
        weight_kg: initial?.weight_kg ?? '',
        microchip_id: initial?.microchip_id ?? '',
        color: initial?.color ?? '',
        insurance_provider: initial?.insurance_provider ?? '',
        insurance_policy_number: initial?.insurance_policy_number ?? '',
        insurance_expiry: initial?.insurance_expiry ?? '',
      });
    }
  }, [open, initial, ownerId]);

  const set = (k: keyof AnimalPatientWrite) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
      setForm((f) => ({ ...f, [k]: e.target.value }));
      setErrors((prev) => (prev[k] ? { ...prev, [k]: '' } : prev));
    };

  const submit = async () => {
    if (!form.owner_id) { setErrors((p) => ({ ...p, owner_id: t('animalForm.ownerRequired') })); return; }
    const errs = zodFieldErrors(animalPatientSchema, form);
    if (Object.keys(errs).length) { setErrors(errs); return; }
    const payload: AnimalPatientWrite = {
      ...form,
      date_of_birth: form.date_of_birth || null,
      weight_kg: form.weight_kg || null,
      insurance_expiry: form.insurance_expiry || null,
    };
    setSaving(true);
    try {
      if (initial) {
        await apiClient.updateAnimal(initial.id, payload);
        toast.success(t('animalForm.updated'));
      } else {
        await apiClient.createAnimal(payload);
        toast.success(t('animalForm.created'));
      }
      onSaved();
      onClose();
    } catch {
      toast.error(t('animalForm.failed'));
    } finally {
      setSaving(false);
    }
  };

  const selectClass =
    'w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-medical bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-medical-500';

  const title = initial
    ? t('animalForm.editTitle')
    : `${t('animalForm.newTitle')}${ownerName ? ` · ${ownerName}` : ''}`;

  return (
    <Modal isOpen={open} onClose={onClose} title={title} size="lg">
      <ModalContent>
        {/* Standalone flow: choose the owner inline before the patient fields. */}
        {needsOwnerPick && (
          <div className="mb-4">
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              {t('animalForm.selectOwner')} <span className="text-error-500">*</span>
            </label>
            {form.owner_id && pickedOwnerName ? (
              <div className="flex items-center justify-between rounded-medical border border-slate-200 dark:border-slate-700 px-3 py-2">
                <span className="font-medium text-slate-800 dark:text-slate-100">{pickedOwnerName}</span>
                <Button variant="ghost" size="sm" onClick={() => { setForm((f) => ({ ...f, owner_id: 0 })); setPickedOwnerName(''); }}>
                  {t('animalForm.changeOwner')}
                </Button>
              </div>
            ) : (
              <OwnerPicker autoFocus onSelect={(o) => {
                setForm((f) => ({ ...f, owner_id: o.id }));
                setPickedOwnerName(`${o.first_name} ${o.last_name}`);
                setErrors((p) => ({ ...p, owner_id: '' }));
              }} />
            )}
            {errors.owner_id && <p className="mt-1 text-sm text-error-600 dark:text-error-400">{errors.owner_id}</p>}
          </div>
        )}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Input label={t('animalForm.name')} required value={form.name} onChange={set('name')} error={errors.name} />
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              {t('animalForm.species')} <span className="text-error-500">*</span>
            </label>
            <select className={selectClass} value={form.species} onChange={set('species')}>
              {SPECIES_VALUES.map((s) => <option key={s} value={s}>{emojiFor(s)} {t(`species.${s}`)}</option>)}
            </select>
          </div>
          <Input label={t('animalForm.breed')} value={form.breed} onChange={set('breed')} />
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">{t('animalForm.sex')}</label>
            <select className={selectClass} value={form.sex} onChange={set('sex')}>
              {SEX_VALUES.map((s) => <option key={s || 'blank'} value={s}>{t(`sex.${s || 'blank'}`)}</option>)}
            </select>
          </div>
          <Input label={t('animalForm.dob')} type="date" value={form.date_of_birth ?? ''} onChange={set('date_of_birth')} error={errors.date_of_birth} />
          <Input label={t('animalForm.weight')} type="number" step="0.01" value={form.weight_kg ?? ''} onChange={set('weight_kg')} error={errors.weight_kg} />
          <Input label={t('animalForm.microchip')} value={form.microchip_id} onChange={set('microchip_id')} error={errors.microchip_id} />
          <Input label={t('animalForm.color')} value={form.color} onChange={set('color')} />
          <Input label={t('animalForm.insuranceProvider')} value={form.insurance_provider ?? ''} onChange={set('insurance_provider')} />
          <Input label={t('animalForm.insurancePolicy')} value={form.insurance_policy_number ?? ''} onChange={set('insurance_policy_number')} />
          <Input label={t('animalForm.insuranceExpiry')} type="date" value={form.insurance_expiry ?? ''} onChange={set('insurance_expiry')} />
        </div>
      </ModalContent>
      <ModalFooter>
        <Button variant="ghost" onClick={onClose} disabled={saving}>{t('animalForm.cancel')}</Button>
        <Button variant="medical" onClick={submit} disabled={saving}>
          {saving ? t('animalForm.saving') : initial ? t('animalForm.save') : t('animalForm.create')}
        </Button>
      </ModalFooter>
    </Modal>
  );
};

// ---------------------------------------------------------------------------
// VHS panel — trend chart + add form (measurement, human-in-the-loop)
// ---------------------------------------------------------------------------
const INTERP_CLS: Record<string, string> = {
  within_range: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  above_range: 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200',
  below_range: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  unknown: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
};

const VHSPanel: React.FC<{ animal: AnimalPatient; onChanged: () => void }> = ({ animal, onChanged }) => {
  const { t } = useTranslation('patients');
  const trend = animal.vhs_trend ?? [];
  const [adding, setAdding] = useState(false);
  const [saving, setSaving] = useState(false);
  const [confirmId, setConfirmId] = useState<number | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [form, setForm] = useState({
    measured_on: new Date().toISOString().slice(0, 10),
    long_axis_vertebrae: '',
    short_axis_vertebrae: '',
    notes: '',
  });

  const interpLabel = (k: string) => t(`vhs.interp.${k}`);

  const ref = animal.species === 'canine' ? { low: 8.5, high: 10.6 }
    : animal.species === 'feline' ? { low: 6.7, high: 8.1 } : null;

  const liveVHS = (() => {
    const l = parseFloat(form.long_axis_vertebrae);
    const s = parseFloat(form.short_axis_vertebrae);
    return (isFinite(l) && isFinite(s)) ? (l + s).toFixed(1) : '—';
  })();

  const submit = async () => {
    const errs = zodFieldErrors(vhsSchema, form);
    if (Object.keys(errs).length) { setErrors(errs); return; }
    const l = parseFloat(form.long_axis_vertebrae);
    const s = parseFloat(form.short_axis_vertebrae);
    setSaving(true);
    try {
      const payload: VHSMeasurementWrite = {
        animal_patient_id: animal.id,
        measured_on: form.measured_on,
        long_axis_vertebrae: l,
        short_axis_vertebrae: s,
        method: 'manual',
        notes: form.notes,
      };
      await apiClient.createVHSMeasurement(payload);
      toast.success(t('vhs.recorded', { value: (l + s).toFixed(1) }));
      setForm({ measured_on: new Date().toISOString().slice(0, 10), long_axis_vertebrae: '', short_axis_vertebrae: '', notes: '' });
      setAdding(false);
      onChanged();
    } catch {
      toast.error(t('vhs.saveFailed'));
    } finally {
      setSaving(false);
    }
  };

  const remove = async (id: number) => {
    try { await apiClient.deleteVHSMeasurement(id); toast.success(t('vhs.deleted')); onChanged(); }
    catch { toast.error(t('vhs.deleteFailed')); }
  };

  const latest = trend.length ? trend[trend.length - 1] : null;

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h4 className="font-semibold text-slate-800 dark:text-slate-200 flex items-center gap-2">
          <Heart className="w-4 h-4 text-medical-500" /> {t('vhs.title')}
        </h4>
        <Button variant="ghost" size="sm" leftIcon={Plus} onClick={() => setAdding((v) => !v)}>
          {adding ? t('vhs.cancel') : t('vhs.add')}
        </Button>
      </div>

      {ref && (
        <p className="text-xs text-slate-400 mb-2">
          {t('vhs.typicalRange', { species: t(`species.${animal.species}`), low: ref.low, high: ref.high })}
        </p>
      )}

      {/* Add form */}
      {adding && (
        <div className="rounded-lg border border-slate-200 dark:border-slate-700 p-3 mb-3 space-y-3">
          <AiDisclaimer />
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <Input label={t('vhs.date')} type="date" value={form.measured_on} error={errors.measured_on}
              onChange={(e) => { setForm((f) => ({ ...f, measured_on: e.target.value })); setErrors((p) => ({ ...p, measured_on: '' })); }} />
            <Input label={t('vhs.longAxis')} type="number" step="0.1" value={form.long_axis_vertebrae} error={errors.long_axis_vertebrae}
              onChange={(e) => { setForm((f) => ({ ...f, long_axis_vertebrae: e.target.value })); setErrors((p) => ({ ...p, long_axis_vertebrae: '' })); }} />
            <Input label={t('vhs.shortAxis')} type="number" step="0.1" value={form.short_axis_vertebrae} error={errors.short_axis_vertebrae}
              onChange={(e) => { setForm((f) => ({ ...f, short_axis_vertebrae: e.target.value })); setErrors((p) => ({ ...p, short_axis_vertebrae: '' })); }} />
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">{t('vhs.value')}</label>
              <div className="px-3 py-2 rounded-medical bg-slate-100 dark:bg-slate-800 font-bold text-slate-900 dark:text-white">{liveVHS}</div>
            </div>
          </div>
          <Input label={t('vhs.notes')} value={form.notes} onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))} />
          <div className="flex justify-end">
            <Button variant="medical" onClick={submit} disabled={saving}>
              {saving ? t('vhs.saving') : t('vhs.save')}
            </Button>
          </div>
        </div>
      )}

      {/* Trend chart */}
      {trend.length > 0 ? (
        <>
          {latest && (
            <div className="flex items-baseline gap-2 mb-2">
              <span className="text-2xl font-bold text-slate-900 dark:text-white">{latest.vhs.toFixed(1)}</span>
              <span className="text-xs text-slate-400">{t('vhs.latest')} ({latest.measured_on})</span>
              <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${INTERP_CLS[latest.interpretation]}`}>
                {interpLabel(latest.interpretation)}
              </span>
            </div>
          )}
          {trend.length > 1 && (
            <div className="h-40 w-full mb-3">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trend} margin={{ top: 5, right: 10, bottom: 5, left: -20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  {ref && <ReferenceArea y1={ref.low} y2={ref.high} fill="#10b981" fillOpacity={0.08} />}
                  <XAxis dataKey="measured_on" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} domain={['auto', 'auto']} />
                  <Tooltip />
                  <Line type="monotone" dataKey="vhs" stroke="#10b981" strokeWidth={2} dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
          <ul className="divide-y divide-slate-100 dark:divide-slate-700 text-sm">
            {[...trend].reverse().map((m) => (
              <li key={m.id} className="flex items-center justify-between py-1.5">
                <span className="text-slate-700 dark:text-slate-200">
                  <strong>{m.vhs.toFixed(1)}</strong> · {m.measured_on}
                  <span className="text-slate-400"> (L {m.long_axis_vertebrae} + S {m.short_axis_vertebrae})</span>
                </span>
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-0.5 rounded-full text-xs ${INTERP_CLS[m.interpretation]}`}>
                    {interpLabel(m.interpretation)}
                  </span>
                  <button className="p-1 text-slate-400 hover:text-error-500" onClick={() => setConfirmId(m.id)} aria-label={t('vhs.deleteConfirm')}>
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </>
      ) : (
        !adding && <p className="text-sm text-slate-400">{t('vhs.noMeasurements')}</p>
      )}

      <ConfirmDialog
        open={confirmId != null}
        message={t('vhs.deleteConfirm')}
        onCancel={() => setConfirmId(null)}
        onConfirm={() => { const id = confirmId; setConfirmId(null); if (id != null) remove(id); }}
        danger
      />
    </div>
  );
};

// ---------------------------------------------------------------------------
// Vaccination panel — mirrors VHSPanel pattern
// ---------------------------------------------------------------------------
const VaccinationPanel: React.FC<{ animalId: number }> = ({ animalId }) => {
  const { t } = useTranslation('patients');
  const [records, setRecords] = useState<VaccinationRecord[]>([]);
  const [adding, setAdding] = useState(false);
  const [saving, setSaving] = useState(false);
  const [confirmId, setConfirmId] = useState<number | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [form, setForm] = useState<Omit<VaccinationRecordWrite, 'animal_patient_id'>>({
    vaccine_name: '', administered_on: new Date().toISOString().slice(0, 10),
  });

  const load = useCallback(() => {
    apiClient.getVaccinations(animalId).then(setRecords).catch(() => {});
  }, [animalId]);

  useEffect(() => { load(); }, [load]);

  const submit = async () => {
    const errs = zodFieldErrors(vaccinationSchema, form);
    if (Object.keys(errs).length) { setErrors(errs); return; }
    setSaving(true);
    try {
      await apiClient.createVaccination({ animal_patient_id: animalId, ...form });
      toast.success(t('vaccinationForm.created'));
      setForm({ vaccine_name: '', administered_on: new Date().toISOString().slice(0, 10) });
      setAdding(false);
      load();
    } catch { toast.error(t('vaccinationForm.failed')); }
    finally { setSaving(false); }
  };

  const remove = async (id: number) => {
    try { await apiClient.deleteVaccination(id); toast.success(t('vaccinationForm.deleted')); load(); }
    catch { toast.error(t('vaccinationForm.deleteFailed')); }
  };

  const today = new Date();
  const daysUntilDue = (due: string) => Math.ceil((new Date(due).getTime() - today.getTime()) / 86400000);

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h4 className="font-semibold text-slate-800 dark:text-slate-200">{t('tabs.vaccinations')}</h4>
        <Button variant="ghost" size="sm" leftIcon={Plus} onClick={() => setAdding(v => !v)}>
          {adding ? t('vaccinationForm.cancel') : t('vaccinationForm.addVaccination')}
        </Button>
      </div>
      {adding && (
        <div className="rounded-lg border border-slate-200 dark:border-slate-700 p-3 mb-3 space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Input label={t('vaccinationForm.vaccineName')} required value={form.vaccine_name}
              error={errors.vaccine_name}
              onChange={e => { setForm(f => ({ ...f, vaccine_name: e.target.value })); setErrors(p => ({ ...p, vaccine_name: '' })); }} />
            <Input label={t('vaccinationForm.administeredOn')} type="date" value={form.administered_on}
              error={errors.administered_on}
              onChange={e => { setForm(f => ({ ...f, administered_on: e.target.value })); setErrors(p => ({ ...p, administered_on: '' })); }} />
            <Input label={t('vaccinationForm.nextDueOn')} type="date" value={form.next_due_on ?? ''}
              onChange={e => setForm(f => ({ ...f, next_due_on: e.target.value || undefined }))} />
            <Input label={t('vaccinationForm.batchNumber')} value={form.batch_number ?? ''}
              onChange={e => setForm(f => ({ ...f, batch_number: e.target.value }))} />
          </div>
          <div className="flex justify-end">
            <Button variant="medical" onClick={submit} disabled={saving}>
              {saving ? t('vaccinationForm.saving') : t('vaccinationForm.save')}
            </Button>
          </div>
        </div>
      )}
      {records.length === 0 && !adding
        ? <p className="text-sm text-slate-400">{t('vaccinationForm.noVaccinations')}</p>
        : (
          <ul className="divide-y divide-slate-100 dark:divide-slate-700 text-sm">
            {records.map(r => {
              const days = r.next_due_on ? daysUntilDue(r.next_due_on) : null;
              return (
                <li key={r.id} className="flex items-center justify-between py-2">
                  <div>
                    <span className="font-medium text-slate-800 dark:text-slate-100">{r.vaccine_name}</span>
                    <span className="text-slate-400 ml-2">· {r.administered_on}</span>
                    {r.next_due_on && (
                      <span className={`ml-2 px-2 py-0.5 rounded-full text-xs ${days !== null && days < 0 ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300' : days !== null && days <= 30 ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300' : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'}`}>
                        {days !== null && days < 0 ? t('vaccinationForm.overdue') : t('vaccinationForm.dueIn', { days })}
                      </span>
                    )}
                  </div>
                  <button className="p-1 text-slate-400 hover:text-error-500" onClick={() => setConfirmId(r.id)}>
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      <ConfirmDialog open={confirmId != null} message={t('vaccinationForm.deleteConfirm')}
        onCancel={() => setConfirmId(null)}
        onConfirm={() => { const id = confirmId; setConfirmId(null); if (id != null) remove(id); }}
        danger />
    </div>
  );
};

// ---------------------------------------------------------------------------
// Weight panel — mirrors VHSPanel pattern
// ---------------------------------------------------------------------------
const WeightPanel: React.FC<{ animalId: number }> = ({ animalId }) => {
  const { t } = useTranslation('patients');
  const [records, setRecords] = useState<WeightRecord[]>([]);
  const [adding, setAdding] = useState(false);
  const [saving, setSaving] = useState(false);
  const [confirmId, setConfirmId] = useState<number | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [form, setForm] = useState<Omit<WeightRecordWrite, 'animal_patient_id'>>({
    measured_on: new Date().toISOString().slice(0, 10), weight_kg: '',
  });

  const load = useCallback(() => {
    apiClient.getWeightRecords(animalId).then(setRecords).catch(() => {});
  }, [animalId]);

  useEffect(() => { load(); }, [load]);

  const submit = async () => {
    const errs = zodFieldErrors(weightRecordSchema, form);
    if (Object.keys(errs).length) { setErrors(errs); return; }
    setSaving(true);
    try {
      await apiClient.createWeightRecord({ animal_patient_id: animalId, ...form });
      toast.success(t('weightForm.created'));
      setForm({ measured_on: new Date().toISOString().slice(0, 10), weight_kg: '' });
      setAdding(false);
      load();
    } catch { toast.error(t('weightForm.failed')); }
    finally { setSaving(false); }
  };

  const remove = async (id: number) => {
    try { await apiClient.deleteWeightRecord(id); toast.success(t('weightForm.deleted')); load(); }
    catch { toast.error(t('weightForm.deleteFailed')); }
  };

  const chartData = [...records].sort((a, b) => a.measured_on.localeCompare(b.measured_on));
  const latest = chartData.at(-1);

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h4 className="font-semibold text-slate-800 dark:text-slate-200 flex items-center gap-2">
          {t('tabs.weight')}
          {latest && <span className="text-sm font-normal text-slate-500">{t('weightForm.latestWeight')}: <strong className="text-slate-900 dark:text-white">{latest.weight_kg} kg</strong></span>}
        </h4>
        <Button variant="ghost" size="sm" leftIcon={Plus} onClick={() => setAdding(v => !v)}>
          {adding ? t('weightForm.cancel') : t('weightForm.addWeight')}
        </Button>
      </div>
      {adding && (
        <div className="rounded-lg border border-slate-200 dark:border-slate-700 p-3 mb-3 space-y-3">
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <Input label={t('weightForm.measuredOn')} type="date" value={form.measured_on}
              onChange={e => { setForm(f => ({ ...f, measured_on: e.target.value })); setErrors(p => ({ ...p, measured_on: '' })); }} />
            <Input label={t('weightForm.weightKg')} type="number" step="0.1" required value={form.weight_kg}
              error={errors.weight_kg}
              onChange={e => { setForm(f => ({ ...f, weight_kg: e.target.value })); setErrors(p => ({ ...p, weight_kg: '' })); }} />
            <Input label={t('weightForm.bcs')} type="number" min="1" max="9" value={form.bcs ?? ''}
              error={errors.bcs}
              onChange={e => setForm(f => ({ ...f, bcs: e.target.value ? Number(e.target.value) : undefined }))} />
          </div>
          <div className="flex justify-end">
            <Button variant="medical" onClick={submit} disabled={saving}>
              {saving ? t('weightForm.saving') : t('weightForm.save')}
            </Button>
          </div>
        </div>
      )}
      {chartData.length > 1 && (
        <div className="h-36 w-full mb-3">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 5, right: 10, bottom: 5, left: -20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="measured_on" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} domain={['auto', 'auto']} />
              <Tooltip />
              <Line type="monotone" dataKey="weight_kg" stroke="#6366f1" strokeWidth={2} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
      {records.length === 0 && !adding
        ? <p className="text-sm text-slate-400">{t('weightForm.noWeightRecords')}</p>
        : (
          <ul className="divide-y divide-slate-100 dark:divide-slate-700 text-sm">
            {[...records].map(r => (
              <li key={r.id} className="flex items-center justify-between py-1.5">
                <span className="text-slate-700 dark:text-slate-200">
                  <strong>{r.weight_kg} kg</strong> · {r.measured_on}
                  {r.bcs != null && <span className="ml-2 text-slate-400">BCS {r.bcs}/9</span>}
                </span>
                <button className="p-1 text-slate-400 hover:text-error-500" onClick={() => setConfirmId(r.id)}>
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </li>
            ))}
          </ul>
        )}
      <ConfirmDialog open={confirmId != null} message={t('weightForm.deleteConfirm')}
        onCancel={() => setConfirmId(null)}
        onConfirm={() => { const id = confirmId; setConfirmId(null); if (id != null) remove(id); }}
        danger />
    </div>
  );
};

// ---------------------------------------------------------------------------
// Visit panel
// ---------------------------------------------------------------------------
const selectCls = 'w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-medical bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-medical-500 text-sm';

const VisitPanel: React.FC<{ animalId: number }> = ({ animalId }) => {
  const { t } = useTranslation('patients');
  const [visits, setVisits] = useState<ClinicalVisit[]>([]);
  const [adding, setAdding] = useState(false);
  const [saving, setSaving] = useState(false);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const [confirmId, setConfirmId] = useState<number | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [form, setForm] = useState<Omit<ClinicalVisitWrite, 'animal_patient_id'>>({
    visit_date: new Date().toISOString().slice(0, 16),
    visit_type: 'consultation',
  });

  const load = useCallback(() => {
    apiClient.getVisits(animalId).then(setVisits).catch(() => {});
  }, [animalId]);

  useEffect(() => { load(); }, [load]);

  const toggleExpand = (id: number) => setExpanded(prev => {
    const next = new Set(prev);
    next.has(id) ? next.delete(id) : next.add(id);
    return next;
  });

  const submit = async () => {
    const errs = zodFieldErrors(clinicalVisitSchema, form);
    if (Object.keys(errs).length) { setErrors(errs); return; }
    setSaving(true);
    try {
      await apiClient.createVisit({ animal_patient_id: animalId, ...form });
      toast.success(t('visitForm.created'));
      setForm({ visit_date: new Date().toISOString().slice(0, 16), visit_type: 'consultation' });
      setAdding(false);
      load();
    } catch { toast.error(t('visitForm.failed')); }
    finally { setSaving(false); }
  };

  const remove = async (id: number) => {
    try { await apiClient.deleteVisit(id); toast.success(t('visitForm.deleted')); load(); }
    catch { toast.error(t('visitForm.deleteFailed')); }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h4 className="font-semibold text-slate-800 dark:text-slate-200">{t('tabs.visits')}</h4>
        <Button variant="ghost" size="sm" leftIcon={Plus} onClick={() => setAdding(v => !v)}>
          {adding ? t('visitForm.cancel') : t('visitForm.addVisit')}
        </Button>
      </div>
      {adding && (
        <div className="rounded-lg border border-slate-200 dark:border-slate-700 p-3 mb-3 space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">{t('visitForm.visitType')}</label>
              <select className={selectCls} value={form.visit_type}
                onChange={e => setForm(f => ({ ...f, visit_type: e.target.value as VisitType }))}>
                {VISIT_TYPE_VALUES.map(v => (
                  <option key={v} value={v}>{t(`visitForm.visitTypes.${v}`)}</option>
                ))}
              </select>
            </div>
            <Input label={t('visitForm.visitDate')} type="datetime-local" required
              value={form.visit_date} error={errors.visit_date}
              onChange={e => { setForm(f => ({ ...f, visit_date: e.target.value })); setErrors(p => ({ ...p, visit_date: '' })); }} />
            <Input label={t('visitForm.weightKg')} type="number" step="0.1" value={form.weight_kg ?? ''}
              error={errors.weight_kg}
              onChange={e => setForm(f => ({ ...f, weight_kg: e.target.value || undefined }))} />
            <Input label={t('visitForm.temperatureC')} type="number" step="0.1" value={form.temperature_celsius ?? ''}
              error={errors.temperature_celsius}
              onChange={e => setForm(f => ({ ...f, temperature_celsius: e.target.value || undefined }))} />
          </div>
          <Input label={t('visitForm.chiefComplaint')} value={form.chief_complaint ?? ''}
            onChange={e => setForm(f => ({ ...f, chief_complaint: e.target.value }))} />
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {(['subjective', 'objective', 'assessment', 'plan'] as const).map(field => (
              <div key={field}>
                <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1 uppercase tracking-wide">{t(`visitForm.${field}`)}</label>
                <textarea
                  className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-medical bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-medical-500 resize-none"
                  rows={3}
                  value={(form as any)[field] ?? ''}
                  onChange={e => setForm(f => ({ ...f, [field]: e.target.value }))}
                />
              </div>
            ))}
          </div>
          <div className="flex justify-end">
            <Button variant="medical" onClick={submit} disabled={saving}>
              {saving ? t('visitForm.saving') : t('visitForm.save')}
            </Button>
          </div>
        </div>
      )}
      {visits.length === 0 && !adding
        ? <p className="text-sm text-slate-400">{t('visitForm.noVisits')}</p>
        : (
          <ul className="divide-y divide-slate-100 dark:divide-slate-700 text-sm">
            {visits.map(v => {
              const open = expanded.has(v.id);
              return (
                <li key={v.id} className="py-2">
                  <div className="flex items-center justify-between">
                    <button className="flex items-center gap-2 text-left flex-1" onClick={() => toggleExpand(v.id)}>
                      {open ? <ChevronDown className="w-3.5 h-3.5 text-slate-400" /> : <ChevronRight className="w-3.5 h-3.5 text-slate-400" />}
                      <span className="font-medium text-slate-800 dark:text-slate-100">{t(`visitForm.visitTypes.${v.visit_type}`)}</span>
                      <span className="text-slate-400">{new Date(v.visit_date).toLocaleDateString()}</span>
                      {v.chief_complaint && <span className="text-slate-500 truncate max-w-xs">· {v.chief_complaint}</span>}
                    </button>
                    <button className="p-1 text-slate-400 hover:text-error-500" onClick={() => setConfirmId(v.id)}>
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                  {open && (
                    <div className="mt-2 pl-6 space-y-2 text-sm text-slate-700 dark:text-slate-300">
                      {v.weight_kg && <p><strong>{t('visitForm.weightKg')}:</strong> {v.weight_kg} kg {v.temperature_celsius && `· ${v.temperature_celsius} °C`}</p>}
                      {(['subjective', 'objective', 'assessment', 'plan'] as const).filter(f => (v as any)[f]).map(field => (
                        <div key={field}>
                          <p className="text-xs uppercase tracking-wide text-slate-400">{t(`visitForm.${field}`)}</p>
                          <p>{(v as any)[field]}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      <ConfirmDialog open={confirmId != null} message={t('visitForm.deleteConfirm')}
        onCancel={() => setConfirmId(null)}
        onConfirm={() => { const id = confirmId; setConfirmId(null); if (id != null) remove(id); }}
        danger />
    </div>
  );
};

// ---------------------------------------------------------------------------
// Appointment panel
// ---------------------------------------------------------------------------
const AppointmentPanel: React.FC<{ animalId: number }> = ({ animalId }) => {
  const { t } = useTranslation('patients');
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [adding, setAdding] = useState(false);
  const [saving, setSaving] = useState(false);
  const [confirmId, setConfirmId] = useState<number | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [form, setForm] = useState<Omit<AppointmentWrite, 'animal_patient_id'>>({
    appointment_type: 'consultation',
    scheduled_at: '',
    duration_minutes: 30,
  });

  const STATUS_CLS: Record<string, string> = {
    pending:   'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
    confirmed: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
    completed: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
    cancelled: 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400',
    no_show:   'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-300',
  };

  const load = useCallback(() => {
    apiClient.getAppointments({ animal: animalId }).then(setAppointments).catch(() => {});
  }, [animalId]);

  useEffect(() => { load(); }, [load]);

  const submit = async () => {
    const errs = zodFieldErrors(appointmentSchema, form);
    if (Object.keys(errs).length) { setErrors(errs); return; }
    setSaving(true);
    try {
      await apiClient.createAppointment({ animal_patient_id: animalId, ...form });
      toast.success(t('appointmentForm.created'));
      setForm({ appointment_type: 'consultation', scheduled_at: '', duration_minutes: 30 });
      setAdding(false);
      load();
    } catch { toast.error(t('appointmentForm.failed')); }
    finally { setSaving(false); }
  };

  const complete = async (id: number) => {
    try {
      await apiClient.completeAppointment(id);
      toast.success(t('appointmentForm.completed'));
      load();
    } catch { toast.error(t('appointmentForm.completeFailed', { ns: 'calendar' })); }
  };

  const remove = async (id: number) => {
    try {
      await apiClient.updateAppointment(id, { appointment_type: appointments.find(a => a.id === id)?.appointment_type ?? 'consultation' });
      await apiClient.deleteAppointment(id);
      toast.success(t('appointmentForm.deleted'));
      load();
    } catch { toast.error(t('appointmentForm.deleteFailed')); }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h4 className="font-semibold text-slate-800 dark:text-slate-200">{t('tabs.appointments')}</h4>
        <Button variant="ghost" size="sm" leftIcon={Plus} onClick={() => setAdding(v => !v)}>
          {adding ? t('appointmentForm.cancel') : t('appointmentForm.addAppointment')}
        </Button>
      </div>
      {adding && (
        <div className="rounded-lg border border-slate-200 dark:border-slate-700 p-3 mb-3 space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">{t('appointmentForm.appointmentType')}</label>
              <select className={selectCls} value={form.appointment_type}
                onChange={e => setForm(f => ({ ...f, appointment_type: e.target.value as VisitType }))}>
                {VISIT_TYPE_VALUES.map(v => (
                  <option key={v} value={v}>{t(`visitForm.visitTypes.${v}`)}</option>
                ))}
              </select>
            </div>
            <Input label={t('appointmentForm.scheduledAt')} type="datetime-local" required
              value={form.scheduled_at} error={errors.scheduled_at}
              onChange={e => { setForm(f => ({ ...f, scheduled_at: e.target.value })); setErrors(p => ({ ...p, scheduled_at: '' })); }} />
            <Input label={t('appointmentForm.durationMinutes')} type="number" min="5" max="480"
              value={form.duration_minutes ?? 30}
              onChange={e => setForm(f => ({ ...f, duration_minutes: Number(e.target.value) }))} />
          </div>
          <div className="flex justify-end">
            <Button variant="medical" onClick={submit} disabled={saving}>
              {saving ? t('appointmentForm.saving') : t('appointmentForm.save')}
            </Button>
          </div>
        </div>
      )}
      {appointments.length === 0 && !adding
        ? <p className="text-sm text-slate-400">{t('appointmentForm.noAppointments')}</p>
        : (
          <ul className="divide-y divide-slate-100 dark:divide-slate-700 text-sm">
            {appointments.map(a => (
              <li key={a.id} className="flex items-center justify-between py-2">
                <div>
                  <span className="font-medium text-slate-800 dark:text-slate-100">{t(`visitForm.visitTypes.${a.appointment_type}`)}</span>
                  <span className="text-slate-400 ml-2">· {new Date(a.scheduled_at).toLocaleString()}</span>
                  <span className={`ml-2 px-2 py-0.5 rounded-full text-xs ${STATUS_CLS[a.status] ?? ''}`}>
                    {t(`appointmentForm.statuses.${a.status}`)}
                  </span>
                </div>
                <div className="flex items-center gap-1">
                  {(a.status === 'pending' || a.status === 'confirmed') && (
                    <Button variant="ghost" size="sm" onClick={() => complete(a.id)}>
                      {t('appointmentForm.complete')}
                    </Button>
                  )}
                  <button className="p-1 text-slate-400 hover:text-error-500" onClick={() => setConfirmId(a.id)}>
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      <ConfirmDialog open={confirmId != null} message={t('appointmentForm.deleteConfirm')}
        onCancel={() => setConfirmId(null)}
        onConfirm={() => { const id = confirmId; setConfirmId(null); if (id != null) remove(id); }}
        danger />
    </div>
  );
};

// ---------------------------------------------------------------------------
// Prescription panel
// ---------------------------------------------------------------------------
const ROUTE_VALUES = ['oral', 'topical', 'injection_sc', 'injection_im', 'injection_iv', 'inhalation', 'ophthalmic', 'otic', 'other'] as const;

const PrescriptionPanel: React.FC<{ animalId: number }> = ({ animalId }) => {
  const { t } = useTranslation('patients');
  const [records, setRecords] = useState<Prescription[]>([]);
  const [adding, setAdding] = useState(false);
  const [saving, setSaving] = useState(false);
  const [confirmId, setConfirmId] = useState<number | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [form, setForm] = useState<Omit<PrescriptionWrite, 'animal_patient_id'>>({
    medication_name: '', prescribed_on: new Date().toISOString().slice(0, 10),
  });

  const load = useCallback(() => { apiClient.getPrescriptions(animalId).then(setRecords).catch(() => {}); }, [animalId]);
  useEffect(() => { load(); }, [load]);

  const submit = async () => {
    const errs = zodFieldErrors(prescriptionSchema, form);
    if (Object.keys(errs).length) { setErrors(errs); return; }
    setSaving(true);
    try {
      await apiClient.createPrescription({ animal_patient_id: animalId, ...form });
      toast.success(t('prescriptionForm.created'));
      setForm({ medication_name: '', prescribed_on: new Date().toISOString().slice(0, 10) });
      setAdding(false); load();
    } catch { toast.error(t('prescriptionForm.failed')); }
    finally { setSaving(false); }
  };

  const remove = async (id: number) => {
    try { await apiClient.deletePrescription(id); toast.success(t('prescriptionForm.deleted')); load(); }
    catch { toast.error(t('prescriptionForm.deleteFailed')); }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h4 className="font-semibold text-slate-800 dark:text-slate-200">{t('tabs.prescriptions')}</h4>
        <Button variant="ghost" size="sm" leftIcon={Plus} onClick={() => setAdding(v => !v)}>
          {adding ? t('prescriptionForm.cancel') : t('prescriptionForm.addPrescription')}
        </Button>
      </div>
      {adding && (
        <div className="rounded-lg border border-slate-200 dark:border-slate-700 p-3 mb-3 space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Input label={t('prescriptionForm.medicationName')} required value={form.medication_name}
              error={errors.medication_name}
              onChange={e => { setForm(f => ({ ...f, medication_name: e.target.value })); setErrors(p => ({ ...p, medication_name: '' })); }} />
            <Input label={t('prescriptionForm.prescribedOn')} type="date" value={form.prescribed_on}
              error={errors.prescribed_on}
              onChange={e => { setForm(f => ({ ...f, prescribed_on: e.target.value })); setErrors(p => ({ ...p, prescribed_on: '' })); }} />
            <Input label={t('prescriptionForm.dose')} value={form.dose ?? ''}
              onChange={e => setForm(f => ({ ...f, dose: e.target.value }))} />
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">{t('prescriptionForm.route')}</label>
              <select className={selectCls} value={form.route ?? ''}
                onChange={e => setForm(f => ({ ...f, route: e.target.value }))}>
                <option value="">—</option>
                {ROUTE_VALUES.map(r => <option key={r} value={r}>{r.replace(/_/g, ' ')}</option>)}
              </select>
            </div>
            <Input label={t('prescriptionForm.frequency')} value={form.frequency ?? ''}
              onChange={e => setForm(f => ({ ...f, frequency: e.target.value }))} />
            <Input label={t('prescriptionForm.durationDays')} type="number" value={form.duration_days ?? ''}
              onChange={e => setForm(f => ({ ...f, duration_days: e.target.value ? Number(e.target.value) : undefined }))} />
          </div>
          <div className="flex justify-end">
            <Button variant="medical" onClick={submit} disabled={saving}>
              {saving ? t('prescriptionForm.saving') : t('prescriptionForm.save')}
            </Button>
          </div>
        </div>
      )}
      {records.length === 0 && !adding
        ? <p className="text-sm text-slate-400">{t('prescriptionForm.noPrescriptions')}</p>
        : (
          <ul className="divide-y divide-slate-100 dark:divide-slate-700 text-sm">
            {records.map(r => (
              <li key={r.id} className="flex items-center justify-between py-2">
                <div>
                  <span className="font-medium text-slate-800 dark:text-slate-100">{r.medication_name}</span>
                  {r.dose && <span className="text-slate-400 ml-2">{r.dose}</span>}
                  {r.frequency && <span className="text-slate-400 ml-2">· {r.frequency}</span>}
                  {r.duration_days && <span className="text-slate-400 ml-2">· {r.duration_days}d</span>}
                  <span className="text-slate-400 ml-2">· {r.prescribed_on}</span>
                </div>
                <button className="p-1 text-slate-400 hover:text-error-500" onClick={() => setConfirmId(r.id)}>
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </li>
            ))}
          </ul>
        )}
      <ConfirmDialog open={confirmId != null} message={t('prescriptionForm.deleteConfirm')}
        onCancel={() => setConfirmId(null)}
        onConfirm={() => { const id = confirmId; setConfirmId(null); if (id != null) remove(id); }}
        danger />
    </div>
  );
};

// ---------------------------------------------------------------------------
// Allergy panel
// ---------------------------------------------------------------------------
const ALLERGEN_TYPES: AllergenType[] = ['drug', 'food', 'environmental', 'contact'];
const ALLERGY_SEVERITIES: AllergySeverity[] = ['mild', 'moderate', 'severe', 'life_threatening'];

const AllergyPanel: React.FC<{ animalId: number }> = ({ animalId }) => {
  const { t } = useTranslation('patients');
  const [records, setRecords] = useState<AllergyRecord[]>([]);
  const [adding, setAdding] = useState(false);
  const [saving, setSaving] = useState(false);
  const [confirmId, setConfirmId] = useState<number | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [form, setForm] = useState<Omit<AllergyRecordWrite, 'animal_patient_id'>>({
    allergen: '', allergen_type: 'drug', severity: 'mild',
  });

  const load = useCallback(() => { apiClient.getAllergies(animalId).then(setRecords).catch(() => {}); }, [animalId]);
  useEffect(() => { load(); }, [load]);

  const SEV_CLS: Record<string, string> = {
    mild: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
    moderate: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
    severe: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
    life_threatening: 'bg-red-200 text-red-800 dark:bg-red-900/60 dark:text-red-200 font-bold',
  };

  const submit = async () => {
    const errs = zodFieldErrors(allergySchema, form);
    if (Object.keys(errs).length) { setErrors(errs); return; }
    setSaving(true);
    try {
      await apiClient.createAllergy({ animal_patient_id: animalId, ...form });
      toast.success(t('allergyForm.created'));
      setForm({ allergen: '', allergen_type: 'drug', severity: 'mild' });
      setAdding(false); load();
    } catch { toast.error(t('allergyForm.failed')); }
    finally { setSaving(false); }
  };

  const remove = async (id: number) => {
    try { await apiClient.deleteAllergy(id); toast.success(t('allergyForm.deleted')); load(); }
    catch { toast.error(t('allergyForm.deleteFailed')); }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h4 className="font-semibold text-slate-800 dark:text-slate-200">{t('tabs.allergies')}</h4>
        <Button variant="ghost" size="sm" leftIcon={Plus} onClick={() => setAdding(v => !v)}>
          {adding ? t('allergyForm.cancel') : t('allergyForm.addAllergy')}
        </Button>
      </div>
      {adding && (
        <div className="rounded-lg border border-slate-200 dark:border-slate-700 p-3 mb-3 space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Input label={t('allergyForm.allergen')} required value={form.allergen}
              error={errors.allergen}
              onChange={e => { setForm(f => ({ ...f, allergen: e.target.value })); setErrors(p => ({ ...p, allergen: '' })); }} />
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">{t('allergyForm.allergenType')}</label>
              <select className={selectCls} value={form.allergen_type}
                onChange={e => setForm(f => ({ ...f, allergen_type: e.target.value as AllergenType }))}>
                {ALLERGEN_TYPES.map(a => <option key={a} value={a}>{t(`allergyForm.allergenTypes.${a}`)}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">{t('allergyForm.severity')}</label>
              <select className={selectCls} value={form.severity}
                onChange={e => setForm(f => ({ ...f, severity: e.target.value as AllergySeverity }))}>
                {ALLERGY_SEVERITIES.map(s => <option key={s} value={s}>{t(`allergyForm.severities.${s}`)}</option>)}
              </select>
            </div>
            <Input label={t('allergyForm.reaction')} value={form.reaction ?? ''}
              onChange={e => setForm(f => ({ ...f, reaction: e.target.value }))} />
          </div>
          <div className="flex justify-end">
            <Button variant="medical" onClick={submit} disabled={saving}>
              {saving ? t('allergyForm.saving') : t('allergyForm.save')}
            </Button>
          </div>
        </div>
      )}
      {records.length === 0 && !adding
        ? <p className="text-sm text-slate-400">{t('allergyForm.noAllergies')}</p>
        : (
          <ul className="divide-y divide-slate-100 dark:divide-slate-700 text-sm">
            {records.map(r => (
              <li key={r.id} className="flex items-center justify-between py-2">
                <div>
                  <span className="font-medium text-slate-800 dark:text-slate-100">{r.allergen}</span>
                  <span className="text-slate-400 ml-2">· {t(`allergyForm.allergenTypes.${r.allergen_type}`)}</span>
                  <span className={`ml-2 px-2 py-0.5 rounded-full text-xs ${SEV_CLS[r.severity] ?? ''}`}>
                    {t(`allergyForm.severities.${r.severity}`)}
                  </span>
                  {r.reaction && <p className="text-xs text-slate-500 mt-0.5">{r.reaction}</p>}
                </div>
                <button className="p-1 text-slate-400 hover:text-error-500" onClick={() => setConfirmId(r.id)}>
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </li>
            ))}
          </ul>
        )}
      <ConfirmDialog open={confirmId != null} message={t('allergyForm.deleteConfirm')}
        onCancel={() => setConfirmId(null)}
        onConfirm={() => { const id = confirmId; setConfirmId(null); if (id != null) remove(id); }}
        danger />
    </div>
  );
};

// ---------------------------------------------------------------------------
// Lab results panel
// ---------------------------------------------------------------------------
const FLAG_CLS: Record<string, string> = {
  N: 'text-green-600 dark:text-green-400',
  L: 'text-blue-600 dark:text-blue-400',
  H: 'text-amber-600 dark:text-amber-400',
  CRITICAL: 'text-red-600 dark:text-red-400 font-bold',
};

const LAB_TYPES_VALS = ['hematology', 'biochemistry', 'urinalysis', 'cytology', 'serology', 'microbiology', 'other'] as const;

const LabResultPanel: React.FC<{ animalId: number }> = ({ animalId }) => {
  const { t } = useTranslation('patients');
  const [records, setRecords] = useState<LabResult[]>([]);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const [adding, setAdding] = useState(false);
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [form, setForm] = useState({
    result_type: 'hematology' as typeof LAB_TYPES_VALS[number],
    panel_name: '', result_date: new Date().toISOString().slice(0, 10), lab_name: '',
  });
  const [importing, setImporting] = useState(false);
  const [importFormat, setImportFormat] = useState<'hl7' | 'fhir'>('hl7');
  const [importText, setImportText] = useState('');
  const [importBusy, setImportBusy] = useState(false);

  const load = useCallback(() => { apiClient.getLabResults(animalId).then(setRecords).catch(() => {}); }, [animalId]);
  useEffect(() => { load(); }, [load]);

  const submitImport = async () => {
    if (!importText.trim()) return;
    setImportBusy(true);
    try {
      if (importFormat === 'hl7') {
        await apiClient.importLabHl7(animalId, importText);
      } else {
        let payload: unknown;
        try { payload = JSON.parse(importText); }
        catch { toast.error(t('labForm.import.invalidJson')); setImportBusy(false); return; }
        await apiClient.importLabFhir(animalId, payload);
      }
      toast.success(t('labForm.import.imported'));
      setImportText(''); setImporting(false); load();
    } catch { toast.error(t('labForm.import.failed')); }
    finally { setImportBusy(false); }
  };

  const toggleExpand = (id: number) => setExpanded(prev => {
    const next = new Set(prev); next.has(id) ? next.delete(id) : next.add(id); return next;
  });

  const submit = async () => {
    const errs = zodFieldErrors(labResultSchema, form);
    if (Object.keys(errs).length) { setErrors(errs); return; }
    setSaving(true);
    try {
      await apiClient.createLabResult({ animal_patient_id: animalId, result_data: {}, ...form });
      toast.success(t('labForm.created'));
      setForm({ result_type: 'hematology', panel_name: '', result_date: new Date().toISOString().slice(0, 10), lab_name: '' });
      setAdding(false); load();
    } catch { toast.error(t('labForm.failed')); }
    finally { setSaving(false); }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h4 className="font-semibold text-slate-800 dark:text-slate-200">{t('tabs.labs')}</h4>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" leftIcon={Upload} onClick={() => setImporting(v => !v)}>
            {importing ? t('labForm.import.cancel') : t('labForm.import.button')}
          </Button>
          <Button variant="ghost" size="sm" leftIcon={Plus} onClick={() => setAdding(v => !v)}>
            {adding ? t('labForm.cancel') : t('labForm.addLabResult')}
          </Button>
        </div>
      </div>
      {importing && (
        <div className="rounded-lg border border-slate-200 dark:border-slate-700 p-3 mb-3 space-y-3">
          <div className="flex items-center gap-4">
            <label className="text-sm font-medium text-slate-700 dark:text-slate-300">{t('labForm.import.format')}</label>
            <label className="flex items-center gap-1.5 text-sm">
              <input type="radio" name="lab-import-format" checked={importFormat === 'hl7'}
                onChange={() => setImportFormat('hl7')} /> {t('labForm.import.hl7')}
            </label>
            <label className="flex items-center gap-1.5 text-sm">
              <input type="radio" name="lab-import-format" checked={importFormat === 'fhir'}
                onChange={() => setImportFormat('fhir')} /> {t('labForm.import.fhir')}
            </label>
          </div>
          <textarea
            className={`${selectCls} font-mono text-xs h-40`}
            placeholder={importFormat === 'hl7' ? t('labForm.import.hl7Placeholder') : t('labForm.import.fhirPlaceholder')}
            value={importText}
            onChange={e => setImportText(e.target.value)}
          />
          <div className="flex justify-end">
            <Button variant="medical" onClick={submitImport} disabled={importBusy || !importText.trim()}>
              {importBusy ? t('labForm.import.importing') : t('labForm.import.submit')}
            </Button>
          </div>
        </div>
      )}
      {adding && (
        <div className="rounded-lg border border-slate-200 dark:border-slate-700 p-3 mb-3 space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">{t('labForm.resultType')}</label>
              <select className={selectCls} value={form.result_type}
                onChange={e => setForm(f => ({ ...f, result_type: e.target.value as any }))}>
                {LAB_TYPES_VALS.map(r => <option key={r} value={r}>{t(`labForm.types.${r}`)}</option>)}
              </select>
            </div>
            <Input label={t('labForm.panelName')} required value={form.panel_name}
              error={errors.panel_name}
              onChange={e => { setForm(f => ({ ...f, panel_name: e.target.value })); setErrors(p => ({ ...p, panel_name: '' })); }} />
            <Input label={t('labForm.resultDate')} type="date" value={form.result_date}
              onChange={e => setForm(f => ({ ...f, result_date: e.target.value }))} />
            <Input label={t('labForm.labName')} value={form.lab_name}
              onChange={e => setForm(f => ({ ...f, lab_name: e.target.value }))} />
          </div>
          <div className="flex justify-end">
            <Button variant="medical" onClick={submit} disabled={saving}>
              {saving ? t('labForm.saving') : t('labForm.save')}
            </Button>
          </div>
        </div>
      )}
      {records.length === 0 && !adding
        ? <p className="text-sm text-slate-400">{t('labForm.noLabResults')}</p>
        : (
          <ul className="divide-y divide-slate-100 dark:divide-slate-700 text-sm">
            {records.map(r => {
              const open = expanded.has(r.id);
              const analytes = Object.entries(r.result_data ?? {});
              return (
                <li key={r.id} className="py-2">
                  <button className="flex items-center gap-2 text-left w-full" onClick={() => toggleExpand(r.id)}>
                    {open ? <ChevronDown className="w-3.5 h-3.5 text-slate-400" /> : <ChevronRight className="w-3.5 h-3.5 text-slate-400" />}
                    <span className="font-medium text-slate-800 dark:text-slate-100">{r.panel_name}</span>
                    <span className="text-slate-400">· {r.result_date} · {t(`labForm.types.${r.result_type}`)}</span>
                    {r.pdf_url && <a href={r.pdf_url} target="_blank" rel="noreferrer" onClick={e => e.stopPropagation()} className="text-xs text-medical-500 hover:underline ml-auto">{t('labForm.downloadPdf')}</a>}
                  </button>
                  {open && analytes.length > 0 && (
                    <div className="mt-2 ml-6 overflow-x-auto">
                      <table className="text-xs w-full">
                        <thead>
                          <tr className="text-slate-400 text-left">
                            <th className="pr-4 py-1">{t('labForm.analyteName')}</th>
                            <th className="pr-4 py-1">{t('labForm.value')}</th>
                            <th className="pr-4 py-1">{t('labForm.unit')}</th>
                            <th className="pr-4 py-1">{t('labForm.refLow')}–{t('labForm.refHigh')}</th>
                            <th className="py-1">{t('labForm.flag')}</th>
                          </tr>
                        </thead>
                        <tbody>
                          {analytes.map(([name, a]) => (
                            <tr key={name} className="border-t border-slate-100 dark:border-slate-700">
                              <td className="pr-4 py-1 font-medium text-slate-800 dark:text-slate-100">{name}</td>
                              <td className="pr-4 py-1">{a.value}</td>
                              <td className="pr-4 py-1 text-slate-400">{a.unit}</td>
                              <td className="pr-4 py-1 text-slate-400">{a.ref_low ?? '—'}–{a.ref_high ?? '—'}</td>
                              <td className={`py-1 ${FLAG_CLS[a.flag ?? 'N'] ?? ''}`}>{a.flag ? t(`labForm.flags.${a.flag}`, a.flag) : '—'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Clinical photos panel
// ---------------------------------------------------------------------------
const PhotoPanel: React.FC<{ animalId: number }> = ({ animalId }) => {
  const { t } = useTranslation('patients');
  const [photos, setPhotos] = useState<ClinicalPhoto[]>([]);
  const [uploading, setUploading] = useState(false);
  const [confirmId, setConfirmId] = useState<number | null>(null);
  const fileRef = React.useRef<HTMLInputElement>(null);

  const load = useCallback(() => { apiClient.getClinicalPhotos(animalId).then(setPhotos).catch(() => {}); }, [animalId]);
  useEffect(() => { load(); }, [load]);

  const handleFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      await apiClient.uploadClinicalPhoto(animalId, file);
      toast.success(t('photoForm.created'));
      load();
    } catch { toast.error(t('photoForm.failed')); }
    finally { setUploading(false); if (fileRef.current) fileRef.current.value = ''; }
  };

  const remove = async (id: number) => {
    try { await apiClient.deleteClinicalPhoto(id); toast.success(t('photoForm.deleted')); load(); }
    catch { toast.error(t('photoForm.deleteFailed')); }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h4 className="font-semibold text-slate-800 dark:text-slate-200">{t('tabs.photos')}</h4>
        <div>
          <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={handleFile} />
          <Button variant="ghost" size="sm" leftIcon={Plus} onClick={() => fileRef.current?.click()} disabled={uploading}>
            {uploading ? t('photoForm.saving') : t('photoForm.addPhoto')}
          </Button>
        </div>
      </div>
      {photos.length === 0
        ? <p className="text-sm text-slate-400">{t('photoForm.noPhotos')}</p>
        : (
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {photos.map(p => (
              <div key={p.id} className="relative group rounded-lg overflow-hidden border border-slate-200 dark:border-slate-700">
                {p.photo_url && <img src={p.photo_url} alt={p.caption ?? ''} className="w-full h-28 object-cover" />}
                {p.caption && <p className="text-xs text-slate-500 px-2 py-1 truncate">{p.caption}</p>}
                <button
                  className="absolute top-1 right-1 bg-white/80 dark:bg-slate-900/80 rounded-full p-1 text-slate-400 hover:text-error-500 opacity-0 group-hover:opacity-100 transition-opacity"
                  onClick={() => setConfirmId(p.id)}
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
        )}
      <ConfirmDialog open={confirmId != null} message={t('photoForm.deleteConfirm')}
        onCancel={() => setConfirmId(null)}
        onConfirm={() => { const id = confirmId; setConfirmId(null); if (id != null) remove(id); }}
        danger />
    </div>
  );
};

// ---------------------------------------------------------------------------
// Reproductive panel
// ---------------------------------------------------------------------------
const ReproductivePanel: React.FC<{ animalId: number }> = ({ animalId }) => {
  const { t } = useTranslation('patients');
  const [records, setRecords] = useState<ReproductiveEvent[]>([]);
  const [adding, setAdding] = useState(false);
  const [saving, setSaving] = useState(false);
  const [confirmId, setConfirmId] = useState<number | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [form, setForm] = useState<Omit<ReproductiveEventWrite, 'animal_patient_id'>>({
    event_type: 'heat', event_date: new Date().toISOString().slice(0, 10),
  });

  const load = useCallback(() => { apiClient.getReproductiveEvents(animalId).then(setRecords).catch(() => {}); }, [animalId]);
  useEffect(() => { load(); }, [load]);

  const submit = async () => {
    const errs = zodFieldErrors(reproductiveEventSchema, form);
    if (Object.keys(errs).length) { setErrors(errs); return; }
    setSaving(true);
    try {
      await apiClient.createReproductiveEvent({ animal_patient_id: animalId, ...form });
      toast.success(t('reproductiveForm.created'));
      setForm({ event_type: 'heat', event_date: new Date().toISOString().slice(0, 10) });
      setAdding(false); load();
    } catch { toast.error(t('reproductiveForm.failed')); }
    finally { setSaving(false); }
  };

  const remove = async (id: number) => {
    try { await apiClient.deleteReproductiveEvent(id); toast.success(t('reproductiveForm.deleted')); load(); }
    catch { toast.error(t('reproductiveForm.deleteFailed')); }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h4 className="font-semibold text-slate-800 dark:text-slate-200">{t('tabs.reproductive')}</h4>
        <Button variant="ghost" size="sm" leftIcon={Plus} onClick={() => setAdding(v => !v)}>
          {adding ? t('reproductiveForm.cancel') : t('reproductiveForm.addEvent')}
        </Button>
      </div>
      {adding && (
        <div className="rounded-lg border border-slate-200 dark:border-slate-700 p-3 mb-3 space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">{t('reproductiveForm.eventType')}</label>
              <select className={selectCls} value={form.event_type}
                onChange={e => setForm(f => ({ ...f, event_type: e.target.value as ReproductiveEventType }))}>
                {REPRO_EVENT_VALUES.map(v => <option key={v} value={v}>{t(`reproductiveForm.types.${v}`)}</option>)}
              </select>
            </div>
            <Input label={t('reproductiveForm.eventDate')} type="date" value={form.event_date}
              error={errors.event_date}
              onChange={e => { setForm(f => ({ ...f, event_date: e.target.value })); setErrors(p => ({ ...p, event_date: '' })); }} />
            <Input label={t('reproductiveForm.partnerId')} value={form.partner_id ?? ''}
              onChange={e => setForm(f => ({ ...f, partner_id: e.target.value }))} />
            <Input label={t('reproductiveForm.litterCount')} type="number" min="0" value={form.litter_count ?? ''}
              onChange={e => setForm(f => ({ ...f, litter_count: e.target.value ? Number(e.target.value) : undefined }))} />
          </div>
          <div className="flex justify-end">
            <Button variant="medical" onClick={submit} disabled={saving}>
              {saving ? t('reproductiveForm.saving') : t('reproductiveForm.save')}
            </Button>
          </div>
        </div>
      )}
      {records.length === 0 && !adding
        ? <p className="text-sm text-slate-400">{t('reproductiveForm.noEvents')}</p>
        : (
          <ul className="divide-y divide-slate-100 dark:divide-slate-700 text-sm">
            {records.map(r => (
              <li key={r.id} className="flex items-center justify-between py-2">
                <div>
                  <span className="font-medium text-slate-800 dark:text-slate-100">{t(`reproductiveForm.types.${r.event_type}`)}</span>
                  <span className="text-slate-400 ml-2">· {r.event_date}</span>
                  {r.litter_count != null && <span className="text-slate-400 ml-2">· {r.litter_count} 🐾</span>}
                  {r.partner_id && <span className="text-slate-400 ml-2">· {r.partner_id}</span>}
                </div>
                <button className="p-1 text-slate-400 hover:text-error-500" onClick={() => setConfirmId(r.id)}>
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </li>
            ))}
          </ul>
        )}
      <ConfirmDialog open={confirmId != null} message={t('reproductiveForm.deleteConfirm')}
        onCancel={() => setConfirmId(null)}
        onConfirm={() => { const id = confirmId; setConfirmId(null); if (id != null) remove(id); }}
        danger />
    </div>
  );
};

// ---------------------------------------------------------------------------
// Animal detail modal — tabbed (Overview | Visits | Vaccinations | Weight | Appointments | Prescriptions | Allergies | Labs | Photos | Reproductive)
// ---------------------------------------------------------------------------
type DetailTab = 'overview' | 'visits' | 'vaccinations' | 'weight' | 'appointments' | 'prescriptions' | 'allergies' | 'labs' | 'photos' | 'reproductive' | 'messages';

const AnimalDetailModal: React.FC<{
  animalId: number | null;
  onClose: () => void;
  onEdit: (a: AnimalPatient) => void;
}> = ({ animalId, onClose, onEdit }) => {
  const { t } = useTranslation('patients');
  const [animal, setAnimal] = useState<AnimalPatient | null>(null);
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState<DetailTab>('overview');
  const [highAllergies, setHighAllergies] = useState<AllergyRecord[]>([]);

  const reload = useCallback(() => {
    if (animalId == null) { setAnimal(null); return; }
    setLoading(true);
    apiClient.getAnimal(animalId)
      .then(setAnimal)
      .catch(() => toast.error(t('actions.loadPatientFailed')))
      .finally(() => setLoading(false));
  }, [animalId, t]);

  useEffect(() => { reload(); setTab('overview'); }, [reload]);

  // Fetch allergies for the high-severity alert banner.
  useEffect(() => {
    if (animalId == null) { setHighAllergies([]); return; }
    apiClient.getAllergies(animalId)
      .then(recs => setHighAllergies(recs.filter(a => a.is_high_severity)))
      .catch(() => setHighAllergies([]));
  }, [animalId, tab]);

  const TABS: DetailTab[] = [
    'overview', 'visits', 'vaccinations', 'weight', 'appointments',
    'prescriptions', 'allergies', 'labs', 'photos', 'reproductive', 'messages',
  ];

  return (
    <Modal isOpen={animalId != null} onClose={onClose} title={animal?.name ?? t('detail.title')} size="lg">
      <ModalContent>
        {loading && <p className="text-slate-500">{t('detail.loading')}</p>}
        {animal && (
          <div className="space-y-4">
            {/* Animal header */}
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-2xl bg-medical-50 dark:bg-medical-900/30 flex items-center justify-center text-2xl">{emojiFor(animal.species)}</div>
              <div>
                <h3 className="text-lg font-bold text-slate-900 dark:text-white">{animal.name}</h3>
                <p className="text-sm text-slate-500">{t(`species.${animal.species}`)}{animal.breed ? ` · ${animal.breed}` : ''}</p>
              </div>
            </div>

            {/* High-severity allergy alert banner */}
            {highAllergies.length > 0 && (
              <div role="alert" className="flex items-start gap-2 rounded-lg border border-red-300 bg-red-50 dark:border-red-800 dark:bg-red-900/30 px-3 py-2">
                <span className="text-red-600 dark:text-red-300 font-bold text-sm">
                  {t('allergyForm.alertBanner', { allergens: highAllergies.map(a => a.allergen).join(', ') })}
                </span>
              </div>
            )}

            {/* Tab bar */}
            <div className="flex gap-1 border-b border-slate-200 dark:border-slate-700">
              {TABS.map(tab_ => (
                <button
                  key={tab_}
                  onClick={() => setTab(tab_)}
                  className={`px-3 py-1.5 text-sm font-medium rounded-t transition-colors ${
                    tab === tab_
                      ? 'border-b-2 border-medical-500 text-medical-600 dark:text-medical-400'
                      : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
                  }`}
                >
                  {t(`tabs.${tab_}`)}
                </button>
              ))}
            </div>

            {/* Tab content */}
            {tab === 'overview' && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-sm">
                  {[
                    [t('detail.sex'), animal.sex ? t(`sex.${animal.sex}`) : '—'],
                    [t('detail.dob'), animal.date_of_birth || '—'],
                    [t('detail.weight'), animal.weight_kg ? `${animal.weight_kg} kg` : '—'],
                    [t('detail.microchip'), animal.microchip_id || '—'],
                    [t('detail.color'), animal.color || '—'],
                    [t('detail.owner'), `${animal.owner.first_name} ${animal.owner.last_name}`],
                  ].map(([k, v]) => (
                    <div key={k} className="bg-slate-50 dark:bg-slate-800 rounded-lg px-3 py-2">
                      <div className="text-xs uppercase tracking-wide text-slate-400">{k}</div>
                      <div className="font-medium text-slate-800 dark:text-slate-100">{v}</div>
                    </div>
                  ))}
                </div>

                {/* Insurance (shown only when on file) */}
                {(animal.insurance_provider || animal.insurance_policy_number) && (
                  <div className="rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-2">
                    <div className="text-xs uppercase tracking-wide text-slate-400 mb-1">{t('insurance.title')}</div>
                    <div className="text-sm text-slate-800 dark:text-slate-100">
                      <span className="font-medium">{animal.insurance_provider || '—'}</span>
                      {animal.insurance_policy_number && <span className="text-slate-400"> · {animal.insurance_policy_number}</span>}
                      {animal.insurance_expiry && (() => {
                        const exp = new Date(animal.insurance_expiry);
                        const now = new Date();
                        const soon = new Date(); soon.setDate(now.getDate() + 30);
                        const cls = exp < now ? 'text-error-600 dark:text-error-400'
                          : exp < soon ? 'text-amber-600 dark:text-amber-400' : 'text-slate-400';
                        const label = exp < now ? t('insurance.expired')
                          : exp < soon ? t('insurance.expiringSoon') : null;
                        return (
                          <span className={`ml-1 ${cls}`}>
                            · {t('insurance.expiry')}: {animal.insurance_expiry}{label ? ` (${label})` : ''}
                          </span>
                        );
                      })()}
                    </div>
                  </div>
                )}

                <div>
                  <h4 className="font-semibold text-slate-800 dark:text-slate-200 mb-2">{t('detail.studyTimeline')}</h4>
                  {animal.studies && animal.studies.length > 0 ? (
                    <ul className="space-y-2">
                      {animal.studies.map(s => (
                        <li key={s.study_instance_uid} className="flex items-center justify-between border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2">
                          <div>
                            <div className="font-medium text-slate-800 dark:text-slate-100">{s.study_description || t('detail.title')}</div>
                            <div className="text-xs text-slate-400 font-mono">{s.study_instance_uid}</div>
                          </div>
                          <span className="text-sm text-slate-500">{s.study_date || '—'}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-sm text-slate-400">{t('detail.noStudies')}</p>
                  )}
                </div>
                <VHSPanel animal={animal} onChanged={reload} />
              </div>
            )}
            {tab === 'visits' && <VisitPanel animalId={animal.id} />}
            {tab === 'vaccinations' && <VaccinationPanel animalId={animal.id} />}
            {tab === 'weight' && <WeightPanel animalId={animal.id} />}
            {tab === 'appointments' && <AppointmentPanel animalId={animal.id} />}
            {tab === 'prescriptions' && <PrescriptionPanel animalId={animal.id} />}
            {tab === 'allergies' && <AllergyPanel animalId={animal.id} />}
            {tab === 'labs' && <LabResultPanel animalId={animal.id} />}
            {tab === 'photos' && <PhotoPanel animalId={animal.id} />}
            {tab === 'reproductive' && <ReproductivePanel animalId={animal.id} />}
            {tab === 'messages' && <MessageThread animalId={animal.id} />}
          </div>
        )}
      </ModalContent>
      <ModalFooter>
        <Button variant="ghost" onClick={onClose}>{t('detail.close')}</Button>
        {animal && (
          <Button
            variant="outline"
            leftIcon={FileDown}
            onClick={() => apiClient.downloadPassport(animal.id, animal.name).catch(() => toast.error(t('detail.passportFailed')))}
          >
            {t('detail.passport')}
          </Button>
        )}
        {animal && <Button variant="outline" leftIcon={Pencil} onClick={() => onEdit(animal)}>{t('detail.edit')}</Button>}
      </ModalFooter>
    </Modal>
  );
};

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------
const PatientsPage: React.FC = () => {
  const { t } = useTranslation('patients');
  const [view, setView] = useState<'owners' | 'patients'>('owners');
  const [owners, setOwners] = useState<Owner[]>([]);
  const [animals, setAnimals] = useState<AnimalPatientListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  const [ownerModal, setOwnerModal] = useState<{ open: boolean; initial: Owner | null }>({ open: false, initial: null });
  const [animalModal, setAnimalModal] = useState<{ open: boolean; ownerId: number | null; ownerName?: string; initial: AnimalPatient | null }>({ open: false, ownerId: null, initial: null });
  const [detailId, setDetailId] = useState<number | null>(null);
  const [confirmOwner, setConfirmOwner] = useState<Owner | null>(null);
  const [confirmAnimal, setConfirmAnimal] = useState<AnimalPatientListItem | null>(null);

  const load = useCallback(async (q?: string) => {
    setLoading(true);
    try {
      setOwners(await apiClient.getOwners(q));
    } catch {
      toast.error(t('actions.loadFailed'));
    } finally {
      setLoading(false);
    }
  }, [t]);

  const loadAnimals = useCallback(async (q?: string) => {
    setLoading(true);
    try {
      setAnimals(await apiClient.getAnimals({ search: q || undefined }));
    } catch {
      toast.error(t('actions.loadFailed'));
    } finally {
      setLoading(false);
    }
  }, [t]);

  // Debounced search, dispatched to the active view.
  useEffect(() => {
    const h = setTimeout(() => {
      if (view === 'owners') load(search || undefined);
      else loadAnimals(search || undefined);
    }, 300);
    return () => clearTimeout(h);
  }, [search, view, load, loadAnimals]);

  const reloadActive = () => (view === 'owners' ? load(search || undefined) : loadAnimals(search || undefined));

  const toggle = (id: number) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  const removeOwner = async (o: Owner) => {
    try {
      await apiClient.deleteOwner(o.id);
      toast.success(t('actions.ownerDeleted'));
      reloadActive();
    } catch {
      toast.error(t('actions.ownerDeleteFailed'));
    }
  };

  const removeAnimal = async (a: AnimalPatientListItem) => {
    try {
      await apiClient.deleteAnimal(a.id);
      toast.success(t('actions.patientDeleted'));
      reloadActive();
    } catch {
      toast.error(t('actions.patientDeleteFailed'));
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-medical-500 to-teal-500 flex items-center justify-center">
            <PawPrint className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white">{t('title')}</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">{t('subtitle')}</p>
          </div>
        </div>
        {view === 'owners' ? (
          <Button variant="medical" leftIcon={Plus} onClick={() => setOwnerModal({ open: true, initial: null })}>
            {t('newOwner')}
          </Button>
        ) : (
          <Button variant="medical" leftIcon={Plus} onClick={() => setAnimalModal({ open: true, ownerId: null, initial: null })}>
            {t('newPatient')}
          </Button>
        )}
      </div>

      {/* View toggle */}
      <div className="inline-flex rounded-medical border border-slate-200 dark:border-slate-700 p-0.5 mb-4">
        {(['owners', 'patients'] as const).map((v) => (
          <button
            key={v}
            onClick={() => { setView(v); setSearch(''); }}
            className={`px-4 py-1.5 text-sm font-medium rounded-[0.4rem] transition-colors ${
              view === v
                ? 'bg-medical-500 text-white'
                : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
            }`}
          >
            {t(`view.${v === 'owners' ? 'owners' : 'allPatients'}`)}
          </button>
        ))}
      </div>

      {/* Search */}
      <div className="relative mb-5">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
        <input
          className="w-full pl-9 pr-3 py-2 border border-slate-300 dark:border-slate-600 rounded-medical bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-medical-500"
          placeholder={view === 'owners' ? t('searchOwners') : t('searchPatients')}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          aria-label={view === 'owners' ? t('searchOwners') : t('searchPatients')}
        />
      </div>

      {/* All-patients view */}
      {view === 'patients' ? (
        loading ? (
          <p className="text-slate-500">{t('loading')}</p>
        ) : animals.length === 0 ? (
          <Card><CardContent className="py-12 text-center text-slate-500">{t('noPatientsTitle')}</CardContent></Card>
        ) : (
          <div className="space-y-2">
            {animals.map((a) => (
              <Card key={a.id}>
                <CardContent className="flex items-center justify-between py-3">
                  <button className="flex items-center gap-3 text-left flex-1" onClick={() => setDetailId(a.id)}>
                    <span className="text-xl">{emojiFor(a.species)}</span>
                    <div>
                      <div className="font-medium text-slate-800 dark:text-slate-100">{a.name}</div>
                      <div className="text-xs text-slate-500">
                        {t(`species.${a.species}`)}{a.breed ? ` · ${a.breed}` : ''} · {a.owner_name}
                      </div>
                    </div>
                  </button>
                  <button className="p-2 text-slate-400 hover:text-error-500" onClick={() => setConfirmAnimal(a)} aria-label={t('actions.patient')}><Trash2 className="w-4 h-4" /></button>
                </CardContent>
              </Card>
            ))}
          </div>
        )
      ) : /* Owners list */ (
      loading ? (
        <p className="text-slate-500">{t('loading')}</p>
      ) : owners.length === 0 ? (
        <Card><CardContent className="py-12 text-center text-slate-500">
          {t('noOwnersHint')}
        </CardContent></Card>
      ) : (
        <div className="space-y-3">
          {owners.map((o) => {
            const isOpen = expanded.has(o.id);
            return (
              <Card key={o.id}>
                <CardContent className="p-0">
                  <div className="flex items-center justify-between px-4 py-3">
                    <button className="flex items-center gap-3 text-left flex-1" onClick={() => toggle(o.id)}>
                      {isOpen ? <ChevronDown className="w-4 h-4 text-slate-400" /> : <ChevronRight className="w-4 h-4 text-slate-400" />}
                      <div className="w-9 h-9 rounded-full bg-slate-100 dark:bg-slate-700 flex items-center justify-center">
                        <User className="w-4 h-4 text-slate-500" />
                      </div>
                      <div>
                        <div className="font-semibold text-slate-900 dark:text-white">{o.first_name} {o.last_name}</div>
                        <div className="text-xs text-slate-500">
                          {t('patientCount', { count: o.animals_count ?? o.animals?.length ?? 0 })}
                          {o.email ? ` · ${o.email}` : ''}{o.phone ? ` · ${o.phone}` : ''}
                        </div>
                      </div>
                    </button>
                    <div className="flex items-center gap-1">
                      <Button variant="ghost" size="sm" leftIcon={Plus}
                        onClick={() => setAnimalModal({ open: true, ownerId: o.id, ownerName: `${o.first_name} ${o.last_name}`, initial: null })}>
                        {t('actions.patient')}
                      </Button>
                      <button className="p-2 text-slate-400 hover:text-medical-600" onClick={() => setOwnerModal({ open: true, initial: o })} aria-label={t('ownerForm.editTitle')}><Pencil className="w-4 h-4" /></button>
                      <button className="p-2 text-slate-400 hover:text-error-500" onClick={() => setConfirmOwner(o)} aria-label={t('ownerForm.editTitle')}><Trash2 className="w-4 h-4" /></button>
                    </div>
                  </div>

                  {isOpen && (
                    <div className="border-t border-slate-100 dark:border-slate-700 px-4 py-2">
                      {(o.animals && o.animals.length > 0) ? (
                        <ul className="divide-y divide-slate-100 dark:divide-slate-700">
                          {o.animals.map((a) => (
                            <li key={a.id} className="flex items-center justify-between py-2">
                              <button className="flex items-center gap-3 text-left flex-1" onClick={() => setDetailId(a.id)}>
                                <span className="text-xl">{emojiFor(a.species)}</span>
                                <div>
                                  <div className="font-medium text-slate-800 dark:text-slate-100">{a.name}</div>
                                  <div className="text-xs text-slate-500">{t(`species.${a.species}`)}{a.breed ? ` · ${a.breed}` : ''}</div>
                                </div>
                              </button>
                              <button className="p-2 text-slate-400 hover:text-error-500" onClick={() => setConfirmAnimal(a)} aria-label={t('actions.patient')}><Trash2 className="w-4 h-4" /></button>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p className="text-sm text-slate-400 py-2">{t('noPatientsForOwner')}</p>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )
      )}

      {/* Modals */}
      <OwnerFormModal
        open={ownerModal.open}
        initial={ownerModal.initial}
        onClose={() => setOwnerModal({ open: false, initial: null })}
        onSaved={() => reloadActive()}
      />
      <AnimalFormModal
        open={animalModal.open}
        ownerId={animalModal.ownerId}
        ownerName={animalModal.ownerName}
        initial={animalModal.initial}
        onClose={() => setAnimalModal({ open: false, ownerId: null, initial: null })}
        onSaved={() => reloadActive()}
      />
      <AnimalDetailModal
        animalId={detailId}
        onClose={() => setDetailId(null)}
        onEdit={(a) => {
          setDetailId(null);
          setAnimalModal({ open: true, ownerId: a.owner.id, ownerName: `${a.owner.first_name} ${a.owner.last_name}`, initial: a });
        }}
      />

      <ConfirmDialog
        open={confirmOwner != null}
        message={confirmOwner ? t('actions.deleteOwnerConfirm', { name: `${confirmOwner.first_name} ${confirmOwner.last_name}` }) : ''}
        onCancel={() => setConfirmOwner(null)}
        onConfirm={() => { const o = confirmOwner; setConfirmOwner(null); if (o) removeOwner(o); }}
        danger
      />
      <ConfirmDialog
        open={confirmAnimal != null}
        message={confirmAnimal ? t('actions.deletePatientConfirm', { name: confirmAnimal.name }) : ''}
        onCancel={() => setConfirmAnimal(null)}
        onConfirm={() => { const a = confirmAnimal; setConfirmAnimal(null); if (a) removeAnimal(a); }}
        danger
      />
    </div>
  );
};

export default PatientsPage;
