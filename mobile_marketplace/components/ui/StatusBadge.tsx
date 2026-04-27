import React from 'react';
import { View, StyleSheet, ViewStyle } from 'react-native';
import { Text } from './Text';
import { useTheme } from '@/hooks/useTheme';

type OrderStatus =
  | 'PENDENTE'
  | 'PAGO'
  | 'PREPARANDO'
  | 'ENVIADO'
  | 'ENTREGUE'
  | 'CANCELADO'
  | 'DEVOLVIDO';

interface StatusBadgeProps {
  status: OrderStatus | string;
  style?: ViewStyle;
}

const STATUS_CONFIG: Record<string, { label: string; variant: 'success' | 'warning' | 'error' | 'info' | 'neutral' }> = {
  PENDENTE: { label: 'Pendente', variant: 'warning' },
  PAGO: { label: 'Pago', variant: 'info' },
  PREPARANDO: { label: 'Preparando', variant: 'info' },
  ENVIADO: { label: 'Enviado', variant: 'info' },
  ENTREGUE: { label: 'Entregue', variant: 'success' },
  CANCELADO: { label: 'Cancelado', variant: 'error' },
  DEVOLVIDO: { label: 'Devolvido', variant: 'neutral' },
};

export function StatusBadge({ status, style }: StatusBadgeProps) {
  const { colors, borderRadius: br } = useTheme();

  const config = STATUS_CONFIG[status] ?? { label: status, variant: 'neutral' as const };

  const colorMap = {
    success: { bg: colors.successSurface, text: colors.success },
    warning: { bg: colors.warningSurface, text: colors.warningDark },
    error: { bg: colors.errorSurface, text: colors.error },
    info: { bg: colors.primarySurface, text: colors.primary },
    neutral: { bg: colors.gray200, text: colors.textSecondary },
  };

  const c = colorMap[config.variant];

  return (
    <View
      style={[
        styles.container,
        { backgroundColor: c.bg, borderRadius: br.sm },
        style,
      ]}
      accessibilityLabel={`Status: ${config.label}`}
    >
      <Text variant="caption" color={c.text} style={styles.text}>
        {config.label}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    alignSelf: 'flex-start',
  },
  text: {
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    fontSize: 10,
  },
});
