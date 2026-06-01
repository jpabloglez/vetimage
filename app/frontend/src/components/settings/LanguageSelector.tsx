/**
 * Language Selector Component
 *
 * Allows users to switch between supported languages (EN/ES/PT).
 * Integrates with react-i18next via the LanguageContext.
 */

import React from 'react';
import { Check } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { useLanguage } from '../../contexts/LanguageContext';

export const LanguageSelector: React.FC = () => {
  const { currentLanguage, setLanguage, languages } = useLanguage();

  const handleLanguageChange = (languageCode: string) => {
    setLanguage(languageCode);
    const language = languages.find(lang => lang.code === languageCode);
    toast.success(`${language?.flag} ${language?.name}`, {
      duration: 2000
    });
  };

  return (
    <div className="py-1">
      {languages.map((language) => (
        <button
          key={language.code}
          onClick={() => handleLanguageChange(language.code)}
          className={`
            w-full flex items-center justify-between px-4 py-2
            text-sm transition-colors duration-150
            ${currentLanguage === language.code
              ? 'bg-medical-50 dark:bg-medical-900/20 text-medical-600 dark:text-medical-400'
              : 'text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700/50'
            }
          `}
        >
          <span className="flex items-center gap-2">
            <span className="text-lg">{language.flag}</span>
            <span>{language.name}</span>
          </span>
          {currentLanguage === language.code && (
            <Check className="w-4 h-4 text-medical-600 dark:text-medical-400" />
          )}
        </button>
      ))}
    </div>
  );
};
