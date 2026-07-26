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
import { Alert } from 'react-native';

export default function ForgotPasswordScreen({ navigation }: any) {
  const [email, setEmail] = useState('');
  const [emailError, setEmailError] = useState<string | null>(null);

  const { forgotPassword, forgotPasswordLoading, forgotPasswordSuccess, forgotPasswordError } = useAuthStore();

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

  const handleEmailChange = (val: string) => {
    setEmail(val);
    if (emailError) {
      setEmailError(validateEmail(val.trim()));
    }
  };

  const handleRequestReset = async () => {
    Alert.alert('System Notice', 'Password reset is not available in this demo.');
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
            <Text style={styles.appTitle}>Password Recovery</Text>
            <Text style={styles.appSubtitle}>Secure Access Restoration</Text>
          </View>

          <View style={styles.formSection}>
            {forgotPasswordSuccess ? (
              <View style={styles.successContainer}>
                <Text style={styles.successTitle}>Reset Code Sent</Text>
                <Text style={styles.successText}>
                  A secure 6-character reset code has been dispatched to your corporate inbox.
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
                  editable={!forgotPasswordLoading}
                />
                {emailError && <Text style={styles.inlineError}>{emailError}</Text>}

                {forgotPasswordError && (
                  <View style={styles.errorContainer}>
                    <Text style={styles.errorText}>{forgotPasswordError}</Text>
                  </View>
                )}

                <TouchableOpacity
                  style={[styles.button, forgotPasswordLoading && styles.buttonDisabled]}
                  onPress={handleRequestReset}
                  disabled={forgotPasswordLoading}
                  activeOpacity={0.8}
                >
                  {forgotPasswordLoading ? (
                    <ActivityIndicator color={COLORS.textOnPrimary} size="small" />
                  ) : (
                    <Text style={styles.buttonText}>Generate Reset Token</Text>
                  )}
                </TouchableOpacity>
              </>
            )}

            <TouchableOpacity
              style={styles.backButton}
              onPress={() => navigation.navigate('AGMLogin')}
            >
              <Text style={styles.backButtonText}>Return to Login Session</Text>
            </TouchableOpacity>
          </View>

          <View style={styles.footerSection}>
            <Text style={styles.footerText}>Secure Domain Access</Text>
            <Text style={styles.footerSub}>Password resets are logged for compliance monitoring.</Text>
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
