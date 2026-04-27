import { TextStyle } from 'react-native';

export const fontFamily = {
  regular: 'Inter_400Regular',
  medium: 'Inter_500Medium',
  semiBold: 'Inter_600SemiBold',
  bold: 'Inter_700Bold',
};

export const fontSize = {
  xs: 11,
  sm: 13,
  md: 15,
  lg: 17,
  xl: 20,
  '2xl': 24,
  '3xl': 30,
  '4xl': 36,
};

export const lineHeight = {
  xs: 16,
  sm: 18,
  md: 22,
  lg: 24,
  xl: 28,
  '2xl': 32,
  '3xl': 38,
  '4xl': 44,
};

export const typography: Record<string, TextStyle> = {
  h1: { fontFamily: fontFamily.bold, fontSize: fontSize['4xl'], lineHeight: lineHeight['4xl'] },
  h2: { fontFamily: fontFamily.bold, fontSize: fontSize['3xl'], lineHeight: lineHeight['3xl'] },
  h3: { fontFamily: fontFamily.bold, fontSize: fontSize['2xl'], lineHeight: lineHeight['2xl'] },
  h4: { fontFamily: fontFamily.semiBold, fontSize: fontSize.xl, lineHeight: lineHeight.xl },
  subtitle1: { fontFamily: fontFamily.semiBold, fontSize: fontSize.lg, lineHeight: lineHeight.lg },
  subtitle2: { fontFamily: fontFamily.medium, fontSize: fontSize.md, lineHeight: lineHeight.md },
  body1: { fontFamily: fontFamily.regular, fontSize: fontSize.md, lineHeight: lineHeight.md },
  body2: { fontFamily: fontFamily.regular, fontSize: fontSize.sm, lineHeight: lineHeight.sm },
  button: { fontFamily: fontFamily.semiBold, fontSize: fontSize.md, lineHeight: lineHeight.md },
  caption: { fontFamily: fontFamily.regular, fontSize: fontSize.xs, lineHeight: lineHeight.xs },
  overline: {
    fontFamily: fontFamily.medium,
    fontSize: fontSize.xs,
    lineHeight: lineHeight.xs,
    textTransform: 'uppercase',
    letterSpacing: 1.2,
  },
  price: { fontFamily: fontFamily.bold, fontSize: fontSize.xl, lineHeight: lineHeight.xl },
  priceSmall: { fontFamily: fontFamily.semiBold, fontSize: fontSize.md, lineHeight: lineHeight.md },
  priceStrike: {
    fontFamily: fontFamily.regular,
    fontSize: fontSize.sm,
    lineHeight: lineHeight.sm,
    textDecorationLine: 'line-through',
  },
};

export type TypographyKey = keyof typeof typography;
