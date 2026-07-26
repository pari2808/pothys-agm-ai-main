import axios from 'axios';
import { getAccessToken, getRefreshToken, saveAccessToken, clearTokens } from './secureStore';
import { useAuthStore, API_BASE_URL } from '../store/authStore';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor: inject Bearer Token on outgoing queries
apiClient.interceptors.request.use(
  async (config) => {
    // Check Zustand state first
    let token = useAuthStore.getState().token;
    if (!token) {
      // Fallback: Fetch from keychain
      token = await getAccessToken();
    }
    
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Interceptor: silently capture 401 Unauthorized errors and attempt token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    // Check if error is 401 and request has not already been retried
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      try {
        const refreshToken = await getRefreshToken();
        if (refreshToken) {
          // Request a new access token
          const refreshRes = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          });
          const { access_token } = refreshRes.data;
          
          // Save and update state
          await saveAccessToken(access_token);
          useAuthStore.setState({ token: access_token });
          
          // Retry original request with new header
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return apiClient(originalRequest);
        }
      } catch (refreshError) {
        console.error('Session refresh failed, logging out user:', refreshError);
        // Logout user globally
        await clearTokens();
        useAuthStore.setState({
          user: null,
          token: null,
          isAuthenticated: false,
        });
      }
    }
    return Promise.reject(error);
  }
);

export default apiClient;
