import { create } from 'zustand';
import { secureStorage } from '@/utils/storage';
import { STORAGE_KEYS } from '@/constants/config';
import { extractApiError } from '@/services/api';
import authService, {
  LoginPayload,
  CadastroPayload,
  SocialLoginPayload,
  SocialConfirmLinkPayload,
  AppleSignInPayload,
  AuthResponse,
  SocialAuthResponse,
} from '@/services/authService';

interface Consumer {
  id: number;
  nome?: string;
  email?: string;
}

interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
  consumer: Consumer | null;
  error: string | null;

  hydrate: () => Promise<void>;
  login: (payload: LoginPayload) => Promise<void>;
  cadastro: (payload: CadastroPayload) => Promise<void>;
  socialLogin: (payload: SocialLoginPayload) => Promise<SocialAuthResponse>;
  appleSignIn: (payload: AppleSignInPayload) => Promise<void>;
  socialConfirmLink: (payload: SocialConfirmLinkPayload) => Promise<void>;
  logout: () => Promise<void>;
  clearError: () => void;
}

async function persistTokens(response: AuthResponse | Pick<SocialAuthResponse, 'access_token' | 'refresh_token' | 'consumidor'>) {
  if (response.access_token) {
    await secureStorage.set(STORAGE_KEYS.ACCESS_TOKEN, response.access_token);
  }
  if (response.refresh_token) {
    await secureStorage.set(STORAGE_KEYS.REFRESH_TOKEN, response.refresh_token);
  }
  if (response.consumidor?.id) {
    await secureStorage.set(STORAGE_KEYS.CONSUMER_ID, String(response.consumidor.id));
  }
}

async function clearTokens() {
  await secureStorage.remove(STORAGE_KEYS.ACCESS_TOKEN);
  await secureStorage.remove(STORAGE_KEYS.REFRESH_TOKEN);
  await secureStorage.remove(STORAGE_KEYS.CONSUMER_ID);
}

export const useAuthStore = create<AuthState>((set) => ({
  isAuthenticated: false,
  isLoading: true,
  consumer: null,
  error: null,

  hydrate: async () => {
    try {
      const token = await secureStorage.get(STORAGE_KEYS.ACCESS_TOKEN);
      const consumerId = await secureStorage.get(STORAGE_KEYS.CONSUMER_ID);
      if (token && consumerId) {
        set({
          isAuthenticated: true,
          consumer: { id: Number(consumerId) },
          isLoading: false,
        });
      } else {
        set({ isAuthenticated: false, consumer: null, isLoading: false });
      }
    } catch {
      set({ isAuthenticated: false, consumer: null, isLoading: false });
    }
  },

  login: async (payload) => {
    set({ isLoading: true, error: null });
    try {
      const response = await authService.login(payload);
      await persistTokens(response);
      set({
        isAuthenticated: true,
        consumer: response.consumidor ?? { id: 0 },
        isLoading: false,
      });
    } catch (err: unknown) {
      const msg = extractApiError(err);
      set({ isLoading: false, error: msg });
      throw err;
    }
  },

  cadastro: async (payload) => {
    set({ isLoading: true, error: null });
    try {
      const response = await authService.cadastro(payload);
      await persistTokens(response);
      set({
        isAuthenticated: true,
        consumer: response.consumidor ?? { id: 0 },
        isLoading: false,
      });
    } catch (err: unknown) {
      const msg = extractApiError(err);
      set({ isLoading: false, error: msg });
      throw err;
    }
  },

  socialLogin: async (payload) => {
    set({ isLoading: true, error: null });
    try {
      const response = await authService.socialLogin(payload);
      if (response.status === 'authenticated' && response.access_token) {
        await persistTokens(response);
        set({
          isAuthenticated: true,
          consumer: response.consumidor ?? { id: 0 },
          isLoading: false,
        });
      } else {
        set({ isLoading: false });
      }
      return response;
    } catch (err: unknown) {
      const msg = extractApiError(err);
      set({ isLoading: false, error: msg });
      throw err;
    }
  },

  appleSignIn: async (payload) => {
    set({ isLoading: true, error: null });
    try {
      const response = await authService.appleSignIn(payload);
      await persistTokens(response);
      set({
        isAuthenticated: true,
        consumer: response.consumidor ?? { id: 0 },
        isLoading: false,
      });
    } catch (err: unknown) {
      const msg = extractApiError(err);
      set({ isLoading: false, error: msg });
      throw err;
    }
  },

  socialConfirmLink: async (payload) => {
    set({ isLoading: true, error: null });
    try {
      const response = await authService.socialConfirmLink(payload);
      if (response.access_token) {
        await persistTokens(response);
        set({
          isAuthenticated: true,
          consumer: response.consumidor ?? { id: 0 },
          isLoading: false,
        });
      }
    } catch (err: unknown) {
      const msg = extractApiError(err);
      set({ isLoading: false, error: msg });
      throw err;
    }
  },

  logout: async () => {
    try {
      await authService.logout();
    } finally {
      await clearTokens();
      set({ isAuthenticated: false, consumer: null, error: null });
    }
  },

  clearError: () => set({ error: null }),
}));
