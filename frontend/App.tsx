import React, { useEffect } from 'react';
import { StatusBar } from 'expo-status-bar';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import AppNavigator from './src/navigation/AppNavigator';
import { useThemeStore } from './src/store/themeStore';

// Initialize React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

export default function App() {
  const { loadTheme, theme } = useThemeStore();

  useEffect(() => {
    loadTheme();
  }, []);

  return (
    <SafeAreaProvider style={{ flex: 1 }}>
      <QueryClientProvider client={queryClient}>
        <AppNavigator />
        <StatusBar style={theme === 'dark' ? 'light' : 'dark'} />
      </QueryClientProvider>
    </SafeAreaProvider>
  );
}

