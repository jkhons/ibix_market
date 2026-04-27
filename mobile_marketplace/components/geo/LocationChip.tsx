import React from 'react';
import { TouchableOpacity, StyleSheet, View, ActivityIndicator } from 'react-native';
import { Icon, Text } from '@/components/ui';
import { useTheme } from '@/hooks/useTheme';

interface LocationChipProps {
  cidade?: string;
  uf?: string;
  loading?: boolean;
  onPress: () => void;
}

export function LocationChip({ cidade, uf, loading, onPress }: LocationChipProps) {
  const { colors, spacing, borderRadius: br } = useTheme();
  const label = cidade && uf ? `${cidade} • ${uf}` : 'Definir localização';
  return (
    <TouchableOpacity
      onPress={onPress}
      style={[
        styles.container,
        {
          backgroundColor: colors.surfaceVariant,
          borderRadius: br.full,
          paddingHorizontal: spacing.md,
          paddingVertical: spacing.xs,
          borderColor: colors.borderLight,
        },
      ]}
      accessibilityLabel={`Localização: ${label}. Tocar para alterar`}
      accessibilityRole="button"
    >
      {loading ? (
        <ActivityIndicator size="small" color={colors.primary} />
      ) : (
        <Icon name="location" size={14} color={colors.primary} />
      )}
      <Text
        variant="caption"
        color={colors.textPrimary}
        style={{ marginLeft: 6, maxWidth: 180 }}
        numberOfLines={1}
      >
        {label}
      </Text>
      <View style={{ marginLeft: 4 }}>
        <Icon name="chevronRight" size={12} color={colors.textSecondary} />
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    alignSelf: 'flex-start',
  },
});
