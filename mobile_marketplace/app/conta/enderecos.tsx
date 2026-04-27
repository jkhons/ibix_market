import React from 'react';
import { View, StyleSheet, FlatList, TouchableOpacity, Alert } from 'react-native';
import { Stack, useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { Text, EmptyState, Skeleton, Card, Icon, Button, Divider } from '@/components/ui';
import { useTheme } from '@/hooks/useTheme';
import { useAuthStore } from '@/store/authStore';
import addressService, { type Address } from '@/services/addressService';
import { extractApiError } from '@/services/api';
import { QUERY_KEYS } from '@/constants/config';

export default function EnderecosScreen() {
  const { colors, spacing } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const qc = useQueryClient();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  const addressesQuery = useQuery<Address[]>({
    queryKey: [QUERY_KEYS.ADDRESSES],
    queryFn: () => addressService.list(),
    enabled: isAuthenticated,
  });

  const setDefaultMutation = useMutation({
    mutationFn: (id: number) => addressService.setDefault(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: [QUERY_KEYS.ADDRESSES] }),
    onError: (err) => Alert.alert('Erro', extractApiError(err)),
  });

  const removeMutation = useMutation({
    mutationFn: (id: number) => addressService.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: [QUERY_KEYS.ADDRESSES] }),
    onError: (err) => Alert.alert('Erro', extractApiError(err)),
  });

  const handleRemove = (addr: Address) => {
    Alert.alert(
      'Remover endereço',
      `Deseja remover ${addr.apelido ?? addr.logradouro ?? 'este endereço'}?`,
      [
        { text: 'Cancelar', style: 'cancel' },
        { text: 'Remover', style: 'destructive', onPress: () => removeMutation.mutate(addr.id) },
      ],
    );
  };

  const renderItem = ({ item }: { item: Address }) => (
    <Card style={[styles.card, { padding: spacing.md, marginBottom: spacing.sm }]}>
      <View style={styles.headerRow}>
        <Text variant="subtitle2" color={colors.textPrimary}>
          {item.apelido ?? item.logradouro ?? 'Endereço'}
        </Text>
        {item.principal && (
          <View style={[styles.tag, { backgroundColor: colors.primarySurface }]}>
            <Text variant="caption" color={colors.primary}>Principal</Text>
          </View>
        )}
      </View>
      <Text variant="body2" color={colors.textSecondary} style={{ marginTop: 4 }}>
        {item.logradouro}{item.numero ? `, ${item.numero}` : ''}
        {item.complemento ? ` — ${item.complemento}` : ''}
      </Text>
      <Text variant="body2" color={colors.textSecondary}>
        {item.bairro ? `${item.bairro} — ` : ''}{item.cidade}/{item.uf}
      </Text>
      {item.cep && (
        <Text variant="caption" color={colors.textSecondary}>
          CEP {item.cep}
        </Text>
      )}
      <Divider style={{ marginVertical: spacing.sm }} />
      <View style={styles.actionsRow}>
        {!item.principal && (
          <Button
            title="Definir como principal"
            onPress={() => setDefaultMutation.mutate(item.id)}
            variant="outline"
            size="sm"
            loading={setDefaultMutation.isPending && setDefaultMutation.variables === item.id}
          />
        )}
        <Button
          title="Remover"
          onPress={() => handleRemove(item)}
          variant="ghost"
          size="sm"
          style={{ marginLeft: 'auto' }}
        />
      </View>
    </Card>
  );

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <Stack.Screen options={{ headerShown: false }} />

      <View style={[styles.header, { paddingTop: insets.top + spacing.md }]}>
        <TouchableOpacity onPress={() => router.back()} accessibilityLabel="Voltar">
          <Icon name="arrowLeft" size={24} color={colors.textPrimary} />
        </TouchableOpacity>
        <Text variant="subtitle1" color={colors.textPrimary} style={{ marginLeft: spacing.sm, flex: 1 }}>
          Meus endereços
        </Text>
      </View>

      {!isAuthenticated ? (
        <EmptyState
          title="Entre para gerenciar endereços"
          actionTitle="Entrar"
          onAction={() => router.push('/(auth)')}
        />
      ) : addressesQuery.isLoading ? (
        <View style={{ padding: spacing.lg }}>
          <Skeleton width="100%" height={120} radius={12} />
          <Skeleton width="100%" height={120} radius={12} style={{ marginTop: 8 }} />
        </View>
      ) : addressesQuery.error ? (
        <EmptyState
          title="Não foi possível carregar"
          description={extractApiError(addressesQuery.error)}
          actionTitle="Tentar novamente"
          onAction={() => addressesQuery.refetch()}
        />
      ) : (addressesQuery.data ?? []).length === 0 ? (
        <EmptyState
          title="Nenhum endereço"
          description="Adicione um endereço durante o checkout"
        />
      ) : (
        <FlatList
          data={addressesQuery.data ?? []}
          keyExtractor={(item) => String(item.id)}
          renderItem={renderItem}
          contentContainerStyle={{
            padding: spacing.lg,
            paddingBottom: insets.bottom + spacing['3xl'],
          }}
        />
      )}
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
  card: {},
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  tag: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 999,
  },
  actionsRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
});
