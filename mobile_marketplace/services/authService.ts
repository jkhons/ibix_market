import { api } from './api';

export interface LoginPayload {
  email: string;
  senha: string;
  loja_id?: number;
}

export interface CadastroPayload {
  nome: string;
  email: string;
  senha: string;
  telefone?: string;
  documento?: string;
  aceite_termos: boolean;
  loja_id?: number;
}

export type SocialProvider = 'google' | 'apple' | 'facebook';

export interface SocialLoginPayload {
  provider: SocialProvider;
  id_token?: string;
  access_token?: string;
  aceite_termos?: boolean;
  nome_fallback?: string;
}

export interface AppleSignInPayload {
  id_token: string;
  authorization_code?: string;
  nome?: string;
}

export interface SocialConfirmLinkPayload {
  link_token: string;
  senha?: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token?: string;
  token_type: string;
  consumidor?: {
    id: number;
    nome?: string;
    email?: string;
  };
}

export interface SocialAuthResponse {
  status: 'authenticated' | 'pending_link';
  access_token?: string;
  refresh_token?: string;
  token_type?: string;
  consumidor?: {
    id: number;
    nome?: string;
    email?: string;
  };
  link_token?: string;
  message?: string;
  requires_password?: boolean;
}

export interface ForgotPasswordPayload {
  email: string;
}

export interface SocialConfig {
  google_client_id: string | null;
  facebook_app_id: string | null;
  apple_client_id: string | null;
}

const authService = {
  async login(payload: LoginPayload): Promise<AuthResponse> {
    const { data } = await api.post<AuthResponse>('/loja/login', payload);
    return data;
  },

  async cadastro(payload: CadastroPayload): Promise<AuthResponse> {
    const { data } = await api.post<AuthResponse>('/loja/cadastro', payload);
    return data;
  },

  async getSocialConfig(): Promise<SocialConfig> {
    const { data } = await api.get<SocialConfig>('/loja/auth/social/config');
    return data;
  },

  async socialLogin(payload: SocialLoginPayload): Promise<SocialAuthResponse> {
    const { data } = await api.post<SocialAuthResponse>('/loja/auth/social/login', payload);
    return data;
  },

  async appleSignIn(payload: AppleSignInPayload): Promise<AuthResponse> {
    const { data } = await api.post<AuthResponse>('/loja/auth/social/apple', payload);
    return data;
  },

  async socialConfirmLink(payload: SocialConfirmLinkPayload): Promise<SocialAuthResponse> {
    const { data } = await api.post<SocialAuthResponse>('/loja/auth/social/confirm-link', payload);
    return data;
  },

  async forgotPassword(payload: ForgotPasswordPayload): Promise<{ detail: string }> {
    const { data } = await api.post<{ detail: string }>('/loja/forgot-password', payload);
    return data;
  },

  async refreshToken(refresh_token: string): Promise<AuthResponse> {
    const { data } = await api.post<AuthResponse>('/loja/refresh-token', { refresh_token });
    return data;
  },

  async logout(): Promise<void> {
    try {
      await api.post('/loja/logout');
    } catch {
      // best-effort
    }
  },
};

export default authService;
