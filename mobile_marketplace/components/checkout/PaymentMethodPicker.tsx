import React from 'react';
import { View, StyleSheet, TouchableOpacity, ViewStyle } from 'react-native';
import { Text, Icon } from '@/components/ui';
import { useTheme } from '@/hooks/useTheme';

export type PaymentMethod = 'pix' | 'cartao' | 'boleto';

interface PaymentMethodPickerProps {
  selected: PaymentMethod | null;
  onSelect: (method: PaymentMethod) => void;
  pixDiscount?: number;
  style?: ViewStyle;
}

const METHODS: Array<{ key: PaymentMethod; label: string; desc: string; iconName: 'cart' | 'user' | 'clipboard' }> = [
  { key: 'pix', label: 'PIX', desc: 'Aprovação imediata', iconName: 'cart' },
  { key: 'cartao', label: 'Cartão de crédito', desc: 'Parcele em até 12x', iconName: 'clipboard' },
  { key: 'boleto', label: 'Boleto bancário', desc: 'Compensação em 1-3 dias', iconName: 'user' },
];

export function PaymentMethodPicker({ selected, onSelect, pixDiscount, style }: PaymentMethodPickerProps) {
  const { colors, spacing, borderRadius: br, shadow } = useTheme();

  return (
    <View style={style}>
      {METHODS.map((m) => {
        const isSelected = selected === m.key;
        return (
          <TouchableOpacity
            key={m.key}
            onPress={() => onSelect(m.key)}
            accessibilityLabel={m.label}
            accessibilityState={{ selected: isSelected }}
            style={[
              styles.option,
              {
                backgroundColor: colors.surface,
                borderRadius: br.lg,
                borderColor: isSelected ? colors.primary : colors.border,
                borderWidth: isSelected ? 2 : 1,
                padding: spacing.md,
                marginBottom: spacing.sm,
                ...shadow('sm'),
              },
            ]}
          >
            <Icon name={m.iconName} size={24} color={isSelected ? colors.primary : colors.textSecondary} />
            <View style={{ flex: 1, marginLeft: spacing.md }}>
              <View style={styles.labelRow}>
                <Text variant="subtitle2" color={isSelected ? colors.primary : colors.textPrimary}>
                  {m.label}
                </Text>
                {m.key === 'pix' && pixDiscount && pixDiscount > 0 && (
                  <View style={[styles.discountBadge, { backgroundColor: colors.successSurface, borderRadius: br.sm }]}>
                    <Text variant="caption" color={colors.success} style={{ fontWeight: '600' }}>
                      {pixDiscount}% OFF
                    </Text>
                  </View>
                )}
              </View>
              <Text variant="caption" color={colors.textSecondary}>
                {m.desc}
              </Text>
            </View>
            {isSelected && <Icon name="check" size={20} color={colors.primary} />}
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  option: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  labelRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  discountBadge: {
    paddingHorizontal: 6,
    paddingVertical: 2,
  },
});
