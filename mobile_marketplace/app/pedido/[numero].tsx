import React from 'react';
import { View, StyleSheet, ScrollView, RefreshControl, TouchableOpacity } from 'react-native';
import { useLocalSearchParams, useRouter, Stack } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useQuery } from '@tanstack/react-query';

import { Text, Card, Divider, StatusBadge, Skeleton, Button, EmptyState, Icon } from '@/components/ui';
import { useTheme } from '@/hooks/useTheme';
import orderService from '@/services/orderService';
import { extractApiError } from '@/services/api';
import { QUERY_KEYS } from '@/constants/config';
import { formatCurrency } from '@/utils/format';

function formatDateTime(value?: string): string {
  if (!value) return '';
  try {
    return new Date(value).toLocaleString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return value;
  }
}

export default function PedidoDetalheScreen() {
  const { numero } = useLocalSearchParams<{ numero: string }>();
  const { colors, spacing } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();

  const orderQuery = useQuery({
    queryKey: [QUERY_KEYS.ORDER_DETAIL, numero],
    queryFn: () => orderService.getMyOrder(String(numero)),
    enabled: !!numero,
  });

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <Stack.Screen options={{ headerShown: false }} />

      <View style={[styles.header, { paddingTop: insets.top + spacing.md }]}>
        <TouchableOpacity onPress={() => router.back()} accessibilityLabel="Voltar">
          <Icon name="arrowLeft" size={24} color={colors.textPrimary} />
        </TouchableOpacity>
        <Text variant="subtitle1" color={colors.textPrimary} style={{ marginLeft: spacing.sm }}>
          Pedido #{numero}
        </Text>
      </View>

      <ScrollView
        contentContainerStyle={{ padding: spacing.lg, paddingBottom: insets.bottom + spacing['3xl'] }}
        refreshControl={
          <RefreshControl
            refreshing={orderQuery.isFetching && !orderQuery.isLoading}
            onRefresh={() => orderQuery.refetch()}
          />
        }
      >
        {orderQuery.isLoading ? (
          <>
            <Skeleton width="100%" height={120} radius={12} />
            <Skeleton width="100%" height={200} radius={12} style={{ marginTop: 12 }} />
          </>
        ) : orderQuery.error ? (
          <EmptyState
            title="Pedido não encontrado"
            description={extractApiError(orderQuery.error)}
            actionTitle="Voltar"
            onAction={() => router.back()}
          />
        ) : orderQuery.data ? (
          <>
            <Card style={{ padding: spacing.md }}>
              <View style={styles.headerRow}>
                <Text variant="subtitle2" color={colors.textPrimary}>
                  Status
                </Text>
                <StatusBadge status={(orderQuery.data.status_pedido ?? '').toUpperCase() || 'PENDENTE'} />
              </View>
              <Text variant="caption" color={colors.textSecondary} style={{ marginTop: 4 }}>
                Pagamento: {orderQuery.data.status_pagamento}
              </Text>
              <Text variant="caption" color={colors.textSecondary}>
                Entrega: {orderQuery.data.status_entrega}
              </Text>
              <Text variant="caption" color={colors.textSecondary} style={{ marginTop: 4 }}>
                Criado em {formatDateTime(orderQuery.data.created_at)}
              </Text>
              <Divider style={{ marginVertical: spacing.sm }} />
              <View style={styles.totalRow}>
                <Text variant="subtitle2" color={colors.textPrimary}>Total</Text>
                <Text variant="subtitle1" color={colors.primary}>
                  {formatCurrency(Number(orderQuery.data.total ?? 0))}
                </Text>
              </View>
            </Card>

            <Card style={{ padding: spacing.md, marginTop: spacing.md }}>
              <Text variant="subtitle2" color={colors.textPrimary}>
                Itens
              </Text>
              {orderQuery.data.itens.map((it, idx) => (
                <View key={`${it.nome}-${idx}`} style={{ marginTop: 8 }}>
                  <Text variant="body2" color={colors.textPrimary} numberOfLines={2}>
                    {it.quantidade}x {it.nome}
                  </Text>
                  <Text variant="caption" color={colors.textSecondary}>
                    Unit. {formatCurrency(it.preco_unitario)} — Subtotal {formatCurrency(it.subtotal)}
                  </Text>
                </View>
              ))}
            </Card>

            {orderQuery.data.timeline.length > 0 && (
              <Card style={{ padding: spacing.md, marginTop: spacing.md }}>
                <Text variant="subtitle2" color={colors.textPrimary}>
                  Linha do tempo
                </Text>
                {orderQuery.data.timeline.map((ev, idx) => (
                  <View key={idx} style={{ marginTop: 8 }}>
                    <Text variant="body2" color={colors.textPrimary}>
                      {ev.status_label ?? ev.status_codigo ?? ev.tipo_evento}
                    </Text>
                    {ev.created_at && (
                      <Text variant="caption" color={colors.textSecondary}>
                        {formatDateTime(ev.created_at)}
                      </Text>
                    )}
                  </View>
                ))}
              </Card>
            )}

            <Button
              title="Voltar para meus pedidos"
              variant="outline"
              size="lg"
              fullWidth
              onPress={() => router.replace('/(tabs)/pedidos')}
              style={{ marginTop: spacing.xl }}
            />
          </>
        ) : null}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingBottom: 12,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  totalRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
});
