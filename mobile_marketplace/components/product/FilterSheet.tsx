import React, { forwardRef, useState, useCallback } from 'react';
import { View, StyleSheet, ScrollView } from 'react-native';
import GorhomBottomSheet from '@gorhom/bottom-sheet';
import { AppBottomSheet } from '@/components/ui/BottomSheet';
import { Text, Button, Chip, Divider } from '@/components/ui';
import { useTheme } from '@/hooks/useTheme';

export interface FilterValues {
  ordenar: string;
  somente_promocao: boolean;
  preco_min?: number;
  preco_max?: number;
}

interface FilterSheetProps {
  initialValues: FilterValues;
  resultCount?: number;
  onApply: (filters: FilterValues) => void;
  onClear: () => void;
}

const SORT_OPTIONS = [
  { key: 'relevancia', label: 'Relevância' },
  { key: 'menor_preco', label: 'Menor preço' },
  { key: 'maior_preco', label: 'Maior preço' },
  { key: 'mais_vendidos', label: 'Mais vendidos' },
  { key: 'recentes', label: 'Mais recentes' },
];

export const FilterSheet = forwardRef<GorhomBottomSheet, FilterSheetProps>(
  ({ initialValues, resultCount, onApply, onClear }, ref) => {
    const { colors, spacing } = useTheme();
    const [filters, setFilters] = useState<FilterValues>(initialValues);

    const updateFilter = useCallback(<K extends keyof FilterValues>(key: K, value: FilterValues[K]) => {
      setFilters((prev) => ({ ...prev, [key]: value }));
    }, []);

    const handleApply = () => onApply(filters);

    const handleClear = () => {
      const cleared: FilterValues = { ordenar: 'relevancia', somente_promocao: false };
      setFilters(cleared);
      onClear();
    };

    return (
      <AppBottomSheet ref={ref} snapPoints={['60%', '90%']}>
        <ScrollView showsVerticalScrollIndicator={false}>
          <Text variant="h4" color={colors.textPrimary}>Filtros</Text>

          <Text variant="subtitle2" color={colors.textPrimary} style={{ marginTop: spacing.xl }}>
            Ordenar por
          </Text>
          <View style={styles.chipRow}>
            {SORT_OPTIONS.map((opt) => (
              <Chip
                key={opt.key}
                label={opt.label}
                selected={filters.ordenar === opt.key}
                onPress={() => updateFilter('ordenar', opt.key)}
                style={{ marginRight: 8, marginTop: 8 }}
              />
            ))}
          </View>

          <Divider style={{ marginVertical: spacing.lg }} />

          <Text variant="subtitle2" color={colors.textPrimary}>Promoções</Text>
          <Chip
            label="Somente promoções"
            selected={filters.somente_promocao}
            onPress={() => updateFilter('somente_promocao', !filters.somente_promocao)}
            style={{ marginTop: 8 }}
          />

          <View style={[styles.actions, { marginTop: spacing['2xl'] }]}>
            <Button
              title="Limpar"
              onPress={handleClear}
              variant="ghost"
              size="md"
              style={{ flex: 1, marginRight: 8 }}
            />
            <Button
              title={resultCount !== undefined ? `Aplicar (${resultCount})` : 'Aplicar'}
              onPress={handleApply}
              variant="primary"
              size="md"
              style={{ flex: 2 }}
            />
          </View>
        </ScrollView>
      </AppBottomSheet>
    );
  },
);

FilterSheet.displayName = 'FilterSheet';

const styles = StyleSheet.create({
  chipRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
  actions: {
    flexDirection: 'row',
  },
});
