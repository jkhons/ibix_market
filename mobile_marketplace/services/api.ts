import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from 'axios';
import ENV from '@/constants/config';
import { secureStorage } from '@/utils/storage';
import { STORAGE_KEYS } from '@/constants/config';

let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (err: unknown) => void;
}> = [];

function processQueue(error: unknown, token: string | null) {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error);
    else if (token) resolve(token);
  });
  failedQueue = [];
}

function createApiClient(): AxiosInstance {
  const client = axios.create({
    baseURL: ENV.API_BASE_URL,
    timeout: 15000,
    headers: {
      'Content-Type': 'application/json',
      'X-Client': 'mobile',
      'X-Client-Version': '1.0.0',
    },
  });

  client.interceptors.request.use(async (config: InternalAxiosRequestConfig) => {
    const token = await secureStorage.get(STORAGE_KEYS.ACCESS_TOKEN);
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  });

  client.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
      const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

      if (error.response?.status === 401 && !originalRequest._retry) {
        if (isRefreshing) {
          return new Promise((resolve, reject) => {
            failedQueue.push({
              resolve: (token: string) => {
                if (originalRequest.headers) {
                  originalRequest.headers.Authorization = `Bearer ${token}`;
                }
                resolve(client(originalRequest));
              },
              reject,
            });
          });
        }

        originalRequest._retry = true;
        isRefreshing = true;

        try {
          const refreshToken = await secureStorage.get(STORAGE_KEYS.REFRESH_TOKEN);
          if (!refreshToken) throw new Error('No refresh token');

          const { data } = await axios.post(`${ENV.API_BASE_URL}/loja/refresh-token`, {
            refresh_token: refreshToken,
          });

          const newAccess = data.access_token;
          const newRefresh = data.refresh_token;

          await secureStorage.set(STORAGE_KEYS.ACCESS_TOKEN, newAccess);
          if (newRefresh) {
            await secureStorage.set(STORAGE_KEYS.REFRESH_TOKEN, newRefresh);
          }

          processQueue(null, newAccess);

          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${newAccess}`;
          }
          return client(originalRequest);
        } catch (refreshError) {
          processQueue(refreshError, null);
          await secureStorage.remove(STORAGE_KEYS.ACCESS_TOKEN);
          await secureStorage.remove(STORAGE_KEYS.REFRESH_TOKEN);
          await secureStorage.remove(STORAGE_KEYS.CONSUMER_ID);
          return Promise.reject(refreshError);
        } finally {
          isRefreshing = false;
        }
      }

      return Promise.reject(error);
    },
  );

  return client;
}

export const api = createApiClient();

export type ApiError = {
  detail?: string | { detail?: string; code?: string };
  code?: string;
};

export function extractApiError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as ApiError | undefined;
    if (typeof data?.detail === 'string') return data.detail;
    if (typeof data?.detail === 'object' && data.detail?.detail) return data.detail.detail;
    if (error.response?.status === 429) return 'Muitas tentativas. Aguarde e tente novamente.';
    if (error.response?.status === 500) return 'Erro interno. Tente novamente mais tarde.';
    if (!error.response) return 'Sem conexão. Verifique sua internet.';
  }
  return 'Ocorreu um erro. Tente novamente.';
}
