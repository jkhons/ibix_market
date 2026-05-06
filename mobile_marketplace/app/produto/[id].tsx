import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  View,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  FlatList,
  useWindowDimensions,
  TextInput,
  Share,
} from 'react-native';
import { useLocalSearchParams, useRouter, Stack } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Image } from 'expo-image';
import GorhomBottomSheet from '@gorhom/bottom-sheet';

import { Text, Button, PriceTag, Skeleton, Card, Icon, Divider, Input, Badge } from '@/components/ui';
import { AppBottomSheet } from '@/components/ui/BottomSheet';
import { ProductCard, RatingStars } from '@/components/product';
import { useTheme } from '@/hooks/useTheme';
import { useCartStore } from '@/store/cartStore';
import { useRecentlyViewedStore } from '@/store/recentlyViewedStore';
import { useAuthStore } from '@/store/authStore';
import catalogService, { type Installment } from '@/services/catalogService';
import favoriteService from '@/services/favoriteService';
import { api } from '@/services/api';
import { QUERY_KEYS, resolveRemoteAssetUrl } from '@/constants/config';
import { formatCurrency, calculateDiscount } from '@/utils/format';
import ENV from '@/constants/config';
import { impactLight, notifySuccess } from '@/utils/haptics';

export default function ProductDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const productId = Number(id);
  const { colors, spacing, borderRadius: br, shadow } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { width } = useWindowDimensions();
  const queryClient = useQueryClient();

  const addItem = useCartStore((s) => s.addItem);
  const addViewed = useRecentlyViewedStore((s) => s.addItem);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  const installmentsRef = useRef<GorhomBottomSheet>(null);
  const [galleryIndex, setGalleryIndex] = useState(0);
  const [descExpanded, setDescExpanded] = useState(false);
  const [isFavorite, setIsFavorite] = useState(false);
  const [cep, setCep] = useState('');
  const [freteResult, setFreteResult] = useState<any>(null);
  const [freteLoading, setFreteLoading] = useState(false);

  const { data: product, isLoading } = useQuery({
    queryKey: [QUERY_KEYS.PRODUCT_DETAIL, productId],
    queryFn: () => catalogService.getProductById(productId),
    enabled: !!productId,
  });

  const { data: installments } = useQuery({
    queryKey: [QUERY_KEYS.INSTALLMENTS, product?.preco_promocional ?? product?.preco],
    queryFn: () => catalogService.getInstallments(product!.preco_promocional ?? product!.preco),
    enabled: !!product,
    staleTime: 5 * 60 * 1000,
  });

  const { data: similar } = useQuery({
    queryKey: [QUERY_KEYS.PRODUCT_SIMILAR, productId],
    queryFn: () => catalogService.getSimilarProducts(productId),
    enabled: !!productId,
    staleTime: 5 * 60 * 1000,
  });

  const { data: reviews } = useQuery({
    queryKey: [QUERY_KEYS.PRODUCT_REVIEWS, productId],
    queryFn: () => catalogService.getProductReviews(productId, { page: 1, page_size: 5 }),
    enabled: !!productId,
    staleTime: 5 * 60 * 1000,
  });

  useEffect(() => {
    if (product) {
      addViewed({
        id: product.id,
        nome: product.nome,
        preco: product.preco_promocional ?? product.preco,
        imageUrl: product.imagens?.[0],
        lojaId: product.loja_id,
      });
      if (product.favorito) setIsFavorite(true);
    }
  }, [product]);

  const hasDiscount = product?.preco_promocional && product.preco_promocional < product.preco;
  const displayPrice = product?.preco_promocional ?? product?.preco ?? 0;
  const discount = hasDiscount ? calculateDiscount(product!.preco, product!.preco_promocional!) : 0;

  const bestInstallment = installments?.filter((i) => !i.juros).sort((a, b) => b.parcelas - a.parcelas)[0];

  const handleAddToCart = useCallback(() => {
    if (!product) return;
    notifySuccess();
    addItem({
      productId: product.id,
      name: product.nome,
      price: product.preco_promocional ?? product.preco,
      originalPrice: product.preco_promocional ? product.preco : undefined,
      imageUrl: product.imagens?.[0],
      lojaId: product.loja_id,
      lojaNome: product.loja_nome,
      maxQuantity: product.estoque_disponivel ?? 99,
    });
  }, [product, addItem]);

  const handleBuyNow = useCallback(() => {
    handleAddToCart();
    if (!isAuthenticated) {
      router.push('/(auth)');
    } else {
      router.push('/checkout/endereco' as any);
    }
  }, [handleAddToCart, isAuthenticated, router]);

  const handleFavoriteToggle = useCallback(async () => {
    if (!isAuthenticated) {
      router.push('/(auth)');
      return;
    }
    impactLight();
    setIsFavorite((prev) => !prev);
    try {
      if (isFavorite) {
        await favoriteService.removeFavorite(productId);
      } else {
        await favoriteService.addFavorite(productId);
      }
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.FAVORITES] });
    } catch {
      setIsFavorite((prev) => !prev);
    }
  }, [isFavorite, productId, isAuthenticated, router, queryClient]);

  const handleShare = useCallback(async () => {
    if (!product) return;
    try {
      await Share.share({
        message: `${product.nome} — ${formatCurrency(displayPrice)} | ${ENV.APP_SCHEME}://produto/${product.id}`,
      });
    } catch {}
  }, [product, displayPrice]);

  const handleCalculateFrete = useCallback(async () => {
    if (!product || cep.length < 8) return;
    setFreteLoading(true);
    try {
      const { data } = await api.get(`/loja/${product.loja_id}/frete`, {
        params: { cep: cep.replace(/\D/g, '') },
      });
      setFreteResult(data);
    } catch {
      setFreteResult({ error: 'CEP não encontrado' });
    } finally {
      setFreteLoading(false);
    }
  }, [product, cep]);

  const handleChat = useCallback(() => {
    if (!isAuthenticated) {
      router.push('/(auth)');
      return;
    }
    router.push(`/chat?loja_id=${product?.loja_id}&anuncio_id=${product?.id}` as any);
  }, [isAuthenticated, product, router]);

  if (isLoading) {
    return (
      <View style={[styles.container, { backgroundColor: colors.background }]}>
        <Stack.Screen options={{ headerShown: false }} />
        <Skeleton width={width} height={width} radius={0} />
        <View style={{ padding: spacing.lg }}>
          <Skeleton width="80%" height={24} />
          <Skeleton width="50%" height={18} style={{ marginTop: 12 }} />
          <Skeleton width="40%" height={28} style={{ marginTop: 16 }} />
        </View>
      </View>
    );
  }

  if (!product) {
    return (
      <View style={[styles.container, styles.center, { backgroundColor: colors.background }]}>
        <Stack.Screen options={{ headerShown: false }} />
        <Text variant="body1" color={colors.textSecondary}>
          Produto não encontrado
        </Text>
        <Button title="Voltar" onPress={() => router.back()} variant="outline" style={{ marginTop: 16 }} />
      </View>
    );
  }

  const images = product.imagens ?? [];
  const lojaLogoUri = resolveRemoteAssetUrl(product.loja?.logo_url);

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <Stack.Screen options={{ headerShown: false }} />

      <ScrollView contentContainerStyle={{ paddingBottom: 100 }} showsVerticalScrollIndicator={false}>
        {/* Gallery */}
        <View style={{ position: 'relative' }}>
          <FlatList
            data={images}
            horizontal
            pagingEnabled
            showsHorizontalScrollIndicator={false}
            onMomentumScrollEnd={(e) => {
              const idx = Math.round(e.nativeEvent.contentOffset.x / width);
              setGalleryIndex(idx);
            }}
            keyExtractor={(_, i) => String(i)}
            renderItem={({ item }) => {
              const uri = resolveRemoteAssetUrl(item);
              return uri ? (
                <Image source={{ uri }} style={{ width, height: width }} contentFit="cover" transition={200} />
              ) : (
                <View style={{ width, height: width, backgroundColor: colors.surfaceVariant }} />
              );
            }}
            ListEmptyComponent={
              <View style={{ width, height: width, backgroundColor: colors.surfaceVariant, alignItems: 'center', justifyContent: 'center' }}>
                <Icon name="cart" size={48} color={colors.textDisabled} />
              </View>
            }
          />

          {/* Overlay buttons */}
          <TouchableOpacity
            onPress={() => router.back()}
            style={[styles.overlayBtn, { top: insets.top + 8, left: 16, backgroundColor: colors.surface }]}
            accessibilityLabel="Voltar"
          >
            <Icon name="chevronLeft" size={20} color={colors.textPrimary} />
          </TouchableOpacity>

          <View style={[styles.overlayActions, { top: insets.top + 8, right: 16 }]}>
            <TouchableOpacity
              onPress={handleFavoriteToggle}
              style={[styles.overlayBtn, { backgroundColor: colors.surface, marginBottom: 8 }]}
              accessibilityLabel={isFavorite ? 'Remover dos favoritos' : 'Adicionar aos favoritos'}
            >
              <Text style={{ fontSize: 18, color: isFavorite ? colors.accent : colors.textDisabled }}>
                {isFavorite ? '♥' : '♡'}
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              onPress={handleShare}
              style={[styles.overlayBtn, { backgroundColor: colors.surface }]}
              accessibilityLabel="Compartilhar"
            >
              <Icon name="share" size={18} color={colors.textPrimary} />
            </TouchableOpacity>
          </View>

          {/* Gallery indicators */}
          {images.length > 1 && (
            <View style={styles.galleryIndicators}>
              <View style={[styles.indicatorPill, { backgroundColor: colors.overlay }]}>
                <Text variant="caption" color={colors.white}>
                  {galleryIndex + 1}/{images.length}
                </Text>
              </View>
            </View>
          )}

          {/* Discount badge */}
          {hasDiscount && (
            <View style={[styles.discountBadge, { backgroundColor: colors.accent }]}>
              <Text variant="caption" color={colors.white} style={{ fontWeight: '700' }}>
                -{discount}%
              </Text>
            </View>
          )}
        </View>

        {/* Price */}
        <View style={[styles.section, { paddingHorizontal: spacing.lg }]}>
          {hasDiscount && (
            <Text variant="priceStrike" color={colors.textDisabled} style={{ marginTop: spacing.lg }}>
              {formatCurrency(product.preco)}
            </Text>
          )}
          <Text variant="h2" color={hasDiscount ? colors.success : colors.textPrimary} style={{ marginTop: hasDiscount ? 2 : spacing.lg }}>
            {formatCurrency(displayPrice)}
          </Text>
          {bestInstallment && (
            <TouchableOpacity
              onPress={() => installmentsRef.current?.snapToIndex(0)}
              accessibilityLabel="Ver parcelas"
            >
              <Text variant="body2" color={colors.textSecondary} style={{ marginTop: 4 }}>
                em até{' '}
                <Text variant="body2" color={colors.primary} style={{ fontWeight: '600' }}>
                  {bestInstallment.parcelas}x de {formatCurrency(bestInstallment.valor_parcela)} sem juros
                </Text>
              </Text>
            </TouchableOpacity>
          )}
        </View>

        {/* Title */}
        <View style={[styles.section, { paddingHorizontal: spacing.lg, marginTop: spacing.md }]}>
          <Text variant="subtitle1" color={colors.textPrimary}>
            {product.nome}
          </Text>

          {product.avaliacoes_media !== undefined && (
            <View style={{ marginTop: spacing.sm }}>
              <RatingStars rating={product.avaliacoes_media} count={product.avaliacoes_count} size="sm" />
            </View>
          )}
        </View>

        <Divider style={{ marginVertical: spacing.lg }} />

        {/* Description */}
        {product.descricao && (
          <View style={{ paddingHorizontal: spacing.lg }}>
            <Text variant="subtitle2" color={colors.textPrimary}>
              Descrição
            </Text>
            <Text
              variant="body2"
              color={colors.textSecondary}
              numberOfLines={descExpanded ? undefined : 4}
              style={{ marginTop: spacing.sm }}
            >
              {product.descricao}
            </Text>
            <TouchableOpacity onPress={() => setDescExpanded(!descExpanded)}>
              <Text variant="body2" color={colors.primary} style={{ marginTop: 4 }}>
                {descExpanded ? 'Ver menos' : 'Ver mais'}
              </Text>
            </TouchableOpacity>
            <Divider style={{ marginVertical: spacing.lg }} />
          </View>
        )}

        {/* Specifications */}
        {product.especificacoes && Object.keys(product.especificacoes).length > 0 && (
          <View style={{ paddingHorizontal: spacing.lg }}>
            <Text variant="subtitle2" color={colors.textPrimary}>
              Especificações
            </Text>
            {Object.entries(product.especificacoes).map(([key, val]) => (
              <View key={key} style={[styles.specRow, { borderBottomColor: colors.divider }]}>
                <Text variant="body2" color={colors.textSecondary}>
                  {key}
                </Text>
                <Text variant="body2" color={colors.textPrimary}>
                  {val}
                </Text>
              </View>
            ))}
            <Divider style={{ marginVertical: spacing.lg }} />
          </View>
        )}

        {/* Loja */}
        {product.loja && (
          <TouchableOpacity
            onPress={() => router.push(`/loja/${product.loja!.slug}`)}
            style={[styles.lojaCard, { marginHorizontal: spacing.lg, backgroundColor: colors.surface, borderRadius: br.lg, ...shadow('sm') }]}
            accessibilityLabel={`Loja ${product.loja.nome}`}
          >
            {lojaLogoUri && (
              <Image
                source={{ uri: lojaLogoUri }}
                style={{ width: 48, height: 48, borderRadius: 24 }}
                contentFit="cover"
              />
            )}
            <View style={{ flex: 1, marginLeft: 12 }}>
              <Text variant="subtitle2" color={colors.textPrimary}>
                {product.loja.nome}
              </Text>
              {product.loja.cidade && (
                <Text variant="caption" color={colors.textSecondary}>
                  {product.loja.cidade}
                </Text>
              )}
              {product.loja.avaliacao_media !== undefined && (
                <RatingStars rating={product.loja.avaliacao_media} size="sm" style={{ marginTop: 4 }} />
              )}
            </View>
            <Icon name="chevronRight" size={20} color={colors.textDisabled} />
          </TouchableOpacity>
        )}

        {/* Chat vendedor */}
        <TouchableOpacity
          onPress={handleChat}
          style={[styles.chatBtn, { marginHorizontal: spacing.lg, marginTop: spacing.md, borderColor: colors.primary, borderRadius: br.lg }]}
          accessibilityLabel="Perguntar ao vendedor"
        >
          <Icon name="chat" size={18} color={colors.primary} />
          <Text variant="button" color={colors.primary} style={{ marginLeft: 8 }}>
            Perguntar ao vendedor
          </Text>
        </TouchableOpacity>

        <Divider style={{ marginVertical: spacing.lg }} />

        {/* Frete */}
        <View style={{ paddingHorizontal: spacing.lg }}>
          <Text variant="subtitle2" color={colors.textPrimary}>
            Calcular frete
          </Text>
          <View style={styles.freteRow}>
            <TextInput
              value={cep}
              onChangeText={setCep}
              placeholder="00000-000"
              placeholderTextColor={colors.textDisabled}
              keyboardType="numeric"
              maxLength={9}
              style={[styles.cepInput, { borderColor: colors.border, borderRadius: br.md, color: colors.textPrimary }]}
              accessibilityLabel="CEP"
            />
            <Button
              title="Calcular"
              onPress={handleCalculateFrete}
              variant="outline"
              size="sm"
              loading={freteLoading}
              disabled={cep.replace(/\D/g, '').length < 8}
              style={{ marginLeft: 8 }}
            />
          </View>
          {freteResult && !freteResult.error && (
            <View style={{ marginTop: spacing.sm }}>
              <Text variant="body2" color={colors.textPrimary}>
                {freteResult.valor_frete === 0
                  ? 'Frete grátis!'
                  : `Frete: ${formatCurrency(freteResult.valor_frete)}`}
              </Text>
              {freteResult.prazo && (
                <Text variant="caption" color={colors.textSecondary}>
                  Prazo: {freteResult.prazo}
                </Text>
              )}
            </View>
          )}
          {freteResult?.error && (
            <Text variant="caption" color={colors.error} style={{ marginTop: 4 }}>
              {freteResult.error}
            </Text>
          )}
        </View>

        <Divider style={{ marginVertical: spacing.lg }} />

        {/* Reviews summary */}
        {reviews && reviews.items.length > 0 && (
          <View style={{ paddingHorizontal: spacing.lg }}>
            <Text variant="subtitle2" color={colors.textPrimary}>
              Avaliações
            </Text>
            <View style={styles.reviewSummary}>
              <Text variant="h2" color={colors.textPrimary}>
                {product.avaliacoes_media?.toFixed(1) ?? '-'}
              </Text>
              <View style={{ marginLeft: 12 }}>
                <RatingStars rating={product.avaliacoes_media ?? 0} size="md" />
                <Text variant="caption" color={colors.textSecondary}>
                  {product.avaliacoes_count ?? 0} avaliações
                </Text>
              </View>
            </View>

            {reviews.items.slice(0, 3).map((rev) => (
              <View key={rev.id} style={[styles.reviewItem, { borderBottomColor: colors.divider }]}>
                <View style={styles.reviewHeader}>
                  <Text variant="body2" color={colors.textPrimary} style={{ fontWeight: '600' }}>
                    {rev.consumidor_nome}
                  </Text>
                  <RatingStars rating={rev.nota} size="sm" />
                </View>
                {rev.comentario && (
                  <Text variant="body2" color={colors.textSecondary} style={{ marginTop: 4 }}>
                    {rev.comentario}
                  </Text>
                )}
              </View>
            ))}
            <Divider style={{ marginVertical: spacing.lg }} />
          </View>
        )}

        {/* Similar products */}
        {similar && similar.length > 0 && (
          <View>
            <Text variant="subtitle2" color={colors.textPrimary} style={{ paddingHorizontal: spacing.lg }}>
              Produtos similares
            </Text>
            <FlatList
              data={similar}
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={{ paddingHorizontal: spacing.lg, paddingTop: spacing.md }}
              keyExtractor={(item) => String(item.id)}
              renderItem={({ item }) => (
                <View style={{ width: width * 0.42, marginRight: spacing.sm }}>
                  <ProductCard product={item} columns={2} />
                </View>
              )}
            />
          </View>
        )}
      </ScrollView>

      {/* Sticky bottom bar */}
      <View
        style={[
          styles.bottomBar,
          {
            backgroundColor: colors.surface,
            paddingBottom: insets.bottom + spacing.sm,
            borderTopColor: colors.divider,
            ...shadow('md'),
          },
        ]}
      >
        <Button
          title="Adicionar"
          onPress={handleAddToCart}
          variant="outline"
          size="lg"
          style={{ flex: 1, marginRight: 8 }}
          disabled={product.estoque_disponivel !== undefined && product.estoque_disponivel <= 0}
        />
        <Button
          title="Comprar agora"
          onPress={handleBuyNow}
          variant="primary"
          size="lg"
          style={{ flex: 1.5 }}
          disabled={product.estoque_disponivel !== undefined && product.estoque_disponivel <= 0}
        />
      </View>

      {/* Installments BottomSheet */}
      <AppBottomSheet ref={installmentsRef} snapPoints={['50%', '80%']}>
        <Text variant="h4" color={colors.textPrimary}>
          Parcelas
        </Text>
        <ScrollView showsVerticalScrollIndicator={false} style={{ marginTop: spacing.md }}>
          {(installments ?? product.parcelas ?? []).map((inst: Installment) => (
            <View key={inst.parcelas} style={[styles.installmentRow, { borderBottomColor: colors.divider }]}>
              <Text variant="body1" color={colors.textPrimary}>
                {inst.parcelas}x de {formatCurrency(inst.valor_parcela)}
              </Text>
              <Text variant="body2" color={inst.juros ? colors.warning : colors.success}>
                {inst.juros ? 'com juros' : 'sem juros'}
              </Text>
            </View>
          ))}
        </ScrollView>
      </AppBottomSheet>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  center: { alignItems: 'center', justifyContent: 'center' },
  section: {},
  overlayBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  overlayActions: {
    position: 'absolute',
    zIndex: 10,
    alignItems: 'center',
  },
  galleryIndicators: {
    position: 'absolute',
    bottom: 12,
    left: 0,
    right: 0,
    alignItems: 'center',
  },
  indicatorPill: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
  },
  discountBadge: {
    position: 'absolute',
    bottom: 12,
    left: 12,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
  },
  specRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 8,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  lojaCard: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
  },
  chatBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 12,
    borderWidth: 1.5,
  },
  freteRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 8,
  },
  cepInput: {
    flex: 1,
    height: 40,
    borderWidth: 1,
    paddingHorizontal: 12,
    fontSize: 15,
  },
  reviewSummary: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 12,
    marginBottom: 12,
  },
  reviewHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  reviewItem: {
    paddingVertical: 12,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  installmentRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 14,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  bottomBar: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    flexDirection: 'row',
    paddingHorizontal: 16,
    paddingTop: 12,
    borderTopWidth: StyleSheet.hairlineWidth,
  },
});
