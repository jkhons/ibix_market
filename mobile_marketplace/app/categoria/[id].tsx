import React, { useCallback, useMemo, useRef, useState } from 'react';
import {
  View,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  useWindowDimensions,
  ListRenderItemInfo,
  RefreshControl,
} from 'react-native';
import { useLocalSearchParams, useRouter, Stack } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useInfiniteQuery, useQuery } from '@tanstack/react-query';
import GorhomBottomSheet from '@gorhom/bottom-sheet';

import { Text, Skeleton, SkeletonCard, EmptyState, Icon } from '@/components/ui';
import { ProductCard, FilterSheet, type FilterValues } from '@/components/product';
import { useTheme } from '@/hooks/useTheme';
import catalogService, { type ProductSummary, type Category } from '@/services/catalogService';
import favoriteService from '@/services/favoriteService';
import { QUERY_KEYS, PAGINATION } from '@/constants/config';

const DEFAULT_FILTERS: FilterValues = { ordenar: 'relevancia', somente_promocao: false };

export default function CategoriaScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const categoryId = Number(id);
  const { colors, spacing } = useTheme();
  const insets = useSafeAreaInsets();
  const { width } = useWindowDimensions();
  const router = useRouter();
  const filterRef = useRef<GorhomBottomSheet>(null);

  const [filters, setFilters] = useState<FilterValues>(DEFAULT_FILTERS);

  const columns = width >= 600 ? 3 : 2;

  const categoryQuery = useQuery({
    queryKey: [QUERY_KEYS.CATEGORIES, categoryId],
    queryFn: async () => {
      const all = await catalogService.getCategories();
      const cat = all.find((c: Category) => c.id === categoryId);
      if (!cat) throw new Error('Categoria não encontrada');
      return cat;
    },
    staleTime: 10 * 60 * 1000,
  });

  const productsQuery = useInfiniteQuery({
    queryKey: [QUERY_KEYS.PRODUCTS, 'categoria', categoryId, filters],
    queryFn: ({ pageParam = 1 }) =>
      catalogService.getProducts({
        categoria_id: categoryId,
        ordenar: filters.ordenar as any,
        page: pageParam,
        page_size: PAGINATION.PRODUCT_PAGE_SIZE,
      }),
    getNextPageParam: (lastPage) => (lastPage.has_next ? lastPage.page + 1 : undefined),
    staleTime: 60 * 1000,
    initialPageParam: 1,
  });

  const allProducts = useMemo(
    () => productsQuery.data?.pages.flatMap((p) => p.items) ?? [],
    [productsQuery.data],
  );

  const totalResults = productsQuery.data?.pages[0]?.total;

  const handleFavoriteToggle = useCallback(async (productId: number) => {
    try {
      await favoriteService.addFavorite(productId);
    } catch {}
  }, []);

  const handleEndReached = useCallback(() => {
    if (productsQuery.hasNextPage && !productsQuery.isFetchingNextPage) {
      productsQuery.fetchNextPage();
    }
  }, [productsQuery.hasNextPage, productsQuery.isFetchingNextPage]);

  const handleApplyFilter = (f: FilterValues) => {
    setFilters(f);
    filterRef.current?.close();
  };

  const handleClearFilter = () => {
    setFilters(DEFAULT_FILTERS);
    filterRef.current?.close();
  };

  const renderItem = useCallback(
    ({ item }: ListRenderItemInfo<ProductSummary>) => (
      <View style={{ width: `${100 / columns}%`, paddingHorizontal: spacing.sm / 2 }}>
        <ProductCard product={item} onFavoriteToggle={handleFavoriteToggle} columns={columns} />
      </View>
    ),
    [columns, handleFavoriteToggle],
  );

  const renderHeader = () => (
    <View style={styles.listHeader}>
      <View style={styles.filterRow}>
        <Text variant="body2" color={colors.textSecondary}>
          {totalResults !== undefined ? `${totalResults} produtos` : ''}
        </Text>
        <TouchableOpacity
          onPress={() => filterRef.current?.snapToIndex(0)}
          style={[styles.filterBtn, { borderColor: colors.border }]}
          accessibilityLabel="Abrir filtros"
        >
          <Icon name="filter" size={16} color={colors.textPrimary} />
          <Text variant="body2" color={colors.textPrimary} style={{ marginLeft: 6 }}>
            Filtros
          </Text>
        </TouchableOpacity>
      </View>
    </View>
  );

  const renderFooter = () => {
    if (!productsQuery.isFetchingNextPage) return null;
    return (
      <View style={{ padding: spacing.lg, alignItems: 'center' }}>
        <Skeleton width={width * 0.4} height={16} radius={8} />
      </View>
    );
  };

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <Stack.Screen
        options={{
          title: categoryQuery.data?.nome ?? 'Categoria',
          headerShadowVisible: false,
          headerStyle: { backgroundColor: colors.background },
          headerTintColor: colors.textPrimary,
        }}
      />

      <FlatList
        data={allProducts}
        numColumns={columns}
        keyExtractor={(item) => String(item.id)}
        renderItem={renderItem}
        ListHeaderComponent={renderHeader}
        ListFooterComponent={renderFooter}
        ListEmptyComponent={
          productsQuery.isLoading ? (
            <View style={styles.loadingGrid}>
              {Array.from({ length: 6 }).map((_, i) => (
                <SkeletonCard key={i} style={{ width: (width - spacing.lg * 2 - spacing.sm) / columns, marginBottom: 12 }} />
              ))}
            </View>
          ) : (
            <EmptyState
              title="Nenhum produto encontrado"
              description="Tente ajustar os filtros ou explorar outras categorias."
              actionLabel="Ver categorias"
              onAction={() => router.back()}
            />
          )
        }
        onEndReached={handleEndReached}
        onEndReachedThreshold={0.4}
        refreshControl={
          <RefreshControl
            refreshing={productsQuery.isRefetching}
            onRefresh={() => productsQuery.refetch()}
            tintColor={colors.primary}
            colors={[colors.primary]}
          />
        }
        contentContainerStyle={{
          paddingHorizontal: spacing.lg,
          paddingBottom: spacing['3xl'] + insets.bottom,
        }}
        columnWrapperStyle={{ gap: spacing.sm }}
        showsVerticalScrollIndicator={false}
      />

      <FilterSheet
        ref={filterRef}
        initialValues={filters}
        resultCount={totalResults}
        onApply={handleApplyFilter}
        onClear={handleClearFilter}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  listHeader: {
    marginBottom: 12,
  },
  filterRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 8,
  },
  filterBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
    borderWidth: 1,
  },
  loadingGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
});
