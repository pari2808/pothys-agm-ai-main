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
  ScrollView,
  Animated,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuthStore } from '../../store/authStore';
import { COLORS } from '../../theme/colors';

export default function ManagerLoginScreen({ navigation }: any) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [emailError, setEmailError] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);

  const { login, loginLoading, error } = useAuthStore();

  const headerOpacity = new Animated.Value(0);

  // Clear previous session errors on screen mount
  useEffect(() => {
    useAuthStore.setState({ error: null });
  }, []);

  useEffect(() => {
    Animated.timing(headerOpacity, {
      toValue: 1, duration: 500, useNativeDriver: true,
    }).start();
  }, []);

  const validateEmail = (val: string) => {
    if (!val) return 'Email is required';
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val)) return 'Invalid email address';
    return null;
  };

  const validatePassword = (val: string) => {
    if (!val) return 'Password is required';
    return null;
  };

  const handleLogin = async () => {
    if (loginLoading) return;
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
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        style={{ flex: 1 }}
      >
        <ScrollView
          contentContainerStyle={styles.scroll}
          keyboardShouldPersistTaps="handled"
        >
          {/* Back Button */}
          <TouchableOpacity style={styles.backBtn} onPress={() => navigation.goBack()}>
            <Text style={styles.backArrow}>‹</Text>
          </TouchableOpacity>

          {/* Header */}
          <Animated.View style={[styles.header, { opacity: headerOpacity }]}>
            <View style={styles.iconWrap}>
              <Text style={styles.iconEmoji}>🏬</Text>
            </View>
            <Text style={styles.headerTitle}>Branch Manager</Text>
            <Text style={styles.headerSub}>Pothys Swarna Mahal · Internal System</Text>
            <View style={styles.headerDivider} />
            <Text style={styles.headerHint}>
              Use your pre-assigned enterprise credentials to access the branch reporting portal.
            </Text>
          </Animated.View>

          {/* Form Card */}
          <View style={styles.formCard}>
            <View style={styles.formAccentBar} />

            <View style={styles.formBody}>
              <Text style={styles.formTitle}>Secure Authentication</Text>

              {/* Email */}
              <Text style={styles.label}>Email Address</Text>
              <TextInput
                style={[styles.input, emailError && styles.inputError]}
                placeholder="manager@pothys.com"
                placeholderTextColor={COLORS.textMuted}
                keyboardType="email-address"
                autoCapitalize="none"
                autoCorrect={false}
                value={email}
                onChangeText={(v) => {
                  setEmail(v);
                  setLocalError(null);
                  useAuthStore.setState({ error: null });
                  if (emailError) setEmailError(validateEmail(v.trim()));
                }}
                editable={!loginLoading}
                returnKeyType="next"
              />
              {emailError && <Text style={styles.fieldError}>{emailError}</Text>}

              {/* Password */}
              <Text style={styles.label}>Password</Text>
              <TextInput
                style={[styles.input, passwordError && styles.inputError]}
                placeholder="••••••••••••"
                placeholderTextColor={COLORS.textMuted}
                secureTextEntry
                autoCapitalize="none"
                autoCorrect={false}
                value={password}
                onChangeText={(v) => {
                  setPassword(v);
                  setLocalError(null);
                  useAuthStore.setState({ error: null });
                  if (passwordError) setPasswordError(validatePassword(v));
                }}
                editable={!loginLoading}
                returnKeyType="done"
                onSubmitEditing={handleLogin}
              />
              {passwordError && <Text style={styles.fieldError}>{passwordError}</Text>}

              {/* API or local validation error */}
              {(localError || error) && (
                <View style={styles.errorBox}>
                  <Text style={styles.errorBoxText}>{localError || error}</Text>
                </View>
              )}

              {/* Login Button */}
              <TouchableOpacity
                style={[styles.loginBtn, loginLoading && styles.loginBtnDisabled]}
                onPress={handleLogin}
                disabled={loginLoading}
                activeOpacity={0.85}
              >
                {loginLoading ? (
                  <ActivityIndicator color="#0B0B0E" size="small" />
                ) : (
                  <Text style={styles.loginBtnText}>Authenticate Session</Text>
                )}
              </TouchableOpacity>

              {/* Internal notice */}
              <View style={styles.noticeRow}>
                <Text style={styles.noticeIcon}>ℹ️</Text>
                <Text style={styles.noticeText}>
                  Manager accounts are provisioned by the system administrator. Contact your AGM if you need access.
                </Text>
              </View>
            </View>
          </View>

          {/* Footer */}
          <View style={styles.footer}>
            <Text style={styles.footerText}>🔒  Authorized Access Only</Text>
            <Text style={styles.footerSub}>Activity is monitored and logged under compliance auditing.</Text>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.background },
  scroll: {
    flexGrow: 1,
    paddingHorizontal: 16,
    paddingVertical: 24,
    justifyContent: 'center',
    alignItems: 'center',
    width: '100%',
  },
  // Back
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
  // Header
  header: { alignItems: 'center', marginBottom: 24, maxWidth: 420, width: '100%' },
  iconWrap: {
    width: 60, height: 60, borderRadius: 16,
    backgroundColor: '#3B82F6' + '18',
    borderWidth: 1, borderColor: '#3B82F6' + '40',
    alignItems: 'center', justifyContent: 'center',
    marginBottom: 14,
    shadowColor: '#3B82F6', shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.3, shadowRadius: 16, elevation: 8,
  },
  iconEmoji: { fontSize: 26 },
  headerTitle: { fontSize: 24, fontWeight: '800', color: COLORS.text, marginBottom: 4, textAlign: 'center' },
  headerSub: { fontSize: 13, color: COLORS.textSecondary, letterSpacing: 0.5, textAlign: 'center' },
  headerDivider: { width: 40, height: 1, backgroundColor: '#3B82F6' + '60', marginVertical: 12 },
  headerHint: {
    fontSize: 13, color: COLORS.textSecondary, textAlign: 'center',
    lineHeight: 18, paddingHorizontal: 12,
  },
  // Form card
  formCard: {
    backgroundColor: COLORS.surface,
    borderRadius: 20, borderWidth: 1, borderColor: COLORS.border,
    overflow: 'hidden',
    shadowColor: '#000', shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.3, shadowRadius: 12, elevation: 10,
    maxWidth: 420, width: '100%',
  },
  formAccentBar: { height: 3, backgroundColor: '#3B82F6' },
  formBody: { padding: 20 },
  formTitle: {
    fontSize: 14, fontWeight: '700', color: COLORS.textSecondary,
    letterSpacing: 1, textTransform: 'uppercase', marginBottom: 18,
  },
  label: {
    fontSize: 13, fontWeight: '500', color: COLORS.textSecondary, marginBottom: 8,
  },
  input: {
    backgroundColor: COLORS.background, borderWidth: 1, borderColor: COLORS.border,
    borderRadius: 10, color: COLORS.text, fontSize: 16,
    paddingHorizontal: 16, paddingVertical: 12, marginBottom: 16,
  },
  inputError: { borderColor: COLORS.error },
  fieldError: {
    color: COLORS.error, fontSize: 12, marginTop: -12, marginBottom: 12, fontWeight: '500',
  },
  errorBox: {
    backgroundColor: COLORS.errorBg, borderWidth: 1, borderColor: COLORS.error,
    padding: 12, borderRadius: 8, marginBottom: 16,
  },
  errorBoxText: { color: COLORS.error, fontSize: 14, textAlign: 'center', fontWeight: '500' },
  loginBtn: {
    backgroundColor: '#3B82F6', borderRadius: 10,
    paddingVertical: 14, alignItems: 'center', marginTop: 6,
  },
  loginBtnDisabled: { opacity: 0.6 },
  loginBtnText: { color: '#fff', fontSize: 16, fontWeight: '700', letterSpacing: 0.5 },
  noticeRow: {
    flexDirection: 'row', alignItems: 'flex-start', gap: 8,
    marginTop: 18, paddingTop: 14,
    borderTopWidth: 1, borderColor: COLORS.border,
  },
  noticeIcon: { fontSize: 14, marginTop: 1 },
  noticeText: { flex: 1, fontSize: 12, color: COLORS.textMuted, lineHeight: 18 },
  // Footer
  footer: { alignItems: 'center', marginTop: 24, paddingHorizontal: 16, maxWidth: 420, width: '100%' },
  footerText: {
    fontSize: 11, fontWeight: '700', color: COLORS.textSecondary,
    letterSpacing: 1.5, textTransform: 'uppercase', marginBottom: 4,
  },
  footerSub: { fontSize: 10, color: COLORS.textMuted, textAlign: 'center' },
});
