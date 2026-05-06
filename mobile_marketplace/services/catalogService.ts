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

/** Payload bruto de item da vitrine (`AnuncioVitrineResponse` no backend). */
interface AnuncioVitrineRaw {
  id: number;
  titulo: string;
  loja_id: number;
  preco_original: number | string;
  preco_promocional?: number | string | null;
  imagens?: string[];
  slug_loja?: string | null;
  nome_loja?: string | null;
  estoque_atual?: number | string | null;
  status?: string;
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
  /** Alias UI — API devolve `termos`. */
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
  /** Marketplace `LojaMarketplace.id` — ainda não há filtro direto em `GET /loja/anuncios`; prefira `loja_slug`. */
  loja_id?: number;
  /** Slug da loja — repassado como `loja_slug` para `GET /loja/anuncios`. */
  loja_slug?: string;
  preco_min?: number;
  preco_max?: number;
  ordenar?: 'relevancia' | 'menor_preco' | 'maior_preco' | 'mais_vendidos' | 'recentes';
  page?: number;
  page_size?: number;
}

function num(v: unknown): number {
  if (v === null || v === undefined) return 0;
  const n = typeof v === 'number' ? v : Number(v);
  return Number.isFinite(n) ? n : 0;
}

function mapAnuncioToProductSummary(raw: AnuncioVitrineRaw): ProductSummary {
  const preco = num(raw.preco_original);
  let promo = raw.preco_promocional != null && raw.preco_promocional !== '' ? num(raw.preco_promocional) : undefined;
  if (promo !== undefined && (promo <= 0 || promo >= preco)) promo = undefined;

  return {
    id: raw.id,
    nome: (raw.titulo ?? '').trim() || `Produto ${raw.id}`,
    preco,
    preco_promocional: promo,
    imagens: raw.imagens,
    slug: raw.slug_loja ?? undefined,
    loja_id: raw.loja_id,
    loja_nome: raw.nome_loja ?? undefined,
    estoque_disponivel: raw.estoque_atual != null ? num(raw.estoque_atual) : undefined,
  };
}

function ordenarToSort(
  ordenar?: ProductSearchParams['ordenar'],
): 'recent' | 'preco_asc' | 'preco_desc' | 'nome' | 'random' {
  switch (ordenar) {
    case 'menor_preco':
      return 'preco_asc';
    case 'maior_preco':
      return 'preco_desc';
    case 'relevancia':
    case 'mais_vendidos':
    case 'recentes':
    default:
      return 'recent';
  }
}

function buildPaginated<T>(
  items: T[],
  total: number,
  skip: number,
  limit: number,
  page: number,
): PaginatedResponse<T> {
  const has_next = skip + items.length < total;
  return {
    items,
    total,
    page,
    page_size: limit,
    has_next,
  };
}

interface AnunciosListRaw {
  items: AnuncioVitrineRaw[];
  total: number;
  skip: number;
  limit: number;
}

interface LojasParceirasRaw {
  items: Array<{
    id: number;
    slug: string;
    nome: string;
    logo_url?: string | null;
    banner_url?: string | null;
  }>;
  total: number;
  skip: number;
  limit: number;
}

const catalogService = {
  async getProducts(params: ProductSearchParams): Promise<PaginatedResponse<ProductSummary>> {
    const page = params.page ?? 1;
    const pageSize = params.page_size ?? 20;
    const skip = (page - 1) * pageSize;

    const { data } = await api.get<AnunciosListRaw>('/loja/anuncios', {
      params: {
        q: params.q?.trim() || undefined,
        categoria_id: params.categoria_id,
        loja_slug: params.loja_slug?.trim() || undefined,
        sort: ordenarToSort(params.ordenar),
        skip,
        limit: pageSize,
      },
    });

    const items = (data.items ?? []).map(mapAnuncioToProductSummary);
    return buildPaginated(items, data.total ?? 0, data.skip ?? skip, data.limit ?? pageSize, page);
  },

  async getProductById(id: number): Promise<ProductDetail> {
    const { data } = await api.get<{
      id: number;
      titulo: string;
      descricao?: string | null;
      produto_ca_descricao?: string | null;
      categoria_id?: number | null;
      imagens?: string[];
      preco_original: number | string;
      preco_promocional?: number | string | null;
      estoque_atual?: number | string | null;
      loja?: {
        id: number;
        slug: string;
        nome_loja: string;
        descricao?: string | null;
      } | null;
    }>(`/loja/anuncios/${id}`);

    const loja = data.loja;
    const preco = num(data.preco_original);
    let promo = data.preco_promocional != null && data.preco_promocional !== '' ? num(data.preco_promocional) : undefined;
    if (promo !== undefined && (promo <= 0 || promo >= preco)) promo = undefined;

    const base: ProductSummary = {
      id: data.id,
      nome: (data.titulo ?? '').trim() || `Produto ${data.id}`,
      preco,
      preco_promocional: promo,
      imagens: data.imagens,
      slug: loja?.slug,
      loja_id: loja?.id ?? 0,
      loja_nome: loja?.nome_loja,
      estoque_disponivel: data.estoque_atual != null ? num(data.estoque_atual) : undefined,
    };

    return {
      ...base,
      descricao: (data.descricao ?? data.produto_ca_descricao ?? '').trim() || undefined,
      categoria_id: data.categoria_id ?? undefined,
      loja: loja
        ? {
            id: loja.id,
            nome: loja.nome_loja,
            slug: loja.slug,
          }
        : undefined,
    };
  },

  async getCategories(): Promise<Category[]> {
    const { data } = await api.get<Array<Category & { icone?: string }>>('/loja/categorias');
    const rows = Array.isArray(data) ? data : [];
    return rows.map((row) => ({
      ...row,
      icone_url: row.icone_url ?? row.icone ?? undefined,
    }));
  },

  async getStores(params?: { page?: number; page_size?: number }): Promise<PaginatedResponse<StoreSummary>> {
    const page = params?.page ?? 1;
    const pageSize = params?.page_size ?? 20;
    const skip = (page - 1) * pageSize;

    const { data } = await api.get<LojasParceirasRaw>('/loja/lojas-parceiras', {
      params: { skip, limit: pageSize },
    });

    const items: StoreSummary[] = (data.items ?? []).map((r) => ({
      id: r.id,
      nome: r.nome,
      slug: r.slug,
      logo_url: r.logo_url ?? undefined,
      banner_url: r.banner_url ?? undefined,
    }));

    return buildPaginated(items, data.total ?? 0, data.skip ?? skip, data.limit ?? pageSize, page);
  },

  async getStoreBySlug(slug: string): Promise<StoreSummary> {
    const norm = slug.trim().toLowerCase();
    const { data } = await api.get<LojasParceirasRaw>('/loja/lojas-parceiras', {
      params: { q: slug, skip: 0, limit: 80 },
    });

    const row =
      (data.items ?? []).find((s) => (s.slug ?? '').toLowerCase() === norm) ??
      (data.items ?? []).find((s) => (s.slug ?? '').toLowerCase().includes(norm));

    if (!row) {
      throw new Error('Loja não encontrada');
    }

    return {
      id: row.id,
      nome: row.nome,
      slug: row.slug,
      logo_url: row.logo_url ?? undefined,
      banner_url: row.banner_url ?? undefined,
    };
  },

  async getStoreProducts(slug: string, params?: ProductSearchParams): Promise<PaginatedResponse<ProductSummary>> {
    return catalogService.getProducts({
      ...params,
      loja_slug: slug.trim(),
    });
  },

  async searchProducts(query: string, params?: Omit<ProductSearchParams, 'q'>): Promise<PaginatedResponse<ProductSummary>> {
    return catalogService.getProducts({ ...params, q: query });
  },

  async autocomplete(query: string, limit = 8): Promise<AutocompleteResult> {
    const { data } = await api.get<{ termos?: string[] }>('/loja/busca/autocomplete', {
      params: { q: query, limit },
    });
    const termos = data.termos ?? [];
    return {
      sugestoes: termos,
      categorias: [],
    };
  },

  async getPopularTerms(): Promise<string[]> {
    const { data } = await api.get<Array<{ termo: string; contagem?: number }>>('/loja/busca/populares');
    if (!Array.isArray(data)) return [];
    return data.map((r) => r.termo).filter(Boolean);
  },

  async getInstallments(valor: number): Promise<Installment[]> {
    const { data } = await api.get<ParcelamentoResponse>('/loja/parcelamento', {
      params: { valor },
    });
    return data.opcoes ?? [];
  },

  async getProductReviews(
    productId: number,
    params?: { page?: number; page_size?: number },
  ): Promise<PaginatedResponse<ProductReview>> {
    const page = params?.page ?? 1;
    const pageSize = params?.page_size ?? 10;
    const skip = (page - 1) * pageSize;

    const { data } = await api.get<
      Array<{
        id: number;
        comprador_nome?: string | null;
        nota: number;
        comentario?: string | null;
        created_at?: string | null;
      }>
    >(`/loja/anuncios/${productId}/avaliacoes`, {
      params: { skip, limit: pageSize },
    });

    const arr = Array.isArray(data) ? data : [];
    const items: ProductReview[] = arr.map((r) => ({
      id: r.id,
      consumidor_nome: (r.comprador_nome ?? '').trim() || 'Comprador',
      nota: r.nota,
      comentario: r.comentario ?? undefined,
      fotos: undefined,
      created_at: r.created_at ?? '',
    }));

    return {
      items,
      total: items.length,
      page,
      page_size: pageSize,
      has_next: items.length >= pageSize,
    };
  },

  async getSimilarProducts(productId: number): Promise<ProductSummary[]> {
    const { data } = await api.get<{ items?: AnuncioVitrineRaw[] }>(`/loja/anuncios/${productId}/semelhantes`);
    const rawItems = data.items ?? [];
    return rawItems.map(mapAnuncioToProductSummary);
  },
};

export default catalogService;
