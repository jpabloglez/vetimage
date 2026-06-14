/**
 * CalendarPage — clinic appointment schedule.
 *
 * Month view: 7-column grid, each cell shows the day's appointments.
 * Week view: 7-column × time-slot grid with appointments at their start time.
 * New appointments via AppointmentFormModal. Completing an appointment
 * calls the /complete/ action which auto-creates a linked ClinicalVisit.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import toast from 'react-hot-toast';
import { CalendarDays, ChevronLeft, ChevronRight, Plus, Clock } from 'lucide-react';
import {
  apiClient,
  type Appointment,
  type AppointmentWrite,
  type VisitType,
} from '../utils/api';
import { Button, Input, Modal, ModalContent, ModalFooter } from '../components/ui';
import { appointmentSchema, zodFieldErrors } from '../utils/validation';

const VISIT_TYPE_VALUES: VisitType[] = ['consultation', 'follow_up', 'vaccination', 'surgery', 'imaging', 'emergency'];

const TYPE_COLOR: Record<string, string> = {
  consultation:  'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
  follow_up:     'bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-300',
  vaccination:   'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300',
  surgery:       'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
  imaging:       'bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300',
  emergency:     'bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300',
};

const STATUS_CLS: Record<string, string> = {
  pending:   'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
  confirmed: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  completed: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
  cancelled: 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400',
  no_show:   'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-300',
};

// ─── Helpers ─────────────────────────────────────────────────────────────────

function startOfMonth(d: Date) {
  return new Date(d.getFullYear(), d.getMonth(), 1);
}

function daysInMonth(d: Date) {
  return new Date(d.getFullYear(), d.getMonth() + 1, 0).getDate();
}

function isoDate(d: Date) {
  return d.toISOString().slice(0, 10);
}

function addMonths(d: Date, n: number) {
  const r = new Date(d);
  r.setMonth(r.getMonth() + n);
  return r;
}

function addWeeks(d: Date, n: number) {
  const r = new Date(d);
  r.setDate(r.getDate() + n * 7);
  return r;
}

function startOfWeek(d: Date) {
  const r = new Date(d);
  r.setDate(r.getDate() - r.getDay()); // Sunday start
  return r;
}

// ─── Appointment form modal ───────────────────────────────────────────────────

const selectCls =
  'w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-medical bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-medical-500 text-sm';

const AppointmentFormModal: React.FC<{
  open: boolean;
  prefillDate?: string;
  onClose: () => void;
  onSaved: () => void;
}> = ({ open, prefillDate, onClose, onSaved }) => {
  const { t } = useTranslation('calendar');
  const { t: tp } = useTranslation('patients');
  const [form, setForm] = useState<Partial<AppointmentWrite>>({
    appointment_type: 'consultation',
    scheduled_at: prefillDate ? `${prefillDate}T09:00` : '',
    duration_minutes: 30,
    animal_patient_id: 0,
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [animalSearch, setAnimalSearch] = useState('');
  const [animalResults, setAnimalResults] = useState<{ id: number; name: string; owner_name: string }[]>([]);
  const [selectedAnimal, setSelectedAnimal] = useState<{ id: number; name: string } | null>(null);

  useEffect(() => {
    if (open) {
      setErrors({});
      setAnimalSearch('');
      setAnimalResults([]);
      setSelectedAnimal(null);
      setForm({
        appointment_type: 'consultation',
        scheduled_at: prefillDate ? `${prefillDate}T09:00` : '',
        duration_minutes: 30,
        animal_patient_id: 0,
      });
    }
  }, [open, prefillDate]);

  useEffect(() => {
    if (!animalSearch.trim()) { setAnimalResults([]); return; }
    const h = setTimeout(async () => {
      try {
        const results = await apiClient.getAnimals({ search: animalSearch });
        setAnimalResults(results.map(a => ({ id: a.id, name: a.name, owner_name: a.owner_name })));
      } catch { setAnimalResults([]); }
    }, 300);
    return () => clearTimeout(h);
  }, [animalSearch]);

  const submit = async () => {
    if (!selectedAnimal) {
      setErrors(p => ({ ...p, animal: 'Please select a patient.' }));
      return;
    }
    const payload = { ...form, animal_patient_id: selectedAnimal.id };
    const errs = zodFieldErrors(appointmentSchema, payload);
    if (Object.keys(errs).length) { setErrors(errs); return; }
    setSaving(true);
    try {
      await apiClient.createAppointment(payload as AppointmentWrite);
      toast.success(t('form.created'));
      onSaved();
      onClose();
    } catch { toast.error(t('form.failed')); }
    finally { setSaving(false); }
  };

  return (
    <Modal isOpen={open} onClose={onClose} title={t('form.title')} size="md">
      <ModalContent>
        <div className="space-y-4">
          {/* Animal picker */}
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              {t('form.animal')} <span className="text-error-500">*</span>
            </label>
            {selectedAnimal ? (
              <div className="flex items-center justify-between rounded-medical border border-slate-200 dark:border-slate-700 px-3 py-2">
                <span className="font-medium text-slate-800 dark:text-slate-100">{selectedAnimal.name}</span>
                <Button variant="ghost" size="sm" onClick={() => setSelectedAnimal(null)}>Change</Button>
              </div>
            ) : (
              <div className="relative">
                <input
                  className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-medical bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-medical-500"
                  placeholder={t('form.searchAnimal')}
                  value={animalSearch}
                  onChange={e => setAnimalSearch(e.target.value)}
                />
                {animalResults.length > 0 && (
                  <ul className="absolute z-50 w-full mt-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-medical shadow-lg max-h-40 overflow-y-auto">
                    {animalResults.map(a => (
                      <li key={a.id}>
                        <button
                          className="w-full text-left px-3 py-2 text-sm hover:bg-medical-50 dark:hover:bg-medical-900/20 transition-colors"
                          onClick={() => { setSelectedAnimal({ id: a.id, name: a.name }); setAnimalSearch(''); setAnimalResults([]); setErrors(p => ({ ...p, animal: '' })); }}
                        >
                          <span className="font-medium">{a.name}</span>
                          <span className="text-slate-400 ml-1">· {a.owner_name}</span>
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
            {errors.animal && <p className="mt-1 text-sm text-error-600">{errors.animal}</p>}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">{t('form.type')}</label>
              <select className={selectCls} value={form.appointment_type}
                onChange={e => setForm(f => ({ ...f, appointment_type: e.target.value as VisitType }))}>
                {VISIT_TYPE_VALUES.map(v => <option key={v} value={v}>{tp(`visitForm.visitTypes.${v}`)}</option>)}
              </select>
            </div>
            <Input
              label={t('form.scheduled')} required type="datetime-local"
              value={form.scheduled_at ?? ''} error={errors.scheduled_at}
              onChange={e => { setForm(f => ({ ...f, scheduled_at: e.target.value })); setErrors(p => ({ ...p, scheduled_at: '' })); }}
            />
            <Input
              label={t('form.duration')} type="number" min="5" max="480"
              value={form.duration_minutes ?? 30}
              onChange={e => setForm(f => ({ ...f, duration_minutes: Number(e.target.value) }))}
            />
          </div>
        </div>
      </ModalContent>
      <ModalFooter>
        <Button variant="ghost" onClick={onClose} disabled={saving}>{t('form.cancel')}</Button>
        <Button variant="medical" onClick={submit} disabled={saving}>
          {saving ? t('form.saving') : t('form.save')}
        </Button>
      </ModalFooter>
    </Modal>
  );
};

// ─── Appointment detail panel ─────────────────────────────────────────────────

const AppointmentDetailPanel: React.FC<{
  appointment: Appointment;
  onClose: () => void;
  onChanged: () => void;
}> = ({ appointment: appt, onClose, onChanged }) => {
  const { t } = useTranslation('calendar');
  const { t: tp } = useTranslation('patients');
  const [completing, setCompleting] = useState(false);

  const complete = async () => {
    setCompleting(true);
    try {
      await apiClient.completeAppointment(appt.id);
      toast.success(t('detail.completed'));
      onChanged();
      onClose();
    } catch { toast.error(t('detail.completeFailed')); }
    finally { setCompleting(false); }
  };

  return (
    <div className="p-4 space-y-3">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="font-semibold text-slate-900 dark:text-white">
            {appt.animal_name}
          </h3>
          <p className="text-sm text-slate-500">{appt.owner_name}</p>
        </div>
        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_CLS[appt.status] ?? ''}`}>
          {tp(`appointmentForm.statuses.${appt.status}`)}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-2 text-sm">
        <div>
          <p className="text-xs text-slate-400 uppercase tracking-wide">{t('detail.type')}</p>
          <p className="font-medium">{tp(`visitForm.visitTypes.${appt.appointment_type}`)}</p>
        </div>
        <div>
          <p className="text-xs text-slate-400 uppercase tracking-wide">{t('detail.scheduled')}</p>
          <p className="font-medium">{new Date(appt.scheduled_at).toLocaleString()}</p>
        </div>
        <div>
          <p className="text-xs text-slate-400 uppercase tracking-wide">{t('detail.duration')}</p>
          <p className="font-medium">{appt.duration_minutes} min</p>
        </div>
      </div>
      {appt.notes && <p className="text-sm text-slate-600 dark:text-slate-300">{appt.notes}</p>}
      {(appt.status === 'pending' || appt.status === 'confirmed') && (
        <Button variant="medical" className="w-full" onClick={complete} disabled={completing}>
          {completing ? t('detail.completing') : t('detail.complete')}
        </Button>
      )}
    </div>
  );
};

// ─── Main CalendarPage ────────────────────────────────────────────────────────

const CalendarPage: React.FC = () => {
  const { t } = useTranslation('calendar');
  const [viewMode, setViewMode] = useState<'month' | 'week'>('month');
  const [currentDate, setCurrentDate] = useState(new Date());
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [loading, setLoading] = useState(true);
  const [formOpen, setFormOpen] = useState(false);
  const [prefillDate, setPrefillDate] = useState<string | undefined>();
  const [selectedAppt, setSelectedAppt] = useState<Appointment | null>(null);

  const loadAppointments = useCallback(async () => {
    setLoading(true);
    try {
      let dateFrom: string, dateTo: string;
      if (viewMode === 'month') {
        const first = startOfMonth(currentDate);
        dateFrom = isoDate(first);
        dateTo = isoDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 0));
      } else {
        const sw = startOfWeek(currentDate);
        dateFrom = isoDate(sw);
        dateTo = isoDate(new Date(sw.getFullYear(), sw.getMonth(), sw.getDate() + 6));
      }
      setAppointments(await apiClient.getAppointments({ date_from: dateFrom, date_to: dateTo }));
    } catch { toast.error(t('loading')); }
    finally { setLoading(false); }
  }, [viewMode, currentDate, t]);

  useEffect(() => { loadAppointments(); }, [loadAppointments]);

  const prev = () => {
    if (viewMode === 'month') setCurrentDate(d => addMonths(d, -1));
    else setCurrentDate(d => addWeeks(d, -1));
  };
  const next = () => {
    if (viewMode === 'month') setCurrentDate(d => addMonths(d, 1));
    else setCurrentDate(d => addWeeks(d, 1));
  };
  const goToday = () => setCurrentDate(new Date());

  const headerLabel = viewMode === 'month'
    ? currentDate.toLocaleDateString(undefined, { month: 'long', year: 'numeric' })
    : (() => {
        const sw = startOfWeek(currentDate);
        const ew = new Date(sw); ew.setDate(sw.getDate() + 6);
        return `${sw.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })} – ${ew.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}`;
      })();

  // ── Month view ──────────────────────────────────────────────────────────────
  const renderMonthGrid = () => {
    const firstDay = startOfMonth(currentDate);
    const totalDays = daysInMonth(currentDate);
    const startDow = firstDay.getDay(); // 0=Sun
    const cells: (Date | null)[] = [...Array(startDow).fill(null)];
    for (let d = 1; d <= totalDays; d++) {
      cells.push(new Date(currentDate.getFullYear(), currentDate.getMonth(), d));
    }
    while (cells.length % 7 !== 0) cells.push(null);

    const byDate: Record<string, Appointment[]> = {};
    appointments.forEach(a => {
      const d = a.scheduled_at.slice(0, 10);
      (byDate[d] ??= []).push(a);
    });

    const today = isoDate(new Date());
    const DOW = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

    return (
      <div>
        <div className="grid grid-cols-7 mb-1">
          {DOW.map(d => <div key={d} className="text-center text-xs font-medium text-slate-400 py-1">{d}</div>)}
        </div>
        <div className="grid grid-cols-7 gap-px bg-slate-200 dark:bg-slate-700 border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden">
          {cells.map((day, i) => {
            if (!day) return <div key={i} className="bg-slate-50 dark:bg-slate-900 min-h-[80px]" />;
            const ds = isoDate(day);
            const dayAppts = byDate[ds] ?? [];
            const isToday = ds === today;
            return (
              <div
                key={ds}
                className="bg-white dark:bg-slate-800 min-h-[80px] p-1 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-750 transition-colors"
                onClick={() => { setPrefillDate(ds); setFormOpen(true); }}
              >
                <span className={`text-xs font-medium inline-block w-6 h-6 flex items-center justify-center rounded-full mb-1 ${isToday ? 'bg-medical-500 text-white' : 'text-slate-600 dark:text-slate-300'}`}>
                  {day.getDate()}
                </span>
                {dayAppts.slice(0, 3).map(a => (
                  <div
                    key={a.id}
                    className={`text-xs px-1 py-0.5 rounded mb-0.5 truncate cursor-pointer ${TYPE_COLOR[a.appointment_type] ?? ''}`}
                    onClick={e => { e.stopPropagation(); setSelectedAppt(a); }}
                  >
                    {new Date(a.scheduled_at).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })} {a.animal_name}
                  </div>
                ))}
                {dayAppts.length > 3 && (
                  <div className="text-xs text-slate-400">+{dayAppts.length - 3} more</div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  // ── Week view ───────────────────────────────────────────────────────────────
  const renderWeekGrid = () => {
    const sw = startOfWeek(currentDate);
    const days = Array.from({ length: 7 }, (_, i) => {
      const d = new Date(sw); d.setDate(sw.getDate() + i); return d;
    });
    const HOURS = Array.from({ length: 13 }, (_, i) => i + 8); // 8–20
    const byDateHour: Record<string, Appointment[]> = {};
    appointments.forEach(a => {
      const key = `${a.scheduled_at.slice(0, 10)}-${new Date(a.scheduled_at).getHours()}`;
      (byDateHour[key] ??= []).push(a);
    });

    return (
      <div className="overflow-x-auto">
        <div className="min-w-[600px]">
          {/* Header */}
          <div className="grid grid-cols-8 mb-1">
            <div className="text-xs text-slate-400 text-right pr-2 pt-1">UTC</div>
            {days.map(d => (
              <div key={isoDate(d)} className={`text-center py-1 ${isoDate(d) === isoDate(new Date()) ? 'font-bold text-medical-600' : 'text-slate-600 dark:text-slate-300'}`}>
                <div className="text-xs">{d.toLocaleDateString(undefined, { weekday: 'short' })}</div>
                <div className="text-sm">{d.getDate()}</div>
              </div>
            ))}
          </div>
          {/* Time slots */}
          {HOURS.map(h => (
            <div key={h} className="grid grid-cols-8 border-t border-slate-100 dark:border-slate-700 min-h-[48px]">
              <div className="text-xs text-slate-400 text-right pr-2 pt-1">{h}:00</div>
              {days.map(d => {
                const key = `${isoDate(d)}-${h}`;
                const dayAppts = byDateHour[key] ?? [];
                return (
                  <div key={key} className="border-l border-slate-100 dark:border-slate-700 px-1 py-0.5">
                    {dayAppts.map(a => (
                      <div
                        key={a.id}
                        className={`text-xs px-1 py-0.5 rounded mb-0.5 truncate cursor-pointer ${TYPE_COLOR[a.appointment_type] ?? ''}`}
                        onClick={() => setSelectedAppt(a)}
                      >
                        {a.animal_name}
                      </div>
                    ))}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-medical-500 to-teal-500 flex items-center justify-center">
            <CalendarDays className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white">{t('title')}</h1>
            <p className="text-sm text-slate-500">{t('subtitle')}</p>
          </div>
        </div>
        <Button variant="medical" leftIcon={Plus} onClick={() => { setPrefillDate(undefined); setFormOpen(true); }}>
          {t('newAppointment')}
        </Button>
      </div>

      {/* Controls */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <button onClick={prev} className="p-1.5 rounded-medical hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300" aria-label={t('nav.prev')}>
            <ChevronLeft className="w-4 h-4" />
          </button>
          <h2 className="text-lg font-semibold text-slate-800 dark:text-white min-w-[220px] text-center">{headerLabel}</h2>
          <button onClick={next} className="p-1.5 rounded-medical hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300" aria-label={t('nav.next')}>
            <ChevronRight className="w-4 h-4" />
          </button>
          <Button variant="outline" size="sm" onClick={goToday}>{t('today')}</Button>
        </div>
        <div className="inline-flex rounded-medical border border-slate-200 dark:border-slate-700 p-0.5">
          {(['month', 'week'] as const).map(v => (
            <button
              key={v}
              onClick={() => setViewMode(v)}
              className={`px-3 py-1 text-sm font-medium rounded-[0.4rem] transition-colors ${viewMode === v ? 'bg-medical-500 text-white' : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'}`}
            >
              {t(v)}
            </button>
          ))}
        </div>
      </div>

      {loading
        ? <p className="text-slate-500 text-center py-12">{t('loading')}</p>
        : viewMode === 'month' ? renderMonthGrid() : renderWeekGrid()
      }

      {/* Appointment form modal */}
      <AppointmentFormModal
        open={formOpen}
        prefillDate={prefillDate}
        onClose={() => setFormOpen(false)}
        onSaved={loadAppointments}
      />

      {/* Appointment detail side panel (simple modal) */}
      {selectedAppt && (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-end sm:justify-end pointer-events-none">
          <div className="pointer-events-auto w-full sm:w-80 bg-white dark:bg-slate-900 rounded-t-2xl sm:rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700 m-0 sm:m-4">
            <div className="flex items-center justify-between px-4 pt-4 pb-2 border-b border-slate-100 dark:border-slate-700">
              <span className="flex items-center gap-2 text-sm font-medium text-slate-600 dark:text-slate-300">
                <Clock className="w-4 h-4" />
                {new Date(selectedAppt.scheduled_at).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })}
              </span>
              <button onClick={() => setSelectedAppt(null)} className="text-slate-400 hover:text-slate-600 text-lg leading-none">&times;</button>
            </div>
            <AppointmentDetailPanel
              appointment={selectedAppt}
              onClose={() => setSelectedAppt(null)}
              onChanged={loadAppointments}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default CalendarPage;
