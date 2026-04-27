const palette = {
  blue50: '#eaf2f8',
  blue100: '#d4e6f1',
  blue200: '#a9cce3',
  blue300: '#7fb3d5',
  blue400: '#5dade2',
  blue500: '#2980b9',
  blue600: '#2471a3',
  blue700: '#1a5276',
  blue800: '#154360',
  blue900: '#0e2f44',

  green50: '#e8f8f0',
  green500: '#27ae60',
  green700: '#1e8449',

  red50: '#fdedec',
  red500: '#e74c3c',
  red700: '#c0392b',

  yellow50: '#fef9e7',
  yellow500: '#f39c12',
  yellow700: '#d68910',

  gray50: '#fafafa',
  gray100: '#f5f5f5',
  gray200: '#eeeeee',
  gray300: '#e0e0e0',
  gray400: '#bdbdbd',
  gray500: '#9e9e9e',
  gray600: '#757575',
  gray700: '#616161',
  gray800: '#424242',
  gray900: '#212121',

  white: '#ffffff',
  black: '#000000',
  transparent: 'transparent',
};

export const lightColors = {
  primary: palette.blue500,
  primaryDark: palette.blue700,
  primaryLight: palette.blue400,
  primarySurface: palette.blue50,

  secondary: palette.green500,
  secondaryDark: palette.green700,

  accent: palette.red500,
  accentDark: palette.red700,
  accentSurface: palette.red50,

  warning: palette.yellow500,
  warningDark: palette.yellow700,
  warningSurface: palette.yellow50,

  success: palette.green500,
  successSurface: palette.green50,

  error: palette.red500,
  errorSurface: palette.red50,

  background: palette.gray100,
  surface: palette.white,
  surfaceVariant: palette.gray50,

  textPrimary: palette.gray900,
  textSecondary: palette.gray600,
  textDisabled: palette.gray400,
  textInverse: palette.white,
  textLink: palette.blue500,

  border: palette.gray300,
  borderLight: palette.gray200,
  divider: palette.gray200,

  skeleton: palette.gray200,
  skeletonHighlight: palette.gray100,

  overlay: 'rgba(0,0,0,0.5)',
  shadow: 'rgba(0,0,0,0.1)',

  tabBarActive: palette.blue500,
  tabBarInactive: palette.gray500,
  tabBarBackground: palette.white,

  statusBar: palette.blue700,

  ...palette,
};

export const darkColors: typeof lightColors = {
  ...lightColors,

  primary: palette.blue400,
  primaryDark: palette.blue500,
  primaryLight: palette.blue300,
  primarySurface: palette.blue900,

  secondaryDark: palette.green500,
  accentDark: palette.red500,

  background: '#121212',
  surface: '#1e1e1e',
  surfaceVariant: '#2c2c2c',

  textPrimary: '#e0e0e0',
  textSecondary: '#a0a0a0',
  textDisabled: '#666666',
  textInverse: palette.gray900,

  border: '#333333',
  borderLight: '#2a2a2a',
  divider: '#2a2a2a',

  skeleton: '#2c2c2c',
  skeletonHighlight: '#383838',

  overlay: 'rgba(0,0,0,0.7)',
  shadow: 'rgba(0,0,0,0.3)',

  tabBarBackground: '#1e1e1e',
  statusBar: '#121212',
};

export type AppColors = typeof lightColors;
