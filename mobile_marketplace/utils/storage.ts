import * as SecureStore from 'expo-secure-store';
import { MMKV } from 'react-native-mmkv';
import { Platform } from 'react-native';

const isWeb = Platform.OS === 'web';

function safeLocalStorage() {
  try {
    if (typeof window === 'undefined') return null;
    return window.localStorage ?? null;
  } catch {
    return null;
  }
}

function canUseSecureStore() {
  // SecureStore (e keychain/keystore) não é confiável no Web.
  return !isWeb;
}

function canUseMMKV() {
  // MMKV usa storage nativo; no Web pode falhar/importar mas não funcionar.
  return !isWeb;
}

export const mmkv = canUseMMKV() ? new MMKV({ id: 'ibix-market' }) : null;

export const secureStorage = {
  async set(key: string, value: string): Promise<void> {
    if (canUseSecureStore()) {
      await SecureStore.setItemAsync(key, value);
      return;
    }
    const ls = safeLocalStorage();
    if (ls) ls.setItem(key, value);
  },

  async get(key: string): Promise<string | null> {
    if (canUseSecureStore()) {
      return SecureStore.getItemAsync(key);
    }
    const ls = safeLocalStorage();
    return ls ? ls.getItem(key) : null;
  },

  async remove(key: string): Promise<void> {
    if (canUseSecureStore()) {
      await SecureStore.deleteItemAsync(key);
      return;
    }
    const ls = safeLocalStorage();
    if (ls) ls.removeItem(key);
  },
};

export const fastStorage = {
  set(key: string, value: string): void {
    if (mmkv) {
      mmkv.set(key, value);
      return;
    }
    const ls = safeLocalStorage();
    if (ls) ls.setItem(key, value);
  },

  get(key: string): string | undefined {
    if (mmkv) return mmkv.getString(key) ?? undefined;
    const ls = safeLocalStorage();
    return ls ? ls.getItem(key) ?? undefined : undefined;
  },

  setObject<T>(key: string, value: T): void {
    const raw = JSON.stringify(value);
    if (mmkv) {
      mmkv.set(key, raw);
      return;
    }
    const ls = safeLocalStorage();
    if (ls) ls.setItem(key, raw);
  },

  getObject<T>(key: string): T | null {
    const raw = mmkv ? mmkv.getString(key) : safeLocalStorage()?.getItem(key) ?? null;
    if (!raw) return null;
    try {
      return JSON.parse(raw) as T;
    } catch {
      return null;
    }
  },

  remove(key: string): void {
    if (mmkv) {
      mmkv.delete(key);
      return;
    }
    const ls = safeLocalStorage();
    if (ls) ls.removeItem(key);
  },

  clearAll(): void {
    if (mmkv) {
      mmkv.clearAll();
      return;
    }
    const ls = safeLocalStorage();
    if (ls) ls.clear();
  },
};
