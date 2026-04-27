import { create } from 'zustand';
import { fastStorage } from '@/utils/storage';
import { STORAGE_KEYS } from '@/constants/config';

const MAX_RECENTLY_VIEWED = 30;

export interface RecentlyViewedItem {
  id: number;
  nome: string;
  preco: number;
  imageUrl?: string;
  lojaId: number;
  viewedAt: string;
}

interface RecentlyViewedState {
  items: RecentlyViewedItem[];
  hydrate: () => void;
  addItem: (item: Omit<RecentlyViewedItem, 'viewedAt'>) => void;
  clearAll: () => void;
}

function persist(items: RecentlyViewedItem[]) {
  fastStorage.setObject(STORAGE_KEYS.RECENTLY_VIEWED, items);
}

export const useRecentlyViewedStore = create<RecentlyViewedState>((set, get) => ({
  items: [],

  hydrate: () => {
    const saved = fastStorage.getObject<RecentlyViewedItem[]>(STORAGE_KEYS.RECENTLY_VIEWED);
    if (saved && Array.isArray(saved)) {
      set({ items: saved });
    }
  },

  addItem: (item) => {
    const current = get().items.filter((i) => i.id !== item.id);
    const newItem: RecentlyViewedItem = { ...item, viewedAt: new Date().toISOString() };
    const items = [newItem, ...current].slice(0, MAX_RECENTLY_VIEWED);
    set({ items });
    persist(items);
  },

  clearAll: () => {
    set({ items: [] });
    persist([]);
  },
}));
