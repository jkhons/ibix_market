/**
 * Paleta canônica Ibix Market — espelho de `app/static/css/loja.css` (vitrine web).
 * Fonte de verdade: tokens `--ibix-*` da vitrine. NÃO inventar cores neste app.
 * Se a vitrine mudar, este arquivo muda — e vice-versa NUNCA acontece.
 */

// Tokens canônicos da vitrine (`loja.css:9-18`)
const IBIX_BG = '#FEF7F1';
const IBIX_SURFACE = '#FFFFFF';
const IBIX_TEXT = '#4A627A';
const IBIX_TEXT_STRONG = '#2F3A44';
const IBIX_ACTION = '#5C6E4A';
const IBIX_ACTION_HOVER = '#4E5F40';
const IBIX_HOVER = '#C47A44';
const IBIX_PREMIUM = '#D9B48B';
const IBIX_BORDER = 'rgba(47,58,68,0.14)';

// Variações utilitárias derivadas — neutros warm-tone alinhados com off-white
const SURFACE_MUTED = '#F5EDE3';
const SURFACE_SOFT = '#F8E9DC';
const SUCCESS_SURFACE = '#E6EDDF';
const WARNING_SURFACE = '#FBEDD9';
const ERROR_SURFACE = '#FBE6DD';
const ERROR = '#B5453A';

export const lightColors = {
  primary: IBIX_ACTION,
  primaryDark: IBIX_ACTION_HOVER,
  primaryLight: IBIX_PREMIUM,
  primarySurface: SUCCESS_SURFACE,

  secondary: IBIX_HOVER,
  secondaryDark: '#B16A38',

  accent: IBIX_HOVER,
  accentDark: '#B16A38',
  accentSurface: ERROR_SURFACE,

  premium: IBIX_PREMIUM,
  premiumSurface: SURFACE_SOFT,

  warning: IBIX_HOVER,
  warningDark: '#B16A38',
  warningSurface: WARNING_SURFACE,

  success: IBIX_ACTION,
  successSurface: SUCCESS_SURFACE,

  error: ERROR,
  errorSurface: ERROR_SURFACE,

  background: IBIX_BG,
  surface: IBIX_SURFACE,
  surfaceVariant: SURFACE_MUTED,
  surfaceStrip: 'rgba(44,62,80,0.06)',
  surfaceTrust: 'rgba(47,58,68,0.04)',

  textPrimary: IBIX_TEXT_STRONG,
  textSecondary: IBIX_TEXT,
  textSoft: '#3B5166',
  textDisabled: 'rgba(47,58,68,0.45)',
  textInverse: IBIX_SURFACE,
  textLink: IBIX_HOVER,

  border: IBIX_BORDER,
  borderLight: 'rgba(47,58,68,0.08)',
  borderStrong: 'rgba(47,58,68,0.24)',
  divider: 'rgba(47,58,68,0.08)',

  skeleton: 'rgba(47,58,68,0.10)',
  skeletonHighlight: 'rgba(47,58,68,0.04)',

  overlay: 'rgba(47,58,68,0.55)',
  shadow: 'rgba(47,58,68,0.12)',

  tabBarActive: IBIX_ACTION,
  tabBarInactive: IBIX_TEXT,
  tabBarBackground: IBIX_SURFACE,

  focusRing: IBIX_HOVER,
  statusBar: IBIX_BG,

  white: '#FFFFFF',
  black: '#000000',
  transparent: 'transparent',

  /**
   * Aliases neutros para retrocompatibilidade (Button, Badge, etc.).
   * Tons quentes alinhados com a paleta off-white/dourado da vitrine.
   * Para uso novo, prefira tokens semânticos (`border`, `divider`, `textDisabled`...).
   */
  gray50: '#FBF5EE',
  gray100: '#F5EDE3',
  gray200: '#EBE0D2',
  gray300: '#D8CDC0',
  gray400: '#B5AB9F',
  gray500: '#8E8579',
  gray600: '#6E665B',
  gray700: '#534D44',
  gray800: '#3B3835',
  gray900: IBIX_TEXT_STRONG,
};

export const darkColors: typeof lightColors = {
  ...lightColors,

  primary: '#7C9165',
  primaryDark: IBIX_ACTION,
  primarySurface: '#26312B',

  accent: IBIX_HOVER,
  accentSurface: '#3C2418',

  premium: IBIX_PREMIUM,
  premiumSurface: '#3A2C1B',

  background: '#1B1F22',
  surface: '#262B30',
  surfaceVariant: '#30363B',
  surfaceStrip: 'rgba(255,255,255,0.04)',
  surfaceTrust: 'rgba(255,255,255,0.03)',

  textPrimary: '#ECE4D9',
  textSecondary: '#C7C0B5',
  textSoft: '#A9A296',
  textDisabled: 'rgba(236,228,217,0.45)',
  textInverse: IBIX_TEXT_STRONG,
  textLink: IBIX_PREMIUM,

  border: 'rgba(236,228,217,0.16)',
  borderLight: 'rgba(236,228,217,0.08)',
  borderStrong: 'rgba(236,228,217,0.28)',
  divider: 'rgba(236,228,217,0.10)',

  skeleton: 'rgba(236,228,217,0.10)',
  skeletonHighlight: 'rgba(236,228,217,0.04)',

  overlay: 'rgba(0,0,0,0.65)',
  shadow: 'rgba(0,0,0,0.45)',

  tabBarBackground: '#262B30',
  statusBar: '#1B1F22',

  focusRing: IBIX_PREMIUM,

  gray50: '#2C3036',
  gray100: '#30363B',
  gray200: '#3A4148',
  gray300: '#4B5260',
  gray400: '#6F7681',
  gray500: '#8E96A1',
  gray600: '#A9B0BB',
  gray700: '#C7CDD6',
  gray800: '#DDE2E9',
  gray900: '#ECE4D9',
};

export type AppColors = typeof lightColors;
