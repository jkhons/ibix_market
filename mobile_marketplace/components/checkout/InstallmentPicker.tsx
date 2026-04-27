import React from 'react';
import { View, StyleSheet, TouchableOpacity, ScrollView, ViewStyle } from 'react-native';
import { Text } from '@/components/ui';
import { useTheme } from '@/hooks/useTheme';
import { formatCurrency } from '@/utils/format';
import type { Installment } from '@/services/catalogService';

interface InstallmentPickerProps {
  installments: Installment[];
  selected: number | null;
  onSelect: (qtd: number) => void;
  style?: ViewStyle;
}

export function InstallmentPicker({ installments, selected, onSelect, style }: InstallmentPickerProps) {
  const { colors, spacing, borderRadius: br } = useTheme();

  return (
    <ScrollView style={style} showsVerticalScrollIndicator={false}>
      {installments.map((inst) => {
        const isSelected = selected === inst.parcelas;
        const total = inst.total ?? inst.valor_parcela * inst.parcelas;
        return (
          <TouchableOpacity
            key={inst.parcelas}
            onPress={() => onSelect(inst.parcelas)}
            accessibilityLabel={`${inst.parcelas}x de ${formatCurrency(inst.valor_parcela)}`}
            accessibilityState={{ selected: isSelected }}
            style={[
              styles.row,
              {
                borderColor: isSelected ? colors.primary : colors.divider,
                borderWidth: isSelected ? 2 : 1,
                borderRadius: br.md,
                padding: spacing.md,
                marginBottom: spacing.xs,
                backgroundColor: isSelected ? colors.primarySurface : colors.surface,
              },
            ]}
          >
            <View style={{ flex: 1 }}>
              <Text variant="body1" color={isSelected ? colors.primary : colors.textPrimary}>
                {inst.parcelas}x de {formatCurrency(inst.valor_parcela)}
              </Text>
              {inst.parcelas > 1 && (
                <Text variant="caption" color={colors.textSecondary}>
                  Total: {formatCurrency(total)}
                </Text>
              )}
            </View>
            <Text
              variant="caption"
              color={inst.juros ? colors.warning : colors.success}
              style={{ fontWeight: '600' }}
            >
              {inst.juros ? 'com juros' : 'sem juros'}
            </Text>
          </TouchableOpacity>
        );
      })}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
  },
});
