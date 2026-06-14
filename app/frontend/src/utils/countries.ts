/**
 * ISO 3166-1 alpha-2 country codes + locale-aware naming.
 *
 * We store the compact 2-letter code and render the display name via the
 * platform's `Intl.DisplayNames` so country names are automatically localized
 * (en/es/pt…) without bundling a translation table. This harmonises owner
 * country data to a canonical code while keeping the UI a searchable dropdown.
 */

// Full ISO 3166-1 alpha-2 set (kept as a compact whitespace list).
const CODES = (
  'AD AE AF AG AI AL AM AO AQ AR AS AT AU AW AX AZ ' +
  'BA BB BD BE BF BG BH BI BJ BL BM BN BO BQ BR BS BT BV BW BY BZ ' +
  'CA CC CD CF CG CH CI CK CL CM CN CO CR CU CV CW CX CY CZ ' +
  'DE DJ DK DM DO DZ ' +
  'EC EE EG EH ER ES ET ' +
  'FI FJ FK FM FO FR ' +
  'GA GB GD GE GF GG GH GI GL GM GN GP GQ GR GS GT GU GW GY ' +
  'HK HM HN HR HT HU ' +
  'ID IE IL IM IN IO IQ IR IS IT ' +
  'JE JM JO JP ' +
  'KE KG KH KI KM KN KP KR KW KY KZ ' +
  'LA LB LC LI LK LR LS LT LU LV LY ' +
  'MA MC MD ME MF MG MH MK ML MM MN MO MP MQ MR MS MT MU MV MW MX MY MZ ' +
  'NA NC NE NF NG NI NL NO NP NR NU NZ ' +
  'OM ' +
  'PA PE PF PG PH PK PL PM PN PR PS PT PW PY ' +
  'QA ' +
  'RE RO RS RU RW ' +
  'SA SB SC SD SE SG SH SI SJ SK SL SM SN SO SR SS ST SV SX SY SZ ' +
  'TC TD TF TG TH TJ TK TL TM TN TO TR TT TV TW TZ ' +
  'UA UG UM US UY UZ ' +
  'VA VC VE VG VI VN VU ' +
  'WF WS ' +
  'YE YT ' +
  'ZA ZM ZW'
).trim().split(/\s+/);

export const COUNTRY_CODES: readonly string[] = CODES;

/** Localized country name for an alpha-2 code (falls back to the code). */
export function countryName(code: string, lang?: string): string {
  if (!code) return '';
  try {
    const dn = new Intl.DisplayNames([lang || 'en'], { type: 'region' });
    return dn.of(code.toUpperCase()) || code;
  } catch {
    return code;
  }
}

/** Country options sorted by localized name, for a select dropdown. */
export function countryOptions(lang?: string): { code: string; name: string }[] {
  return COUNTRY_CODES
    .map((code) => ({ code, name: countryName(code, lang) }))
    .sort((a, b) => a.name.localeCompare(b.name, lang));
}

/** True if a value is a known ISO alpha-2 country code (or empty). */
export function isValidCountryCode(code: string): boolean {
  return code === '' || COUNTRY_CODES.includes(code.toUpperCase());
}
