import React from 'react';
import { View, StyleSheet, TouchableOpacity, ViewStyle } from 'react-native';
import { Text, Icon } from '@/components/ui';
import { useTheme } from '@/hooks/useTheme';
import type { Address } from '@/services/addressService';

interface AddressCardProps {
  address: Address;
  selected?: boolean;
  onPress?: () => void;
  onEdit?: () => void;
  onDelete?: () => void;
  style?: ViewStyle;
}

export function AddressCard({ address, selected, onPress, onEdit, onDelete, style }: AddressCardProps) {
  const { colors, spacing, borderRadius: br, shadow } = useTheme();

  return (
    <TouchableOpacity
      onPress={onPress}
      disabled={!onPress}
      activeOpacity={0.7}
      accessibilityLabel={`${address.logradouro}, ${address.numero}`}
      accessibilityState={{ selected }}
      style={[
        styles.card,
        {
          backgroundColor: colors.surface,
          borderRadius: br.lg,
          borderColor: selected ? colors.primary : colors.border,
          borderWidth: selected ? 2 : 1,
          padding: spacing.md,
          ...shadow('sm'),
        },
        style,
      ]}
    >
      <View style={styles.row}>
        <View style={{ flex: 1 }}>
          {address.apelido && (
            <Text variant="subtitle2" color={colors.textPrimary}>
              {address.apelido}
            </Text>
          )}
          <Text variant="body2" color={colors.textPrimary} style={{ marginTop: 2 }}>
            {address.logradouro}, {address.numero}
            {address.complemento ? ` - ${address.complemento}` : ''}
          </Text>
          <Text variant="caption" color={colors.textSecondary} style={{ marginTop: 2 }}>
            {address.bairro} — {address.cidade}/{address.uf}
          </Text>
          <Text variant="caption" color={colors.textSecondary}>
            CEP: {address.cep}
          </Text>
          {address.principal && (
            <View style={[styles.badge, { backgroundColor: colors.primarySurface, borderRadius: br.sm }]}>
              <Text variant="caption" color={colors.primary} style={{ fontWeight: '600' }}>
                Padrão
              </Text>
            </View>
          )}
        </View>

        {selected && <Icon name="check" size={20} color={colors.primary} />}
      </View>

      {(onEdit || onDelete) && (
        <View style={styles.actions}>
          {onEdit && (
            <TouchableOpacity onPress={onEdit} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
              <Text variant="body2" color={colors.textLink}>
                Editar
              </Text>
            </TouchableOpacity>
          )}
          {onDelete && (
            <TouchableOpacity onPress={onDelete} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
              <Text variant="body2" color={colors.error}>
                Excluir
              </Text>
            </TouchableOpacity>
          )}
        </View>
      )}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: {},
  row: {
    flexDirection: 'row',
    alignItems: 'flex-start',
  },
  badge: {
    alignSelf: 'flex-start',
    marginTop: 6,
    paddingHorizontal: 8,
    paddingVertical: 2,
  },
  actions: {
    flexDirection: 'row',
    gap: 16,
    marginTop: 10,
    paddingTop: 10,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: '#eee',
  },
});
