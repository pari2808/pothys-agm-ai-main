import { create } from 'zustand';
import axios from 'axios';
import { getAccessToken, getRefreshToken, saveAccessToken, saveRefreshToken, clearTokens } from '../services/secureStore';

import { Platform } from 'react-native';

// Dev API base url (10.0.2.2 resolves to host localhost inside Android emulator, localhost for iOS/web)
export const API_BASE_URL = Platform.OS === 'android'
  ? 'http://10.0.2.2:8000/api/v1'
  : 'http://localhost:8000/api/v1';

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  role: 'AGM' | 'MANAGER';
  branch_id: string | null;
  branch_name: string | null;
  created_at: string;
}

interface AuthState {
  user: UserProfile | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  loginLoading: boolean;
  
  hasAgm: boolean | null;
  setupLoading: boolean;
  setupError: string | null;

  forgotPasswordLoading: boolean;
  forgotPasswordSuccess: boolean;
  forgotPasswordError: string | null;

  resetPasswordLoading: boolean;
  resetPasswordSuccess: boolean;
  resetPasswordError: string | null;

  login: (email: string, password: string) => Promise<boolean>;
  logout: () => Promise<void>;
  checkAuthStatus: () => Promise<void>;
  setupExecutive: (fullName: string, email: string, password: string) => Promise<boolean>;
  forgotPassword: (email: string) => Promise<boolean>;
  resetPassword: (email: string, token: string, newPassword: string) => Promise<boolean>;
}

// Parses backend errors and validation issues into clean user-friendly strings
function parseValidationError(err: any): string {
  if (err.response?.data) {
    const data = err.response.data;
    if (data.detail) {
      const detail = data.detail;
      if (Array.isArray(detail)) {
        // FastAPI / Pydantic validation error array
        return detail.map((d: any) => {
          const field = d.loc && d.loc.length > 1 ? d.loc[1] : '';
          const rawMsg = d.msg || 'invalid value';
          const fieldName = field ? field.charAt(0).toUpperCase() + field.slice(1) : '';
          
          if (rawMsg.includes('value is not a valid email')) {
            return 'Invalid email address';
          }
          if (rawMsg.includes('field required')) {
            return `${fieldName || 'Field'} is required`;
          }
          return fieldName ? `${fieldName}: ${rawMsg}` : rawMsg;
        }).join(', ');
      }
      if (typeof detail === 'string') {
        return detail;
      }
    }
  }
  return err.response?.data?.message || err.message || 'An unexpected connection error occurred';
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  token: null,
  isAuthenticated: false,
  isLoading: true,
  error: null,
  loginLoading: false,
  
  hasAgm: null,
  setupLoading: false,
  setupError: null,

  forgotPasswordLoading: false,
  forgotPasswordSuccess: false,
  forgotPasswordError: null,

  resetPasswordLoading: false,
  resetPasswordSuccess: false,
  resetPasswordError: null,

  login: async (email, password) => {
    set({ loginLoading: true, error: null });
    try {
      const response = await axios.post(`${API_BASE_URL}/auth/login`, { email, password });
      const { access_token, refresh_token } = response.data;
      
      await saveAccessToken(access_token);
      await saveRefreshToken(refresh_token);
      
      const meResponse = await axios.get(`${API_BASE_URL}/auth/me`, {
        headers: { Authorization: `Bearer ${access_token}` }
      });
      
      set({
        user: meResponse.data,
        token: access_token,
        isAuthenticated: true,
        hasAgm: true,
        loginLoading: false
      });
      return true;
    } catch (err: any) {
      const msg = parseValidationError(err);
      set({ error: msg, loginLoading: false });
      return false;
    }
  },

  logout: async () => {
    set({ isLoading: true });
    await clearTokens();
    set({
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
      forgotPasswordSuccess: false,
      resetPasswordSuccess: false
    });
  },

  checkAuthStatus: async () => {
    set({ isLoading: true });
    try {
      // First check setup status
      const statusResponse = await axios.get(`${API_BASE_URL}/auth/setup-status`);
      const { has_agm } = statusResponse.data;
      set({
        hasAgm: has_agm,
        isAuthenticated: false, // Always start unauthenticated on launch to show Role Selection
        user: null,
        token: null,
        isLoading: false
      });
    } catch (err) {
      set({
        hasAgm: null,
        isAuthenticated: false,
        isLoading: false
      });
    }
  },

  setupExecutive: async (fullName, email, password) => {
    set({ setupLoading: true, setupError: null });
    try {
      const response = await axios.post(`${API_BASE_URL}/auth/setup`, {
        full_name: fullName,
        email,
        password
      });
      const { access_token, refresh_token } = response.data;
      
      await saveAccessToken(access_token);
      await saveRefreshToken(refresh_token);
      
      const meResponse = await axios.get(`${API_BASE_URL}/auth/me`, {
        headers: { Authorization: `Bearer ${access_token}` }
      });
      
      set({
        user: meResponse.data,
        token: access_token,
        isAuthenticated: true,
        hasAgm: true,
        setupLoading: false
      });
      return true;
    } catch (err: any) {
      const msg = parseValidationError(err);
      set({ setupError: msg, setupLoading: false });
      return false;
    }
  },

  forgotPassword: async (email) => {
    set({ forgotPasswordLoading: true, forgotPasswordError: null, forgotPasswordSuccess: false });
    try {
      await axios.post(`${API_BASE_URL}/auth/forgot-password`, { email });
      set({ forgotPasswordLoading: false, forgotPasswordSuccess: true });
      return true;
    } catch (err: any) {
      const msg = parseValidationError(err);
      set({ forgotPasswordError: msg, forgotPasswordLoading: false, forgotPasswordSuccess: false });
      return false;
    }
  },

  resetPassword: async (email, token, newPassword) => {
    set({ resetPasswordLoading: true, resetPasswordError: null, resetPasswordSuccess: false });
    try {
      await axios.post(`${API_BASE_URL}/auth/reset-password`, {
        email,
        token,
        new_password: newPassword
      });
      set({ resetPasswordLoading: false, resetPasswordSuccess: true });
      return true;
    } catch (err: any) {
      const msg = parseValidationError(err);
      set({ resetPasswordError: msg, resetPasswordLoading: false, resetPasswordSuccess: false });
      return false;
    }
  }
}));
