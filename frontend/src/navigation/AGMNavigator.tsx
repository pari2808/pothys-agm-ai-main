import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
} from 'react-native';
import { createStackNavigator } from '@react-navigation/stack';
import AGMDashboardScreen from '../screens/agm/AGMDashboardScreen';
import AICopilotScreen from '../screens/agm/AICopilotScreen';
import BranchOperationsScreen from '../screens/agm/BranchOperationsScreen';
import BranchDetailScreen from '../screens/agm/BranchDetailScreen';
import NotificationCenterScreen from '../screens/agm/NotificationCenterScreen';
import { useThemeStore } from '../store/themeStore';

const Stack = createStackNavigator();

export default function AGMNavigator() {
  const { colors } = useThemeStore();

  return (
    <Stack.Navigator
      screenOptions={{
        headerStyle: {
          backgroundColor: colors.surface,
          borderBottomWidth: 1,
          borderColor: colors.border,
          elevation: 0,
          shadowOpacity: 0,
        },
        headerTintColor: colors.primary,
        headerTitleStyle: {
          fontWeight: '700',
          fontSize: 16,
          color: colors.text,
        },
        headerBackTitleVisible: false,
        cardStyle: { flex: 1, backgroundColor: colors.background },
        // Smooth slide transition
        cardStyleInterpolator: ({ current, layouts }: any) => ({
          cardStyle: {
            transform: [
              {
                translateX: current.progress.interpolate({
                  inputRange: [0, 1],
                  outputRange: [layouts.screen.width, 0],
                }),
              },
            ],
            opacity: current.progress.interpolate({
              inputRange: [0, 0.5, 1],
              outputRange: [0, 0.8, 1],
            }),
          },
        }),
      } as any}
    >
      <Stack.Screen
        name="AGMDashboard"
        component={AGMDashboardScreen}
        options={{ headerShown: false }}
      />
      <Stack.Screen
        name="BranchOperations"
        component={BranchOperationsScreen}
        options={{
          title: 'Branch Operations',
          headerLeft: ({ onPress }) => (
            <TouchableOpacity onPress={onPress} style={styles.backBtn}>
              <Text style={[styles.backBtnText, { color: colors.primary }]}>‹</Text>
            </TouchableOpacity>
          ),
        }}
      />
      <Stack.Screen
        name="BranchDetail"
        component={BranchDetailScreen}
        options={({ route }: any) => ({
          title: route.params?.branch
            ? route.params.branch.name.replace(/Swarna\s+Mahal/i, '').trim()
            : 'Branch Detail',
          headerLeft: ({ onPress }) => (
            <TouchableOpacity onPress={onPress} style={styles.backBtn}>
              <Text style={[styles.backBtnText, { color: colors.primary }]}>‹</Text>
            </TouchableOpacity>
          ),
        })}
      />
      <Stack.Screen
        name="AICopilot"
        component={AICopilotScreen}
        options={{
          title: 'AI Copilot',
          headerLeft: ({ onPress }) => (
            <TouchableOpacity onPress={onPress} style={styles.backBtn}>
              <Text style={[styles.backBtnText, { color: colors.primary }]}>‹</Text>
            </TouchableOpacity>
          ),
          headerRight: () => (
            <View style={[styles.aiHeaderBadge, { backgroundColor: colors.primary + '18', borderColor: colors.primary + '40' }]}>
              <View style={[styles.aiHeaderDot, { backgroundColor: colors.primary }]} />
              <Text style={[styles.aiHeaderBadgeText, { color: colors.primary }]}>RAG Mode</Text>
            </View>
          ),
        }}
      />
      <Stack.Screen
        name="NotificationCenter"
        component={NotificationCenterScreen}
        options={{
          title: 'Notification Center',
          headerLeft: ({ onPress }) => (
            <TouchableOpacity onPress={onPress} style={styles.backBtn}>
              <Text style={[styles.backBtnText, { color: colors.primary }]}>‹</Text>
            </TouchableOpacity>
          ),
        }}
      />
    </Stack.Navigator>
  );
}

const styles = StyleSheet.create({
  backBtn: {
    paddingLeft: 16,
    paddingRight: 8,
    paddingVertical: 4,
  },
  backBtnText: {
    fontSize: 28,
    fontWeight: '300',
    lineHeight: 32,
  },
  aiHeaderBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    marginRight: 16,
    borderWidth: 1,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
    gap: 5,
  },
  aiHeaderDot: {
    width: 5,
    height: 5,
    borderRadius: 3,
  },
  aiHeaderBadgeText: {
    fontSize: 9,
    fontWeight: '700',
    letterSpacing: 1,
  },
});

