import React, { useCallback } from 'react';
import { View, StyleSheet, TouchableOpacity, useWindowDimensions } from 'react-native';
import { Image } from 'expo-image';
import { useRouter } from 'expo-router';
import * as Haptics from 'expo-haptics';
import { Text, Badge } from '@/components/ui';
import { useTheme } from '@/hooks/useTheme';
import { formatCurrency, calculateDiscount } from '@/utils/format';
import type { ProductSummary } from '@/services/catalogService';

interface ProductCardProps {
  product: ProductSummary;
  onFavoriteToggle?: (id: number) => void;
  isFavorite?: boolean;
  columns?: number;
}

export function ProductCard({ product, onFavoriteToggle, isFavorite, columns = 2 }: ProductCardProps) {
  const { colors, spacing, borderRadius: br, shadow } = useTheme();
  const router = useRouter();
  const { width } = useWindowDimensions();

  const cardWidth = (width - spacing.lg * 2 - spacing.sm * (columns - 1)) / columns;
  const imageHeight = cardWidth * 1.1;

  const hasDiscount = product.preco_promocional && product.preco_promocional < product.preco;
  const displayPrice = product.preco_promocional ?? product.preco;
  const discount = hasDiscount ? calculateDiscount(product.preco, product.preco_promocional!) : 0;

  const handlePress = useCallback(() => {
    router.push(`/produto/${product.id}`);
  }, [product.id]);

  const handleFavorite = useCallback(() => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    onFavoriteToggle?.(product.id);
  }, [product.id, onFavoriteToggle]);

  return (
    <TouchableOpacity
      onPress={handlePress}
      activeOpacity={0.8}
      accessibilityLabel={`${product.nome}, ${formatCurrency(displayPrice)}`}
      style={[styles.card, { width: cardWidth, backgroundColor: colors.surface, borderRadius: br.lg, ...shadow('sm') }]}
    >
      <View style={[styles.imageContainer, { height: imageHeight, borderTopLeftRadius: br.lg, borderTopRightRadius: br.lg }]}>
        {product.imagens?.[0] ? (
          <Image
            source={{ uri: product.imagens[0] }}
            style={StyleSheet.absoluteFill}
            contentFit="cover"
            transition={200}
            recyclingKey={`product-${product.id}`}
          />
        ) : (
          <View style={[StyleSheet.absoluteFill, { backgroundColor: colors.surfaceVariant, alignItems: 'center', justifyContent: 'center' }]}>
            <Text variant="caption" color={colors.textDisabled}>Sem foto</Text>
          </View>
        )}

        {hasDiscount && (
          <View style={[styles.discountBadge, { backgroundColor: colors.accent }]}>
            <Text variant="caption" color={colors.white} style={styles.discountText}>
              -{discount}%
            </Text>
          </View>
        )}

        {onFavoriteToggle && (
          <TouchableOpacity
            onPress={handleFavorite}
            style={[styles.favoriteBtn, { backgroundColor: colors.surface }]}
            hitSlop={{ top: 6, bottom: 6, left: 6, right: 6 }}
            accessibilityLabel={isFavorite ? 'Remover dos favoritos' : 'Adicionar aos favoritos'}
          >
            <Text variant="body2" color={isFavorite ? colors.accent : colors.textDisabled}>
              {isFavorite ? '♥' : '♡'}
            </Text>
          </TouchableOpacity>
        )}
      </View>

      <View style={[styles.info, { padding: spacing.sm }]}>
        <Text variant="body2" color={colors.textPrimary} numberOfLines={2} style={styles.title}>
          {product.nome}
        </Text>

        {hasDiscount && (
          <Text variant="caption" color={colors.textDisabled} style={styles.oldPrice}>
            {formatCurrency(product.preco)}
          </Text>
        )}

        <Text variant="priceSmall" color={hasDiscount ? colors.success : colors.textPrimary}>
          {formatCurrency(displayPrice)}
        </Text>

        {product.parcela_sem_juros && (
          <Text variant="caption" color={colors.textSecondary} style={{ marginTop: 2 }}>
            {product.parcela_sem_juros}
          </Text>
        )}

        {product.loja_nome && (
          <Text variant="caption" color={colors.textDisabled} numberOfLines={1} style={{ marginTop: 4 }}>
            {product.loja_nome}
          </Text>
        )}
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: {
    overflow: 'hidden',
    marginBottom: 12,
  },
  imageContainer: {
    overflow: 'hidden',
    position: 'relative',
  },
  discountBadge: {
    position: 'absolute',
    top: 8,
    left: 8,
    paddingHorizontal: 6,
    paddingVertical: 3,
    borderRadius: 4,
  },
  discountText: {
    fontSize: 10,
    fontWeight: '700',
  },
  favoriteBtn: {
    position: 'absolute',
    top: 8,
    right: 8,
    width: 30,
    height: 30,
    borderRadius: 15,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  info: {},
  title: {
    minHeight: 34,
  },
  oldPrice: {
    textDecorationLine: 'line-through',
    marginTop: 6,
  },
});
