import React from 'react';
import { Text as RNText, TextProps as RNTextProps, StyleSheet } from 'react-native';
import { useTheme } from '@/hooks/useTheme';
import { TypographyKey } from '@/theme';

interface TextProps extends RNTextProps {
  variant?: TypographyKey;
  color?: string;
  align?: 'auto' | 'left' | 'right' | 'center' | 'justify';
}

export function Text({ variant = 'body1', color, align, style, children, ...props }: TextProps) {
  const { colors, typography } = useTheme();
  const typo = typography[variant] ?? typography.body1;

  return (
    <RNText
      style={[
        typo,
        { color: color ?? colors.textPrimary },
        align ? { textAlign: align } : undefined,
        style,
      ]}
      {...props}
    >
      {children}
    </RNText>
  );
}
