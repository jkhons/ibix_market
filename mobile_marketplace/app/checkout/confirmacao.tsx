import React, { useEffect, useRef, useState } from 'react';
import { View, StyleSheet, ScrollView, Linking } from 'react-native';
import { useRouter, useLocalSearchParams, Stack } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import * as Haptics from 'expo-haptics';

import { Text, Button, Icon } from '@/components/ui';
import { PixPayment } from '@/components/checkout';
import { useTheme } from '@/hooks/useTheme';
import { useAuthStore } from '@/store/authStore';
import checkoutService from '@/services/checkoutService';
import { formatCurrency } from '@/utils/format';

type ConfirmationState =
  | 'loading'
  | 'approved'
  | 'pending_pix'
  | 'pending_redirect'
  | 'pending_other'
  | 'failed';

const APPROVED_STATUSES = new Set(['pago', 'approved', 'confirmado']);
const FAILED_STATUSES = new Set(['recusado', 'rejected', 'cancelado', 'cancelled', 'falhou', 'failed']);

export default function CheckoutConfirmacaoScreen() {
  const params = useLocalSearchParams<{
    mode?: string;
    numero_pedido?: string;
    comprador_email?: string;
    total?: string;
    status_pagamento?: string;
    status_pedido?: string;
    redirect_url?: string;
    checkout_type?: string;
    pix_copia_cola?: string;
    pix_qr_code?: string;
    pix_qr_code_base64?: string;
    pix_expiracao_minutos?: string;
  }>();

  const { colors, spacing } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { isAuthenticated } = useAuthStore();

  const numeroPedido = params.numero_pedido ?? '';
  const compradorEmail = params.comprador_email ?? '';
  const total = Number(params.total ?? 0);
  const statusPagamentoInicial = params.status_pagamento ?? '';
  const checkoutType = params.checkout_type ?? '';
  const redirectUrl = params.redirect_url;
  const pixCopiaCola = params.pix_copia_cola;
  const pixQrCode = params.pix_qr_code;
  const pixExpiracaoMin = Number(params.pix_expiracao_minutos ?? 30);

  const pollRef = useRef<ReturnType<typeof setInterval>>();
  const [state, setState] = useState<ConfirmationState>('loading');

  useEffect(() => {
    if (!numeroPedido) {
      setState('failed');
      return;
    }

    if (APPROVED_STATUSES.has(statusPagamentoInicial)) {
      setState('approved');
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      return;
    }

    if (checkoutType === 'pix' && pixCopiaCola) {
      setState('pending_pix');
      startPolling('pix');
    } else if (redirectUrl) {
      setState('pending_redirect');
      Linking.openURL(redirectUrl).catch(() => undefined);
      startPolling('redirect');
    } else if (checkoutType === 'boleto') {
      setState('pending_other');
      startPolling('boleto');
    } else {
      setState('pending_other');
      startPolling('other');
    }

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const startPolling = (kind: 'pix' | 'redirect' | 'boleto' | 'other') => {
    const interval = kind === 'pix' ? 5000 : 10000;
    pollRef.current = setInterval(async () => {
      try {
        const status = isAuthenticated
          ? await checkoutService.getMyOrderStatus(numeroPedido)
          : compradorEmail
            ? await checkoutService.getPublicOrderStatus(numeroPedido, compradorEmail)
            : null;
        if (!status) return;
        if (APPROVED_STATUSES.has(status.status_pagamento)) {
          if (pollRef.current) clearInterval(pollRef.current);
          setState('approved');
          Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
        } else if (FAILED_STATUSES.has(status.status_pagamento) || FAILED_STATUSES.has(status.status_pedido)) {
          if (pollRef.current) clearInterval(pollRef.current);
          setState('failed');
        }
      } catch {
        // mantém polling
      }
    }, interval);
  };

  const renderApproved = () => (
    <View style={styles.centeredContent}>
      <View style={[styles.successCircle, { backgroundColor: colors.successSurface }]}>
        <Icon name="check" size={48} color={colors.success} />
      </View>
      <Text variant="h3" color={colors.textPrimary} align="center" style={{ marginTop: spacing.xl }}>
        Pedido realizado!
      </Text>
      {numeroPedido !== '' && (
        <Text variant="body2" color={colors.textSecondary} align="center" style={{ marginTop: spacing.sm }}>
          Pedido #{numeroPedido}
        </Text>
      )}
      <Text variant="body2" color={colors.textSecondary} align="center" style={{ marginTop: spacing.sm }}>
        Pagamento confirmado. Você receberá atualizações por notificação.
      </Text>
      <Text variant="price" color={colors.primary} align="center" style={{ marginTop: spacing.lg }}>
        {formatCurrency(total)}
      </Text>

      <Button
        title="Ver meus pedidos"
        onPress={() => router.replace('/(tabs)/pedidos')}
        fullWidth
        size="lg"
        style={{ marginTop: spacing['2xl'] }}
      />
      <Button
        title="Continuar comprando"
        onPress={() => router.replace('/(tabs)')}
        variant="outline"
        fullWidth
        size="lg"
        style={{ marginTop: spacing.sm }}
      />
    </View>
  );

  const renderPendingPix = () => (
    <View style={styles.centeredContent}>
      {pixCopiaCola && (
        <PixPayment
          copiaCola={pixCopiaCola}
          expiracaoMinutos={pixExpiracaoMin}
          onExpired={() => setState('failed')}
        />
      )}

      <Text variant="body2" color={colors.textSecondary} align="center" style={{ marginTop: spacing.xl }}>
        Aguardando confirmação do pagamento...
      </Text>

      <Button
        title="Ver meus pedidos"
        onPress={() => router.replace('/(tabs)/pedidos')}
        variant="outline"
        fullWidth
        size="lg"
        style={{ marginTop: spacing.xl }}
      />
    </View>
  );

  const renderPendingRedirect = () => (
    <View style={styles.centeredContent}>
      <View style={[styles.successCircle, { backgroundColor: colors.primarySurface }]}>
        <Icon name="refresh" size={48} color={colors.primary} />
      </View>
      <Text variant="h3" color={colors.textPrimary} align="center" style={{ marginTop: spacing.xl }}>
        Aguardando pagamento
      </Text>
      <Text variant="body2" color={colors.textSecondary} align="center" style={{ marginTop: spacing.sm }}>
        Conclua o pagamento na página do gateway que abrimos no navegador.
      </Text>

      {redirectUrl && (
        <Button
          title="Reabrir pagamento"
          onPress={() => Linking.openURL(redirectUrl).catch(() => undefined)}
          variant="outline"
          fullWidth
          size="lg"
          style={{ marginTop: spacing.xl }}
        />
      )}

      <Button
        title="Ver meus pedidos"
        onPress={() => router.replace('/(tabs)/pedidos')}
        variant="outline"
        fullWidth
        size="lg"
        style={{ marginTop: spacing.sm }}
      />
    </View>
  );

  const renderPendingOther = () => (
    <View style={styles.centeredContent}>
      <View style={[styles.successCircle, { backgroundColor: colors.warningSurface }]}>
        <Icon name="clipboard" size={48} color={colors.warning} />
      </View>
      <Text variant="h3" color={colors.textPrimary} align="center" style={{ marginTop: spacing.xl }}>
        Pedido criado
      </Text>
      {numeroPedido !== '' && (
        <Text variant="body2" color={colors.textSecondary} align="center" style={{ marginTop: spacing.sm }}>
          Pedido #{numeroPedido}
        </Text>
      )}
      <Text variant="body2" color={colors.textSecondary} align="center" style={{ marginTop: spacing.sm }}>
        Estamos aguardando a confirmação do pagamento. Vamos avisar você assim que for processado.
      </Text>
      <Text variant="price" color={colors.primary} align="center" style={{ marginTop: spacing.lg }}>
        {formatCurrency(total)}
      </Text>

      <Button
        title="Ver meus pedidos"
        onPress={() => router.replace('/(tabs)/pedidos')}
        fullWidth
        size="lg"
        style={{ marginTop: spacing.xl }}
      />
    </View>
  );

  const renderFailed = () => (
    <View style={styles.centeredContent}>
      <View style={[styles.successCircle, { backgroundColor: colors.errorSurface }]}>
        <Icon name="x" size={48} color={colors.error} />
      </View>
      <Text variant="h3" color={colors.textPrimary} align="center" style={{ marginTop: spacing.xl }}>
        Pagamento não aprovado
      </Text>
      <Text variant="body2" color={colors.textSecondary} align="center" style={{ marginTop: spacing.sm }}>
        Seu pagamento não foi processado. Tente novamente com outro método.
      </Text>

      <Button
        title="Tentar novamente"
        onPress={() => router.back()}
        fullWidth
        size="lg"
        style={{ marginTop: spacing['2xl'] }}
      />
      <Button
        title="Voltar à loja"
        onPress={() => router.replace('/(tabs)')}
        variant="outline"
        fullWidth
        size="lg"
        style={{ marginTop: spacing.sm }}
      />
    </View>
  );

  const renderLoading = () => (
    <View style={styles.centeredContent}>
      <Text variant="body1" color={colors.textSecondary} align="center">
        Processando...
      </Text>
    </View>
  );

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <Stack.Screen options={{ headerShown: false, gestureEnabled: false }} />

      <ScrollView
        contentContainerStyle={{
          flexGrow: 1,
          justifyContent: 'center',
          paddingHorizontal: spacing.lg,
          paddingTop: insets.top + spacing.xl,
          paddingBottom: insets.bottom + spacing['3xl'],
        }}
        showsVerticalScrollIndicator={false}
      >
        {state === 'approved' && renderApproved()}
        {state === 'pending_pix' && renderPendingPix()}
        {state === 'pending_redirect' && renderPendingRedirect()}
        {state === 'pending_other' && renderPendingOther()}
        {state === 'failed' && renderFailed()}
        {state === 'loading' && renderLoading()}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  centeredContent: {
    alignItems: 'center',
  },
  successCircle: {
    width: 96,
    height: 96,
    borderRadius: 48,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
