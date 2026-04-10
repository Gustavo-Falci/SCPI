import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';

/**
 * Um wrapper de armazenamento multiplataforma que usa SecureStore em nativo
 * e localStorage na web. Fornece uma API assíncrona consistente.
 */
export const storage = {
  async setItem(key, value) {
    if (Platform.OS === 'web') {
      try {
        localStorage.setItem(key, value);
      } catch (e) {
        console.error('Failed to save to localStorage', e);
      }
    } else {
      await SecureStore.setItemAsync(key, value);
    }
  },

  async getItem(key) {
    if (Platform.OS === 'web') {
      try {
        return localStorage.getItem(key);
      } catch (e) {
        console.error('Failed to get from localStorage', e);
        return null;
      }
    } else {
      return await SecureStore.getItemAsync(key);
    }
  },

  async removeItem(key) {
    if (Platform.OS === 'web') {
      try {
        localStorage.removeItem(key);
      } catch (e) {
        console.error('Failed to remove from localStorage', e);
      }
    } else {
      await SecureStore.deleteItemAsync(key);
    }
  }
};
