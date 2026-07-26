import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

const ACCESS_TOKEN_KEY = 'pothys_access_token';
const REFRESH_TOKEN_KEY = 'pothys_refresh_token';

const isWeb = Platform.OS === 'web';

export async function saveAccessToken(token: string): Promise<void> {
  if (isWeb) {
    localStorage.setItem(ACCESS_TOKEN_KEY, token);
  } else {
    await SecureStore.setItemAsync(ACCESS_TOKEN_KEY, token);
  }
}

export async function saveRefreshToken(token: string): Promise<void> {
  if (isWeb) {
    localStorage.setItem(REFRESH_TOKEN_KEY, token);
  } else {
    await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, token);
  }
}

export async function getAccessToken(): Promise<string | null> {
  if (isWeb) {
    return localStorage.getItem(ACCESS_TOKEN_KEY);
  }
  try {
    return await SecureStore.getItemAsync(ACCESS_TOKEN_KEY);
  } catch (error) {
    console.error('Error reading access token from SecureStore:', error);
    return null;
  }
}

export async function getRefreshToken(): Promise<string | null> {
  if (isWeb) {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  }
  try {
    return await SecureStore.getItemAsync(REFRESH_TOKEN_KEY);
  } catch (error) {
    console.error('Error reading refresh token from SecureStore:', error);
    return null;
  }
}

export async function clearTokens(): Promise<void> {
  if (isWeb) {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  } else {
    try {
      await SecureStore.deleteItemAsync(ACCESS_TOKEN_KEY);
      await SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY);
    } catch (error) {
      console.error('Error clearing tokens from SecureStore:', error);
    }
  }
}
