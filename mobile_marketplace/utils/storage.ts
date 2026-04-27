import * as SecureStore from 'expo-secure-store';
import { MMKV } from 'react-native-mmkv';

export const mmkv = new MMKV({ id: 'ibix-market' });

export const secureStorage = {
  async set(key: string, value: string): Promise<void> {
    await SecureStore.setItemAsync(key, value);
  },

  async get(key: string): Promise<string | null> {
    return SecureStore.getItemAsync(key);
  },

  async remove(key: string): Promise<void> {
    await SecureStore.deleteItemAsync(key);
  },
};

export const fastStorage = {
  set(key: string, value: string): void {
    mmkv.set(key, value);
  },

  get(key: string): string | undefined {
    return mmkv.getString(key);
  },

  setObject<T>(key: string, value: T): void {
    mmkv.set(key, JSON.stringify(value));
  },

  getObject<T>(key: string): T | null {
    const raw = mmkv.getString(key);
    if (!raw) return null;
    try {
      return JSON.parse(raw) as T;
    } catch {
      return null;
    }
  },

  remove(key: string): void {
    mmkv.delete(key);
  },

  clearAll(): void {
    mmkv.clearAll();
  },
};
