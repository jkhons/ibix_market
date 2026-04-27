import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  View,
  StyleSheet,
  TouchableOpacity,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  TextInput,
  ActivityIndicator,
} from 'react-native';
import { useLocalSearchParams, useRouter, Stack } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { Text, Skeleton, EmptyState, Icon, IconButton } from '@/components/ui';
import { useTheme } from '@/hooks/useTheme';
import chatService, { type MensagemResponse } from '@/services/chatService';
import { extractApiError } from '@/services/api';
import { QUERY_KEYS } from '@/constants/config';
import { useAuthStore } from '@/store/authStore';

function formatTime(value: string): string {
  try {
    return new Date(value).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
}

export default function ChatDetailScreen() {
  const { id, nome } = useLocalSearchParams<{ id: string; nome?: string }>();
  const conversaId = Number(id);
  const { colors, spacing, borderRadius: br } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const qc = useQueryClient();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const consumerId = useAuthStore((s) => s.consumer?.id);

  const [draft, setDraft] = useState('');
  const inputRef = useRef<TextInput>(null);

  const messagesQuery = useQuery({
    queryKey: [QUERY_KEYS.MESSAGES, conversaId],
    queryFn: () => chatService.listMessages(conversaId, { limit: 50 }),
    enabled: isAuthenticated && Number.isFinite(conversaId) && conversaId > 0,
    refetchInterval: 8000,
  });

  const sendMutation = useMutation({
    mutationFn: (texto: string) => chatService.sendMessage(conversaId, { texto }),
    onSuccess: (msg) => {
      qc.setQueryData<MensagemResponse[]>([QUERY_KEYS.MESSAGES, conversaId], (prev) => {
        if (!prev) return [msg];
        if (prev.some((m) => m.id === msg.id)) return prev;
        return [...prev, msg];
      });
      qc.invalidateQueries({ queryKey: [QUERY_KEYS.CONVERSATIONS] });
      setDraft('');
    },
  });

  useEffect(() => {
    if (!conversaId || !isAuthenticated) return;
    chatService
      .markRead(conversaId)
      .then(() => qc.invalidateQueries({ queryKey: [QUERY_KEYS.CONVERSATIONS] }))
      .catch(() => {});
  }, [conversaId, isAuthenticated, qc]);

  const orderedMessages = useMemo(() => {
    return [...(messagesQuery.data ?? [])].sort(
      (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
    );
  }, [messagesQuery.data]);

  const handleSend = () => {
    const trimmed = draft.trim();
    if (!trimmed || sendMutation.isPending) return;
    sendMutation.mutate(trimmed);
  };

  const renderItem = ({ item }: { item: MensagemResponse }) => {
    const isMine = item.remetente_tipo === 'consumidor';
    return (
      <View
        style={[
          styles.bubbleWrapper,
          { justifyContent: isMine ? 'flex-end' : 'flex-start' },
        ]}
      >
        <View
          style={[
            styles.bubble,
            {
              backgroundColor: isMine ? colors.primary : colors.surfaceVariant,
              borderRadius: br.lg,
              borderBottomRightRadius: isMine ? 4 : br.lg,
              borderBottomLeftRadius: isMine ? br.lg : 4,
            },
          ]}
        >
          {item.texto && (
            <Text
              variant="body2"
              color={isMine ? colors.textInverse : colors.textPrimary}
            >
              {item.texto}
            </Text>
          )}
          <Text
            variant="caption"
            color={isMine ? colors.textInverse : colors.textSecondary}
            style={{ marginTop: 4, opacity: 0.85 }}
          >
            {formatTime(item.created_at)}
          </Text>
        </View>
      </View>
    );
  };

  if (!isAuthenticated) {
    return (
      <View style={[styles.container, { backgroundColor: colors.background }]}>
        <EmptyState
          title="Entre para conversar"
          actionTitle="Entrar"
          onAction={() => router.replace('/(auth)')}
        />
      </View>
    );
  }

  return (
    <KeyboardAvoidingView
      style={[styles.container, { backgroundColor: colors.background }]}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={Platform.OS === 'ios' ? 0 : 0}
    >
      <Stack.Screen options={{ headerShown: false }} />

      <View style={[styles.header, { paddingTop: insets.top + spacing.md, borderBottomColor: colors.border }]}>
        <TouchableOpacity onPress={() => router.back()} accessibilityLabel="Voltar">
          <Icon name="arrowLeft" size={24} color={colors.textPrimary} />
        </TouchableOpacity>
        <Text variant="subtitle1" color={colors.textPrimary} style={{ marginLeft: spacing.sm, flex: 1 }} numberOfLines={1}>
          {nome ?? 'Conversa'}
        </Text>
      </View>

      {messagesQuery.isLoading ? (
        <View style={{ padding: spacing.lg }}>
          <Skeleton width="60%" height={40} radius={12} />
          <Skeleton width="50%" height={40} radius={12} style={{ marginTop: 8, alignSelf: 'flex-end' }} />
          <Skeleton width="70%" height={40} radius={12} style={{ marginTop: 8 }} />
        </View>
      ) : messagesQuery.error ? (
        <EmptyState
          title="Não foi possível carregar"
          description={extractApiError(messagesQuery.error)}
          actionTitle="Tentar novamente"
          onAction={() => messagesQuery.refetch()}
        />
      ) : (
        <FlatList
          data={orderedMessages}
          keyExtractor={(item) => String(item.id)}
          renderItem={renderItem}
          contentContainerStyle={{ padding: spacing.lg, paddingBottom: spacing.md }}
          ListEmptyComponent={
            <EmptyState
              title="Sem mensagens"
              description="Envie a primeira mensagem para iniciar"
              style={{ paddingVertical: spacing['3xl'] }}
            />
          }
        />
      )}

      <View
        style={[
          styles.inputBar,
          {
            backgroundColor: colors.surface,
            borderTopColor: colors.border,
            paddingBottom: insets.bottom + 8,
          },
        ]}
      >
        <TextInput
          ref={inputRef}
          value={draft}
          onChangeText={setDraft}
          placeholder="Escreva uma mensagem..."
          placeholderTextColor={colors.textDisabled}
          style={[
            styles.textInput,
            {
              color: colors.textPrimary,
              backgroundColor: colors.surfaceVariant,
              borderRadius: br.full,
            },
          ]}
          multiline
          maxLength={2000}
        />
        <View style={{ marginLeft: 8 }}>
          {sendMutation.isPending ? (
            <ActivityIndicator color={colors.primary} />
          ) : (
            <IconButton
              icon={<Icon name="send" size={20} color={colors.textInverse} />}
              backgroundColor={colors.primary}
              onPress={handleSend}
              accessibilityLabel="Enviar mensagem"
              disabled={!draft.trim()}
            />
          )}
        </View>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingBottom: 12,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  bubbleWrapper: {
    flexDirection: 'row',
    marginVertical: 3,
  },
  bubble: {
    maxWidth: '78%',
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  inputBar: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    borderTopWidth: StyleSheet.hairlineWidth,
    paddingHorizontal: 12,
    paddingTop: 8,
  },
  textInput: {
    flex: 1,
    minHeight: 40,
    maxHeight: 120,
    paddingHorizontal: 14,
    paddingVertical: 10,
  },
});
