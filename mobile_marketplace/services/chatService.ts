import { api } from './api';

export interface ConversaResumo {
  id: number;
  loja_id: number;
  loja_nome?: string;
  anuncio_id?: number;
  status: string;
  ultima_mensagem_em?: string;
  ultima_mensagem_texto?: string;
  nao_lidas: number;
  created_at: string;
}

export interface ConversasListResponse {
  items: ConversaResumo[];
  total: number;
}

export interface MensagemResponse {
  id: number;
  conversa_id: number;
  remetente_tipo: 'consumidor' | 'loja';
  remetente_id: number;
  texto?: string;
  imagem_url?: string;
  lida: boolean;
  created_at: string;
}

export interface IniciarConversaPayload {
  loja_id: number;
  anuncio_id?: number;
  mensagem: string;
}

export interface IniciarConversaResponse {
  conversa_id: number;
  mensagem_id: number;
}

export interface EnviarMensagemPayload {
  texto?: string;
  imagem_url?: string;
}

const chatService = {
  async listConversations(params?: { offset?: number; limit?: number }): Promise<ConversasListResponse> {
    const { data } = await api.get<ConversasListResponse>('/loja/conversas', { params });
    return data;
  },

  async startConversation(payload: IniciarConversaPayload): Promise<IniciarConversaResponse> {
    if (!payload.mensagem || !payload.mensagem.trim()) {
      throw new Error('Mensagem inicial obrigatória');
    }
    const { data } = await api.post<IniciarConversaResponse>('/loja/conversas', payload);
    return data;
  },

  async listMessages(
    conversaId: number,
    params?: { before_id?: number; limit?: number },
  ): Promise<MensagemResponse[]> {
    const { data } = await api.get<MensagemResponse[]>(`/loja/conversas/${conversaId}/mensagens`, {
      params,
    });
    return data;
  },

  async sendMessage(conversaId: number, payload: EnviarMensagemPayload): Promise<MensagemResponse> {
    if (!payload.texto && !payload.imagem_url) {
      throw new Error('Envie texto ou imagem');
    }
    const { data } = await api.post<MensagemResponse>(
      `/loja/conversas/${conversaId}/mensagens`,
      payload,
    );
    return data;
  },

  async markRead(conversaId: number): Promise<{ marcadas: number }> {
    const { data } = await api.patch<{ marcadas: number }>(`/loja/conversas/${conversaId}/lida`);
    return data;
  },
};

export default chatService;
