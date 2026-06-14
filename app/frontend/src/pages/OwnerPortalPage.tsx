/**
 * OwnerPortalPage — authenticated pet-owner dashboard (#21).
 *
 * Owner accounts are users.User rows with role === PET_OWNER_ROLE (6), linked to
 * their clinical Owner record(s) by email. This page aggregates their pets
 * (with vaccination status + upcoming appointments) and the reports a clinic has
 * approved and shared. Non-owner accounts are redirected to the staff dashboard.
 */
import React, { useEffect, useState } from 'react';
import { Navigate, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { PawPrint, Syringe, CalendarClock, FileText, AlertTriangle, MessageSquare } from 'lucide-react';
import { apiClient, type PortalDashboard } from '../utils/api';
import { useAuth } from '../contexts';
import MessageThread from '../components/patients/MessageThread';

const PET_OWNER_ROLE = 6;

const OwnerPortalPage: React.FC = () => {
  const { t } = useTranslation('patients');
  const { user, isAuthenticated, isLoading } = useAuth();
  const [data, setData] = useState<PortalDashboard | null>(null);
  const [state, setState] = useState<'loading' | 'ok' | 'error'>('loading');
  const [msgPetId, setMsgPetId] = useState<number | null>(null);

  useEffect(() => {
    if (user && user.role === PET_OWNER_ROLE) {
      apiClient.getPortalDashboard()
        .then((d) => { setData(d); setState('ok'); })
        .catch(() => setState('error'));
    }
  }, [user]);

  if (isLoading) return null;
  if (!isAuthenticated) return <Navigate to="/auth/login" replace />;
  // Staff accounts don't belong here — send them to the clinic dashboard.
  if (!user || user.role !== PET_OWNER_ROLE) return <Navigate to="/dashboard" replace />;

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
      <header className="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
        <div className="max-w-3xl mx-auto px-4 h-16 flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-medical-500 to-teal-500 flex items-center justify-center">
            <PawPrint className="w-4 h-4 text-white" />
          </div>
          <span className="text-lg font-bold text-slate-900 dark:text-white">VetImage</span>
          <span className="ml-auto text-sm text-slate-500">{user.email}</span>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-8 space-y-6">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">{t('portal.title')}</h1>

        {state === 'loading' && (
          <div className="flex justify-center py-12">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-medical-500" />
          </div>
        )}

        {state === 'error' && (
          <p className="text-slate-500 dark:text-slate-400">{t('portal.loadError')}</p>
        )}

        {state === 'ok' && data && (
          <>
            {/* Pets */}
            <section className="space-y-4">
              <h2 className="font-semibold text-slate-800 dark:text-slate-200">{t('portal.myPets')}</h2>
              {data.pets.length === 0 ? (
                <p className="text-slate-500 dark:text-slate-400">{t('portal.noPets')}</p>
              ) : data.pets.map((pet) => (
                <div key={pet.id} className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
                  <div className="flex items-center gap-3 mb-3">
                    {pet.profile_photo
                      ? <img src={pet.profile_photo} alt={pet.name} className="w-12 h-12 rounded-full object-cover" />
                      : <div className="w-12 h-12 rounded-full bg-medical-100 dark:bg-medical-900 flex items-center justify-center">
                          <PawPrint className="w-6 h-6 text-medical-500" />
                        </div>}
                    <div>
                      <h3 className="font-semibold text-slate-900 dark:text-white">{pet.name}</h3>
                      <p className="text-sm text-slate-500">{pet.species}{pet.breed ? ` · ${pet.breed}` : ''}{pet.clinic ? ` · ${pet.clinic}` : ''}</p>
                    </div>
                  </div>

                  {/* Vaccinations */}
                  {pet.vaccinations.length > 0 && (
                    <div className="mb-3">
                      <h4 className="text-xs uppercase tracking-wide text-slate-400 mb-1 flex items-center gap-1.5">
                        <Syringe className="w-3.5 h-3.5" /> {t('portal.vaccinations')}
                      </h4>
                      <ul className="text-sm space-y-1">
                        {pet.vaccinations.map((v, i) => (
                          <li key={i} className="flex items-center gap-2 text-slate-700 dark:text-slate-300">
                            <span>{v.vaccine_name}</span>
                            {v.next_due_on && (
                              <span className={v.overdue ? 'text-red-600 dark:text-red-400 font-medium' : 'text-slate-400'}>
                                {v.overdue ? t('portal.overdue', { date: v.next_due_on }) : t('portal.dueOn', { date: v.next_due_on })}
                              </span>
                            )}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Upcoming appointments */}
                  {pet.upcoming_appointments.length > 0 && (
                    <div>
                      <h4 className="text-xs uppercase tracking-wide text-slate-400 mb-1 flex items-center gap-1.5">
                        <CalendarClock className="w-3.5 h-3.5" /> {t('portal.upcoming')}
                      </h4>
                      <ul className="text-sm space-y-1">
                        {pet.upcoming_appointments.map((a, i) => (
                          <li key={i} className="text-slate-700 dark:text-slate-300">
                            {new Date(a.scheduled_at).toLocaleString()} — {t(`portal.apptTypes.${a.appointment_type}`, a.appointment_type)}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Message the clinic */}
                  <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-700">
                    <button
                      className="flex items-center gap-1.5 text-sm font-medium text-medical-600 dark:text-medical-400 hover:underline"
                      onClick={() => setMsgPetId((id) => (id === pet.id ? null : pet.id))}
                    >
                      <MessageSquare className="w-4 h-4" /> {t('portal.messageClinic')}
                    </button>
                    {msgPetId === pet.id && (
                      <div className="mt-3">
                        <MessageThread animalId={pet.id} isOwner />
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </section>

            {/* Shared reports */}
            <section>
              <h2 className="font-semibold text-slate-800 dark:text-slate-200 mb-3">{t('portal.sharedReports')}</h2>
              {data.shared_reports.length === 0 ? (
                <p className="text-slate-500 dark:text-slate-400">{t('portal.noReports')}</p>
              ) : (
                <ul className="space-y-2">
                  {data.shared_reports.map((r, i) => (
                    <li key={i}>
                      <Link to={r.share_path}
                        className="flex items-center gap-3 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 hover:border-medical-400 transition-colors">
                        <FileText className="w-5 h-5 text-medical-500 flex-shrink-0" />
                        <div className="min-w-0">
                          <p className="font-medium text-slate-900 dark:text-white truncate">{r.title}</p>
                          <p className="text-xs text-slate-500">
                            {r.pet_name}{r.approved_at ? ` · ${new Date(r.approved_at).toLocaleDateString()}` : ''}
                          </p>
                        </div>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <div className="flex items-start gap-2 text-xs text-slate-400 leading-relaxed">
              <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <p>{t('portal.disclaimer')}</p>
            </div>
          </>
        )}
      </main>
    </div>
  );
};

export default OwnerPortalPage;
