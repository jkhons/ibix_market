import { api } from './api';

export interface ProductSummary {
  id: number;
  nome: string;
  preco: number;
  preco_promocional?: number;
  imagens?: string[];
  slug?: string;
  loja_id: number;
  loja_nome?: string;
  estoque_disponivel?: number;
  parcela_sem_juros?: string;
  favorito?: boolean;
}

export interface Installment {
  parcelas: number;
  valor_parcela: number;
  total: number;
  juros: boolean;
  taxa_juros?: number | null;
}

export interface ParcelamentoResponse {
  valor_original: number;
  opcoes: Installment[];
}

export interface ProductReview {
  id: number;
  consumidor_nome: string;
  nota: number;
  comentario?: string;
  fotos?: string[];
  created_at: string;
}

export interface ProductDetail extends ProductSummary {
  descricao?: string;
  especificacoes?: Record<string, string>;
  categoria_id?: number;
  categoria_nome?: string;
  avaliacoes_media?: number;
  avaliacoes_count?: number;
  parcelas?: Installment[];
  variantes?: Array<{
    id: number;
    nome: string;
    opcoes: string[];
  }>;
  loja?: {
    id: number;
    nome: string;
    slug: string;
    logo_url?: string;
    avaliacao_media?: number;
    cidade?: string;
  };
}

export interface AutocompleteResult {
  sugestoes: string[];
  categorias: Array<{ id: number; nome: string }>;
}

export interface Category {
  id: number;
  nome: string;
  icone_url?: string;
  slug?: string;
  parent_id?: number | null;
  count_produtos?: number;
}

export interface StoreSummary {
  id: number;
  nome: string;
  slug: string;
  logo_url?: string;
  banner_url?: string;
  avaliacao_media?: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
}

export interface ProductSearchParams {
  q?: string;
  categoria_id?: number;
  loja_id?: number;
  preco_min?: number;
  preco_max?: number;
  ordenar?: 'relevancia' | 'menor_preco' | 'maior_preco' | 'mais_vendidos' | 'recentes';
  page?: number;
  page_size?: number;
}

const catalogService = {
  async getProducts(params: ProductSearchParams): Promise<PaginatedResponse<ProductSummary>> {
    const { data } = await api.get('/loja/busca/produtos', { params });
    return data;
  },

  async getProductById(id: number): Promise<ProductDetail> {
    const { data } = await api.get(`/loja/produtos/${id}`);
    return data;
  },

  async getCategories(): Promise<Category[]> {
    const { data } = await api.get('/loja/categorias');
    return data;
  },

  async getStores(params?: { page?: number; page_size?: number }): Promise<PaginatedResponse<StoreSummary>> {
    const { data } = await api.get('/loja/lojas', { params });
    return data;
  },

  async getStoreBySlug(slug: string): Promise<StoreSummary> {
    const { data } = await api.get(`/loja/${slug}`);
    return data;
  },

  async getStoreProducts(slug: string, params?: ProductSearchParams): Promise<PaginatedResponse<ProductSummary>> {
    const { data } = await api.get(`/loja/${slug}/produtos`, { params });
    return data;
  },

  async searchProducts(query: string, params?: Omit<ProductSearchParams, 'q'>): Promise<PaginatedResponse<ProductSummary>> {
    const { data } = await api.get('/loja/busca/produtos', { params: { q: query, ...params } });
    return data;
  },

  async autocomplete(query: string, limit = 8): Promise<AutocompleteResult> {
    const { data } = await api.get<AutocompleteResult>('/loja/busca/autocomplete', {
      params: { q: query, limit },
    });
    return data;
  },

  async getPopularTerms(): Promise<string[]> {
    const { data } = await api.get<{ termos: string[] }>('/loja/busca/populares');
    return data.termos;
  },

  async getInstallments(valor: number): Promise<Installment[]> {
    const { data } = await api.get<ParcelamentoResponse>('/loja/parcelamento', {
      params: { valor },
    });
    return data.opcoes ?? [];
  },

  async getProductReviews(productId: number, params?: { page?: number; page_size?: number }): Promise<PaginatedResponse<ProductReview>> {
    const { data } = await api.get(`/loja/anuncios/${productId}/avaliacoes`, { params });
    return data;
  },

  async getSimilarProducts(productId: number): Promise<ProductSummary[]> {
    const { data } = await api.get<ProductSummary[]>(`/loja/anuncios/${productId}/semelhantes`);
    return data;
  },
};

export default catalogService;
