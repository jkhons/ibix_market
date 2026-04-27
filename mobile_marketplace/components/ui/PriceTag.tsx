import React from 'react';
import { View, StyleSheet, ViewStyle } from 'react-native';
import { Text } from './Text';
import { useTheme } from '@/hooks/useTheme';
import { formatCurrency, calculateDiscount } from '@/utils/format';

interface PriceTagProps {
  price: number;
  originalPrice?: number;
  installments?: number;
  installmentValue?: number;
  size?: 'sm' | 'md' | 'lg';
  style?: ViewStyle;
}

export function PriceTag({
  price,
  originalPrice,
  installments,
  installmentValue,
  size = 'md',
  style,
}: PriceTagProps) {
  const { colors, spacing } = useTheme();

  const hasDiscount = originalPrice && originalPrice > price;
  const discountPercent = hasDiscount ? calculateDiscount(originalPrice, price) : 0;

  const priceVariant = size === 'lg' ? 'price' : size === 'md' ? 'priceSmall' : 'body2';

  return (
    <View style={[styles.container, style]} accessibilityLabel={`Preço ${formatCurrency(price)}`}>
      {hasDiscount && (
        <View style={styles.discountRow}>
          <Text variant="priceStrike" color={colors.textDisabled}>
            {formatCurrency(originalPrice)}
          </Text>
          <View
            style={[
              styles.discountBadge,
              { backgroundColor: colors.accentSurface, marginLeft: spacing.xs },
            ]}
          >
            <Text variant="caption" color={colors.accent}>
              -{discountPercent}%
            </Text>
          </View>
        </View>
      )}
      <Text variant={priceVariant} color={hasDiscount ? colors.success : colors.textPrimary}>
        {formatCurrency(price)}
      </Text>
      {installments && installments > 1 && installmentValue && (
        <Text variant="caption" color={colors.textSecondary} style={{ marginTop: 2 }}>
          {installments}x de {formatCurrency(installmentValue)} sem juros
        </Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {},
  discountRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  discountBadge: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
  },
});
