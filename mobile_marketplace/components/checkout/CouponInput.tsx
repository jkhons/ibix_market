import React, { useState } from 'react';
import { View, StyleSheet, TextInput, ViewStyle } from 'react-native';
import { Text, Button } from '@/components/ui';
import { useTheme } from '@/hooks/useTheme';
import couponService, { type CouponValidation } from '@/services/couponService';
import { extractApiError } from '@/services/api';

interface CouponInputProps {
  cartTotal: number;
  cartItems?: Array<{ anuncio_id: number; quantidade: number; preco_unitario: number }>;
  onApplied: (result: CouponValidation & { codigo: string }) => void;
  onRemove: () => void;
  appliedCode?: string;
  style?: ViewStyle;
}

export function CouponInput({ cartTotal, cartItems, onApplied, onRemove, appliedCode, style }: CouponInputProps) {
  const { colors, spacing, borderRadius: br, fontFamily, fontSize } = useTheme();
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleApply = async () => {
    const trimmed = code.trim().toUpperCase();
    if (!trimmed) return;
    setLoading(true);
    setError('');
    try {
      const result = await couponService.validate({
        codigo: trimmed,
        itens: cartItems,
        valor_total: cartTotal,
      });
      if (!result.valido) {
        setError(result.mensagem ?? 'Cupom inválido');
      } else {
        onApplied({ ...result, codigo: trimmed });
        setCode('');
      }
    } catch (err) {
      setError(extractApiError(err));
    } finally {
      setLoading(false);
    }
  };

  if (appliedCode) {
    return (
      <View style={[styles.applied, { backgroundColor: colors.successSurface, borderRadius: br.md, padding: spacing.md }, style]}>
        <View style={{ flex: 1 }}>
          <Text variant="body2" color={colors.success} style={{ fontWeight: '600' }}>
            Cupom aplicado: {appliedCode}
          </Text>
        </View>
        <Button title="Remover" onPress={onRemove} variant="ghost" size="sm" />
      </View>
    );
  }

  return (
    <View style={style}>
      <View style={styles.row}>
        <TextInput
          value={code}
          onChangeText={setCode}
          placeholder="Código do cupom"
          placeholderTextColor={colors.textDisabled}
          autoCapitalize="characters"
          style={[
            styles.input,
            {
              borderColor: error ? colors.error : colors.border,
              borderRadius: br.md,
              color: colors.textPrimary,
              fontFamily: fontFamily.regular,
              fontSize: fontSize.md,
            },
          ]}
          accessibilityLabel="Código do cupom"
        />
        <Button
          title="Aplicar"
          onPress={handleApply}
          variant="outline"
          size="md"
          loading={loading}
          disabled={!code.trim()}
          style={{ marginLeft: 8 }}
        />
      </View>
      {error !== '' && (
        <Text variant="caption" color={colors.error} style={{ marginTop: 4 }}>
          {error}
        </Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  input: {
    flex: 1,
    height: 44,
    borderWidth: 1,
    paddingHorizontal: 12,
  },
  applied: {
    flexDirection: 'row',
    alignItems: 'center',
  },
});
