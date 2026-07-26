import React from 'react';
import { createStackNavigator } from '@react-navigation/stack';
import { COLORS } from '../theme/colors';

import RoleSelectionScreen from '../screens/auth/RoleSelectionScreen';
import LoginScreen          from '../screens/auth/LoginScreen';
import ManagerLoginScreen   from '../screens/auth/ManagerLoginScreen';
import ForgotPasswordScreen from '../screens/auth/ForgotPasswordScreen';
import ResetPasswordScreen  from '../screens/auth/ResetPasswordScreen';
import ExecutiveSetupScreen from '../screens/auth/ExecutiveSetupScreen';

export type AuthStackParamList = {
  RoleSelection: undefined;
  AGMLogin:      undefined;
  ManagerLogin:  undefined;
  ForgotPassword: undefined;
  ResetPassword:  { email: string; token: string };
  ExecutiveSetup: undefined;
};

const Stack = createStackNavigator<AuthStackParamList>();

export default function AuthNavigator() {
  return (
    <Stack.Navigator
      initialRouteName="RoleSelection"
      screenOptions={{
        headerShown: false,
        cardStyle: { flex: 1, backgroundColor: COLORS.background },
        // Smooth horizontal slide transitions
        cardStyleInterpolator: ({ current, layouts }) => ({
          cardStyle: {
            opacity: current.progress,
            transform: [
              {
                translateX: current.progress.interpolate({
                  inputRange:  [0, 1],
                  outputRange: [layouts.screen.width * 0.08, 0],
                }),
              },
            ],
          },
        }),
      }}
    >
      <Stack.Screen name="RoleSelection"  component={RoleSelectionScreen} />
      <Stack.Screen name="AGMLogin"       component={LoginScreen} />
      <Stack.Screen name="ManagerLogin"   component={ManagerLoginScreen} />
      <Stack.Screen name="ForgotPassword" component={ForgotPasswordScreen} />
      <Stack.Screen name="ResetPassword"  component={ResetPasswordScreen} />
      <Stack.Screen name="ExecutiveSetup" component={ExecutiveSetupScreen} />
    </Stack.Navigator>
  );
}
