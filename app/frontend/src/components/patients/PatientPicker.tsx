/**
 * PatientPicker — a searchable Animal Patient selector.
 *
 * Debounced search over /api/patients/animals/ (name, breed, microchip, owner).
 * Used to assign a DICOM study to a veterinary patient (study↔patient linking).
 */
import React, { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Search, PawPrint, X } from 'lucide-react';
import { apiClient, type AnimalPatientListItem } from '../../utils/api';

const SPECIES_EMOJI: Record<string, string> = {
  canine: '🐕', feline: '🐈', equine: '🐎', bovine: '🐄',
  avian: '🦜', exotic: '🦎', other: '🐾',
};

interface PatientPickerProps {
  onSelect: (animal: AnimalPatientListItem) => void;
  onClear?: () => void;
  autoFocus?: boolean;
  placeholder?: string;
}

const PatientPicker: React.FC<PatientPickerProps> = ({ onSelect, onClear, autoFocus, placeholder }) => {
  const { t } = useTranslation('patients');
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<AnimalPatientListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const debounce = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    clearTimeout(debounce.current);
    debounce.current = setTimeout(async () => {
      setLoading(true);
      try {
        setResults(await apiClient.getAnimals({ search: query || undefined }));
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 250);
    return () => clearTimeout(debounce.current);
  }, [query]);

  return (
    <div>
      <div className="relative mb-2">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
        <input
          autoFocus={autoFocus}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={placeholder ?? t('picker.placeholder', 'Search patients by name, microchip, owner…')}
          className="w-full pl-9 pr-8 py-2 border border-slate-300 dark:border-slate-600 rounded-medical bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-medical-500"
          aria-label={t('picker.placeholder', 'Search patients')}
        />
        {onClear && (
          <button
            type="button"
            onClick={onClear}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-error-500"
            title={t('picker.unassign', 'Unassign')}
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      <div className="max-h-56 overflow-y-auto border border-slate-200 dark:border-slate-700 rounded-medical divide-y divide-slate-100 dark:divide-slate-700">
        {loading && <p className="px-3 py-2 text-sm text-slate-400">{t('picker.loading', 'Searching…')}</p>}
        {!loading && results.length === 0 && (
          <p className="px-3 py-2 text-sm text-slate-400">{t('picker.noResults', 'No patients found')}</p>
        )}
        {results.map((a) => (
          <button
            key={a.id}
            type="button"
            onClick={() => onSelect(a)}
            className="w-full flex items-center gap-3 px-3 py-2 text-left hover:bg-medical-50 dark:hover:bg-medical-900/20 transition-colors"
          >
            <span className="text-lg">{SPECIES_EMOJI[a.species] ?? '🐾'}</span>
            <span className="flex-1 min-w-0">
              <span className="block font-medium text-slate-800 dark:text-slate-100 truncate">{a.name}</span>
              <span className="block text-xs text-slate-500 truncate">
                {a.breed ? `${a.breed} · ` : ''}{a.owner_name}
              </span>
            </span>
            <PawPrint className="w-4 h-4 text-medical-500 flex-shrink-0" />
          </button>
        ))}
      </div>
    </div>
  );
};

export default PatientPicker;
