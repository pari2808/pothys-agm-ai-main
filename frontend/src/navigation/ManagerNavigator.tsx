import React from 'react';
import { createStackNavigator } from '@react-navigation/stack';
import { COLORS } from '../theme/colors';
import ManagerDashboardScreen from '../screens/manager/ManagerDashboardScreen';

export type ManagerStackParamList = {
  ManagerDashboard: undefined;
};

const Stack = createStackNavigator<ManagerStackParamList>();

export default function ManagerNavigator() {
  return (
    <Stack.Navigator
      screenOptions={{
        headerShown: false,
        cardStyle: { flex: 1, backgroundColor: COLORS.background },
      }}
    >
      <Stack.Screen
        name="ManagerDashboard"
        component={ManagerDashboardScreen}
      />
    </Stack.Navigator>
  );
}
