import React, { useState, useEffect } from 'react';
import {
  StyleSheet,
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  ScrollView
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuthStore } from '../../store/authStore';
import { COLORS } from '../../theme/colors';

export default function ResetPasswordScreen({ route, navigation }: any) {
  const [email, setEmail] = useState('');
  const [token, setToken] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  // Inline error state variables
  const [emailError, setEmailError] = useState<string | null>(null);
  const [tokenError, setTokenError] = useState<string | null>(null);
  const [newPasswordError, setNewPasswordError] = useState<string | null>(null);
  const [confirmPasswordError, setConfirmPasswordError] = useState<string | null>(null);

  const { resetPassword, resetPasswordLoading, resetPasswordSuccess, resetPasswordError } = useAuthStore();

  // Prefill fields from route params or URL query params on Web
  useEffect(() => {
    const routeEmail = route?.params?.email || '';
    const routeToken = route?.params?.token || '';
    
    if (routeEmail) setEmail(routeEmail);
    if (routeToken) setToken(routeToken);

    if (Platform.OS === 'web' && typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const urlToken = params.get('token');
      const urlEmail = params.get('email');
      if (urlToken) setToken(urlToken);
      if (urlEmail) setEmail(urlEmail);
    }
  }, [route]);

  const validateEmail = (val: string) => {
    if (!val) {
      return 'Email is required';
    }
    const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!regex.test(val)) {
      return 'Invalid email address';
    }
    return null;
  };

  const validateToken = (val: string) => {
    if (!val.trim()) {
      return 'Verification code is required';
    }
    return null;
  };

  const validateNewPassword = (val: string) => {
    if (!val) {
      return 'Password is required';
    }
    if (val.length < 8) {
      return 'Password must be at least 8 characters';
    }
    return null;
  };

  const validateConfirmPassword = (val: string, pass: string) => {
    if (!val) {
      return 'Please confirm your new password';
    }
    if (val !== pass) {
      return 'Passwords do not match';
    }
    return null;
  };

  const handleEmailChange = (val: string) => {
    setEmail(val);
    if (emailError) {
      setEmailError(validateEmail(val.trim()));
    }
  };

  const handleTokenChange = (val: string) => {
    setToken(val);
    if (tokenError) {
      setTokenError(validateToken(val));
    }
  };

  const handleNewPasswordChange = (val: string) => {
    setNewPassword(val);
    if (newPasswordError) {
      setNewPasswordError(validateNewPassword(val));
    }
    if (confirmPasswordError) {
      setConfirmPasswordError(validateConfirmPassword(confirmPassword, val));
    }
  };

  const handleConfirmPasswordChange = (val: string) => {
    setConfirmPassword(val);
    if (confirmPasswordError) {
      setConfirmPasswordError(validateConfirmPassword(val, newPassword));
    }
  };

  const handleResetPassword = async () => {
    if (resetPasswordLoading) return; // Prevent multiple requests

    const eErr = validateEmail(email.trim());
    const tErr = validateToken(token);
    const npErr = validateNewPassword(newPassword);
    const cpErr = validateConfirmPassword(confirmPassword, newPassword);

    if (eErr || tErr || npErr || cpErr) {
      setEmailError(eErr);
      setTokenError(tErr);
      setNewPasswordError(npErr);
      setConfirmPasswordError(cpErr);
      return;
    }

    const success = await resetPassword(email.trim(), token.trim(), newPassword);
    if (success) {
      if (Platform.OS === 'web' && typeof window !== 'undefined' && window.history) {
        window.history.replaceState({}, document.title, window.location.pathname);
      }
      setTimeout(() => {
        navigation.navigate('Login');
      }, 2000);
    }
  };

  return (
    <SafeAreaView style={styles.safeContainer}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        style={styles.keyboardContainer}
      >
        <ScrollView 
          style={{ flex: 1 }}
          contentContainerStyle={styles.scrollContent}
          keyboardShouldPersistTaps="handled"
        >
          <View style={styles.logoSection}>
            <Text style={styles.brandTitle}>POTHYS</Text>
            <Text style={styles.brandSub}>Swarna Mahal</Text>
            <View style={styles.dividerLine} />
            <Text style={styles.appTitle}>Initialize New Credentials</Text>
            <Text style={styles.appSubtitle}>Secure Token Verification</Text>
          </View>

          <View style={styles.formSection}>
            {resetPasswordSuccess ? (
              <View style={styles.successContainer}>
                <Text style={styles.successTitle}>Security Updated</Text>
                <Text style={styles.successText}>
                  Your password was successfully updated. Redirecting to Login session...
                </Text>
                <ActivityIndicator color={COLORS.primary} style={{ marginTop: 12 }} />
              </View>
            ) : (
              <>
                <Text style={styles.label}>Corporate Email Address</Text>
                <TextInput
                  style={[styles.input, emailError && styles.inputError]}
                  placeholder="agm@pothys.com"
                  placeholderTextColor={COLORS.textMuted}
                  keyboardType="email-address"
                  autoCapitalize="none"
                  autoCorrect={false}
                  value={email}
                  onChangeText={handleEmailChange}
                  editable={!resetPasswordLoading}
                />
                {emailError && <Text style={styles.inlineError}>{emailError}</Text>}

                <Text style={styles.label}>Security Verification Code</Text>
                <TextInput
                  style={[styles.input, tokenError && styles.inputError]}
                  placeholder="6-Digit Reset Code"
                  placeholderTextColor={COLORS.textMuted}
                  autoCapitalize="none"
                  autoCorrect={false}
                  value={token}
                  onChangeText={handleTokenChange}
                  editable={!resetPasswordLoading}
                />
                {tokenError && <Text style={styles.inlineError}>{tokenError}</Text>}

                <Text style={styles.label}>New Password</Text>
                <TextInput
                  style={[styles.input, newPasswordError && styles.inputError]}
                  placeholder="Min. 8 characters"
                  placeholderTextColor={COLORS.textMuted}
                  secureTextEntry
                  autoCapitalize="none"
                  autoCorrect={false}
                  value={newPassword}
                  onChangeText={handleNewPasswordChange}
                  editable={!resetPasswordLoading}
                />
                {newPasswordError && <Text style={styles.inlineError}>{newPasswordError}</Text>}

                <Text style={styles.label}>Confirm New Password</Text>
                <TextInput
                  style={[styles.input, confirmPasswordError && styles.inputError]}
                  placeholder="••••••••••••"
                  placeholderTextColor={COLORS.textMuted}
                  secureTextEntry
                  autoCapitalize="none"
                  autoCorrect={false}
                  value={confirmPassword}
                  onChangeText={handleConfirmPasswordChange}
                  editable={!resetPasswordLoading}
                />
                {confirmPasswordError && <Text style={styles.inlineError}>{confirmPasswordError}</Text>}

                {resetPasswordError && (
                  <View style={styles.errorContainer}>
                    <Text style={styles.errorText}>{resetPasswordError}</Text>
                  </View>
                )}

                <TouchableOpacity
                  style={[styles.button, resetPasswordLoading && styles.buttonDisabled]}
                  onPress={handleResetPassword}
                  disabled={resetPasswordLoading}
                  activeOpacity={0.8}
                >
                  {resetPasswordLoading ? (
                    <ActivityIndicator color={COLORS.textOnPrimary} size="small" />
                  ) : (
                    <Text style={styles.buttonText}>Update Password</Text>
                  )}
                </TouchableOpacity>
              </>
            )}

            <TouchableOpacity
              style={styles.backButton}
              onPress={() => !resetPasswordLoading && navigation.navigate('Login')}
              disabled={resetPasswordLoading}
            >
              <Text style={styles.backButtonText}>Return to Login Session</Text>
            </TouchableOpacity>
          </View>

          <View style={styles.footerSection}>
            <Text style={styles.footerText}>Secure Domain Access</Text>
            <Text style={styles.footerSub}>Security configuration logs are stored for auditing.</Text>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeContainer: {
    flex: 1,
    backgroundColor: COLORS.background,
  },
  keyboardContainer: {
    flex: 1,
  },
  scrollContent: {
    flexGrow: 1,
    justifyContent: 'center',
    paddingHorizontal: 32,
    paddingVertical: 40,
  },
  logoSection: {
    alignItems: 'center',
    marginBottom: 30,
  },
  brandTitle: {
    fontSize: 48,
    fontWeight: '900',
    color: COLORS.primary,
    letterSpacing: 4,
  },
  brandSub: {
    fontSize: 20,
    fontWeight: '300',
    color: COLORS.text,
    letterSpacing: 8,
    marginTop: -4,
    textTransform: 'uppercase',
  },
  dividerLine: {
    height: 1,
    width: 60,
    backgroundColor: COLORS.primary,
    marginVertical: 16,
  },
  appTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: COLORS.text,
    textAlign: 'center',
  },
  appSubtitle: {
    fontSize: 12,
    color: COLORS.textSecondary,
    marginTop: 4,
    textTransform: 'uppercase',
    letterSpacing: 1.5,
  },
  formSection: {
    backgroundColor: COLORS.surface,
    padding: 24,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: COLORS.border,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 10,
    elevation: 8,
  },
  label: {
    fontSize: 14,
    fontWeight: '500',
    color: COLORS.textSecondary,
    marginBottom: 8,
  },
  input: {
    backgroundColor: COLORS.background,
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: 8,
    color: COLORS.text,
    fontSize: 16,
    paddingHorizontal: 16,
    paddingVertical: 12,
    marginBottom: 16,
  },
  inputError: {
    borderColor: COLORS.error,
  },
  inlineError: {
    color: COLORS.error,
    fontSize: 12,
    marginTop: -12,
    marginBottom: 12,
    fontWeight: '500',
  },
  errorContainer: {
    backgroundColor: COLORS.errorBg,
    borderWidth: 1,
    borderColor: COLORS.error,
    padding: 12,
    borderRadius: 8,
    marginBottom: 20,
  },
  errorText: {
    color: COLORS.error,
    fontSize: 14,
    textAlign: 'center',
    fontWeight: '500',
  },
  successContainer: {
    alignItems: 'center',
    paddingVertical: 16,
  },
  successTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: COLORS.primary,
    marginBottom: 8,
  },
  successText: {
    fontSize: 14,
    color: COLORS.text,
    textAlign: 'center',
    lineHeight: 20,
  },
  button: {
    backgroundColor: COLORS.primary,
    borderRadius: 8,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 10,
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  buttonText: {
    color: COLORS.textOnPrimary,
    fontSize: 16,
    fontWeight: '700',
  },
  backButton: {
    alignItems: 'center',
    marginTop: 20,
    paddingVertical: 8,
  },
  backButtonText: {
    color: COLORS.textSecondary,
    fontSize: 14,
    fontWeight: '600',
  },
  footerSection: {
    alignItems: 'center',
    marginTop: 30,
  },
  footerText: {
    fontSize: 12,
    fontWeight: '600',
    color: COLORS.textSecondary,
    letterSpacing: 2,
    textTransform: 'uppercase',
  },
  footerSub: {
    fontSize: 10,
    color: COLORS.textMuted,
    textAlign: 'center',
    marginTop: 4,
    paddingHorizontal: 20,
  },
});
