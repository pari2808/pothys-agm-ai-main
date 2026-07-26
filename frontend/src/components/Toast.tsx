import React, { useEffect, useRef } from 'react';
import {
  StyleSheet,
  Text,
  View,
  Animated,
  TouchableOpacity,
  Platform,
} from 'react-native';
import { useThemeStore } from '../store/themeStore';

export interface ToastProps {
  visible: boolean;
  message: string;
  type?: 'error' | 'warning' | 'info' | 'success';
  onDismiss?: () => void;
  duration?: number;
}

export default function Toast({
  visible,
  message,
  type = 'error',
  onDismiss,
  duration = 3500,
}: ToastProps) {
  const { colors } = useThemeStore();
  const translateY = useRef(new Animated.Value(60)).current;
  const opacity = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    if (visible) {
      Animated.parallel([
        Animated.timing(translateY, {
          toValue: 0,
          duration: 300,
          useNativeDriver: true,
        }),
        Animated.timing(opacity, {
          toValue: 1,
          duration: 300,
          useNativeDriver: true,
        }),
      ]).start();

      if (duration > 0 && onDismiss) {
        timer = setTimeout(() => {
          dismissToast();
        }, duration);
      }
    } else {
      dismissToast();
    }

    return () => {
      if (timer) clearTimeout(timer);
    };
  }, [visible]);

  const dismissToast = () => {
    Animated.parallel([
      Animated.timing(translateY, {
        toValue: 60,
        duration: 250,
        useNativeDriver: true,
      }),
      Animated.timing(opacity, {
        toValue: 0,
        duration: 250,
        useNativeDriver: true,
      }),
    ]).start(() => {
      if (onDismiss && visible) {
        onDismiss();
      }
    });
  };

  if (!visible) return null;

  const getAccentColor = () => {
    switch (type) {
      case 'error':
        return colors.error || '#EF4444';
      case 'warning':
        return colors.warning || '#F59E0B';
      case 'success':
        return colors.success || '#10B981';
      default:
        return colors.primary || '#D4AF37';
    }
  };

  const getIcon = () => {
    switch (type) {
      case 'error':
      case 'warning':
        return '⚠️';
      case 'success':
        return '✅';
      default:
        return 'ℹ️';
    }
  };

  const accentColor = getAccentColor();

  return (
    <Animated.View
      style={[
        styles.toastContainer,
        {
          backgroundColor: colors.surfaceAlt || '#1A1A22',
          borderColor: accentColor,
          opacity: opacity,
          transform: [{ translateY: translateY }],
        },
      ]}
      pointerEvents="box-none"
    >
      <View style={styles.toastContent}>
        <Text style={styles.toastIcon}>{getIcon()}</Text>
        <Text style={[styles.toastText, { color: colors.text || '#F5F5F7' }]} numberOfLines={2}>
          {message}
        </Text>
        {onDismiss && (
          <TouchableOpacity
            style={styles.closeBtn}
            onPress={dismissToast}
            hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
          >
            <Text style={[styles.closeBtnText, { color: colors.textMuted || '#8E8E93' }]}>✕</Text>
          </TouchableOpacity>
        )}
      </View>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  toastContainer: {
    position: 'absolute',
    bottom: Platform.OS === 'ios' ? 40 : 24,
    left: 20,
    right: 20,
    borderWidth: 1.5,
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 12,
    zIndex: 9999,
    elevation: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
  },
  toastContent: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  toastIcon: {
    fontSize: 16,
    marginRight: 10,
  },
  toastText: {
    flex: 1,
    fontSize: 14,
    fontWeight: '500',
  },
  closeBtn: {
    marginLeft: 10,
    padding: 4,
  },
  closeBtnText: {
    fontSize: 14,
    fontWeight: 'bold',
  },
});
