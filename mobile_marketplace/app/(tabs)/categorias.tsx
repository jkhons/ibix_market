import React from 'react';
import { View, StyleSheet, FlatList, useWindowDimensions, TouchableOpacity, RefreshControl } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { useQuery } from '@tanstack/react-query';
import { Image } from 'expo-image';
import { Text, Skeleton, SearchBar } from '@/components/ui';
import { useTheme } from '@/hooks/useTheme';
import catalogService, { type Category } from '@/services/catalogService';
import { QUERY_KEYS, resolveRemoteAssetUrl } from '@/constants/config';

export default function CategoriasScreen() {
  const { colors, spacing, borderRadius: br, shadow } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { width } = useWindowDimensions();

  const columns = width >= 600 ? 4 : 3;
  const cardWidth = (width - spacing.lg * 2 - spacing.sm * (columns - 1)) / columns;

  const categoriesQuery = useQuery({
    queryKey: [QUERY_KEYS.CATEGORIES],
    queryFn: catalogService.getCategories,
    staleTime: 10 * 60 * 1000,
  });

  const renderCategory = ({ item }: { item: Category }) => {
    const iconUri = resolveRemoteAssetUrl(item.icone_url);
    return (
    <TouchableOpacity
      onPress={() => router.push(`/categoria/${item.id}`)}
      style={[
        styles.card,
        {
          width: cardWidth,
          backgroundColor: colors.surface,
          borderRadius: br.lg,
          ...shadow('sm'),
        },
      ]}
      accessibilityLabel={item.nome}
    >
      <View
        style={[
          styles.iconWrap,
          { width: cardWidth * 0.55, height: cardWidth * 0.55, borderRadius: (cardWidth * 0.55) / 2, backgroundColor: colors.primarySurface },
        ]}
      >
        {iconUri ? (
          <Image
            source={{ uri: iconUri }}
            style={{ width: cardWidth * 0.35, height: cardWidth * 0.35 }}
            contentFit="contain"
          />
        ) : (
          <Text variant="h3" color={colors.primary}>
            {item.nome.charAt(0)}
          </Text>
        )}
      </View>
      <Text variant="body2" color={colors.textPrimary} align="center" numberOfLines={2} style={{ marginTop: 8 }}>
        {item.nome}
      </Text>
      {item.count_produtos !== undefined && (
        <Text variant="caption" color={colors.textSecondary} align="center" style={{ marginTop: 2 }}>
          {item.count_produtos} produtos
        </Text>
      )}
    </TouchableOpacity>
    );
  };

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <View style={[styles.header, { paddingTop: insets.top + spacing.md, paddingHorizontal: spacing.lg }]}>
        <Text variant="h3" color={colors.textPrimary}>
          Categorias
        </Text>
        <SearchBar
          containerStyle={{ marginTop: spacing.md }}
          placeholder="Buscar categorias..."
          onFocus={() => router.push('/busca')}
          editable={false}
        />
      </View>

      <FlatList
        data={categoriesQuery.data ?? []}
        numColumns={columns}
        keyExtractor={(item) => String(item.id)}
        renderItem={renderCategory}
        contentContainerStyle={{
          paddingHorizontal: spacing.lg,
          paddingTop: spacing.lg,
          paddingBottom: spacing['3xl'] + insets.bottom,
        }}
        columnWrapperStyle={{ gap: spacing.sm, marginBottom: spacing.sm }}
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl
            refreshing={categoriesQuery.isRefetching}
            onRefresh={() => categoriesQuery.refetch()}
            tintColor={colors.primary}
            colors={[colors.primary]}
          />
        }
        ListEmptyComponent={
          categoriesQuery.isLoading ? (
            <View style={styles.loadingGrid}>
              {Array.from({ length: 9 }).map((_, i) => (
                <View key={i} style={{ width: cardWidth, alignItems: 'center', marginBottom: spacing.sm }}>
                  <Skeleton width={cardWidth * 0.55} height={cardWidth * 0.55} radius={(cardWidth * 0.55) / 2} />
                  <Skeleton width={cardWidth * 0.7} height={12} radius={4} style={{ marginTop: 8 }} />
                </View>
              ))}
            </View>
          ) : null
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: {},
  card: {
    alignItems: 'center',
    padding: 12,
  },
  iconWrap: {
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
  },
  loadingGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
});
