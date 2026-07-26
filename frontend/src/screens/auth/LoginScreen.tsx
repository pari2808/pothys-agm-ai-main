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

export default function LoginScreen({ navigation }: any) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  
  // Inline error state variables
  const [emailError, setEmailError] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);

  const { login, loginLoading, error } = useAuthStore();

  // Clear previous session errors on screen mount
  useEffect(() => {
    useAuthStore.setState({ error: null });
  }, []);

  // Redirect to ResetPassword if URL parameters are set on mount (Expo Web)
  useEffect(() => {
    if (Platform.OS === 'web' && typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const urlToken = params.get('token');
      const urlEmail = params.get('email');
      if (urlToken && urlEmail) {
        navigation.navigate('ResetPassword', { email: urlEmail, token: urlToken });
      }
    }
  }, []);

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

  const validatePassword = (val: string) => {
    if (!val) {
      return 'Password is required';
    }
    return null;
  };

  const handleEmailChange = (val: string) => {
    setEmail(val);
    setLocalError(null);
    useAuthStore.setState({ error: null });
    if (emailError) {
      setEmailError(validateEmail(val.trim()));
    }
  };

  const handlePasswordChange = (val: string) => {
    setPassword(val);
    setLocalError(null);
    useAuthStore.setState({ error: null });
    if (passwordError) {
      setPasswordError(validatePassword(val));
    }
  };

  const handleLogin = async () => {
    if (loginLoading) return; // Prevent multiple requests
    setLocalError(null);
    useAuthStore.setState({ error: null });

    if (!email.trim() && !password) {
      setLocalError('Please enter your email and password.');
      return;
    }

    const eErr = validateEmail(email.trim());
    const pErr = validatePassword(password);

    if (eErr || pErr) {
      setEmailError(eErr);
      setPasswordError(pErr);
      return;
    }

    await login(email.trim(), password);
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
          {/* Back to role selection */}
          <TouchableOpacity style={styles.backBtn} onPress={() => navigation.goBack()}>
            <Text style={styles.backArrow}>‹</Text>
          </TouchableOpacity>

          <View style={styles.logoSection}>
            <View style={styles.agmIconWrap}>
              <Text style={styles.agmIcon}>👔</Text>
            </View>
            <Text style={styles.brandTitle}>POTHYS</Text>
            <Text style={styles.brandSub}>Swarna Mahal</Text>
            <View style={styles.dividerLine} />
            <Text style={styles.appTitle}>AGM AI Executive Assistant</Text>
            <Text style={styles.appSubtitle}>AGM · Executive Access</Text>
          </View>

          <View style={styles.formSection}>
            <Text style={styles.label}>Email Address</Text>
            <TextInput
              style={[styles.input, emailError && styles.inputError]}
              placeholder="agm@pothys.com"
              placeholderTextColor={COLORS.textMuted}
              keyboardType="email-address"
              autoCapitalize="none"
              autoCorrect={false}
              value={email}
              onChangeText={handleEmailChange}
              editable={!loginLoading}
            />
            {emailError && <Text style={styles.inlineError}>{emailError}</Text>}

            <Text style={styles.label}>Password</Text>
            <TextInput
              style={[styles.input, passwordError && styles.inputError]}
              placeholder="••••••••••••"
              placeholderTextColor={COLORS.textMuted}
              secureTextEntry
              autoCapitalize="none"
              autoCorrect={false}
              value={password}
              onChangeText={handlePasswordChange}
              editable={!loginLoading}
            />
            {passwordError && <Text style={styles.inlineError}>{passwordError}</Text>}

            {(localError || error) && (
              <View style={styles.errorContainer}>
                <Text style={styles.errorText}>{localError || error}</Text>
              </View>
            )}

            <TouchableOpacity
              style={[styles.button, loginLoading && styles.buttonDisabled]}
              onPress={handleLogin}
              disabled={loginLoading}
              activeOpacity={0.8}
            >
              {loginLoading ? (
                <ActivityIndicator color={COLORS.textOnPrimary} size="small" />
              ) : (
                <Text style={styles.buttonText}>Authenticate Session</Text>
              )}
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.forgotButton}
              onPress={() => !loginLoading && navigation.navigate('ForgotPassword')}
              disabled={loginLoading}
            >
              <Text style={styles.forgotButtonText}>Forgot Password?</Text>
            </TouchableOpacity>
          </View>

          <View style={styles.footerSection}>
            <Text style={styles.footerText}>Authorized Access Only</Text>
            <Text style={styles.footerSub}>Activity is monitored and logged under compliance auditing.</Text>
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
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 32,
    width: '100%',
  },
  backBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginBottom: 20,
    alignSelf: 'flex-start',
    maxWidth: 420,
    width: '100%',
  },
  backArrow: { fontSize: 26, color: COLORS.textSecondary, lineHeight: 30 },
  backLabel: { fontSize: 14, color: COLORS.textSecondary, fontWeight: '600' },
  logoSection: {
    alignItems: 'center',
    marginBottom: 32,
    maxWidth: 420,
    width: '100%',
  },
  agmIconWrap: {
    width: 60, height: 60, borderRadius: 16,
    backgroundColor: COLORS.primary + '18',
    borderWidth: 1, borderColor: COLORS.primary + '40',
    alignItems: 'center', justifyContent: 'center',
    marginBottom: 14,
    shadowColor: COLORS.primary, shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.3, shadowRadius: 16, elevation: 8,
  },
  agmIcon: { fontSize: 26 },
  brandTitle: {
    fontSize: 32,
    fontWeight: '900',
    color: COLORS.primary,
    letterSpacing: 4,
    textAlign: 'center',
  },
  brandSub: {
    fontSize: 13,
    fontWeight: '300',
    color: COLORS.text,
    letterSpacing: 4,
    marginTop: -2,
    textTransform: 'uppercase',
    textAlign: 'center',
  },
  dividerLine: {
    height: 1,
    width: 50,
    backgroundColor: COLORS.primary,
    marginVertical: 14,
  },
  appTitle: {
    fontSize: 16,
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
    textAlign: 'center',
  },
  formSection: {
    backgroundColor: COLORS.surface,
    padding: 20,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: COLORS.border,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 10,
    elevation: 8,
    maxWidth: 420,
    width: '100%',
  },
  label: {
    fontSize: 13,
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
  forgotButton: {
    alignItems: 'center',
    marginTop: 16,
    paddingVertical: 4,
  },
  forgotButtonText: {
    color: COLORS.textSecondary,
    fontSize: 14,
    fontWeight: '600',
  },
  footerSection: {
    alignItems: 'center',
    marginTop: 32,
    maxWidth: 420,
    width: '100%',
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
