import { api } from './api';

export interface CheckoutItem {
  anuncio_id: number;
  quantidade: number;
}

export interface CheckoutItemUnificado extends CheckoutItem {
  loja_id: number;
}

export interface FreightOption {
  tipo: string;
  valor: number;
  prazo_min: number;
  prazo_max: number;
  descricao?: string;
  frete_gratis?: boolean;
}

export interface FreightResult {
  loja_id: number;
  loja_nome: string;
  opcoes: FreightOption[];
}

export type PaymentMethod = 'pix' | 'credit_card' | 'boleto';

export interface BuyerInfo {
  comprador_nome: string;
  comprador_email: string;
  comprador_telefone?: string;
  comprador_documento?: string;
  destinatario_nome?: string;
}

export interface AddressInfo {
  endereco_cep?: string;
  endereco_logradouro?: string;
  endereco_numero?: string;
  endereco_complemento?: string;
  endereco_bairro?: string;
  endereco_cidade?: string;
  endereco_uf?: string;
}

interface CheckoutBaseFields extends BuyerInfo, AddressInfo {
  tipo_entrega?: string;
  desconto?: number;
  taxa_entrega?: number;
  aceite_marketing?: boolean;
  aceite_politica_privacidade: boolean;
  payment_method: PaymentMethod;
  observacoes_cliente?: string;
  canal_origem?: string;
  idempotency_key?: string;
}

export interface CheckoutSingleLojaPayload extends CheckoutBaseFields {
  loja_id: number;
  itens: CheckoutItem[];
}

export interface CheckoutUnificadoPayload extends CheckoutBaseFields {
  itens: CheckoutItemUnificado[];
}

export interface MarketplacePixPayload {
  copia_cola: string;
  qr_code: string;
  qr_code_base64?: string;
  expiracao_minutos: number;
}

export interface CheckoutSingleLojaResponse {
  id: number;
  numero_pedido: string;
  loja_id: number;
  status_pedido: string;
  status_pagamento: string;
  status_entrega?: string;
  subtotal?: number;
  desconto?: number;
  taxa_entrega?: number;
  total: number;
  comprador_email?: string;
  created_at?: string;
  redirect_url?: string;
  transaction_uuid?: string;
  checkout_type?: 'redirect' | 'pix' | 'boleto' | string;
  qr_code?: string;
  copy_paste_code?: string;
  pix?: MarketplacePixPayload;
}

export interface PedidoResumoUnificado {
  id: number;
  numero_pedido: string;
  loja_id: number;
  total: number;
}

export interface CheckoutUnificadoResponse {
  session_uuid: string;
  pedidos: PedidoResumoUnificado[];
  comprador_email?: string;
  redirect_url?: string;
  transaction_uuid?: string;
  checkout_type?: string;
  qr_code?: string;
  copy_paste_code?: string;
  pix?: MarketplacePixPayload;
}

export interface PedidoConsultarResponse {
  id?: number;
  numero_pedido: string;
  status_pedido: string;
  status_pagamento: string;
  status_entrega: string;
  total: number;
  created_at?: string;
  itens: Array<{
    nome: string;
    quantidade: number;
    preco_unitario: number;
    subtotal: number;
  }>;
  timeline: Array<{
    tipo_evento: string;
    status_codigo?: string;
    status_label?: string;
    created_at?: string;
  }>;
}

const checkoutService = {
  async calculateFreight(lojaId: number, cep: string): Promise<FreightResult> {
    const { data } = await api.get<FreightResult>(`/loja/${lojaId}/frete`, {
      params: { cep: cep.replace(/\D/g, '') },
    });
    return data;
  },

  async submitSingleLoja(payload: CheckoutSingleLojaPayload): Promise<CheckoutSingleLojaResponse> {
    const { data } = await api.post<CheckoutSingleLojaResponse>('/loja/checkout', payload);
    return data;
  },

  async submitUnificado(payload: CheckoutUnificadoPayload): Promise<CheckoutUnificadoResponse> {
    const { data } = await api.post<CheckoutUnificadoResponse>('/loja/checkout-unificado', payload);
    return data;
  },

  async getMyOrderStatus(numeroPedido: string): Promise<PedidoConsultarResponse> {
    const { data } = await api.get<PedidoConsultarResponse>('/loja/pedido/meu', {
      params: { numero_pedido: numeroPedido },
    });
    return data;
  },

  async getPublicOrderStatus(numeroPedido: string, email: string): Promise<PedidoConsultarResponse> {
    const { data } = await api.get<PedidoConsultarResponse>('/loja/pedido/consultar', {
      params: { numero_pedido: numeroPedido, email },
    });
    return data;
  },
};

export default checkoutService;
