import React, { useState, useRef } from 'react';
import {
  View,
  ScrollView,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  TextInput,
  TouchableOpacity,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Text, Button, Input, Divider } from '@/components/ui';
import { useTheme } from '@/hooks/useTheme';
import { useAuthStore } from '@/store/authStore';
import { useSocialAuth, type SocialAuthOutcome } from '@/hooks/useSocialAuth';
import { extractApiError } from '@/services/api';
import { BrandLogo } from '@/components/common/BrandLogo';

export default function LoginScreen() {
  const { colors, spacing } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { login, isLoading } = useAuthStore();
  const {
    googleAvailable,
    facebookAvailable,
    appleAvailable,
    signInWithGoogle,
    signInWithFacebook,
    signInWithApple,
  } = useSocialAuth();

  const [email, setEmail] = useState('');
  const [senha, setSenha] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [socialBusy, setSocialBusy] = useState<'google' | 'apple' | 'facebook' | null>(null);

  const senhaRef = useRef<TextInput>(null);

  const handleLogin = async () => {
    setError('');
    if (!email.trim() || !senha.trim()) {
      setError('Preencha todos os campos');
      return;
    }
    try {
      await login({ email: email.trim(), senha });
      router.replace('/(tabs)');
    } catch (err) {
      setError(extractApiError(err));
    }
  };

  const handleSocialOutcome = (outcome: SocialAuthOutcome) => {
    if (outcome.status === 'authenticated') {
      router.replace('/(tabs)');
      return;
    }
    if (outcome.status === 'pending_link') {
      setError('Conta existente. Confirme sua senha para vincular.');
      return;
    }
    if (outcome.status === 'cancelled') {
      return;
    }
    if (outcome.status === 'unsupported') {
      setError('Provedor não configurado para este app.');
      return;
    }
    if (outcome.status === 'error') {
      setError(outcome.message || 'Falha no login social');
    }
  };

  const handleGoogleLogin = async () => {
    setError('');
    setSocialBusy('google');
    try {
      const outcome = await signInWithGoogle();
      handleSocialOutcome(outcome);
    } finally {
      setSocialBusy(null);
    }
  };

  const handleAppleLogin = async () => {
    setError('');
    setSocialBusy('apple');
    try {
      const outcome = await signInWithApple();
      handleSocialOutcome(outcome);
    } finally {
      setSocialBusy(null);
    }
  };

  const handleFacebookLogin = async () => {
    setError('');
    setSocialBusy('facebook');
    try {
      const outcome = await signInWithFacebook();
      handleSocialOutcome(outcome);
    } finally {
      setSocialBusy(null);
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.flex}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView
        style={[styles.flex, { backgroundColor: colors.background }]}
        contentContainerStyle={[styles.content, { paddingTop: insets.top + 60, paddingBottom: insets.bottom + 32 }]}
        keyboardShouldPersistTaps="handled"
      >
        <TouchableOpacity
          onPress={() => router.back()}
          style={styles.backBtn}
          accessibilityLabel="Voltar"
        >
          <Text variant="body1" color={colors.textSecondary}>← Voltar</Text>
        </TouchableOpacity>

        <BrandLogo height={44} style={{ marginBottom: spacing.xl }} />

        <Text variant="h2" color={colors.textPrimary}>Entrar</Text>
        <Text variant="body2" color={colors.textSecondary} style={{ marginTop: spacing.sm }}>
          Acesse sua conta Ibix Market
        </Text>

        {error ? (
          <View style={[styles.errorBox, { backgroundColor: colors.errorSurface }]}>
            <Text variant="body2" color={colors.error}>{error}</Text>
          </View>
        ) : null}

        <View style={{ marginTop: spacing['2xl'] }}>
          <Input
            label="E-mail"
            placeholder="seu@email.com"
            keyboardType="email-address"
            autoCapitalize="none"
            autoComplete="email"
            value={email}
            onChangeText={setEmail}
            returnKeyType="next"
            onSubmitEditing={() => senhaRef.current?.focus()}
          />
          <Input
            ref={senhaRef}
            label="Senha"
            placeholder="Sua senha"
            secureTextEntry={!showPassword}
            autoComplete="password"
            value={senha}
            onChangeText={setSenha}
            returnKeyType="done"
            onSubmitEditing={handleLogin}
            rightIcon={
              <Text variant="caption" color={colors.primary}>
                {showPassword ? 'Ocultar' : 'Mostrar'}
              </Text>
            }
            onRightIconPress={() => setShowPassword(!showPassword)}
          />

          <TouchableOpacity
            onPress={() => router.push('/(auth)/esqueci-senha')}
            style={{ alignSelf: 'flex-end', marginTop: -8, marginBottom: spacing.lg }}
            accessibilityLabel="Esqueci minha senha"
          >
            <Text variant="body2" color={colors.textLink}>Esqueci minha senha</Text>
          </TouchableOpacity>

          <Button
            title="Entrar"
            onPress={handleLogin}
            loading={isLoading}
            fullWidth
            size="lg"
          />
        </View>

        {(googleAvailable || appleAvailable || facebookAvailable) && (
          <>
            <View style={styles.dividerRow}>
              <Divider style={{ flex: 1 }} />
              <Text variant="caption" color={colors.textDisabled} style={{ marginHorizontal: 12 }}>
                ou continue com
              </Text>
              <Divider style={{ flex: 1 }} />
            </View>

            <View style={styles.socialRow}>
              {googleAvailable && (
                <Button
                  title="Google"
                  onPress={handleGoogleLogin}
                  variant="outline"
                  size="lg"
                  style={{ flex: 1, marginRight: 8 }}
                  loading={socialBusy === 'google'}
                  disabled={socialBusy !== null}
                />
              )}
              {appleAvailable && (
                <Button
                  title="Apple"
                  onPress={handleAppleLogin}
                  variant="outline"
                  size="lg"
                  style={{ flex: 1, marginHorizontal: 8 }}
                  loading={socialBusy === 'apple'}
                  disabled={socialBusy !== null}
                />
              )}
              {facebookAvailable && (
                <Button
                  title="Facebook"
                  onPress={handleFacebookLogin}
                  variant="outline"
                  size="lg"
                  style={{ flex: 1, marginLeft: 8 }}
                  loading={socialBusy === 'facebook'}
                  disabled={socialBusy !== null}
                />
              )}
            </View>
          </>
        )}

        <View style={styles.footerRow}>
          <Text variant="body2" color={colors.textSecondary}>Não tem conta? </Text>
          <TouchableOpacity
            onPress={() => router.push('/(auth)/cadastro')}
            accessibilityLabel="Criar conta"
          >
            <Text variant="body2" color={colors.textLink}>Criar conta</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  content: { paddingHorizontal: 24 },
  backBtn: { marginBottom: 24 },
  errorBox: { marginTop: 16, padding: 12, borderRadius: 8 },
  dividerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginVertical: 24,
  },
  socialRow: {
    flexDirection: 'row',
    marginBottom: 24,
  },
  footerRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginTop: 8,
  },
});
