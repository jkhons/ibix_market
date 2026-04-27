import { api } from './api';

export interface ConsumerProfile {
  id: number;
  nome: string;
  email: string;
  telefone?: string;
  documento?: string;
  data_nascimento?: string;
  genero?: string;
  ativo: boolean;
  aceite_marketing?: boolean;
  email_verificado?: boolean;
  origem_social_provider?: string;
  avatar_url?: string;
  created_at?: string;
}

export interface ConsumerUpdatePayload {
  nome?: string;
  telefone?: string;
  documento?: string;
  data_nascimento?: string;
  genero?: string;
  aceite_marketing?: boolean;
}

const consumerService = {
  async getProfile(): Promise<ConsumerProfile> {
    const { data } = await api.get<ConsumerProfile>('/loja/minha-conta');
    return data;
  },

  async updateProfile(payload: ConsumerUpdatePayload): Promise<ConsumerProfile> {
    const { data } = await api.put<ConsumerProfile>('/loja/minha-conta', payload);
    return data;
  },
};

export default consumerService;
