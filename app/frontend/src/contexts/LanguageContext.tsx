import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import i18n from '../i18n';

export interface Language {
  code: string;
  name: string;
  flag: string;
}

// Context + hook co-location is intentional here (standard pattern across
// this codebase's contexts); Fast Refresh works slightly worse for it but
// that's an accepted tradeoff, not a bug.
// eslint-disable-next-line react-refresh/only-export-components
export const SUPPORTED_LANGUAGES: Language[] = [
  { code: 'en', name: 'English', flag: '🇺🇸' },
  { code: 'es', name: 'Español', flag: '🇪🇸' },
  { code: 'pt', name: 'Português', flag: '🇧🇷' },
];

export interface LanguageContextType {
  currentLanguage: string;
  setLanguage: (code: string) => void;
  languages: Language[];
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export const LanguageProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentLanguage, setCurrentLanguage] = useState(i18n.language?.substring(0, 2) || 'en');

  const setLanguage = useCallback((code: string) => {
    i18n.changeLanguage(code);
    localStorage.setItem('medai-language', code);
    document.documentElement.lang = code;
    setCurrentLanguage(code);
  }, []);

  // Sync state when i18n language changes externally (e.g. from AuthContext)
  useEffect(() => {
    const handleLanguageChanged = (lng: string) => {
      const code = lng.substring(0, 2);
      setCurrentLanguage(code);
      document.documentElement.lang = code;
    };

    i18n.on('languageChanged', handleLanguageChanged);
    return () => {
      i18n.off('languageChanged', handleLanguageChanged);
    };
  }, []);

  // Set initial document lang only — the sync effect above already keeps
  // it updated on every subsequent language change.
  useEffect(() => {
    document.documentElement.lang = currentLanguage;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <LanguageContext.Provider
      value={{
        currentLanguage,
        setLanguage,
        languages: SUPPORTED_LANGUAGES,
      }}
    >
      {children}
    </LanguageContext.Provider>
  );
};

// eslint-disable-next-line react-refresh/only-export-components
export const useLanguage = (): LanguageContextType => {
  const context = useContext(LanguageContext);
  if (context === undefined) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
};
