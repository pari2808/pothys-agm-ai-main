import React, { useEffect } from 'react';
import { View, ActivityIndicator, StyleSheet, Text } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import { useAuthStore } from '../store/authStore';
import { useThemeStore } from '../store/themeStore';
import AuthNavigator from './AuthNavigator';
import AGMNavigator from './AGMNavigator';
import ManagerNavigator from './ManagerNavigator';
import { AuthErrorBoundary } from '../components/AuthErrorBoundary';

export default function AppNavigator() {
  const { isAuthenticated, user, isLoading, hasAgm, checkAuthStatus } = useAuthStore();
  const { colors } = useThemeStore();

  // Validate session status on startup
  useEffect(() => {
    checkAuthStatus();
  }, []);

  if (isLoading) {
    return (
      <View style={[styles.splashContainer, { backgroundColor: colors.background }]}>
        <ActivityIndicator color={colors.primary} size="large" />
        <Text style={[styles.splashText, { color: colors.primary }]}>Authenticating Secure Link...</Text>
      </View>
    );
  }

  return (
    <NavigationContainer>
      <AuthErrorBoundary>
        {!isAuthenticated ? (
          <AuthNavigator />
        ) : user?.role === 'AGM' ? (
          <AGMNavigator />
        ) : (
          <ManagerNavigator />
        )}
      </AuthErrorBoundary>
    </NavigationContainer>
  );
}


const styles = StyleSheet.create({
  splashContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  splashText: {
    fontSize: 14,
    marginTop: 16,
    fontWeight: '600',
    letterSpacing: 1.5,
    textTransform: 'uppercase',
  },
});

