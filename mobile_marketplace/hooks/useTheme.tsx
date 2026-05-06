import React, { createContext, useContext, useMemo } from 'react';
import { useColorScheme } from 'react-native';
import { lightColors, darkColors, AppColors } from '@/theme/colors';
import { typography, fontFamily, fontSize, lineHeight } from '@/theme/typography';
import { spacing, borderRadius, iconSize, hitSlop, focusRing } from '@/theme/spacing';
import { shadow } from '@/theme/shadows';

export interface Theme {
  colors: AppColors;
  typography: typeof typography;
  fontFamily: typeof fontFamily;
  fontSize: typeof fontSize;
  lineHeight: typeof lineHeight;
  spacing: typeof spacing;
  borderRadius: typeof borderRadius;
  iconSize: typeof iconSize;
  hitSlop: typeof hitSlop;
  focusRing: typeof focusRing;
  shadow: typeof shadow;
  isDark: boolean;
}

const ThemeContext = createContext<Theme | null>(null);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const colorScheme = useColorScheme();
  // Identidade visual canônica do Marketplace é clara (vitrine web).
  // Dark mode fica desativado por padrão até existir preferência explícita.
  const enableDarkMode = process.env.EXPO_PUBLIC_ENABLE_DARK_MODE === 'true';
  const isDark = enableDarkMode ? colorScheme === 'dark' : false;

  const theme = useMemo<Theme>(
    () => ({
      colors: isDark ? darkColors : lightColors,
      typography,
      fontFamily,
      fontSize,
      lineHeight,
      spacing,
      borderRadius,
      iconSize,
      hitSlop,
      focusRing,
      shadow,
      isDark,
    }),
    [isDark],
  );

  return <ThemeContext.Provider value={theme}>{children}</ThemeContext.Provider>;
}

export function useTheme(): Theme {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useTheme must be within ThemeProvider');
  return ctx;
}
