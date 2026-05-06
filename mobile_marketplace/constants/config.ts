import Constants from 'expo-constants';
import { Platform } from 'react-native';

const extra = Constants.expoConfig?.extra ?? {};

/** Padrão alinha com testers (API pública). Para backend local, defina EXPO_PUBLIC_* no `.env`. */
const rawApiBaseUrl =
  extra.API_BASE_URL ??
  process.env.EXPO_PUBLIC_API_BASE_URL ??
  'https://www.ibix.com.br/api/v1';

/**
 * Origem do site (sem `/api/v1`) para resolver paths relativos `/static/...` da API.
 * No Web dev o app roda em localhost mas as imagens ficam no domínio público — sem isso o browser pede `localhost/static/...` e falha.
 */
function derivePublicSiteOrigin(rawApiBase: string): string {
  const b = rawApiBase.trim().replace(/\/+$/, '');
  if (/^https?:\/\//i.test(b)) {
    const lower = b.toLowerCase();
    const marker = '/api/v1';
    const idx = lower.lastIndexOf(marker);
    if (idx !== -1 && idx + marker.length === lower.length) {
      return b.slice(0, idx).replace(/\/+$/, '') || b;
    }
    return b;
  }
  const envOrigin =
    (typeof process.env.EXPO_PUBLIC_ASSET_ORIGIN === 'string' && process.env.EXPO_PUBLIC_ASSET_ORIGIN.trim()) ||
    (typeof extra.ASSET_ORIGIN === 'string' && extra.ASSET_ORIGIN.trim());
  if (envOrigin) return envOrigin.replace(/\/+$/, '');
  return 'https://www.ibix.com.br';
}

/** Base absoluta para mídias relativas retornadas pela API (ex.: `/static/uploads/...`). */
export const PUBLIC_SITE_ORIGIN = derivePublicSiteOrigin(rawApiBaseUrl);

/** Converte URI da API em URL absoluta utilizável no browser e nos builds nativos. */
export function resolveRemoteAssetUrl(uri: string | null | undefined): string | undefined {
  if (uri == null || typeof uri !== 'string') return undefined;
  const u = uri.trim();
  if (!u) return undefined;
  if (/^https?:\/\//i.test(u)) return u;
  if (u.startsWith('//')) return `https:${u}`;
  const path = u.startsWith('/') ? u : `/${u}`;
  return `${PUBLIC_SITE_ORIGIN}${path}`;
}

const rawWsBaseUrl =
  extra.WS_BASE_URL ?? process.env.EXPO_PUBLIC_WS_BASE_URL ?? 'wss://api.ibix.com.br';

/**
 * Web dev (browser) sofre CORS ao chamar `https://www.ibix.com.br/api/v1` direto.
 * Em dev, preferimos proxy no Metro: `/<prefix>/api/v1` no mesmo origin do dev server.
 *
 * Para desativar explicitamente: EXPO_PUBLIC_DISABLE_WEB_PROXY=true
 */
const useWebProxy =
  __DEV__ && Platform.OS === 'web' && process.env.EXPO_PUBLIC_DISABLE_WEB_PROXY !== 'true';

const ENV = {
  API_BASE_URL: useWebProxy ? '/__ibix_api/api/v1' : rawApiBaseUrl,
  WS_BASE_URL: rawWsBaseUrl,
  SENTRY_DSN: extra.SENTRY_DSN ?? process.env.EXPO_PUBLIC_SENTRY_DSN ?? '',
  GOOGLE_WEB_CLIENT_ID: extra.GOOGLE_WEB_CLIENT_ID ?? process.env.EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID ?? '',
  GOOGLE_IOS_CLIENT_ID: extra.GOOGLE_IOS_CLIENT_ID ?? process.env.EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID ?? '',
  GOOGLE_ANDROID_CLIENT_ID: extra.GOOGLE_ANDROID_CLIENT_ID ?? process.env.EXPO_PUBLIC_GOOGLE_ANDROID_CLIENT_ID ?? '',
  APP_SCHEME: 'ibixmarket',
  MIN_APP_VERSION: '1.0.0',
  ENABLE_CERTIFICATE_PINNING: !__DEV__,
};

export default ENV;

export const QUERY_KEYS = {
  PRODUCTS: 'products',
  PRODUCT_DETAIL: 'product-detail',
  PRODUCT_REVIEWS: 'product-reviews',
  PRODUCT_SIMILAR: 'product-similar',
  CATEGORIES: 'categories',
  STORES: 'stores',
  STORE_DETAIL: 'store-detail',
  STORE_PRODUCTS: 'store-products',
  CART: 'cart',
  ORDERS: 'orders',
  ORDER_DETAIL: 'order-detail',
  FAVORITES: 'favorites',
  NOTIFICATIONS: 'notifications',
  UNREAD_COUNT: 'unread-count',
  ADDRESSES: 'addresses',
  CONVERSATIONS: 'conversations',
  MESSAGES: 'messages',
  SEARCH: 'search',
  AUTOCOMPLETE: 'autocomplete',
  POPULAR_TERMS: 'popular-terms',
  INSTALLMENTS: 'installments',
  COUPONS: 'coupons',
  APP_VERSION: 'app-version',
  CONSUMER_PROFILE: 'consumer-profile',
  CONSENT: 'consent',
  VITRINE_HOME: 'vitrine-home',
  NEARBY_ADS: 'nearby-ads',
  NEARBY_CITIES: 'nearby-cities',
  NEARBY_BY_QUERY: 'nearby-by-query',
} as const;

export const STORAGE_KEYS = {
  ACCESS_TOKEN: 'ibix_access_token',
  REFRESH_TOKEN: 'ibix_refresh_token',
  CONSUMER_ID: 'ibix_consumer_id',
  BIOMETRIC_ENABLED: 'ibix_biometric',
  ONBOARDING_DONE: 'ibix_onboarding_done',
  DARK_MODE_PREFERENCE: 'ibix_dark_mode',
  RECENT_SEARCHES: 'ibix_recent_searches',
  RECENTLY_VIEWED: 'ibix_recently_viewed',
  CART_ITEMS: 'ibix_cart_items',
  PUSH_PERMISSION_ASKED: 'ibix_push_asked',
  LGPD_CONSENT: 'ibix_lgpd_consent',
  GEO_LOCATION: 'ibix_geo_location',
  GEO_PERMISSION_ASKED: 'ibix_geo_asked',
} as const;

export const ANIMATION_DURATION = {
  FAST: 150,
  NORMAL: 250,
  SLOW: 400,
} as const;

export const PAGINATION = {
  DEFAULT_PAGE_SIZE: 20,
  PRODUCT_PAGE_SIZE: 20,
  ORDER_PAGE_SIZE: 15,
  MESSAGE_PAGE_SIZE: 30,
  NOTIFICATION_PAGE_SIZE: 20,
} as const;
