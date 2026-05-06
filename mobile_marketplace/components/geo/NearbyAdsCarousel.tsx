import React from 'react';
import {
  View,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  useWindowDimensions,
} from 'react-native';
import { Image } from 'expo-image';
import { useRouter } from 'expo-router';

import { Text, Icon } from '@/components/ui';
import { useTheme } from '@/hooks/useTheme';
import { formatCurrency } from '@/utils/format';
import type { NearbyAd } from '@/services/geoService';
import { resolveRemoteAssetUrl } from '@/constants/config';

interface NearbyAdsCarouselProps {
  items: NearbyAd[];
}

function formatDistance(km?: number): string | null {
  if (km == null || !Number.isFinite(km)) return null;
  if (km < 1) return `${Math.round(km * 1000)} m`;
  if (km < 10) return `${km.toFixed(1).replace('.', ',')} km`;
  return `${Math.round(km)} km`;
}

function formatDuration(min?: number): string | null {
  if (min == null || !Number.isFinite(min)) return null;
  if (min < 1) return null;
  if (min < 60) return `${Math.round(min)} min`;
  const horas = Math.floor(min / 60);
  const mins = Math.round(min % 60);
  return mins > 0 ? `${horas}h${mins}min` : `${horas}h`;
}

export function NearbyAdsCarousel({ items }: NearbyAdsCarouselProps) {
  const { colors, spacing, borderRadius: br, shadow } = useTheme();
  const router = useRouter();
  const { width } = useWindowDimensions();
  const cardW = Math.min(width * 0.45, 200);

  return (
    <FlatList
      data={items}
      horizontal
      showsHorizontalScrollIndicator={false}
      contentContainerStyle={{ paddingHorizontal: spacing.lg, paddingTop: spacing.md }}
      keyExtractor={(item) => String(item.id)}
      renderItem={({ item }) => {
        const hasDiscount =
          item.preco_promocional != null && Number(item.preco_promocional) < Number(item.preco_original);
        const price = hasDiscount ? Number(item.preco_promocional) : Number(item.preco_original);
        const dist = formatDistance(item.distancia_rota_km ?? item.distancia_km);
        const dur = formatDuration(item.duracao_rota_min);
        const cidade = item.cidade_loja
          ? `${item.cidade_loja}${item.uf_loja ? ` • ${item.uf_loja}` : ''}`
          : null;
        const thumbUri = resolveRemoteAssetUrl(item.imagens?.[0]);

        return (
          <TouchableOpacity
            onPress={() => router.push(`/produto/${item.id}`)}
            activeOpacity={0.85}
            style={[
              styles.card,
              {
                width: cardW,
                marginRight: spacing.sm,
                backgroundColor: colors.surface,
                borderRadius: br.lg,
                ...shadow('sm'),
              },
            ]}
            accessibilityLabel={`${item.titulo}, ${formatCurrency(price)}${dist ? `, a ${dist}` : ''}`}
          >
            <View
              style={{
                width: cardW,
                height: cardW * 1.05,
                borderTopLeftRadius: br.lg,
                borderTopRightRadius: br.lg,
                overflow: 'hidden',
                backgroundColor: colors.surfaceVariant,
              }}
            >
              {thumbUri ? (
                <Image
                  source={{ uri: thumbUri }}
                  style={StyleSheet.absoluteFill}
                  contentFit="cover"
                  transition={200}
                />
              ) : (
                <View style={[StyleSheet.absoluteFill, styles.center]}>
                  <Icon name="cart" size={24} color={colors.textDisabled} />
                </View>
              )}

              {dist && (
                <View
                  style={[
                    styles.distanceBadge,
                    {
                      backgroundColor: colors.surface,
                      borderRadius: br.full,
                      paddingHorizontal: spacing.sm,
                      paddingVertical: 4,
                    },
                  ]}
                >
                  <Icon name="location" size={10} color={colors.primary} />
                  <Text
                    variant="caption"
                    color={colors.textPrimary}
                    style={{ marginLeft: 4, fontWeight: '600' }}
                  >
                    {dist}
                    {dur ? ` • ${dur}` : ''}
                  </Text>
                </View>
              )}
            </View>

            <View style={{ padding: spacing.sm }}>
              <Text variant="body2" color={colors.textPrimary} numberOfLines={2}>
                {item.titulo}
              </Text>
              <Text
                variant="priceSmall"
                color={colors.textPrimary}
                style={{ marginTop: 4 }}
              >
                {formatCurrency(price)}
              </Text>
              {cidade && (
                <Text
                  variant="caption"
                  color={colors.textSecondary}
                  style={{ marginTop: 2 }}
                  numberOfLines={1}
                >
                  {item.nome_loja ? `${item.nome_loja} • ${cidade}` : cidade}
                </Text>
              )}
            </View>
          </TouchableOpacity>
        );
      }}
    />
  );
}

const styles = StyleSheet.create({
  card: {
    overflow: 'hidden',
  },
  center: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  distanceBadge: {
    position: 'absolute',
    bottom: 8,
    left: 8,
    flexDirection: 'row',
    alignItems: 'center',
  },
});
