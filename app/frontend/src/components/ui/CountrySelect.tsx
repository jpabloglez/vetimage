/**
 * CountrySelect — a localized ISO-3166 country dropdown that stores the alpha-2
 * code, harmonising owner country data. Names are localized to the active i18n
 * language via Intl.DisplayNames.
 */
import React, { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { countryOptions } from '../../utils/countries';

interface CountrySelectProps {
  label?: string;
  value?: string;
  onChange: (code: string) => void;
  placeholder?: string;
  id?: string;
}

const CountrySelect: React.FC<CountrySelectProps> = ({ label, value, onChange, placeholder, id }) => {
  const { i18n } = useTranslation();
  const options = useMemo(() => countryOptions(i18n.language), [i18n.language]);
  const selectId = id || 'country-select';

  return (
    <div>
      {label && (
        <label htmlFor={selectId} className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
          {label}
        </label>
      )}
      <select
        id={selectId}
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-medical bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-medical-500"
      >
        <option value="">{placeholder ?? '—'}</option>
        {options.map((o) => (
          <option key={o.code} value={o.code}>{o.name}</option>
        ))}
      </select>
    </div>
  );
};

export default CountrySelect;
