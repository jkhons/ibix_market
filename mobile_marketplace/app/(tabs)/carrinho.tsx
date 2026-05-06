import React, { useMemo, useState } from 'react';
import { View, StyleSheet, TouchableOpacity, SectionList, SectionListData, Alert } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Image } from 'expo-image';
import { Text, EmptyState, Button, QuantitySelector, Divider, Icon } from '@/components/ui';
import { CouponInput } from '@/components/checkout';
import { useTheme } from '@/hooks/useTheme';
import { useCartStore, CartItem } from '@/store/cartStore';
import { useAuthStore } from '@/store/authStore';
import { formatCurrency } from '@/utils/format';
import type { CouponValidation } from '@/services/couponService';
import { resolveRemoteAssetUrl } from '@/constants/config';

interface CartSection {
  lojaId: number;
  lojaNome: string;
  data: CartItem[];
}

function CartItemRow({ item }: { item: CartItem }) {
  const { colors, spacing, borderRadius: br } = useTheme();
  const { updateQuantity, removeItem } = useCartStore();
  const thumbUri = resolveRemoteAssetUrl(item.imageUrl);

  return (
    <View style={[styles.itemRow, { paddingVertical: spacing.md }]}>
      {thumbUri && (
        <Image source={{ uri: thumbUri }} style={[styles.thumb, { borderRadius: br.md }]} contentFit="cover" />
      )}
      <View style={{ flex: 1, marginLeft: spacing.md }}>
        <Text variant="body1" color={colors.textPrimary} numberOfLines={2}>
          {item.name}
        </Text>
        {item.originalPrice && item.originalPrice > item.price && (
          <Text variant="priceStrike" color={colors.textDisabled} style={{ marginTop: 2 }}>
            {formatCurrency(item.originalPrice)}
          </Text>
        )}
        <View style={styles.itemFooter}>
          <QuantitySelector
            value={item.quantity}
            max={item.maxQuantity}
            onChange={(qty) => updateQuantity(item.productId, qty, item.variantId)}
            size="sm"
          />
          <Text variant="priceSmall" color={colors.textPrimary}>
            {formatCurrency(item.price * item.quantity)}
          </Text>
        </View>
      </View>
      <TouchableOpacity
        onPress={() => removeItem(item.productId, item.variantId)}
        hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
        accessibilityLabel="Remover item"
        style={{ marginLeft: 8, padding: 4 }}
      >
        <Icon name="trash" size={18} color={colors.error} />
      </TouchableOpacity>
    </View>
  );
}

export default function CarrinhoScreen() {
  const { colors, spacing, shadow } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  const { items, totalPrice, totalItems } = useCartStore();
  const count = totalItems();
  const subtotal = totalPrice();

  const [coupon, setCoupon] = useState<(CouponValidation & { codigo: string }) | null>(null);

  const discount = coupon?.valido
    ? coupon.tipo_desconto === 'percentual'
      ? subtotal * ((coupon.desconto ?? 0) / 100)
      : (coupon.desconto ?? 0)
    : 0;

  const total = subtotal - discount;

  const sections: CartSection[] = useMemo(() => {
    const grouped: Record<number, CartSection> = {};
    for (const item of items) {
      if (!grouped[item.lojaId]) {
        grouped[item.lojaId] = { lojaId: item.lojaId, lojaNome: item.lojaNome ?? `Loja #${item.lojaId}`, data: [] };
      }
      grouped[item.lojaId].data.push(item);
    }
    return Object.values(grouped);
  }, [items]);

  const cartItemsForCoupon = useMemo(
    () => items.map((i) => ({ anuncio_id: i.productId, quantidade: i.quantity, preco_unitario: i.price })),
    [items],
  );

  const handleCheckout = () => {
    if (!isAuthenticated) {
      router.push('/(auth)');
      return;
    }
    router.push('/checkout/endereco' as any);
  };

  if (count === 0) {
    return (
      <View style={[styles.container, { backgroundColor: colors.background, paddingTop: insets.top + spacing.md }]}>
        <View style={{ paddingHorizontal: spacing.lg }}>
          <Text variant="h3" color={colors.textPrimary}>Carrinho</Text>
        </View>
        <EmptyState
          title="Carrinho vazio"
          description="Adicione produtos ao carrinho para continuar"
          actionLabel="Explorar"
          onAction={() => router.push('/(tabs)')}
        />
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <View style={{ paddingTop: insets.top + spacing.md, paddingHorizontal: spacing.lg }}>
        <Text variant="h3" color={colors.textPrimary}>
          Carrinho ({count})
        </Text>
      </View>

      <SectionList
        sections={sections}
        keyExtractor={(item) => `${item.productId}-${item.variantId ?? 0}`}
        renderSectionHeader={({ section }) => (
          <View style={[styles.sectionHeader, { backgroundColor: colors.surfaceVariant, paddingHorizontal: spacing.lg, paddingVertical: spacing.sm }]}>
            <Icon name="cart" size={16} color={colors.textSecondary} />
            <Text variant="subtitle2" color={colors.textPrimary} style={{ marginLeft: 8 }}>
              {(section as CartSection).lojaNome}
            </Text>
          </View>
        )}
        renderItem={({ item }) => (
          <View style={{ paddingHorizontal: spacing.lg }}>
            <CartItemRow item={item} />
          </View>
        )}
        ItemSeparatorComponent={() => <Divider style={{ marginHorizontal: spacing.lg }} />}
        SectionSeparatorComponent={() => <View style={{ height: spacing.sm }} />}
        ListFooterComponent={
          <View style={{ paddingHorizontal: spacing.lg, paddingTop: spacing.lg, paddingBottom: 180 }}>
            <Text variant="subtitle2" color={colors.textPrimary}>
              Cupom de desconto
            </Text>
            <CouponInput
              cartTotal={subtotal}
              cartItems={cartItemsForCoupon}
              onApplied={setCoupon}
              onRemove={() => setCoupon(null)}
              appliedCode={coupon?.codigo}
              style={{ marginTop: spacing.sm }}
            />
          </View>
        }
        showsVerticalScrollIndicator={false}
      />

      <View style={[styles.bottomBar, { backgroundColor: colors.surface, borderTopColor: colors.divider, paddingBottom: insets.bottom + spacing.sm, ...shadow('md') }]}>
        <View style={styles.priceRows}>
          <View style={styles.totalRow}>
            <Text variant="body2" color={colors.textSecondary}>Subtotal</Text>
            <Text variant="body2" color={colors.textPrimary}>{formatCurrency(subtotal)}</Text>
          </View>
          {discount > 0 && (
            <View style={styles.totalRow}>
              <Text variant="body2" color={colors.success}>Cupom</Text>
              <Text variant="body2" color={colors.success}>-{formatCurrency(discount)}</Text>
            </View>
          )}
          <View style={styles.totalRow}>
            <Text variant="subtitle1" color={colors.textPrimary}>Total</Text>
            <Text variant="price" color={colors.primary}>{formatCurrency(total)}</Text>
          </View>
        </View>
        <Button
          title="Finalizar Compra"
          onPress={handleCheckout}
          fullWidth
          size="lg"
          style={{ marginTop: spacing.sm }}
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  itemRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
  },
  thumb: { width: 72, height: 72 },
  itemFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 8,
  },
  bottomBar: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    paddingHorizontal: 16,
    paddingTop: 12,
    borderTopWidth: StyleSheet.hairlineWidth,
  },
  priceRows: {
    gap: 4,
  },
  totalRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
});
