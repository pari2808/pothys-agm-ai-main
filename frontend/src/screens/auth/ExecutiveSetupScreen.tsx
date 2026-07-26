import React, { useState } from 'react';
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

export default function ExecutiveSetupScreen({ navigation }: any) {
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  // Inline error state variables
  const [fullNameError, setFullNameError] = useState<string | null>(null);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [confirmPasswordError, setConfirmPasswordError] = useState<string | null>(null);

  const { setupExecutive, setupLoading, setupError } = useAuthStore();

  const validateFullName = (val: string) => {
    if (!val.trim()) {
      return 'Full Name is required';
    }
    return null;
  };

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
    if (val.length < 8) {
      return 'Password must be at least 8 characters';
    }
    if (!/[A-Za-z]/.test(val)) {
      return 'Password must contain at least one letter';
    }
    if (!/[0-9]/.test(val)) {
      return 'Password must contain at least one number';
    }
    return null;
  };

  const validateConfirmPassword = (val: string, pass: string) => {
    if (!val) {
      return 'Please confirm your password';
    }
    if (val !== pass) {
      return 'Passwords do not match';
    }
    return null;
  };

  const handleFullNameChange = (val: string) => {
    setFullName(val);
    if (fullNameError) {
      setFullNameError(validateFullName(val));
    }
  };

  const handleEmailChange = (val: string) => {
    setEmail(val);
    if (emailError) {
      setEmailError(validateEmail(val.trim()));
    }
  };

  const handlePasswordChange = (val: string) => {
    setPassword(val);
    if (passwordError) {
      setPasswordError(validatePassword(val));
    }
    if (confirmPasswordError) {
      setConfirmPasswordError(validateConfirmPassword(confirmPassword, val));
    }
  };

  const handleConfirmPasswordChange = (val: string) => {
    setConfirmPassword(val);
    if (confirmPasswordError) {
      setConfirmPasswordError(validateConfirmPassword(val, password));
    }
  };

  const handleSetup = async () => {
    if (setupLoading) return; // Prevent multiple requests

    const fnErr = validateFullName(fullName);
    const eErr = validateEmail(email.trim());
    const pErr = validatePassword(password);
    const cpErr = validateConfirmPassword(confirmPassword, password);

    if (fnErr || eErr || pErr || cpErr) {
      setFullNameError(fnErr);
      setEmailError(eErr);
      setPasswordError(pErr);
      setConfirmPasswordError(cpErr);
      return;
    }

    await setupExecutive(fullName.trim(), email.trim(), password);
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
            <Text style={styles.brandTitle}>POTHYS</Text>
            <Text style={styles.brandSub}>Swarna Mahal</Text>
            <View style={styles.dividerLine} />
            <Text style={styles.appTitle}>Executive Account Setup</Text>
            <Text style={styles.appSubtitle}>Configure First AGM Profile</Text>
          </View>

          <View style={styles.formSection}>
            <Text style={styles.label}>Full Name</Text>
            <TextInput
              style={[styles.input, fullNameError && styles.inputError]}
              placeholder="e.g. AGM Executive Officer"
              placeholderTextColor={COLORS.textMuted}
              autoCapitalize="words"
              value={fullName}
              onChangeText={handleFullNameChange}
              editable={!setupLoading}
            />
            {fullNameError && <Text style={styles.inlineError}>{fullNameError}</Text>}

            <Text style={styles.label}>Corporate Email</Text>
            <TextInput
              style={[styles.input, emailError && styles.inputError]}
              placeholder="agm@pothys.com"
              placeholderTextColor={COLORS.textMuted}
              keyboardType="email-address"
              autoCapitalize="none"
              autoCorrect={false}
              value={email}
              onChangeText={handleEmailChange}
              editable={!setupLoading}
            />
            {emailError && <Text style={styles.inlineError}>{emailError}</Text>}

            <Text style={styles.label}>Create Password</Text>
            <TextInput
              style={[styles.input, passwordError && styles.inputError]}
              placeholder="••••••••••••"
              placeholderTextColor={COLORS.textMuted}
              secureTextEntry
              autoCapitalize="none"
              autoCorrect={false}
              value={password}
              onChangeText={handlePasswordChange}
              editable={!setupLoading}
            />
            {passwordError && <Text style={styles.inlineError}>{passwordError}</Text>}

            <Text style={styles.label}>Confirm Password</Text>
            <TextInput
              style={[styles.input, confirmPasswordError && styles.inputError]}
              placeholder="••••••••••••"
              placeholderTextColor={COLORS.textMuted}
              secureTextEntry
              autoCapitalize="none"
              autoCorrect={false}
              value={confirmPassword}
              onChangeText={handleConfirmPasswordChange}
              editable={!setupLoading}
            />
            {confirmPasswordError && <Text style={styles.inlineError}>{confirmPasswordError}</Text>}

            {setupError && (
              <View style={styles.errorContainer}>
                <Text style={styles.errorText}>{setupError}</Text>
              </View>
            )}

            <TouchableOpacity
              style={[styles.button, setupLoading && styles.buttonDisabled]}
              onPress={handleSetup}
              disabled={setupLoading}
              activeOpacity={0.8}
            >
              {setupLoading ? (
                <ActivityIndicator color={COLORS.textOnPrimary} size="small" />
              ) : (
                <Text style={styles.buttonText}>Create Executive Account</Text>
              )}
            </TouchableOpacity>
          </View>

          <View style={styles.footerSection}>
            <Text style={styles.footerText}>Secure System Initialization</Text>
            <Text style={styles.footerSub}>Only one corporate AGM profile can be initialized per instance.</Text>
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
  logoSection: {
    alignItems: 'center',
    marginBottom: 28,
    maxWidth: 420,
    width: '100%',
  },
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
  footerSection: {
    alignItems: 'center',
    marginTop: 28,
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
