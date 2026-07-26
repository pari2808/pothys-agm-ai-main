import { create } from 'zustand';
import { Platform } from 'react-native';

const THEME_KEY = 'pothys_theme';
const isWeb = Platform.OS === 'web';

export const THEME_COLORS = {
  dark: {
    primary: '#D4AF37',       // Metallic Gold
    primaryPressed: '#B3922E',// Darkened Gold for active states
    background: '#0B0B0E',    // Deep Rich Black
    surface: '#121217',       // Dark Charcoal Card Background
    surfaceAlt: '#1A1A22',    // Subtle Raised Charcoal Area
    border: '#22222E',        // Thin separator border grid
    borderFocused: '#3E3E50', // Highlighted border grid
    success: '#10B981',       // Factual/Submitted Emerald
    successBg: 'rgba(16, 185, 129, 0.1)',
    error: '#EF4444',         // Warning/Alert Rose
    errorBg: 'rgba(239, 68, 68, 0.1)',
    warning: '#F59E0B',       // Amber Alert
    warningBg: 'rgba(245, 158, 11, 0.1)',
    info: '#3B82F6',          // Cobalt Blue Accent
    infoBg: 'rgba(59, 130, 246, 0.1)',
    text: '#F5F5F7',          // High contrast bright silver white
    textSecondary: '#D1D5DB', // Bright readable silver white for labels/titles
    textMuted: '#A1A1AA',     // Clear readable light slate for subtext/meta
    textOnPrimary: '#0B0B0E', // High-contrast black on brand gold
  },
  light: {
    primary: '#D4AF37',       // Metallic Gold
    primaryPressed: '#B3922E',// Darkened Gold
    background: '#F8F9FA',    // Clean soft gray background
    surface: '#FFFFFF',       // Pure white cards
    surfaceAlt: '#F1F3F5',    // Light gray secondary areas
    border: '#E9ECEF',        // Light gray border
    borderFocused: '#CED4DA', // Focused state border
    success: '#10B981',
    successBg: 'rgba(16, 185, 129, 0.1)',
    error: '#EF4444',
    errorBg: 'rgba(239, 68, 68, 0.1)',
    warning: '#F59E0B',
    warningBg: 'rgba(245, 158, 11, 0.1)',
    info: '#3B82F6',
    infoBg: 'rgba(59, 130, 246, 0.1)',
    text: '#1A1A1E',          // Dark slate text
    textSecondary: '#6C757D', // Muted slate text
    textMuted: '#ADB5BD',     // Light gray placeholder/muted text
    textOnPrimary: '#FFFFFF', // High-contrast white text on gold
  }
};

interface ThemeState {
  theme: 'dark' | 'light';
  colors: typeof THEME_COLORS.dark;
  toggleTheme: () => void;
  loadTheme: () => Promise<void>;
}

export const useThemeStore = create<ThemeState>((set) => ({
  theme: 'dark',
  colors: THEME_COLORS.dark,
  toggleTheme: () => {
    set((state) => {
      const nextTheme = state.theme === 'dark' ? 'light' : 'dark';
      if (isWeb) {
        try {
          localStorage.setItem(THEME_KEY, nextTheme);
        } catch (e) {
          console.warn(e);
        }
      } else {
        // Safe import/call for native SecureStore to avoid Web bundling/runtime crashes
        import('expo-secure-store').then((SecureStore) => {
          SecureStore.setItemAsync(THEME_KEY, nextTheme).catch(() => {});
        }).catch(() => {});
      }
      return {
        theme: nextTheme,
        colors: THEME_COLORS[nextTheme],
      };
    });
  },
  loadTheme: async () => {
    let savedTheme: 'dark' | 'light' = 'dark';
    try {
      if (isWeb) {
        const val = localStorage.getItem(THEME_KEY);
        if (val === 'light' || val === 'dark') savedTheme = val;
      } else {
        const SecureStore = await import('expo-secure-store');
        const val = await SecureStore.getItemAsync(THEME_KEY);
        if (val === 'light' || val === 'dark') savedTheme = val;
      }
    } catch (e) {
      console.warn('Failed to load theme:', e);
    }
    set({
      theme: savedTheme,
      colors: THEME_COLORS[savedTheme],
    });
  },
}));
