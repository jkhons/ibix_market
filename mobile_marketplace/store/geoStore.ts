import { create } from 'zustand';
import { fastStorage } from '@/utils/storage';
import { STORAGE_KEYS } from '@/constants/config';

export interface GeoLocation {
  lat: number;
  lng: number;
  cidade?: string;
  uf?: string;
  source: 'gps' | 'manual' | 'reverse';
  updated_at: number;
}

interface GeoState {
  location: GeoLocation | null;
  isHydrated: boolean;
  permissionDenied: boolean;
  hydrate: () => void;
  setLocation: (loc: GeoLocation) => void;
  clearLocation: () => void;
  setPermissionDenied: (denied: boolean) => void;
}

export const useGeoStore = create<GeoState>((set) => ({
  location: null,
  isHydrated: false,
  permissionDenied: false,

  hydrate: () => {
    try {
      const stored = fastStorage.getObject<GeoLocation>(STORAGE_KEYS.GEO_LOCATION);
      set({ location: stored ?? null, isHydrated: true });
    } catch {
      set({ isHydrated: true });
    }
  },

  setLocation: (loc) => {
    fastStorage.setObject(STORAGE_KEYS.GEO_LOCATION, loc);
    set({ location: loc, permissionDenied: false });
  },

  clearLocation: () => {
    fastStorage.remove(STORAGE_KEYS.GEO_LOCATION);
    set({ location: null });
  },

  setPermissionDenied: (denied) => set({ permissionDenied: denied }),
}));
