import { api } from './api';
import type { PedidoConsultarResponse } from './checkoutService';

export interface PedidoItemResumo {
  anuncio_id: number;
  titulo: string;
  quantidade: number;
  preco_unitario: number;
  subtotal: number;
}

export interface PedidoResumo {
  id: number;
  numero_pedido: string;
  loja_id: number;
  status_pedido: string;
  status_pagamento: string;
  status_entrega: string;
  subtotal: number;
  desconto: number;
  taxa_entrega: number;
  total: number;
  created_at?: string;
  itens: PedidoItemResumo[];
}

const orderService = {
  async getMyOrders(): Promise<PedidoResumo[]> {
    const { data } = await api.get<PedidoResumo[]>('/loja/meus-pedidos');
    return data;
  },

  async getMyOrder(numeroPedido: string): Promise<PedidoConsultarResponse> {
    const { data } = await api.get<PedidoConsultarResponse>('/loja/pedido/meu', {
      params: { numero_pedido: numeroPedido },
    });
    return data;
  },

  async cancelOrder(pedidoId: number, motivoId: number, descricao?: string): Promise<void> {
    await api.post(`/loja/pedidos/${pedidoId}/cancelar`, {
      motivo_id: motivoId,
      descricao_adicional: descricao,
    });
  },
};

export default orderService;
