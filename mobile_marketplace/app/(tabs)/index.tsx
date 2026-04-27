import React, { useCallback, useEffect, useMemo, useRef } from 'react';
import {
  View,
  StyleSheet,
  RefreshControl,
  FlatList,
  TouchableOpacity,
  useWindowDimensions,
  ListRenderItemInfo,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { useQuery, useInfiniteQuery, useQueryClient } from '@tanstack/react-query';
import { Image } from 'expo-image';
import GorhomBottomSheet from '@gorhom/bottom-sheet';

import { Text, SearchBar, Skeleton, SkeletonCard, Icon, Badge } from '@/components/ui';
import { ProductCard, CategoryCard, BannerCarousel } from '@/components/product';
import { LocationChip, CitySelectorSheet, NearbyAdsCarousel } from '@/components/geo';
import { useTheme } from '@/hooks/useTheme';
import { useGeo } from '@/hooks/useGeo';
import { useRecentlyViewedStore } from '@/store';
import { useNotificationStore } from '@/store';
import { useGeoStore } from '@/store/geoStore';
import catalogService, { type ProductSummary } from '@/services/catalogService';
import marketingService, { type MarketingBlock } from '@/services/marketingService';
import favoriteService from '@/services/favoriteService';
import geoService from '@/services/geoService';
import { QUERY_KEYS, PAGINATION } from '@/constants/config';
import { formatCurrency } from '@/utils/format';

export default function HomeScreen() {
  const { colors, spacing, borderRadius: br } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { width } = useWindowDimensions();
  const queryClient = useQueryClient();

  const recentlyViewed = useRecentlyViewedStore((s) => s.items);
  const unreadCount = useNotificationStore((s) => s.unreadCount);
  const hydrateGeo = useGeoStore((s) => s.hydrate);
  const isGeoHydrated = useGeoStore((s) => s.isHydrated);
  const { location } = useGeo();
  const citySheetRef = useRef<GorhomBottomSheet>(null);

  useEffect(() => {
    if (!isGeoHydrated) hydrateGeo();
  }, [hydrateGeo, isGeoHydrated]);

  const vitrineQuery = useQuery({
    queryKey: [QUERY_KEYS.VITRINE_HOME],
    queryFn: marketingService.getVitrineHome,
    staleTime: 5 * 60 * 1000,
  });

  const nearbyQuery = useQuery({
    queryKey: [QUERY_KEYS.NEARBY_ADS, location?.lat, location?.lng],
    queryFn: () =>
      geoService.getNearbyAds({
        lat: location!.lat,
        lng: location!.lng,
        limit: 12,
      }),
    enabled: !!location?.lat && !!location?.lng,
    staleTime: 60 * 1000,
  });

  const categoriesQuery = useQuery({
    queryKey: [QUERY_KEYS.CATEGORIES],
    queryFn: catalogService.getCategories,
    staleTime: 10 * 60 * 1000,
  });

  const productsQuery = useInfiniteQuery({
    queryKey: [QUERY_KEYS.PRODUCTS, 'recentes'],
    queryFn: ({ pageParam = 1 }) =>
      catalogService.getProducts({ ordenar: 'recentes', page: pageParam, page_size: PAGINATION.PRODUCT_PAGE_SIZE }),
    getNextPageParam: (lastPage) => (lastPage.has_next ? lastPage.page + 1 : undefined),
    staleTime: 60 * 1000,
    initialPageParam: 1,
  });

  const allProducts = useMemo(
    () => productsQuery.data?.pages.flatMap((p) => p.items) ?? [],
    [productsQuery.data],
  );

  const blocos = vitrineQuery.data?.blocos ?? [];
  const bannerCards = blocos.find((b) => b.tipo_bloco === 'cabecalho_ofertas')?.cards ?? [];
  const destaquesBlock = blocos.find((b) => b.tipo_bloco === 'destaques');
  const ofertasSemanaBlock = blocos.find((b) => b.tipo_bloco === 'oferta_semana');

  const isRefreshing =
    vitrineQuery.isRefetching || categoriesQuery.isRefetching || productsQuery.isRefetching;

  const handleRefresh = useCallback(() => {
    vitrineQuery.refetch();
    categoriesQuery.refetch();
    productsQuery.refetch();
    if (location?.lat && location?.lng) nearbyQuery.refetch();
  }, [location?.lat, location?.lng]);

  const handleOpenCitySheet = useCallback(() => {
    citySheetRef.current?.snapToIndex(0);
  }, []);

  const handleFavoriteToggle = useCallback(
    async (productId: number) => {
      try {
        await favoriteService.addFavorite(productId);
        queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.FAVORITES] });
      } catch {}
    },
    [queryClient],
  );

  const handleEndReached = useCallback(() => {
    if (productsQuery.hasNextPage && !productsQuery.isFetchingNextPage) {
      productsQuery.fetchNextPage();
    }
  }, [productsQuery.hasNextPage, productsQuery.isFetchingNextPage]);

  const renderSectionHeader = (title: string, onSeeAll?: () => void) => (
    <View style={[styles.sectionHeader, { paddingHorizontal: spacing.lg, marginTop: spacing.xl }]}>
      <Text variant="subtitle1" color={colors.textPrimary}>
        {title}
      </Text>
      {onSeeAll && (
        <TouchableOpacity onPress={onSeeAll} accessibilityLabel={`Ver todos: ${title}`}>
          <Text variant="body2" color={colors.primary}>
            Ver todos
          </Text>
        </TouchableOpacity>
      )}
    </View>
  );

  const renderProductHorizontal = (items: MarketingBlock['cards']) => (
    <FlatList
      data={items}
      horizontal
      showsHorizontalScrollIndicator={false}
      contentContainerStyle={{ paddingHorizontal: spacing.lg, paddingTop: spacing.md }}
      keyExtractor={(item) => String(item.id)}
      renderItem={({ item }) => {
        const cardW = width * 0.38;
        return (
          <TouchableOpacity
            onPress={() => item.anuncio_id && router.push(`/produto/${item.anuncio_id}`)}
            style={[styles.marketingCard, { width: cardW, marginRight: spacing.sm, borderRadius: br.lg, backgroundColor: colors.surface }]}
            accessibilityLabel={item.titulo ?? 'Produto em destaque'}
          >
            <Image
              source={{ uri: item.imagem_url_mobile ?? item.imagem_url }}
              style={{ width: cardW, height: cardW * 1.1, borderTopLeftRadius: br.lg, borderTopRightRadius: br.lg }}
              contentFit="cover"
              transition={200}
            />
            {item.titulo && (
              <View style={{ padding: spacing.sm }}>
                <Text variant="body2" color={colors.textPrimary} numberOfLines={2}>
                  {item.titulo}
                </Text>
                {item.subtitulo && (
                  <Text variant="caption" color={colors.accent} style={{ marginTop: 2 }}>
                    {item.subtitulo}
                  </Text>
                )}
              </View>
            )}
          </TouchableOpacity>
        );
      }}
    />
  );

  const renderRecentlyViewed = () => {
    if (!recentlyViewed.length) return null;

    return (
      <>
        {renderSectionHeader('Vistos recentemente')}
        <FlatList
          data={recentlyViewed.slice(0, 20)}
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={{ paddingHorizontal: spacing.lg, paddingTop: spacing.md }}
          keyExtractor={(item) => String(item.id)}
          renderItem={({ item }) => {
            const cardW = width * 0.3;
            return (
              <TouchableOpacity
                onPress={() => router.push(`/produto/${item.id}`)}
                style={[styles.recentCard, { width: cardW, marginRight: spacing.sm, borderRadius: br.md, backgroundColor: colors.surface }]}
                accessibilityLabel={item.nome}
              >
                {item.imageUrl ? (
                  <Image
                    source={{ uri: item.imageUrl }}
                    style={{ width: cardW, height: cardW, borderTopLeftRadius: br.md, borderTopRightRadius: br.md }}
                    contentFit="cover"
                    transition={150}
                  />
                ) : (
                  <View style={{ width: cardW, height: cardW, backgroundColor: colors.surfaceVariant, borderTopLeftRadius: br.md, borderTopRightRadius: br.md, alignItems: 'center', justifyContent: 'center' }}>
                    <Icon name="cart" size={24} color={colors.textDisabled} />
                  </View>
                )}
                <View style={{ padding: spacing.xs }}>
                  <Text variant="caption" color={colors.textPrimary} numberOfLines={1}>
                    {item.nome}
                  </Text>
                  <Text variant="priceSmall" color={colors.textPrimary} style={{ fontSize: 12, marginTop: 2 }}>
                    {formatCurrency(item.preco)}
                  </Text>
                </View>
              </TouchableOpacity>
            );
          }}
        />
      </>
    );
  };

  const renderTrustBlock = () => (
    <View style={[styles.trustBlock, { marginTop: spacing['2xl'], paddingHorizontal: spacing.lg }]}>
      {[
        { icon: 'cart' as const, title: 'Compra segura', sub: 'Pagamento protegido' },
        { icon: 'home' as const, title: 'Entrega rápida', sub: 'Frete calculado' },
        { icon: 'refresh' as const, title: 'Devolução fácil', sub: 'Até 7 dias' },
        { icon: 'notifications' as const, title: 'Acompanhe', sub: 'Tempo real' },
      ].map((item) => (
        <View key={item.title} style={[styles.trustItem, { backgroundColor: colors.surface, borderRadius: br.lg }]}>
          <Icon name={item.icon} size={24} color={colors.primary} />
          <Text variant="caption" color={colors.textPrimary} align="center" style={{ marginTop: 6, fontWeight: '600' }}>
            {item.title}
          </Text>
          <Text variant="caption" color={colors.textSecondary} align="center" style={{ marginTop: 2 }}>
            {item.sub}
          </Text>
        </View>
      ))}
    </View>
  );

  const renderHeader = () => (
    <>
      {/* Header */}
      <View style={[styles.header, { paddingHorizontal: spacing.lg, paddingTop: insets.top + spacing.md }]}>
        <View style={styles.headerRow}>
          <Text variant="h3" color={colors.textPrimary}>
            Ibix Market
          </Text>
          <View style={styles.headerActions}>
            <TouchableOpacity
              onPress={() => router.push('/notificacoes')}
              style={styles.headerIcon}
              accessibilityLabel={`Notificações${unreadCount > 0 ? `, ${unreadCount} não lidas` : ''}`}
            >
              <Icon name="notifications" size={24} color={colors.textPrimary} />
              {unreadCount > 0 && (
                <Badge count={unreadCount} style={{ position: 'absolute', top: -6, right: -8 }} />
              )}
            </TouchableOpacity>
          </View>
        </View>
        <View style={{ marginTop: spacing.sm }}>
          <LocationChip
            cidade={location?.cidade}
            uf={location?.uf}
            onPress={handleOpenCitySheet}
          />
        </View>
        <SearchBar
          containerStyle={{ marginTop: spacing.md }}
          onFocus={() => router.push('/busca')}
          editable={false}
          placeholder="Buscar produtos..."
        />
      </View>

      {/* Banners */}
      {vitrineQuery.isLoading ? (
        <View style={{ paddingHorizontal: spacing.lg, marginTop: spacing.lg }}>
          <Skeleton width={width - spacing.lg * 2} height={(width - spacing.lg * 2) * 0.45} radius={12} />
        </View>
      ) : (
        bannerCards.length > 0 && <BannerCarousel cards={bannerCards} />
      )}

      {/* Categorias em destaque */}
      {renderSectionHeader('Categorias', () => router.push('/(tabs)/categorias'))}
      {categoriesQuery.isLoading ? (
        <View style={[styles.categoryRow, { paddingLeft: spacing.lg }]}>
          {Array.from({ length: 5 }).map((_, i) => (
            <View key={i} style={{ marginRight: 12, alignItems: 'center' }}>
              <Skeleton width={64} height={64} radius={32} />
              <Skeleton width={50} height={10} radius={4} style={{ marginTop: 8 }} />
            </View>
          ))}
        </View>
      ) : (
        <FlatList
          data={categoriesQuery.data?.slice(0, 10)}
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={{ paddingLeft: spacing.lg, paddingTop: spacing.md }}
          keyExtractor={(item) => String(item.id)}
          renderItem={({ item }) => <CategoryCard category={item} size="sm" />}
        />
      )}

      {/* Perto de você (geo) */}
      {!location ? (
        <View
          style={{
            marginTop: spacing.xl,
            marginHorizontal: spacing.lg,
            padding: spacing.lg,
            borderRadius: br.lg,
            backgroundColor: colors.surfaceVariant,
            borderWidth: 1,
            borderColor: colors.borderLight,
          }}
        >
          <View style={{ flexDirection: 'row', alignItems: 'center' }}>
            <Icon name="location" size={18} color={colors.primary} />
            <Text variant="subtitle2" color={colors.textPrimary} style={{ marginLeft: 8 }}>
              Compre perto de você
            </Text>
          </View>
          <Text variant="caption" color={colors.textSecondary} style={{ marginTop: 4 }}>
            Defina sua cidade ou ative o GPS para vermos lojas e produtos próximos.
          </Text>
          <TouchableOpacity
            onPress={handleOpenCitySheet}
            style={{
              marginTop: spacing.md,
              alignSelf: 'flex-start',
              paddingHorizontal: spacing.md,
              paddingVertical: spacing.sm,
              borderRadius: br.full,
              backgroundColor: colors.primary,
            }}
            accessibilityLabel="Definir localização"
          >
            <Text variant="body2" color={colors.textInverse}>
              Definir localização
            </Text>
          </TouchableOpacity>
        </View>
      ) : (
        nearbyQuery.data?.items && nearbyQuery.data.items.length > 0 && (
          <>
            {renderSectionHeader(`Perto de você${location?.cidade ? ` em ${location.cidade}` : ''}`)}
            <NearbyAdsCarousel items={nearbyQuery.data.items} />
          </>
        )
      )}
      {!!location && nearbyQuery.isLoading && (
        <View style={{ paddingHorizontal: spacing.lg, paddingTop: spacing.md, flexDirection: 'row' }}>
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

      {/* Destaques (marketing-vitrine) */}
      {destaquesBlock && destaquesBlock.cards.length > 0 && (
        <>
          {renderSectionHeader(destaquesBlock.titulo ?? 'Destaques')}
          {renderProductHorizontal(destaquesBlock.cards)}
        </>
      )}

      {/* Ofertas da semana (marketing-vitrine) */}
      {ofertasSemanaBlock && ofertasSemanaBlock.cards.length > 0 && (
        <>
          {renderSectionHeader(ofertasSemanaBlock.titulo ?? 'Ofertas da semana')}
          {renderProductHorizontal(ofertasSemanaBlock.cards)}
        </>
      )}

      {/* Vistos recentemente */}
      {renderRecentlyViewed()}

      {/* Bloco de confiança */}
      {renderTrustBlock()}

      {/* Produtos recentes - titulo */}
      {renderSectionHeader('Novidades')}
    </>
  );

  const renderProductItem = useCallback(
    ({ item }: ListRenderItemInfo<ProductSummary>) => (
      <View style={{ width: '50%', paddingHorizontal: spacing.sm / 2 }}>
        <ProductCard product={item} onFavoriteToggle={handleFavoriteToggle} columns={2} />
      </View>
    ),
    [handleFavoriteToggle, spacing.sm],
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
    <View style={{ flex: 1, backgroundColor: colors.background }}>
      <FlatList
        data={allProducts}
        numColumns={2}
        keyExtractor={(item) => String(item.id)}
        renderItem={renderProductItem}
        ListHeaderComponent={renderHeader}
        ListFooterComponent={renderFooter}
        ListEmptyComponent={
          productsQuery.isLoading ? (
            <View style={[styles.gridLoading, { paddingHorizontal: spacing.lg }]}>
              {Array.from({ length: 4 }).map((_, i) => (
                <SkeletonCard key={i} style={{ width: (width - spacing.lg * 2 - spacing.sm) / 2, marginBottom: 12 }} />
              ))}
            </View>
          ) : null
        }
        onEndReached={handleEndReached}
        onEndReachedThreshold={0.4}
        refreshControl={
          <RefreshControl
            refreshing={isRefreshing}
            onRefresh={handleRefresh}
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
        style={{ flex: 1 }}
      />
      <CitySelectorSheet ref={citySheetRef} />
    </View>
  );
}

const styles = StyleSheet.create({
  header: {},
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  headerActions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  headerIcon: {
    padding: 4,
    position: 'relative',
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  categoryRow: {
    flexDirection: 'row',
    paddingTop: 12,
  },
  marketingCard: {
    overflow: 'hidden',
  },
  recentCard: {
    overflow: 'hidden',
  },
  trustBlock: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    gap: 8,
  },
  trustItem: {
    width: '48%',
    padding: 12,
    alignItems: 'center',
  },
  gridLoading: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
});
