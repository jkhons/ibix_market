import React, { useCallback, useMemo, useState } from 'react';
import {
  View,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  useWindowDimensions,
  ListRenderItemInfo,
  RefreshControl,
} from 'react-native';
import Animated, {
  useAnimatedScrollHandler,
  useAnimatedStyle,
  useSharedValue,
  interpolate,
  Extrapolation,
} from 'react-native-reanimated';
import { useLocalSearchParams, useRouter, Stack } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useQuery, useInfiniteQuery } from '@tanstack/react-query';
import { Image } from 'expo-image';

import { Text, Skeleton, SkeletonCard, Button, Icon, EmptyState, Chip, Divider } from '@/components/ui';
import { ProductCard, RatingStars } from '@/components/product';
import { useTheme } from '@/hooks/useTheme';
import { useAuthStore } from '@/store/authStore';
import catalogService, { type ProductSummary } from '@/services/catalogService';
import { QUERY_KEYS, PAGINATION } from '@/constants/config';

const BANNER_HEIGHT = 200;

const AnimatedFlatList = Animated.createAnimatedComponent(FlatList<ProductSummary>);

export default function StoreDetailScreen() {
  const { slug } = useLocalSearchParams<{ slug: string }>();
  const { colors, spacing, borderRadius: br, shadow } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { width } = useWindowDimensions();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  const columns = width >= 600 ? 3 : 2;
  const scrollY = useSharedValue(0);

  const scrollHandler = useAnimatedScrollHandler({
    onScroll: (e) => {
      scrollY.value = e.contentOffset.y;
    },
  });

  const headerStyle = useAnimatedStyle(() => ({
    opacity: interpolate(scrollY.value, [BANNER_HEIGHT - 80, BANNER_HEIGHT], [0, 1], Extrapolation.CLAMP),
  }));

  const { data: store, isLoading: storeLoading } = useQuery({
    queryKey: [QUERY_KEYS.STORE_DETAIL, slug],
    queryFn: () => catalogService.getStoreBySlug(slug!),
    enabled: !!slug,
  });

  const productsQuery = useInfiniteQuery({
    queryKey: [QUERY_KEYS.STORE_PRODUCTS, slug],
    queryFn: ({ pageParam = 1 }) =>
      catalogService.getStoreProducts(slug!, { page: pageParam, page_size: PAGINATION.PRODUCT_PAGE_SIZE }),
    getNextPageParam: (lastPage) => (lastPage.has_next ? lastPage.page + 1 : undefined),
    enabled: !!slug,
    staleTime: 60 * 1000,
    initialPageParam: 1,
  });

  const allProducts = useMemo(
    () => productsQuery.data?.pages.flatMap((p) => p.items) ?? [],
    [productsQuery.data],
  );

  const handleEndReached = useCallback(() => {
    if (productsQuery.hasNextPage && !productsQuery.isFetchingNextPage) {
      productsQuery.fetchNextPage();
    }
  }, [productsQuery.hasNextPage, productsQuery.isFetchingNextPage]);

  const handleChat = useCallback(() => {
    if (!isAuthenticated) {
      router.push('/(auth)');
      return;
    }
    router.push(`/chat?loja_id=${store?.id}` as any);
  }, [isAuthenticated, store, router]);

  const renderHeader = () => (
    <>
      {/* Parallax Banner */}
      <View style={{ height: BANNER_HEIGHT, position: 'relative' }}>
        {store?.banner_url ? (
          <Image source={{ uri: store.banner_url }} style={StyleSheet.absoluteFill} contentFit="cover" />
        ) : (
          <View style={[StyleSheet.absoluteFill, { backgroundColor: colors.primary }]} />
        )}

        <View style={[StyleSheet.absoluteFill, { backgroundColor: 'rgba(0,0,0,0.3)' }]} />

        <TouchableOpacity
          onPress={() => router.back()}
          style={[styles.overlayBtn, { top: insets.top + 8, left: 16, backgroundColor: 'rgba(255,255,255,0.9)' }]}
          accessibilityLabel="Voltar"
        >
          <Icon name="chevronLeft" size={20} color={colors.textPrimary} />
        </TouchableOpacity>

        {/* Store info overlay */}
        <View style={[styles.storeOverlay, { bottom: 16, left: 16, right: 16 }]}>
          <View style={{ flexDirection: 'row', alignItems: 'center' }}>
            {store?.logo_url && (
              <Image
                source={{ uri: store.logo_url }}
                style={{ width: 56, height: 56, borderRadius: 28, borderWidth: 2, borderColor: colors.white }}
                contentFit="cover"
              />
            )}
            <View style={{ marginLeft: 12, flex: 1 }}>
              <Text variant="h4" color={colors.white}>
                {store?.nome ?? 'Loja'}
              </Text>
              {store?.avaliacao_media !== undefined && (
                <RatingStars rating={store.avaliacao_media} size="sm" style={{ marginTop: 4 }} />
              )}
            </View>
          </View>
        </View>
      </View>

      {/* Actions bar */}
      <View style={[styles.actionsBar, { paddingHorizontal: spacing.lg, paddingVertical: spacing.md, backgroundColor: colors.surface }]}>
        <TouchableOpacity
          onPress={handleChat}
          style={[styles.actionBtn, { borderColor: colors.primary, borderRadius: br.lg }]}
          accessibilityLabel="Conversar com vendedor"
        >
          <Icon name="chat" size={16} color={colors.primary} />
          <Text variant="body2" color={colors.primary} style={{ marginLeft: 6 }}>
            Conversar
          </Text>
        </TouchableOpacity>
      </View>

      <Divider />

      {/* Product count header */}
      <View style={[styles.productCountRow, { paddingHorizontal: spacing.lg, paddingVertical: spacing.md }]}>
        <Text variant="subtitle2" color={colors.textPrimary}>
          Produtos
        </Text>
        {productsQuery.data?.pages[0]?.total !== undefined && (
          <Text variant="body2" color={colors.textSecondary}>
            {productsQuery.data.pages[0].total} encontrados
          </Text>
        )}
      </View>
    </>
  );

  const renderItem = useCallback(
    ({ item }: ListRenderItemInfo<ProductSummary>) => (
      <View style={{ width: `${100 / columns}%`, paddingHorizontal: spacing.sm / 2 }}>
        <ProductCard product={item} columns={columns} />
      </View>
    ),
    [columns],
  );

  const renderFooter = () => {
    if (!productsQuery.isFetchingNextPage) return null;
    return (
      <View style={{ padding: spacing.lg, alignItems: 'center' }}>
        <Skeleton width={width * 0.4} height={16} radius={8} />
      </View>
    );
  };

  if (storeLoading) {
    return (
      <View style={[styles.container, { backgroundColor: colors.background }]}>
        <Stack.Screen options={{ headerShown: false }} />
        <Skeleton width={width} height={BANNER_HEIGHT} radius={0} />
        <View style={{ padding: spacing.lg }}>
          <Skeleton width="60%" height={24} />
          <Skeleton width="40%" height={16} style={{ marginTop: 8 }} />
        </View>
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <Stack.Screen options={{ headerShown: false }} />

      {/* Sticky header (shows on scroll) */}
      <Animated.View
        style={[
          styles.stickyHeader,
          {
            backgroundColor: colors.surface,
            paddingTop: insets.top,
            borderBottomColor: colors.divider,
          },
          headerStyle,
        ]}
      >
        <View style={styles.stickyHeaderInner}>
          <TouchableOpacity onPress={() => router.back()} accessibilityLabel="Voltar">
            <Icon name="chevronLeft" size={20} color={colors.textPrimary} />
          </TouchableOpacity>
          <Text variant="subtitle1" color={colors.textPrimary} style={{ marginLeft: 12 }}>
            {store?.nome}
          </Text>
        </View>
      </Animated.View>

      <AnimatedFlatList
        data={allProducts}
        numColumns={columns}
        keyExtractor={(item: ProductSummary) => String(item.id)}
        renderItem={renderItem}
        ListHeaderComponent={renderHeader}
        ListFooterComponent={renderFooter}
        ListEmptyComponent={
          productsQuery.isLoading ? (
            <View style={styles.loadingGrid}>
              {Array.from({ length: 4 }).map((_, i) => (
                <SkeletonCard key={i} style={{ width: (width - spacing.lg * 2 - spacing.sm) / columns, marginBottom: 12 }} />
              ))}
            </View>
          ) : (
            <EmptyState
              title="Nenhum produto"
              description="Esta loja ainda não possui produtos publicados."
            />
          )
        }
        onEndReached={handleEndReached}
        onEndReachedThreshold={0.4}
        onScroll={scrollHandler}
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
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  overlayBtn: {
    position: 'absolute',
    zIndex: 10,
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
    elevation: 3,
  },
  storeOverlay: {
    position: 'absolute',
  },
  actionsBar: {
    flexDirection: 'row',
  },
  actionBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderWidth: 1.5,
  },
  productCountRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  stickyHeader: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    zIndex: 20,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  stickyHeaderInner: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  loadingGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
});
