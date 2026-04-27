import React from 'react';
import { View, StyleSheet, ViewStyle } from 'react-native';
import { Text } from './Text';
import { useTheme } from '@/hooks/useTheme';

type BadgeVariant = 'primary' | 'success' | 'warning' | 'error' | 'info' | 'neutral';

interface BadgeProps {
  label?: string;
  count?: number;
  variant?: BadgeVariant;
  size?: 'sm' | 'md';
  dot?: boolean;
  style?: ViewStyle;
}

export function Badge({ label, count, variant = 'primary', size = 'md', dot = false, style }: BadgeProps) {
  const { colors, borderRadius: br } = useTheme();

  const variantColors: Record<BadgeVariant, { bg: string; text: string }> = {
    primary: { bg: colors.primary, text: colors.textInverse },
    success: { bg: colors.success, text: colors.textInverse },
    warning: { bg: colors.warning, text: colors.textInverse },
    error: { bg: colors.error, text: colors.textInverse },
    info: { bg: colors.primarySurface, text: colors.primary },
    neutral: { bg: colors.gray200, text: colors.textSecondary },
  };

  const v = variantColors[variant];

  if (dot) {
    return (
      <View
        style={[styles.dot, { backgroundColor: v.bg }, style]}
        accessibilityLabel={label ?? `${variant} indicator`}
      />
    );
  }

  const displayText = count !== undefined ? (count > 99 ? '99+' : String(count)) : label;
  if (!displayText) return null;

  const isSingle = displayText.length === 1;
  const isSmall = size === 'sm';
  const height = isSmall ? 18 : 22;

  return (
    <View
      style={[
        styles.badge,
        {
          backgroundColor: v.bg,
          borderRadius: br.full,
          height,
          minWidth: isSingle ? height : height + 8,
          paddingHorizontal: isSingle ? 0 : isSmall ? 5 : 7,
        },
        style,
      ]}
      accessibilityLabel={`${displayText} ${label ?? ''}`}
    >
      <Text variant="caption" color={v.text} style={isSmall ? styles.textSm : styles.textMd}>
        {displayText}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  badge: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  textSm: {
    fontSize: 10,
    lineHeight: 14,
    fontWeight: '700',
  },
  textMd: {
    fontSize: 11,
    lineHeight: 16,
    fontWeight: '700',
  },
});
