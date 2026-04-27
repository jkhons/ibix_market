import React, { useState, useRef, useCallback, useMemo } from 'react';
import {
  View,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  FlatList,
  useWindowDimensions,
  ListRenderItemInfo,
  RefreshControl,
} from 'react-native';
import { useRouter, Stack } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useQuery, useInfiniteQuery } from '@tanstack/react-query';
import GorhomBottomSheet from '@gorhom/bottom-sheet';

import { Text, SearchBar, Skeleton, SkeletonCard, Chip, EmptyState, Icon } from '@/components/ui';
import { ProductCard, FilterSheet, type FilterValues } from '@/components/product';
import { NearbyAdsCarousel, LocationChip, CitySelectorSheet } from '@/components/geo';
import { useTheme } from '@/hooks/useTheme';
import { useDebounce } from '@/hooks/useDebounce';
import { useGeo } from '@/hooks/useGeo';
import catalogService, { type ProductSummary } from '@/services/catalogService';
import favoriteService from '@/services/favoriteService';
import geoService from '@/services/geoService';
import { QUERY_KEYS, PAGINATION, STORAGE_KEYS } from '@/constants/config';
import { fastStorage } from '@/utils/storage';

const MAX_RECENT_SEARCHES = 15;
const DEFAULT_FILTERS: FilterValues = { ordenar: 'relevancia', somente_promocao: false };

export default function SearchScreen() {
  const { colors, spacing } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { width } = useWindowDimensions();
  const inputRef = useRef<TextInput>(null);
  const filterRef = useRef<GorhomBottomSheet>(null);
  const citySheetRef = useRef<GorhomBottomSheet>(null);
  const { location } = useGeo();

  const [query, setQuery] = useState('');
  const [submittedQuery, setSubmittedQuery] = useState('');
  const [filters, setFilters] = useState<FilterValues>(DEFAULT_FILTERS);
  const debouncedQuery = useDebounce(query, 300);

  const columns = width >= 600 ? 3 : 2;

  const [recentSearches, setRecentSearches] = useState<string[]>(
    () => fastStorage.getObject<string[]>(STORAGE_KEYS.RECENT_SEARCHES) ?? [],
  );

  const autocompleteQuery = useQuery({
    queryKey: [QUERY_KEYS.AUTOCOMPLETE, debouncedQuery],
    queryFn: () => catalogService.autocomplete(debouncedQuery),
    enabled: debouncedQuery.length >= 2 && !submittedQuery,
    staleTime: 30 * 1000,
  });

  const popularQuery = useQuery({
    queryKey: [QUERY_KEYS.POPULAR_TERMS],
    queryFn: catalogService.getPopularTerms,
    staleTime: 60 * 60 * 1000,
  });

  const resultsQuery = useInfiniteQuery({
    queryKey: [QUERY_KEYS.SEARCH, submittedQuery, filters],
    queryFn: ({ pageParam = 1 }) =>
      catalogService.getProducts({
        q: submittedQuery,
        ordenar: filters.ordenar as any,
        page: pageParam,
        page_size: PAGINATION.PRODUCT_PAGE_SIZE,
      }),
    getNextPageParam: (lastPage) => (lastPage.has_next ? lastPage.page + 1 : undefined),
    enabled: submittedQuery.length >= 2,
    staleTime: 60 * 1000,
    initialPageParam: 1,
  });

  const allResults = useMemo(
    () => resultsQuery.data?.pages.flatMap((p) => p.items) ?? [],
    [resultsQuery.data],
  );
  const totalResults = resultsQuery.data?.pages[0]?.total;

  const nearbyByQuery = useQuery({
    queryKey: [QUERY_KEYS.NEARBY_BY_QUERY, submittedQuery, location?.lat, location?.lng],
    queryFn: () =>
      geoService.getNearbyByQuery({
        q: submittedQuery,
        lat: location!.lat,
        lng: location!.lng,
        limit: 10,
      }),
    enabled: submittedQuery.length >= 2 && !!location?.lat && !!location?.lng,
    staleTime: 60 * 1000,
  });

  const saveSearch = useCallback(
    (term: string) => {
      const updated = [term, ...recentSearches.filter((s) => s !== term)].slice(0, MAX_RECENT_SEARCHES);
      setRecentSearches(updated);
      fastStorage.setObject(STORAGE_KEYS.RECENT_SEARCHES, updated);
    },
    [recentSearches],
  );

  const removeRecentSearch = useCallback(
    (term: string) => {
      const updated = recentSearches.filter((s) => s !== term);
      setRecentSearches(updated);
      fastStorage.setObject(STORAGE_KEYS.RECENT_SEARCHES, updated);
    },
    [recentSearches],
  );

  const clearRecentSearches = useCallback(() => {
    setRecentSearches([]);
    fastStorage.setObject(STORAGE_KEYS.RECENT_SEARCHES, []);
  }, []);

  const handleSubmitSearch = useCallback(
    (term?: string) => {
      const t = (term ?? query).trim();
      if (t.length < 2) return;
      setSubmittedQuery(t);
      saveSearch(t);
    },
    [query, saveSearch],
  );

  const handleSelectSuggestion = useCallback(
    (term: string) => {
      setQuery(term);
      setSubmittedQuery(term);
      saveSearch(term);
    },
    [saveSearch],
  );

  const handleFavoriteToggle = useCallback(async (id: number) => {
    try { await favoriteService.addFavorite(id); } catch {}
  }, []);

  const handleEndReached = useCallback(() => {
    if (resultsQuery.hasNextPage && !resultsQuery.isFetchingNextPage) {
      resultsQuery.fetchNextPage();
    }
  }, [resultsQuery.hasNextPage, resultsQuery.isFetchingNextPage]);

  const showingResults = submittedQuery.length >= 2;
  const showingAutocomplete = !showingResults && debouncedQuery.length >= 2;
  const showingIdle = !showingResults && !showingAutocomplete;

  const renderAutocomplete = () => {
    const suggestions = autocompleteQuery.data?.sugestoes ?? [];
    const categories = autocompleteQuery.data?.categorias ?? [];

    return (
      <View style={{ paddingHorizontal: spacing.lg, paddingTop: spacing.md }}>
        {suggestions.map((s) => (
          <TouchableOpacity
            key={s}
            onPress={() => handleSelectSuggestion(s)}
            style={[styles.suggestionRow, { borderBottomColor: colors.divider }]}
            accessibilityLabel={`Buscar ${s}`}
          >
            <Icon name="search" size={16} color={colors.textDisabled} />
            <Text variant="body1" color={colors.textPrimary} style={{ marginLeft: 12, flex: 1 }}>
              {s}
            </Text>
          </TouchableOpacity>
        ))}
        {categories.length > 0 && (
          <View style={{ marginTop: spacing.lg }}>
            <Text variant="subtitle2" color={colors.textSecondary}>
              Categorias
            </Text>
            {categories.map((c) => (
              <TouchableOpacity
                key={c.id}
                onPress={() => router.push(`/categoria/${c.id}`)}
                style={[styles.suggestionRow, { borderBottomColor: colors.divider }]}
              >
                <Icon name="category" size={16} color={colors.primary} />
                <Text variant="body1" color={colors.primary} style={{ marginLeft: 12 }}>
                  {c.nome}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        )}
      </View>
    );
  };

  const renderIdle = () => (
    <View style={{ paddingHorizontal: spacing.lg, paddingTop: spacing.xl }}>
      {/* Popular terms */}
      {(popularQuery.data?.length ?? 0) > 0 && (
        <>
          <Text variant="subtitle2" color={colors.textPrimary}>
            Mais buscados
          </Text>
          <View style={styles.chipRow}>
            {popularQuery.data!.map((term) => (
              <Chip
                key={term}
                label={term}
                onPress={() => handleSelectSuggestion(term)}
                style={{ marginRight: 8, marginTop: 8 }}
              />
            ))}
          </View>
        </>
      )}

      {/* Recent searches */}
      {recentSearches.length > 0 && (
        <View style={{ marginTop: spacing.xl }}>
          <View style={styles.recentHeader}>
            <Text variant="subtitle2" color={colors.textPrimary}>
              Buscas recentes
            </Text>
            <TouchableOpacity onPress={clearRecentSearches}>
              <Text variant="body2" color={colors.textLink}>
                Limpar
              </Text>
            </TouchableOpacity>
          </View>
          {recentSearches.map((term) => (
            <View key={term} style={[styles.recentRow, { borderBottomColor: colors.divider }]}>
              <TouchableOpacity
                onPress={() => handleSelectSuggestion(term)}
                style={{ flex: 1, flexDirection: 'row', alignItems: 'center' }}
              >
                <Icon name="refresh" size={14} color={colors.textDisabled} />
                <Text variant="body1" color={colors.textSecondary} style={{ marginLeft: 12 }}>
                  {term}
                </Text>
              </TouchableOpacity>
              <TouchableOpacity
                onPress={() => removeRecentSearch(term)}
                hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
                accessibilityLabel={`Remover ${term} do histórico`}
              >
                <Icon name="close" size={14} color={colors.textDisabled} />
              </TouchableOpacity>
            </View>
          ))}
        </View>
      )}
    </View>
  );

  const renderResultsHeader = () => (
    <View style={styles.resultsHeader}>
      <View style={[styles.locationRow, { marginTop: 8 }]}>
        <LocationChip
          cidade={location?.cidade}
          uf={location?.uf}
          onPress={() => citySheetRef.current?.snapToIndex(0)}
        />
      </View>
      {location?.lat != null && nearbyByQuery.data?.items && nearbyByQuery.data.items.length > 0 && (
        <View style={{ marginTop: 16 }}>
          <Text variant="subtitle2" color={colors.textPrimary}>
            Mais perto de você que vendem isso
          </Text>
          <NearbyAdsCarousel items={nearbyByQuery.data.items} />
        </View>
      )}
      {!!location?.lat && nearbyByQuery.isLoading && (
        <View style={{ marginTop: 12, flexDirection: 'row' }}>
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton
              key={i}
              width={width * 0.4}
              height={width * 0.5}
              radius={12}
              style={{ marginRight: 12 }}
            />
          ))}
        </View>
      )}
      <View style={[styles.filterRow, { marginTop: 16 }]}>
        <Text variant="body2" color={colors.textSecondary}>
          {totalResults !== undefined ? `${totalResults} resultados` : ''}
        </Text>
        <TouchableOpacity
          onPress={() => filterRef.current?.snapToIndex(0)}
          style={[styles.filterBtn, { borderColor: colors.border }]}
          accessibilityLabel="Filtros"
        >
          <Icon name="filter" size={16} color={colors.textPrimary} />
          <Text variant="body2" color={colors.textPrimary} style={{ marginLeft: 6 }}>
            Filtros
          </Text>
        </TouchableOpacity>
      </View>
    </View>
  );

  const renderResultItem = useCallback(
    ({ item }: ListRenderItemInfo<ProductSummary>) => (
      <View style={{ width: `${100 / columns}%`, paddingHorizontal: spacing.sm / 2 }}>
        <ProductCard product={item} onFavoriteToggle={handleFavoriteToggle} columns={columns} />
      </View>
    ),
    [columns, handleFavoriteToggle],
  );

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <Stack.Screen options={{ headerShown: false }} />

      {/* Header */}
      <View style={[styles.header, { paddingHorizontal: spacing.lg, paddingTop: insets.top + spacing.sm }]}>
        <View style={{ flex: 1 }}>
          <SearchBar
            ref={inputRef}
            value={query}
            onChangeText={(t) => {
              setQuery(t);
              if (submittedQuery) setSubmittedQuery('');
            }}
            onSearch={handleSubmitSearch}
            onClear={() => {
              setQuery('');
              setSubmittedQuery('');
            }}
            autoFocus
          />
        </View>
        <TouchableOpacity onPress={() => router.back()} style={{ marginLeft: spacing.md }}>
          <Text variant="body2" color={colors.textLink}>
            Cancelar
          </Text>
        </TouchableOpacity>
      </View>

      {/* Content */}
      {showingResults ? (
        <FlatList
          data={allResults}
          numColumns={columns}
          keyExtractor={(item) => String(item.id)}
          renderItem={renderResultItem}
          ListHeaderComponent={renderResultsHeader}
          ListFooterComponent={
            resultsQuery.isFetchingNextPage ? (
              <View style={{ padding: spacing.lg, alignItems: 'center' }}>
                <Skeleton width={width * 0.4} height={16} radius={8} />
              </View>
            ) : null
          }
          ListEmptyComponent={
            resultsQuery.isLoading ? (
              <View style={styles.loadingGrid}>
                {Array.from({ length: 4 }).map((_, i) => (
                  <SkeletonCard key={i} style={{ width: (width - spacing.lg * 2 - spacing.sm) / columns, marginBottom: 12 }} />
                ))}
              </View>
            ) : (
              <EmptyState
                title={`Nenhum resultado para "${submittedQuery}"`}
                description="Tente outros termos ou verifique a ortografia."
                actionLabel="Limpar busca"
                onAction={() => {
                  setQuery('');
                  setSubmittedQuery('');
                }}
              />
            )
          }
          onEndReached={handleEndReached}
          onEndReachedThreshold={0.4}
          refreshControl={
            <RefreshControl
              refreshing={resultsQuery.isRefetching}
              onRefresh={() => resultsQuery.refetch()}
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
      ) : showingAutocomplete ? (
        renderAutocomplete()
      ) : (
        renderIdle()
      )}

      {showingResults && (
        <FilterSheet
          ref={filterRef}
          initialValues={filters}
          resultCount={totalResults}
          onApply={(f) => {
            setFilters(f);
            filterRef.current?.close();
          }}
          onClear={() => {
            setFilters(DEFAULT_FILTERS);
            filterRef.current?.close();
          }}
        />
      )}
      <CitySelectorSheet ref={citySheetRef} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: { flexDirection: 'row', alignItems: 'center' },
  chipRow: { flexDirection: 'row', flexWrap: 'wrap' },
  recentHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  recentRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  suggestionRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  resultsHeader: {
    marginBottom: 8,
  },
  locationRow: {
    flexDirection: 'row',
    alignItems: 'center',
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
