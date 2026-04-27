import { api } from './api';

export interface CouponValidation {
  valido: boolean;
  desconto?: number;
  tipo_desconto?: 'percentual' | 'fixo';
  mensagem?: string;
  code?: string;
}

export interface CouponAvailable {
  id: number;
  codigo: string;
  tipo_desconto: 'percentual' | 'fixo';
  valor_desconto: number;
  valor_minimo_pedido?: number;
  valido_ate?: string;
  descricao?: string;
}

export interface CouponValidatePayload {
  codigo: string;
  itens?: Array<{ anuncio_id: number; quantidade: number; preco_unitario: number }>;
  valor_total?: number;
}

const couponService = {
  async validate(payload: CouponValidatePayload): Promise<CouponValidation> {
    const { data } = await api.post<CouponValidation>('/loja/cupons/validar', payload);
    return data;
  },

  async getAvailable(): Promise<CouponAvailable[]> {
    const { data } = await api.get<CouponAvailable[]>('/loja/cupons/disponiveis');
    return data;
  },
};

export default couponService;
