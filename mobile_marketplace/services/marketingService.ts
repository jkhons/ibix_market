import { api } from './api';

export interface MarketingCard {
  id: number;
  titulo?: string;
  subtitulo?: string;
  imagem_url: string;
  imagem_url_mobile?: string;
  link?: string;
  anuncio_id?: number;
  categoria_id?: number;
  ordem: number;
}

export interface MarketingBlock {
  tipo_bloco: 'cabecalho_ofertas' | 'destaques' | 'oferta_semana' | string;
  titulo?: string;
  cards: MarketingCard[];
}

export interface VitrineHome {
  blocos: MarketingBlock[];
}

const marketingService = {
  async getVitrineHome(): Promise<VitrineHome> {
    const { data } = await api.get<VitrineHome>('/marketing-vitrine/vitrine-home');
    return data;
  },
};

export default marketingService;
