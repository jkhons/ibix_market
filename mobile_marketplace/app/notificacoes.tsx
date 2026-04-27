import React, { useEffect } from 'react';
import { View, StyleSheet, TouchableOpacity } from 'react-native';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { FlashList } from '@shopify/flash-list';
import { Text, EmptyState, Badge, Skeleton } from '@/components/ui';
import { useTheme } from '@/hooks/useTheme';
import { useNotificationStore } from '@/store/notificationStore';
import { formatRelativeTime } from '@/utils/format';

export default function NotificacoesScreen() {
  const { colors, spacing } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();

  const { notifications, unreadCount, isLoading, fetchNotifications, markAsRead, markAllAsRead } =
    useNotificationStore();

  useEffect(() => {
    fetchNotifications(1);
  }, []);

  const handleNotificationPress = (id: number, lida: boolean) => {
    if (!lida) markAsRead([id]);
  };

  return (
    <View style={[styles.container, { backgroundColor: colors.background, paddingTop: insets.top + spacing.md }]}>
      <View style={[styles.header, { paddingHorizontal: spacing.lg }]}>
        <TouchableOpacity onPress={() => router.back()} accessibilityLabel="Voltar">
          <Text variant="body1" color={colors.textSecondary}>← Voltar</Text>
        </TouchableOpacity>
        <View style={styles.headerRow}>
          <Text variant="h3" color={colors.textPrimary}>Notificações</Text>
          {unreadCount > 0 && (
            <TouchableOpacity onPress={markAllAsRead} accessibilityLabel="Marcar todas como lidas">
              <Text variant="body2" color={colors.textLink}>Marcar todas</Text>
            </TouchableOpacity>
          )}
        </View>
      </View>

      {isLoading && !notifications.length ? (
        <View style={{ padding: spacing.lg }}>
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} width="100%" height={60} style={{ marginBottom: 12 }} />
          ))}
        </View>
      ) : !notifications.length ? (
        <EmptyState
          title="Nenhuma notificação"
          description="Você será notificado sobre seus pedidos e promoções"
        />
      ) : (
        <FlashList
          data={notifications}
          estimatedItemSize={70}
          contentContainerStyle={{ paddingHorizontal: spacing.lg }}
          renderItem={({ item }) => (
            <TouchableOpacity
              onPress={() => handleNotificationPress(item.id, item.lida)}
              style={[
                styles.notificationRow,
                {
                  backgroundColor: item.lida ? colors.surface : colors.primarySurface,
                  borderBottomColor: colors.divider,
                },
              ]}
              accessibilityLabel={`${item.titulo}. ${item.corpo ?? ''}`}
            >
              <View style={{ flex: 1 }}>
                <View style={styles.titleRow}>
                  <Text variant="subtitle2" color={colors.textPrimary} style={{ flex: 1 }} numberOfLines={1}>
                    {item.titulo}
                  </Text>
                  {!item.lida && <Badge dot variant="primary" style={{ marginLeft: 8 }} />}
                </View>
                {item.corpo && (
                  <Text variant="body2" color={colors.textSecondary} numberOfLines={2} style={{ marginTop: 2 }}>
                    {item.corpo}
                  </Text>
                )}
                <Text variant="caption" color={colors.textDisabled} style={{ marginTop: 4 }}>
                  {formatRelativeTime(item.created_at)}
                </Text>
              </View>
            </TouchableOpacity>
          )}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: {},
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 12,
  },
  notificationRow: {
    padding: 14,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderRadius: 8,
    marginBottom: 4,
  },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
});
