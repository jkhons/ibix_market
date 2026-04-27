import { api } from './api';

export interface Address {
  id: number;
  consumidor_id?: number;
  apelido?: string;
  logradouro?: string;
  numero?: string;
  complemento?: string;
  bairro?: string;
  cidade?: string;
  uf?: string;
  cep?: string;
  tipo_endereco?: string;
  referencia?: string;
  principal: boolean;
  latitude?: number;
  longitude?: number;
  created_at?: string;
}

export interface AddressPayload {
  apelido?: string;
  logradouro?: string;
  numero?: string;
  complemento?: string;
  bairro?: string;
  cidade?: string;
  uf?: string;
  cep?: string;
  tipo_endereco?: string;
  referencia?: string;
  principal?: boolean;
}

export interface ViaCepResult {
  logradouro: string;
  bairro: string;
  localidade: string;
  uf: string;
  erro?: boolean;
}

const addressService = {
  async list(): Promise<Address[]> {
    const { data } = await api.get<Address[]>('/loja/minha-conta/enderecos');
    return data;
  },

  async create(payload: AddressPayload): Promise<Address> {
    const { data } = await api.post<Address>('/loja/minha-conta/enderecos', payload);
    return data;
  },

  async update(id: number, payload: Partial<AddressPayload>): Promise<Address> {
    const { data } = await api.patch<Address>(`/loja/minha-conta/enderecos/${id}`, payload);
    return data;
  },

  async remove(id: number): Promise<void> {
    await api.delete(`/loja/minha-conta/enderecos/${id}`);
  },

  async setDefault(id: number): Promise<Address> {
    const { data } = await api.patch<Address>(`/loja/minha-conta/enderecos/${id}/padrao`);
    return data;
  },

  async lookupCep(cep: string): Promise<ViaCepResult> {
    const cleanCep = cep.replace(/\D/g, '');
    const res = await fetch(`https://viacep.com.br/ws/${cleanCep}/json/`);
    const data: ViaCepResult = await res.json();
    if (data.erro) throw new Error('CEP não encontrado');
    return data;
  },
};

export default addressService;
