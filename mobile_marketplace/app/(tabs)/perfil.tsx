import React from 'react';
import { View, ScrollView, StyleSheet, TouchableOpacity, Alert, Linking } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { useQuery } from '@tanstack/react-query';

import { Text, Avatar, Card, Divider, Button, Skeleton } from '@/components/ui';
import { useTheme } from '@/hooks/useTheme';
import { useAuthStore } from '@/store/authStore';
import consumerService from '@/services/consumerService';
import { QUERY_KEYS } from '@/constants/config';

interface MenuItemProps {
  title: string;
  subtitle?: string;
  onPress: () => void;
  disabled?: boolean;
}

function MenuItem({ title, subtitle, onPress, disabled }: MenuItemProps) {
  const { colors, spacing } = useTheme();
  return (
    <TouchableOpacity
      onPress={onPress}
      disabled={disabled}
      style={[
        styles.menuItem,
        { paddingVertical: spacing.md, paddingHorizontal: spacing.lg, opacity: disabled ? 0.5 : 1 },
      ]}
      accessibilityRole="button"
      accessibilityLabel={title}
    >
      <View style={{ flex: 1 }}>
        <Text variant="body1" color={colors.textPrimary}>{title}</Text>
        {subtitle && (
          <Text variant="caption" color={colors.textSecondary} style={{ marginTop: 2 }}>
            {subtitle}
          </Text>
        )}
      </View>
      <Text variant="body2" color={colors.textDisabled}>›</Text>
    </TouchableOpacity>
  );
}

export default function PerfilScreen() {
  const { colors, spacing } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { isAuthenticated, consumer, logout } = useAuthStore();

  const profileQuery = useQuery({
    queryKey: [QUERY_KEYS.CONSUMER_PROFILE],
    queryFn: () => consumerService.getProfile(),
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000,
  });

  const handleLogout = () => {
    Alert.alert('Sair', 'Deseja realmente sair da sua conta?', [
      { text: 'Cancelar', style: 'cancel' },
      {
        text: 'Sair',
        style: 'destructive',
        onPress: async () => {
          await logout();
          router.replace('/(tabs)');
        },
      },
    ]);
  };

  const displayName =
    profileQuery.data?.nome?.trim() ||
    consumer?.nome ||
    consumer?.email ||
    'Conta';
  const initial = (displayName?.[0] ?? '?').toUpperCase();

  return (
    <ScrollView
      style={[styles.container, { backgroundColor: colors.background }]}
      contentContainerStyle={{ paddingTop: insets.top + spacing.md, paddingBottom: spacing['3xl'] }}
    >
      <View style={{ paddingHorizontal: spacing.lg }}>
        <Text variant="h3" color={colors.textPrimary}>Perfil</Text>
      </View>

      <Card style={{ marginHorizontal: spacing.lg, marginTop: spacing.xl }}>
        {!isAuthenticated ? (
          <TouchableOpacity
            style={styles.profileRow}
            onPress={() => router.push('/(auth)')}
            accessibilityLabel="Fazer login"
          >
            <Avatar name="?" size="lg" />
            <View style={{ marginLeft: spacing.lg, flex: 1 }}>
              <Text variant="subtitle1" color={colors.textPrimary}>Entre ou cadastre-se</Text>
              <Text variant="caption" color={colors.textSecondary} style={{ marginTop: 2 }}>
                Acesse seus pedidos e favoritos
              </Text>
            </View>
          </TouchableOpacity>
        ) : profileQuery.isLoading ? (
          <View style={styles.profileRow}>
            <Skeleton width={56} height={56} radius={28} />
            <View style={{ marginLeft: spacing.lg, flex: 1 }}>
              <Skeleton width={140} height={16} radius={4} />
              <Skeleton width={180} height={12} radius={4} style={{ marginTop: 6 }} />
            </View>
          </View>
        ) : (
          <View style={styles.profileRow}>
            <Avatar name={initial} size="lg" />
            <View style={{ marginLeft: spacing.lg, flex: 1 }}>
              <Text variant="subtitle1" color={colors.textPrimary} numberOfLines={1}>
                {displayName}
              </Text>
              {profileQuery.data?.email && (
                <Text variant="caption" color={colors.textSecondary} style={{ marginTop: 2 }} numberOfLines={1}>
                  {profileQuery.data.email}
                </Text>
              )}
              {profileQuery.data?.origem_social_provider && (
                <Text variant="caption" color={colors.textSecondary} style={{ marginTop: 2 }}>
                  Conectado via {profileQuery.data.origem_social_provider}
                </Text>
              )}
            </View>
          </View>
        )}
      </Card>

      <Card style={{ marginHorizontal: spacing.lg, marginTop: spacing.xl }} padded={false}>
        <MenuItem
          title="Meus Pedidos"
          subtitle={isAuthenticated ? 'Acompanhe suas compras' : 'Entre para acompanhar'}
          onPress={() => (isAuthenticated ? router.push('/(tabs)/pedidos') : router.push('/(auth)'))}
        />
        <Divider />
        <MenuItem
          title="Conversas"
          subtitle={isAuthenticated ? 'Mensagens com lojas' : 'Entre para conversar'}
          onPress={() => (isAuthenticated ? router.push('/chat') : router.push('/(auth)'))}
        />
        <Divider />
        <MenuItem
          title="Favoritos"
          onPress={() => router.push('/favoritos')}
        />
        <Divider />
        <MenuItem
          title="Endereços"
          subtitle={isAuthenticated ? 'Gerencie seus endereços' : 'Entre para gerenciar'}
          onPress={() => (isAuthenticated ? router.push('/conta/enderecos') : router.push('/(auth)'))}
        />
        <Divider />
        <MenuItem
          title="Notificações"
          onPress={() => router.push('/notificacoes')}
        />
      </Card>

      <Card style={{ marginHorizontal: spacing.lg, marginTop: spacing.lg }} padded={false}>
        <MenuItem
          title="Privacidade e Dados (LGPD)"
          subtitle="Política, consentimentos e direitos"
          onPress={() => Linking.openURL('https://ibix.com.br/privacidade').catch(() => {})}
        />
        <Divider />
        <MenuItem
          title="Ajuda e Suporte"
          subtitle="Fale com a gente"
          onPress={() => Linking.openURL('https://ibix.com.br/suporte').catch(() => {})}
        />
        <Divider />
        <MenuItem title="Sobre o App" subtitle="Versão 1.0.0" onPress={() => {}} />
      </Card>

      {isAuthenticated && (
        <View style={{ paddingHorizontal: spacing.lg, marginTop: spacing.xl }}>
          <Button
            title="Sair da conta"
            onPress={handleLogout}
            variant="outline"
            size="md"
            fullWidth
          />
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  profileRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
});
