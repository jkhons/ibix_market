import React from 'react';
import { View, StyleSheet, TouchableOpacity, FlatList, RefreshControl } from 'react-native';
import { useRouter, Stack } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useQuery } from '@tanstack/react-query';

import { Text, Card, Skeleton, EmptyState, Icon, Badge } from '@/components/ui';
import { useTheme } from '@/hooks/useTheme';
import { useAuthStore } from '@/store/authStore';
import chatService, { type ConversaResumo } from '@/services/chatService';
import { extractApiError } from '@/services/api';
import { QUERY_KEYS } from '@/constants/config';

function formatRelative(value?: string): string {
  if (!value) return '';
  try {
    const date = new Date(value);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const minutes = Math.floor(diffMs / (1000 * 60));
    if (minutes < 1) return 'agora';
    if (minutes < 60) return `${minutes}min`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h`;
    const days = Math.floor(hours / 24);
    if (days < 7) return `${days}d`;
    return date.toLocaleDateString('pt-BR');
  } catch {
    return '';
  }
}

export default function ChatListScreen() {
  const { colors, spacing } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  const conversationsQuery = useQuery({
    queryKey: [QUERY_KEYS.CONVERSATIONS],
    queryFn: () => chatService.listConversations({ offset: 0, limit: 50 }),
    enabled: isAuthenticated,
  });

  const renderItem = ({ item }: { item: ConversaResumo }) => (
    <TouchableOpacity
      onPress={() =>
        router.push({
          pathname: '/chat/[id]',
          params: { id: String(item.id), nome: item.loja_nome ?? `Loja ${item.loja_id}` },
        })
      }
      activeOpacity={0.85}
    >
      <Card style={[styles.row, { padding: spacing.md, marginBottom: spacing.sm }]}>
        <View style={{ flex: 1 }}>
          <View style={styles.headerRow}>
            <Text variant="subtitle2" color={colors.textPrimary} numberOfLines={1} style={{ flex: 1 }}>
              {item.loja_nome ?? `Loja #${item.loja_id}`}
            </Text>
            <Text variant="caption" color={colors.textSecondary} style={{ marginLeft: 8 }}>
              {formatRelative(item.ultima_mensagem_em)}
            </Text>
          </View>
          <View style={[styles.bodyRow, { marginTop: 4 }]}>
            <Text
              variant="body2"
              color={colors.textSecondary}
              numberOfLines={1}
              style={{ flex: 1 }}
            >
              {item.ultima_mensagem_texto ?? 'Sem mensagens ainda'}
            </Text>
            {item.nao_lidas > 0 && (
              <Badge label={String(item.nao_lidas)} variant="primary" style={{ marginLeft: 8 }} />
            )}
          </View>
        </View>
      </Card>
    </TouchableOpacity>
  );

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <Stack.Screen options={{ headerShown: false }} />

      <View style={[styles.header, { paddingTop: insets.top + spacing.md }]}>
        <TouchableOpacity onPress={() => router.back()} accessibilityLabel="Voltar">
          <Icon name="arrowLeft" size={24} color={colors.textPrimary} />
        </TouchableOpacity>
        <Text variant="subtitle1" color={colors.textPrimary} style={{ marginLeft: spacing.sm }}>
          Conversas
        </Text>
      </View>

      {!isAuthenticated ? (
        <EmptyState
          title="Entre para conversar"
          description="Acesse sua conta para falar com as lojas"
          actionTitle="Entrar"
          onAction={() => router.push('/(auth)')}
        />
      ) : conversationsQuery.isLoading ? (
        <View style={{ padding: spacing.lg }}>
          <Skeleton width="100%" height={70} radius={12} />
          <Skeleton width="100%" height={70} radius={12} style={{ marginTop: 8 }} />
          <Skeleton width="100%" height={70} radius={12} style={{ marginTop: 8 }} />
        </View>
      ) : conversationsQuery.error ? (
        <EmptyState
          title="Não foi possível carregar"
          description={extractApiError(conversationsQuery.error)}
          actionTitle="Tentar novamente"
          onAction={() => conversationsQuery.refetch()}
        />
      ) : (conversationsQuery.data?.items ?? []).length === 0 ? (
        <EmptyState
          title="Nenhuma conversa"
          description="Inicie um chat a partir da página de uma loja ou produto"
        />
      ) : (
        <FlatList
          data={conversationsQuery.data?.items ?? []}
          keyExtractor={(item) => String(item.id)}
          renderItem={renderItem}
          contentContainerStyle={{
            padding: spacing.lg,
            paddingBottom: insets.bottom + spacing['3xl'],
          }}
          refreshControl={
            <RefreshControl
              refreshing={conversationsQuery.isFetching && !conversationsQuery.isLoading}
              onRefresh={() => conversationsQuery.refetch()}
            />
          }
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
  row: { flexDirection: 'row', alignItems: 'center' },
  headerRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  bodyRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
});
