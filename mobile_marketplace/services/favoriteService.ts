import { api } from './api';

export interface FavoriteItem {
  id: number;
  produto_id: number;
  produto_nome: string;
  produto_preco: number;
  produto_imagem?: string;
  loja_id: number;
  created_at: string;
}

const favoriteService = {
  async getFavorites(params?: { page?: number; page_size?: number }): Promise<{
    items: FavoriteItem[];
    total: number;
  }> {
    const { data } = await api.get('/loja/favoritos', { params });
    return data;
  },

  async addFavorite(produtoId: number): Promise<{ id: number }> {
    const { data } = await api.post('/loja/favoritos', { produto_id: produtoId });
    return data;
  },

  async removeFavorite(produtoId: number): Promise<void> {
    await api.delete(`/loja/favoritos/${produtoId}`);
  },

  async checkFavorite(produtoId: number): Promise<boolean> {
    try {
      const { data } = await api.get(`/loja/favoritos/check/${produtoId}`);
      return data.is_favorito ?? false;
    } catch {
      return false;
    }
  },
};

export default favoriteService;
