// Export all contexts from a single file for easy importing
export { ThemeProvider, useTheme } from './ThemeContext';
export type { Theme, ThemeContextType, ThemeProviderProps } from './ThemeContext';

export { AuthProvider, useAuth } from './AuthContext';

export { LanguageProvider, useLanguage } from './LanguageContext';
export type { Language, LanguageContextType } from './LanguageContext';
export { SUPPORTED_LANGUAGES } from './LanguageContext';