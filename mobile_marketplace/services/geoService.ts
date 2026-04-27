import { api } from './api';

export interface NearbyAd {
  id: number;
  titulo: string;
  loja_id?: number;
  preco_original: number;
  preco_promocional?: number;
  imagens?: string[];
  og_image_url?: string;
  slug_loja?: string;
  nome_loja?: string;
  estoque_atual?: number;
  status: string;
  frete_formato_efetivo?: string;
  frete_origem_regra?: string;
  frete_gratis?: boolean;
  distancia_km?: number;
  cidade_loja?: string;
  uf_loja?: string;
  bairro_loja?: string;
  distancia_rota_km?: number;
  duracao_rota_min?: number;
  rota_estimada?: boolean;
}

export interface NearbyAdsResponse {
  items: NearbyAd[];
  total: number;
  lat: number;
  lng: number;
}

export interface CityWithCoords {
  cidade: string;
  uf: string;
  lat?: number | null;
  lng?: number | null;
}

export interface NearestCityResult {
  cidade: string | null;
  uf: string | null;
  distancia_km: number | null;
  lat?: number;
  lng?: number;
}

export interface NearbyParams {
  lat: number;
  lng: number;
  limit?: number;
  pool?: number;
  bbox_km?: number;
  loja_slug?: string;
  cliente_ids?: number[];
}

export interface NearbyByQueryParams extends NearbyParams {
  q: string;
  top_n_lojas?: number;
  max_km?: number;
}

const geoService = {
  async getNearbyAds(params: NearbyParams): Promise<NearbyAdsResponse> {
    const { data } = await api.get<NearbyAdsResponse>('/loja/anuncios/perto-de-voce', {
      params,
    });
    return data;
  },

  async getNearbyByQuery(params: NearbyByQueryParams): Promise<NearbyAdsResponse> {
    const { data } = await api.get<NearbyAdsResponse>('/loja/anuncios/proximos', {
      params,
    });
    return data;
  },

  async listCities(q?: string): Promise<CityWithCoords[]> {
    const { data } = await api.get<CityWithCoords[]>('/loja/geo/cidades', {
      params: q ? { q } : undefined,
    });
    return data;
  },

  async nearestCity(lat: number, lng: number): Promise<NearestCityResult> {
    const { data } = await api.get<NearestCityResult>('/loja/geo/cidade-proxima', {
      params: { lat, lng },
    });
    return data;
  },

  async reverseGeo(lat: number, lng: number): Promise<{ cidade?: string; uf?: string }> {
    const { data } = await api.get<{ cidade?: string; uf?: string }>('/loja/geo/reverso', {
      params: { lat, lng },
    });
    return data;
  },
};

export default geoService;
