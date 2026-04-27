import React, { createContext, useContext, useMemo } from 'react';
import { useColorScheme } from 'react-native';
import { lightColors, darkColors, AppColors } from '@/theme/colors';
import { typography, fontFamily, fontSize, lineHeight } from '@/theme/typography';
import { spacing, borderRadius, iconSize, hitSlop } from '@/theme/spacing';
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
  shadow: typeof shadow;
  isDark: boolean;
}

const ThemeContext = createContext<Theme | null>(null);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const colorScheme = useColorScheme();
  const isDark = colorScheme === 'dark';

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
