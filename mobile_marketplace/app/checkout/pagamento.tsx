import React, { useMemo, useState } from 'react';
import { View, StyleSheet, ScrollView, Alert, Switch } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useQuery, useMutation } from '@tanstack/react-query';

import { Text, Button, Divider, Card, Icon } from '@/components/ui';
import { PaymentMethodPicker, InstallmentPicker, type PaymentMethod } from '@/components/checkout';
import { useTheme } from '@/hooks/useTheme';
import { useCartStore } from '@/store/cartStore';
import { useAuthStore } from '@/store/authStore';
import catalogService from '@/services/catalogService';
import addressService from '@/services/addressService';
import consumerService from '@/services/consumerService';
import checkoutService, {
  type CheckoutSingleLojaPayload,
  type CheckoutSingleLojaResponse,
  type CheckoutUnificadoPayload,
  type CheckoutUnificadoResponse,
} from '@/services/checkoutService';
import { extractApiError } from '@/services/api';
import { QUERY_KEYS } from '@/constants/config';
import { formatCurrency } from '@/utils/format';

type CheckoutMode = 'single' | 'unified';

interface ConfirmationParams {
  mode: CheckoutMode;
  numero_pedido: string;
  comprador_email: string;
  total: number;
  status_pagamento: string;
  status_pedido?: string;
  redirect_url?: string;
  checkout_type?: string;
  pix_copia_cola?: string;
  pix_qr_code?: string;
  pix_qr_code_base64?: string;
  pix_expiracao_minutos?: number;
}

function buildPaymentMethod(method: PaymentMethod): 'pix' | 'credit_card' | 'boleto' {
  if (method === 'cartao') return 'credit_card';
  return method;
}

function generateIdempotencyKey(): string {
  const rand = Math.random().toString(36).slice(2, 10);
  return `mob-${Date.now()}-${rand}`;
}

export default function CheckoutPagamentoScreen() {
  const params = useLocalSearchParams<{
    endereco_id: string;
    fretes: string;
    total_frete: string;
  }>();

  const { colors, spacing, shadow } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();

  const { items, totalPrice, clearCart, itemsByLoja } = useCartStore();
  const { isAuthenticated } = useAuthStore();
  const subtotal = totalPrice();
  const totalFrete = Number(params.total_frete ?? 0);
  const fretes: Array<{ loja_id: number; tipo_frete: string }> = params.fretes
    ? JSON.parse(params.fretes)
    : [];

  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod | null>(null);
  const [selectedInstallment, setSelectedInstallment] = useState<number | null>(null);
  const [aceitePolitica, setAceitePolitica] = useState(false);
  const [aceiteMarketing, setAceiteMarketing] = useState(false);

  const totalGeral = subtotal + totalFrete;

  const installmentsQuery = useQuery({
    queryKey: [QUERY_KEYS.INSTALLMENTS, totalGeral],
    queryFn: () => catalogService.getInstallments(totalGeral),
    enabled: totalGeral > 0,
    staleTime: 5 * 60 * 1000,
  });

  const profileQuery = useQuery({
    queryKey: [QUERY_KEYS.CONSUMER_PROFILE],
    queryFn: () => consumerService.getProfile(),
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000,
  });

  const addressQuery = useQuery({
    queryKey: [QUERY_KEYS.ADDRESSES, 'selected', params.endereco_id],
    queryFn: async () => {
      const all = await addressService.list();
      const found = all.find((a) => a.id === Number(params.endereco_id));
      if (!found) throw new Error('Endereço não encontrado');
      return found;
    },
    enabled: !!params.endereco_id,
  });

  const selectedInst = installmentsQuery.data?.find((i) => i.parcelas === selectedInstallment);
  const totalWithInstallment = selectedInst
    ? selectedInst.total ?? selectedInst.valor_parcela * selectedInst.parcelas
    : totalGeral;

  const lojasUnicas = useMemo(() => {
    const grouped = itemsByLoja();
    return Object.keys(grouped).map(Number);
  }, [items]);
  const isMultiLoja = lojasUnicas.length > 1;

  const taxaEntregaPorLoja = useMemo(() => {
    const map: Record<number, number> = {};
    fretes.forEach((f) => {
      map[f.loja_id] = 0;
    });
    return map;
  }, [params.fretes]);

  const checkoutMutation = useMutation({
    mutationFn: async (): Promise<{ confirm: ConfirmationParams }> => {
      if (!profileQuery.data) {
        throw new Error('Carregando dados do consumidor. Tente novamente em instantes.');
      }
      if (!addressQuery.data) {
        throw new Error('Endereço de entrega não encontrado.');
      }
      if (!paymentMethod) {
        throw new Error('Selecione um método de pagamento.');
      }
      if (!aceitePolitica) {
        throw new Error('Aceite a Política de Privacidade para continuar.');
      }

      const profile = profileQuery.data;
      const addr = addressQuery.data;
      const baseFields = {
        comprador_nome: profile.nome,
        comprador_email: profile.email,
        comprador_telefone: profile.telefone,
        comprador_documento: profile.documento,
        endereco_cep: addr.cep,
        endereco_logradouro: addr.logradouro,
        endereco_numero: addr.numero,
        endereco_complemento: addr.complemento,
        endereco_bairro: addr.bairro,
        endereco_cidade: addr.cidade,
        endereco_uf: addr.uf,
        tipo_entrega: 'entrega',
        aceite_marketing: aceiteMarketing,
        aceite_politica_privacidade: true,
        payment_method: buildPaymentMethod(paymentMethod),
        canal_origem: 'mobile',
        idempotency_key: generateIdempotencyKey(),
        taxa_entrega: totalFrete,
      };

      if (isMultiLoja) {
        const payload: CheckoutUnificadoPayload = {
          ...baseFields,
          itens: items.map((i) => ({
            anuncio_id: i.productId,
            quantidade: i.quantity,
            loja_id: i.lojaId,
          })),
        };
        const response: CheckoutUnificadoResponse = await checkoutService.submitUnificado(payload);
        const primeiro = response.pedidos[0];
        if (!primeiro) {
          throw new Error('Pedido não foi criado. Tente novamente.');
        }
        return {
          confirm: {
            mode: 'unified',
            numero_pedido: primeiro.numero_pedido,
            comprador_email: response.comprador_email ?? profile.email,
            total: response.pedidos.reduce((acc, p) => acc + Number(p.total ?? 0), 0),
            status_pagamento: 'pendente',
            redirect_url: response.redirect_url,
            checkout_type: response.checkout_type,
            pix_copia_cola: response.pix?.copia_cola,
            pix_qr_code: response.pix?.qr_code,
            pix_qr_code_base64: response.pix?.qr_code_base64,
            pix_expiracao_minutos: response.pix?.expiracao_minutos,
          },
        };
      }

      const lojaId = lojasUnicas[0];
      const payload: CheckoutSingleLojaPayload = {
        ...baseFields,
        loja_id: lojaId,
        itens: items.map((i) => ({
          anuncio_id: i.productId,
          quantidade: i.quantity,
        })),
      };
      const response: CheckoutSingleLojaResponse = await checkoutService.submitSingleLoja(payload);
      return {
        confirm: {
          mode: 'single',
          numero_pedido: response.numero_pedido,
          comprador_email: response.comprador_email ?? profile.email,
          total: Number(response.total ?? 0),
          status_pagamento: response.status_pagamento,
          status_pedido: response.status_pedido,
          redirect_url: response.redirect_url,
          checkout_type: response.checkout_type,
          pix_copia_cola: response.pix?.copia_cola,
          pix_qr_code: response.pix?.qr_code,
          pix_qr_code_base64: response.pix?.qr_code_base64,
          pix_expiracao_minutos: response.pix?.expiracao_minutos,
        },
      };
    },
    onSuccess: ({ confirm }) => {
      clearCart();
      const queryParams: Record<string, string> = {
        mode: confirm.mode,
        numero_pedido: confirm.numero_pedido,
        comprador_email: confirm.comprador_email,
        total: String(confirm.total),
        status_pagamento: confirm.status_pagamento,
      };
      if (confirm.status_pedido) queryParams.status_pedido = confirm.status_pedido;
      if (confirm.redirect_url) queryParams.redirect_url = confirm.redirect_url;
      if (confirm.checkout_type) queryParams.checkout_type = confirm.checkout_type;
      if (confirm.pix_copia_cola) queryParams.pix_copia_cola = confirm.pix_copia_cola;
      if (confirm.pix_qr_code) queryParams.pix_qr_code = confirm.pix_qr_code;
      if (confirm.pix_qr_code_base64) queryParams.pix_qr_code_base64 = confirm.pix_qr_code_base64;
      if (confirm.pix_expiracao_minutos) {
        queryParams.pix_expiracao_minutos = String(confirm.pix_expiracao_minutos);
      }
      router.replace({
        pathname: '/checkout/confirmacao',
        params: queryParams,
      } as any);
    },
    onError: (err) => {
      Alert.alert('Erro no checkout', extractApiError(err));
    },
  });

  const handleConfirm = () => {
    if (!isAuthenticated) {
      Alert.alert(
        'Login necessário',
        'É preciso entrar com sua conta para finalizar o pedido.',
        [{ text: 'Cancelar' }, { text: 'Entrar', onPress: () => router.push('/(auth)') }],
      );
      return;
    }
    if (!paymentMethod) {
      Alert.alert('Selecione um método', 'Escolha como deseja pagar.');
      return;
    }
    if (paymentMethod === 'cartao' && !selectedInstallment) {
      Alert.alert('Parcelas', 'Selecione a quantidade de parcelas.');
      return;
    }
    if (!aceitePolitica) {
      Alert.alert(
        'Aceite necessário',
        'É necessário aceitar a Política de Privacidade para finalizar o pedido.',
      );
      return;
    }
    checkoutMutation.mutate();
  };

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <ScrollView
        contentContainerStyle={{ padding: spacing.lg, paddingBottom: 220 }}
        showsVerticalScrollIndicator={false}
      >
        <Card style={{ padding: spacing.md }}>
          <Text variant="subtitle2" color={colors.textPrimary}>Resumo do pedido</Text>
          <View style={styles.summaryRow}>
            <Text variant="body2" color={colors.textSecondary}>Subtotal ({items.length} itens)</Text>
            <Text variant="body2" color={colors.textPrimary}>{formatCurrency(subtotal)}</Text>
          </View>
          <View style={styles.summaryRow}>
            <Text variant="body2" color={colors.textSecondary}>Frete</Text>
            <Text variant="body2" color={totalFrete === 0 ? colors.success : colors.textPrimary}>
              {totalFrete === 0 ? 'Grátis' : formatCurrency(totalFrete)}
            </Text>
          </View>
          {isMultiLoja && (
            <Text variant="caption" color={colors.textSecondary} style={{ marginTop: 6 }}>
              Pedido com itens de {lojasUnicas.length} lojas — checkout unificado
            </Text>
          )}
          <Divider style={{ marginVertical: 8 }} />
          <View style={styles.summaryRow}>
            <Text variant="subtitle1" color={colors.textPrimary}>Total</Text>
            <Text variant="price" color={colors.primary}>{formatCurrency(totalWithInstallment)}</Text>
          </View>
        </Card>

        {!isAuthenticated && (
          <Card style={{ marginTop: spacing.lg, padding: spacing.md, backgroundColor: colors.warningSurface }}>
            <Text variant="body2" color={colors.warningDark}>
              Você precisa entrar com sua conta para finalizar o pedido.
            </Text>
            <Button
              title="Entrar"
              variant="outline"
              size="md"
              onPress={() => router.push('/(auth)')}
              style={{ marginTop: 8 }}
            />
          </Card>
        )}

        <Text variant="subtitle2" color={colors.textPrimary} style={{ marginTop: spacing.xl }}>
          Forma de pagamento
        </Text>
        <PaymentMethodPicker
          selected={paymentMethod}
          onSelect={(m) => {
            setPaymentMethod(m);
            if (m !== 'cartao') setSelectedInstallment(null);
          }}
          style={{ marginTop: spacing.md }}
        />

        {paymentMethod === 'cartao' && (
          <>
            <Text variant="subtitle2" color={colors.textPrimary} style={{ marginTop: spacing.xl }}>
              Parcelas
            </Text>
            {installmentsQuery.isLoading ? (
              <Text variant="body2" color={colors.textSecondary} style={{ marginTop: spacing.sm }}>
                Carregando parcelas...
              </Text>
            ) : installmentsQuery.data ? (
              <InstallmentPicker
                installments={installmentsQuery.data}
                selected={selectedInstallment}
                onSelect={setSelectedInstallment}
                style={{ marginTop: spacing.sm, maxHeight: 300 }}
              />
            ) : null}
          </>
        )}

        {paymentMethod === 'pix' && (
          <Card style={{ marginTop: spacing.lg, padding: spacing.md, backgroundColor: colors.successSurface }}>
            <View style={styles.pixInfo}>
              <Icon name="check" size={18} color={colors.success} />
              <Text variant="body2" color={colors.success} style={{ marginLeft: 8 }}>
                Pagamento via PIX com aprovação imediata
              </Text>
            </View>
          </Card>
        )}

        {paymentMethod === 'boleto' && (
          <Card style={{ marginTop: spacing.lg, padding: spacing.md, backgroundColor: colors.warningSurface }}>
            <View style={styles.pixInfo}>
              <Icon name="bell" size={18} color={colors.warning} />
              <Text variant="body2" color={colors.warningDark} style={{ marginLeft: 8 }}>
                Boleto: compensação em 1-3 dias úteis. Pedido confirmado após pagamento.
              </Text>
            </View>
          </Card>
        )}

        <Card style={{ marginTop: spacing.lg, padding: spacing.md }}>
          <View style={styles.consentRow}>
            <Switch
              value={aceitePolitica}
              onValueChange={setAceitePolitica}
              trackColor={{ false: colors.gray300, true: colors.primaryLight }}
              thumbColor={aceitePolitica ? colors.primary : colors.gray400}
              accessibilityLabel="Aceitar política de privacidade"
            />
            <Text variant="body2" color={colors.textSecondary} style={{ flex: 1, marginLeft: 12 }}>
              Li e aceito a{' '}
              <Text variant="body2" color={colors.textLink}>Política de Privacidade</Text>
              {' '}e os{' '}
              <Text variant="body2" color={colors.textLink}>Termos de Uso</Text>.
            </Text>
          </View>
          <View style={[styles.consentRow, { marginTop: spacing.md }]}>
            <Switch
              value={aceiteMarketing}
              onValueChange={setAceiteMarketing}
              trackColor={{ false: colors.gray300, true: colors.primaryLight }}
              thumbColor={aceiteMarketing ? colors.primary : colors.gray400}
              accessibilityLabel="Aceitar comunicações de marketing"
            />
            <Text variant="body2" color={colors.textSecondary} style={{ flex: 1, marginLeft: 12 }}>
              Quero receber ofertas e novidades por e-mail e push (LGPD).
            </Text>
          </View>
        </Card>
      </ScrollView>

      <View style={[styles.bottomBar, { backgroundColor: colors.surface, borderTopColor: colors.divider, paddingBottom: insets.bottom + spacing.sm, ...shadow('md') }]}>
        <View style={styles.summaryRow}>
          <Text variant="subtitle1" color={colors.textPrimary}>Total</Text>
          <Text variant="price" color={colors.primary}>{formatCurrency(totalWithInstallment)}</Text>
        </View>
        {selectedInstallment && selectedInstallment > 1 && selectedInst && (
          <Text variant="caption" color={colors.textSecondary} align="right">
            {selectedInstallment}x de {formatCurrency(selectedInst.valor_parcela)}
            {selectedInst.juros ? ' (com juros)' : ' (sem juros)'}
          </Text>
        )}
        <Button
          title="Confirmar Pedido"
          onPress={handleConfirm}
          loading={checkoutMutation.isPending}
          fullWidth
          size="lg"
          disabled={!paymentMethod || !aceitePolitica || profileQuery.isLoading || addressQuery.isLoading}
          style={{ marginTop: spacing.sm }}
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  summaryRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 4,
  },
  pixInfo: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  consentRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
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
