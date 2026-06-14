/**
 * OwnerPicker — searchable owner selector for the standalone "new patient" flow,
 * so a patient can be created and attached to an owner in one step.
 */
import React, { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Search, User } from 'lucide-react';
import { apiClient, type Owner } from '../../utils/api';

interface OwnerPickerProps {
  onSelect: (owner: Owner) => void;
  autoFocus?: boolean;
}

const OwnerPicker: React.FC<OwnerPickerProps> = ({ onSelect, autoFocus }) => {
  const { t } = useTranslation('patients');
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<Owner[]>([]);
  const [loading, setLoading] = useState(false);
  const debounce = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    clearTimeout(debounce.current);
    debounce.current = setTimeout(async () => {
      setLoading(true);
      try {
        setResults(await apiClient.getOwners(query || undefined));
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
          placeholder={t('ownerPicker.placeholder')}
          aria-label={t('ownerPicker.placeholder')}
          className="w-full pl-9 pr-3 py-2 border border-slate-300 dark:border-slate-600 rounded-medical bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-medical-500"
        />
      </div>
      <div className="max-h-48 overflow-y-auto border border-slate-200 dark:border-slate-700 rounded-medical divide-y divide-slate-100 dark:divide-slate-700">
        {loading && <p className="px-3 py-2 text-sm text-slate-400">{t('picker.loading')}</p>}
        {!loading && results.length === 0 && (
          <p className="px-3 py-2 text-sm text-slate-400">{t('ownerPicker.noResults')}</p>
        )}
        {results.map((o) => (
          <button
            key={o.id}
            type="button"
            onClick={() => onSelect(o)}
            className="w-full flex items-center gap-3 px-3 py-2 text-left hover:bg-medical-50 dark:hover:bg-medical-900/20 transition-colors"
          >
            <User className="w-4 h-4 text-slate-500 flex-shrink-0" />
            <span className="flex-1 min-w-0">
              <span className="block font-medium text-slate-800 dark:text-slate-100 truncate">{o.first_name} {o.last_name}</span>
              {(o.email || o.phone) && <span className="block text-xs text-slate-500 truncate">{o.email || o.phone}</span>}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
};

export default OwnerPicker;
