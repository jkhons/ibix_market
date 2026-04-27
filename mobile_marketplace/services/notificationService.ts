import { api } from './api';

export interface Notification {
  id: number;
  tipo: string;
  titulo: string;
  corpo?: string;
  lida: boolean;
  data?: Record<string, unknown>;
  created_at: string;
}

export interface PushTokenPayload {
  token: string;
  plataforma: 'ios' | 'android';
  device_info?: string;
}

const notificationService = {
  async getNotifications(params?: { page?: number; page_size?: number }): Promise<{
    items: Notification[];
    total: number;
    nao_lidas: number;
  }> {
    const { data } = await api.get('/loja/notificacoes', { params });
    return data;
  },

  async getUnreadCount(): Promise<{ nao_lidas: number }> {
    const { data } = await api.get('/loja/notificacoes/nao-lidas');
    return data;
  },

  async markAsRead(ids: number[]): Promise<{ lidas: number }> {
    const { data } = await api.post('/loja/notificacoes/marcar-lida', { ids });
    return data;
  },

  async registerPushToken(payload: PushTokenPayload): Promise<void> {
    await api.post('/loja/push-token', payload);
  },

  async removePushToken(token: string): Promise<void> {
    await api.delete('/loja/push-token', { data: { token } });
  },
};

export default notificationService;
