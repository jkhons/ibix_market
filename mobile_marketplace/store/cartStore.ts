import { create } from 'zustand';
import { fastStorage } from '@/utils/storage';
import { STORAGE_KEYS } from '@/constants/config';

export interface CartItem {
  productId: number;
  name: string;
  price: number;
  originalPrice?: number;
  imageUrl?: string;
  quantity: number;
  lojaId: number;
  lojaNome?: string;
  variantId?: number;
  variantLabel?: string;
  maxQuantity?: number;
}

interface CartState {
  items: CartItem[];
  hydrate: () => void;
  addItem: (item: Omit<CartItem, 'quantity'> & { quantity?: number }) => void;
  removeItem: (productId: number, variantId?: number) => void;
  updateQuantity: (productId: number, quantity: number, variantId?: number) => void;
  clearCart: () => void;
  clearLojaItems: (lojaId: number) => void;

  totalItems: () => number;
  totalPrice: () => number;
  itemsByLoja: () => Record<number, CartItem[]>;
}

function persist(items: CartItem[]) {
  fastStorage.setObject(STORAGE_KEYS.CART_ITEMS, items);
}

function findIndex(items: CartItem[], productId: number, variantId?: number): number {
  return items.findIndex(
    (i) => i.productId === productId && i.variantId === variantId,
  );
}

export const useCartStore = create<CartState>((set, get) => ({
  items: [],

  hydrate: () => {
    const saved = fastStorage.getObject<CartItem[]>(STORAGE_KEYS.CART_ITEMS);
    if (saved && Array.isArray(saved)) {
      set({ items: saved });
    }
  },

  addItem: (item) => {
    const items = [...get().items];
    const idx = findIndex(items, item.productId, item.variantId);
    const qty = item.quantity ?? 1;

    if (idx >= 0) {
      const max = items[idx].maxQuantity ?? 99;
      items[idx] = { ...items[idx], quantity: Math.min(items[idx].quantity + qty, max) };
    } else {
      items.push({ ...item, quantity: qty });
    }

    set({ items });
    persist(items);
  },

  removeItem: (productId, variantId) => {
    const items = get().items.filter(
      (i) => !(i.productId === productId && i.variantId === variantId),
    );
    set({ items });
    persist(items);
  },

  updateQuantity: (productId, quantity, variantId) => {
    const items = [...get().items];
    const idx = findIndex(items, productId, variantId);
    if (idx >= 0) {
      if (quantity <= 0) {
        items.splice(idx, 1);
      } else {
        const max = items[idx].maxQuantity ?? 99;
        items[idx] = { ...items[idx], quantity: Math.min(quantity, max) };
      }
      set({ items });
      persist(items);
    }
  },

  clearCart: () => {
    set({ items: [] });
    persist([]);
  },

  clearLojaItems: (lojaId) => {
    const items = get().items.filter((i) => i.lojaId !== lojaId);
    set({ items });
    persist(items);
  },

  totalItems: () => get().items.reduce((acc, i) => acc + i.quantity, 0),
  totalPrice: () => get().items.reduce((acc, i) => acc + i.price * i.quantity, 0),

  itemsByLoja: () => {
    const grouped: Record<number, CartItem[]> = {};
    for (const item of get().items) {
      if (!grouped[item.lojaId]) grouped[item.lojaId] = [];
      grouped[item.lojaId].push(item);
    }
    return grouped;
  },
}));
