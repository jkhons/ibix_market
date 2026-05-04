import React, { useEffect, useMemo, useState } from 'react';
import { View, StyleSheet, ScrollView, TouchableOpacity } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useQuery } from '@tanstack/react-query';

import { Text, Button, Skeleton, Icon, Divider } from '@/components/ui';
import { useTheme } from '@/hooks/useTheme';
import { useCartStore } from '@/store/cartStore';
import addressService from '@/services/addressService';
import checkoutService, { type FreightResult, type FreightOption } from '@/services/checkoutService';
import { QUERY_KEYS } from '@/constants/config';
import { formatCurrency } from '@/utils/format';

export default function CheckoutFreteScreen() {
  const { endereco_id } = useLocalSearchParams<{ endereco_id: string }>();
  const { colors, spacing, borderRadius: br, shadow } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();

  const { items, itemsByLoja } = useCartStore();
  const grouped = itemsByLoja();
  const lojaIds = Object.keys(grouped).map(Number);

  const [selectedFreight, setSelectedFreight] = useState<Record<number, string>>({});

  const addressQuery = useQuery({
    queryKey: [QUERY_KEYS.ADDRESSES, 'selected', endereco_id],
    queryFn: async () => {
      const all = await addressService.list();
      const addr = all.find((a) => a.id === Number(endereco_id));
      if (!addr) throw new Error('Endereço não encontrado');
      return addr;
    },
    enabled: !!endereco_id,
  });

  const cep = addressQuery.data?.cep?.replace(/\D/g, '') ?? '';

  const freightQueries = useQuery({
    queryKey: ['freight', cep, lojaIds],
    queryFn: async () => {
      const results = await Promise.all(
        lojaIds.map((lojaId) => checkoutService.calculateFreight(lojaId, cep)),
      );
      return results;
    },
    enabled: cep.length === 8 && lojaIds.length > 0,
    staleTime: 5 * 60 * 1000,
  });

  useEffect(() => {
    if (freightQueries.data) {
      const defaults: Record<number, string> = {};
      for (const result of freightQueries.data) {
        if (result.opcoes.length > 0) {
          const freeOption = result.opcoes.find((o) => o.frete_gratis);
          defaults[result.loja_id] = freeOption?.tipo ?? result.opcoes[0].tipo;
        }
      }
      setSelectedFreight(defaults);
    }
  }, [freightQueries.data]);

  const totalFrete = useMemo(() => {
    if (!freightQueries.data) return 0;
    let total = 0;
    for (const result of freightQueries.data) {
      const sel = selectedFreight[result.loja_id];
      const option = result.opcoes.find((o) => o.tipo === sel);
      total += option?.frete_gratis ? 0 : (option?.valor ?? 0);
    }
    return total;
  }, [freightQueries.data, selectedFreight]);

  const handleContinue = () => {
    const fretes = Object.entries(selectedFreight).map(([lojaId, tipo]) => ({
      loja_id: Number(lojaId),
      tipo_frete: tipo,
    }));
    router.push({
      pathname: '/checkout/pagamento',
      params: {
        endereco_id: endereco_id!,
        fretes: JSON.stringify(fretes),
        total_frete: String(totalFrete),
      },
    } as any);
  };

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <ScrollView
        contentContainerStyle={{ padding: spacing.lg, paddingBottom: 120 }}
        showsVerticalScrollIndicator={false}
      >
        {/* Address summary */}
        {addressQuery.data && (
          <View style={[styles.addressSummary, { backgroundColor: colors.surface, borderRadius: br.lg, padding: spacing.md, ...shadow('sm') }]}>
            <Icon name="location" size={18} color={colors.primary} />
            <View style={{ flex: 1, marginLeft: spacing.sm }}>
              <Text variant="body2" color={colors.textPrimary}>
                {addressQuery.data.logradouro}, {addressQuery.data.numero}
              </Text>
              <Text variant="caption" color={colors.textSecondary}>
                {addressQuery.data.cidade}/{addressQuery.data.uf} — CEP {addressQuery.data.cep}
              </Text>
            </View>
          </View>
        )}

        {/* Freight options per store */}
        {freightQueries.isLoading ? (
          Array.from({ length: lojaIds.length }).map((_, i) => (
            <Skeleton key={i} width="100%" height={100} radius={12} style={{ marginTop: 16 }} />
          ))
        ) : freightQueries.data ? (
          freightQueries.data.map((result) => (
            <View key={result.loja_id} style={{ marginTop: spacing.xl }}>
              <Text variant="subtitle2" color={colors.textPrimary}>
                {result.loja_nome}
              </Text>

              {result.opcoes.length === 0 ? (
                <Text variant="body2" color={colors.error} style={{ marginTop: spacing.sm }}>
                  Frete indisponível para este endereço
                </Text>
              ) : (
                result.opcoes.map((option) => {
                  const isSelected = selectedFreight[result.loja_id] === option.tipo;
                  return (
                    <TouchableOpacity
                      key={option.tipo}
                      onPress={() => setSelectedFreight((p) => ({ ...p, [result.loja_id]: option.tipo }))}
                      accessibilityLabel={`${option.descricao ?? option.tipo}: ${option.frete_gratis ? 'Grátis' : formatCurrency(option.valor)}`}
                      accessibilityState={{ selected: isSelected }}
                      style={[
                        styles.freightOption,
                        {
                          borderColor: isSelected ? colors.primary : colors.border,
                          borderWidth: isSelected ? 2 : 1,
                          borderRadius: br.lg,
                          padding: spacing.md,
                          marginTop: spacing.sm,
                          backgroundColor: isSelected ? colors.primarySurface : colors.surface,
                        },
                      ]}
                    >
                      <View style={{ flex: 1 }}>
                        <Text variant="body2" color={isSelected ? colors.primary : colors.textPrimary} style={{ fontWeight: '600' }}>
                          {option.descricao ?? option.tipo}
                        </Text>
                        <Text variant="caption" color={colors.textSecondary}>
                          Chega entre {option.prazo_min} e {option.prazo_max} dias úteis
                        </Text>
                      </View>
                      <Text
                        variant="subtitle2"
                        color={option.frete_gratis ? colors.success : colors.textPrimary}
                      >
                        {option.frete_gratis ? 'Grátis' : formatCurrency(option.valor)}
                      </Text>
                    </TouchableOpacity>
                  );
                })
              )}
            </View>
          ))
        ) : null}

        {/* Freight total */}
        {freightQueries.data && (
          <>
            <Divider style={{ marginVertical: spacing.xl }} />
            <View style={styles.totalRow}>
              <Text variant="subtitle1" color={colors.textPrimary}>Total do frete</Text>
              <Text variant="subtitle1" color={totalFrete === 0 ? colors.success : colors.textPrimary}>
                {totalFrete === 0 ? 'Grátis' : formatCurrency(totalFrete)}
              </Text>
            </View>
          </>
        )}
      </ScrollView>

      <View style={[styles.bottomBar, { backgroundColor: colors.surface, borderTopColor: colors.divider, paddingBottom: insets.bottom + spacing.sm }]}>
        <Button
          title="Continuar para pagamento"
          onPress={handleContinue}
          fullWidth
          size="lg"
          disabled={Object.keys(selectedFreight).length < lojaIds.length}
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  addressSummary: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  freightOption: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  totalRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
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
});
