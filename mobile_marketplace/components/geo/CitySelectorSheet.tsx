import React, { forwardRef, useCallback, useMemo, useState } from 'react';
import { View, StyleSheet, FlatList, ActivityIndicator, TouchableOpacity } from 'react-native';
import GorhomBottomSheet, {
  BottomSheetBackdrop,
  BottomSheetBackdropProps,
  BottomSheetView,
  BottomSheetTextInput,
} from '@gorhom/bottom-sheet';
import { useQuery } from '@tanstack/react-query';

import { Text, Icon, Button, Divider } from '@/components/ui';
import { useTheme } from '@/hooks/useTheme';
import { useGeo } from '@/hooks/useGeo';
import geoService, { type CityWithCoords } from '@/services/geoService';
import { QUERY_KEYS } from '@/constants/config';

interface CitySelectorSheetProps {
  onClose?: () => void;
}

export const CitySelectorSheet = forwardRef<GorhomBottomSheet, CitySelectorSheetProps>(
  ({ onClose }, ref) => {
    const { colors, spacing, borderRadius: br } = useTheme();
    const [query, setQuery] = useState('');
    const [requestingGps, setRequestingGps] = useState(false);
    const { location, requestAndUpdate, setManualLocation, clearLocation } = useGeo();

    const snapPoints = useMemo(() => ['75%'], []);

    const renderBackdrop = useCallback(
      (props: BottomSheetBackdropProps) => (
        <BottomSheetBackdrop {...props} disappearsOnIndex={-1} appearsOnIndex={0} opacity={0.5} />
      ),
      [],
    );

    const citiesQuery = useQuery({
      queryKey: [QUERY_KEYS.NEARBY_CITIES, query.trim()],
      queryFn: () => geoService.listCities(query.trim() || undefined),
      staleTime: 60 * 60 * 1000,
    });

    const filteredCities = useMemo(() => {
      const all = citiesQuery.data ?? [];
      const valid = all.filter(
        (c) => c.lat != null && c.lng != null && Number.isFinite(c.lat) && Number.isFinite(c.lng),
      );
      return valid.slice(0, 80);
    }, [citiesQuery.data]);

    const handleUseGps = useCallback(async () => {
      setRequestingGps(true);
      try {
        await requestAndUpdate();
      } finally {
        setRequestingGps(false);
        if (typeof (ref as any)?.current?.close === 'function') {
          (ref as any).current.close();
        }
      }
    }, [ref, requestAndUpdate]);

    const handleSelectCity = useCallback(
      (city: CityWithCoords) => {
        setManualLocation({
          cidade: city.cidade,
          uf: city.uf,
          lat: city.lat,
          lng: city.lng,
        });
        if (typeof (ref as any)?.current?.close === 'function') {
          (ref as any).current.close();
        }
      },
      [ref, setManualLocation],
    );

    const handleClear = useCallback(() => {
      clearLocation();
      if (typeof (ref as any)?.current?.close === 'function') {
        (ref as any).current.close();
      }
    }, [clearLocation, ref]);

    return (
      <GorhomBottomSheet
        ref={ref}
        index={-1}
        snapPoints={snapPoints}
        enablePanDownToClose
        onClose={onClose}
        backdropComponent={renderBackdrop}
        handleIndicatorStyle={{ backgroundColor: colors.gray400, width: 40 }}
        backgroundStyle={{
          backgroundColor: colors.surface,
          borderTopLeftRadius: br['2xl'],
          borderTopRightRadius: br['2xl'],
        }}
      >
        <BottomSheetView style={[styles.content, { paddingHorizontal: spacing.lg }]}>
          <Text variant="h4" color={colors.textPrimary} style={{ marginBottom: spacing.sm }}>
            Definir localização
          </Text>
          <Text variant="body2" color={colors.textSecondary} style={{ marginBottom: spacing.lg }}>
            Escolha sua cidade ou use o GPS para mostrarmos lojas e produtos perto de você.
          </Text>

          <Button
            title={requestingGps ? 'Obtendo localização...' : 'Usar minha localização (GPS)'}
            onPress={handleUseGps}
            variant="primary"
            size="md"
            fullWidth
            disabled={requestingGps}
          />

          {location && (
            <TouchableOpacity onPress={handleClear} style={{ marginTop: spacing.sm, alignItems: 'center' }}>
              <Text variant="caption" color={colors.textLink}>
                Limpar localização atual
              </Text>
            </TouchableOpacity>
          )}

          <View style={{ marginTop: spacing.lg }}>
            <View
              style={[
                styles.searchRow,
                {
                  backgroundColor: colors.surfaceVariant,
                  borderRadius: br.lg,
                  paddingHorizontal: spacing.md,
                },
              ]}
            >
              <Icon name="search" size={16} color={colors.textSecondary} />
              <BottomSheetTextInput
                placeholder="Buscar cidade..."
                placeholderTextColor={colors.textSecondary}
                value={query}
                onChangeText={setQuery}
                autoCorrect={false}
                style={[styles.searchInput, { color: colors.textPrimary }]}
              />
            </View>
          </View>

          {citiesQuery.isLoading ? (
            <View style={{ paddingVertical: spacing.xl, alignItems: 'center' }}>
              <ActivityIndicator color={colors.primary} />
            </View>
          ) : filteredCities.length === 0 ? (
            <View style={{ paddingVertical: spacing.xl, alignItems: 'center' }}>
              <Text variant="body2" color={colors.textSecondary}>
                Nenhuma cidade encontrada.
              </Text>
            </View>
          ) : (
            <FlatList
              data={filteredCities}
              keyExtractor={(item) => `${item.cidade}-${item.uf}`}
              keyboardShouldPersistTaps="handled"
              ItemSeparatorComponent={() => <Divider />}
              style={{ marginTop: spacing.md }}
              renderItem={({ item }) => (
                <TouchableOpacity
                  onPress={() => handleSelectCity(item)}
                  style={[styles.cityRow, { paddingVertical: spacing.sm }]}
                  accessibilityLabel={`Selecionar ${item.cidade} - ${item.uf}`}
                >
                  <Icon name="location" size={16} color={colors.primary} />
                  <Text
                    variant="body1"
                    color={colors.textPrimary}
                    style={{ marginLeft: spacing.sm, flex: 1 }}
                  >
                    {item.cidade} - {item.uf}
                  </Text>
                </TouchableOpacity>
              )}
            />
          )}
        </BottomSheetView>
      </GorhomBottomSheet>
    );
  },
);

CitySelectorSheet.displayName = 'CitySelectorSheet';

const styles = StyleSheet.create({
  content: {
    flex: 1,
  },
  searchRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 4,
  },
  searchInput: {
    flex: 1,
    marginLeft: 8,
    fontSize: 15,
    paddingVertical: 10,
  },
  cityRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
});
