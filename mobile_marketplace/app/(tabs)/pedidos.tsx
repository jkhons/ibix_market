import React from 'react';
import { View, StyleSheet, FlatList, RefreshControl, TouchableOpacity } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { useQuery } from '@tanstack/react-query';

import { Text, EmptyState, Card, StatusBadge, Skeleton } from '@/components/ui';
import { useTheme } from '@/hooks/useTheme';
import { useAuthStore } from '@/store/authStore';
import orderService, { type PedidoResumo } from '@/services/orderService';
import { extractApiError } from '@/services/api';
import { QUERY_KEYS } from '@/constants/config';
import { formatCurrency } from '@/utils/format';

function formatDate(value?: string): string {
  if (!value) return '';
  try {
    const d = new Date(value);
    return d.toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    });
  } catch {
    return '';
  }
}

export default function PedidosScreen() {
  const { colors, spacing } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { isAuthenticated } = useAuthStore();

  const ordersQuery = useQuery({
    queryKey: [QUERY_KEYS.ORDERS],
    queryFn: () => orderService.getMyOrders(),
    enabled: isAuthenticated,
    staleTime: 60 * 1000,
  });

  const renderItem = ({ item }: { item: PedidoResumo }) => (
    <TouchableOpacity
      onPress={() => router.push({ pathname: '/pedido/[numero]', params: { numero: item.numero_pedido } } as any)}
      accessibilityRole="button"
      accessibilityLabel={`Pedido ${item.numero_pedido}`}
    >
      <Card style={[styles.cardOuter, { padding: spacing.md, marginBottom: spacing.sm }]}>
        <View style={styles.headerRow}>
          <View style={{ flex: 1 }}>
            <Text variant="subtitle2" color={colors.textPrimary}>
              Pedido #{item.numero_pedido}
            </Text>
            <Text variant="caption" color={colors.textSecondary}>
              {formatDate(item.created_at)}
            </Text>
          </View>
          <StatusBadge status={item.status_pedido?.toUpperCase() ?? 'PENDENTE'} />
        </View>

        <View style={styles.itemsRow}>
          {item.itens.slice(0, 2).map((it) => (
            <Text
              key={it.anuncio_id}
              variant="body2"
              color={colors.textPrimary}
              numberOfLines={1}
              style={{ marginTop: 2 }}
            >
              • {it.quantidade}x {it.titulo}
            </Text>
          ))}
          {item.itens.length > 2 && (
            <Text variant="caption" color={colors.textSecondary} style={{ marginTop: 2 }}>
              +{item.itens.length - 2} item(ns)
            </Text>
          )}
        </View>

        <View style={styles.footerRow}>
          <Text variant="caption" color={colors.textSecondary}>
            Pagamento: {item.status_pagamento}
          </Text>
          <Text variant="subtitle2" color={colors.primary}>
            {formatCurrency(item.total)}
          </Text>
        </View>
      </Card>
    </TouchableOpacity>
  );

  if (!isAuthenticated) {
    return (
      <View style={[styles.container, { backgroundColor: colors.background, paddingTop: insets.top + spacing.md }]}>
        <View style={{ paddingHorizontal: spacing.lg }}>
          <Text variant="h3" color={colors.textPrimary}>Pedidos</Text>
        </View>
        <EmptyState
          title="Entre para ver seus pedidos"
          description="Acompanhe suas compras quando estiver logado"
          actionTitle="Entrar"
          onAction={() => router.push('/(auth)')}
        />
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: colors.background, paddingTop: insets.top + spacing.md }]}>
      <View style={{ paddingHorizontal: spacing.lg, marginBottom: spacing.sm }}>
        <Text variant="h3" color={colors.textPrimary}>Pedidos</Text>
      </View>

      {ordersQuery.isLoading ? (
        <View style={{ paddingHorizontal: spacing.lg }}>
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} width="100%" height={120} radius={12} style={{ marginBottom: 12 }} />
          ))}
        </View>
      ) : ordersQuery.error ? (
        <EmptyState
          title="Não foi possível carregar"
          description={extractApiError(ordersQuery.error)}
          actionTitle="Tentar novamente"
          onAction={() => ordersQuery.refetch()}
        />
      ) : (ordersQuery.data ?? []).length === 0 ? (
        <EmptyState
          title="Nenhum pedido"
          description="Suas compras aparecerão aqui"
          actionTitle="Explorar produtos"
          onAction={() => router.push('/(tabs)')}
        />
      ) : (
        <FlatList
          data={ordersQuery.data ?? []}
          keyExtractor={(item) => String(item.id)}
          contentContainerStyle={{ paddingHorizontal: spacing.lg, paddingBottom: spacing['3xl'] }}
          renderItem={renderItem}
          refreshControl={
            <RefreshControl refreshing={ordersQuery.isFetching} onRefresh={() => ordersQuery.refetch()} />
          }
          showsVerticalScrollIndicator={false}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  cardOuter: {},
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  itemsRow: {
    marginTop: 8,
  },
  footerRow: {
    marginTop: 10,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
});
