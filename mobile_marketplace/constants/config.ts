import Constants from 'expo-constants';

const extra = Constants.expoConfig?.extra ?? {};

const ENV = {
  API_BASE_URL: extra.API_BASE_URL ?? process.env.EXPO_PUBLIC_API_BASE_URL ?? 'http://localhost:8000/api/v1',
  WS_BASE_URL: extra.WS_BASE_URL ?? process.env.EXPO_PUBLIC_WS_BASE_URL ?? 'ws://localhost:8000',
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
