import React, { useState, useRef } from 'react';
import {
  View,
  ScrollView,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  TextInput,
  TouchableOpacity,
  Switch,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Text, Button, Input, Divider } from '@/components/ui';
import { useTheme } from '@/hooks/useTheme';
import { useAuthStore } from '@/store/authStore';
import { useSocialAuth, type SocialAuthOutcome } from '@/hooks/useSocialAuth';
import { extractApiError } from '@/services/api';

export default function CadastroScreen() {
  const { colors, spacing } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { cadastro, isLoading } = useAuthStore();
  const {
    googleAvailable,
    facebookAvailable,
    appleAvailable,
    signInWithGoogle,
    signInWithFacebook,
    signInWithApple,
  } = useSocialAuth();

  const [socialBusy, setSocialBusy] = useState<'google' | 'apple' | 'facebook' | null>(null);

  const [nome, setNome] = useState('');
  const [email, setEmail] = useState('');
  const [telefone, setTelefone] = useState('');
  const [senha, setSenha] = useState('');
  const [confirmarSenha, setConfirmarSenha] = useState('');
  const [aceiteTermos, setAceiteTermos] = useState(false);
  const [consentMarketing, setConsentMarketing] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [apiError, setApiError] = useState('');

  const emailRef = useRef<TextInput>(null);
  const telefoneRef = useRef<TextInput>(null);
  const senhaRef = useRef<TextInput>(null);
  const confirmarRef = useRef<TextInput>(null);

  const validate = (): boolean => {
    const e: Record<string, string> = {};
    if (!nome.trim()) e.nome = 'Nome obrigatório';
    if (!email.trim() || !email.includes('@')) e.email = 'E-mail inválido';
    if (senha.length < 8) e.senha = 'Mínimo 8 caracteres';
    if (senha !== confirmarSenha) e.confirmarSenha = 'Senhas não coincidem';
    if (!aceiteTermos) e.termos = 'Você precisa aceitar os termos';
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleCadastro = async () => {
    if (!validate()) return;
    setApiError('');
    try {
      await cadastro({
        nome: nome.trim(),
        email: email.trim(),
        senha,
        telefone: telefone.trim() || undefined,
        aceite_termos: aceiteTermos,
      });
      router.replace('/(tabs)');
    } catch (err) {
      setApiError(extractApiError(err));
    }
  };

  const handleSocialOutcome = (outcome: SocialAuthOutcome) => {
    if (outcome.status === 'authenticated') {
      router.replace('/(tabs)');
      return;
    }
    if (outcome.status === 'pending_link') {
      setApiError('Conta existente. Faça login para vincular sua conta social.');
      return;
    }
    if (outcome.status === 'cancelled') return;
    if (outcome.status === 'unsupported') {
      setApiError('Provedor não configurado para este app.');
      return;
    }
    if (outcome.status === 'error') {
      setApiError(outcome.message || 'Falha no cadastro social');
    }
  };

  const handleSocialAction = async (
    provider: 'google' | 'apple' | 'facebook',
    fn: () => Promise<SocialAuthOutcome>,
  ) => {
    if (!aceiteTermos) {
      setErrors((prev) => ({ ...prev, termos: 'Aceite os termos antes de continuar' }));
      return;
    }
    setApiError('');
    setSocialBusy(provider);
    try {
      const outcome = await fn();
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
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn} accessibilityLabel="Voltar">
          <Text variant="body1" color={colors.textSecondary}>← Voltar</Text>
        </TouchableOpacity>

        <Text variant="h2" color={colors.textPrimary}>Criar conta</Text>
        <Text variant="body2" color={colors.textSecondary} style={{ marginTop: spacing.sm }}>
          Cadastre-se para começar a comprar
        </Text>

        {apiError ? (
          <View style={[styles.errorBox, { backgroundColor: colors.errorSurface }]}>
            <Text variant="body2" color={colors.error}>{apiError}</Text>
          </View>
        ) : null}

        <View style={{ marginTop: spacing['2xl'] }}>
          <Input
            label="Nome completo"
            placeholder="Seu nome"
            autoCapitalize="words"
            autoComplete="name"
            value={nome}
            onChangeText={setNome}
            error={errors.nome}
            returnKeyType="next"
            onSubmitEditing={() => emailRef.current?.focus()}
          />
          <Input
            ref={emailRef}
            label="E-mail"
            placeholder="seu@email.com"
            keyboardType="email-address"
            autoCapitalize="none"
            autoComplete="email"
            value={email}
            onChangeText={setEmail}
            error={errors.email}
            returnKeyType="next"
            onSubmitEditing={() => telefoneRef.current?.focus()}
          />
          <Input
            ref={telefoneRef}
            label="Telefone (opcional)"
            placeholder="(00) 00000-0000"
            keyboardType="phone-pad"
            autoComplete="tel"
            value={telefone}
            onChangeText={setTelefone}
            returnKeyType="next"
            onSubmitEditing={() => senhaRef.current?.focus()}
          />
          <Input
            ref={senhaRef}
            label="Senha"
            placeholder="Mínimo 8 caracteres"
            secureTextEntry
            autoComplete="new-password"
            value={senha}
            onChangeText={setSenha}
            error={errors.senha}
            returnKeyType="next"
            onSubmitEditing={() => confirmarRef.current?.focus()}
          />
          <Input
            ref={confirmarRef}
            label="Confirmar senha"
            placeholder="Repita sua senha"
            secureTextEntry
            value={confirmarSenha}
            onChangeText={setConfirmarSenha}
            error={errors.confirmarSenha}
            returnKeyType="done"
          />

          <View style={[styles.switchRow, { marginTop: spacing.md }]}>
            <Switch
              value={aceiteTermos}
              onValueChange={setAceiteTermos}
              trackColor={{ false: colors.gray300, true: colors.primaryLight }}
              thumbColor={aceiteTermos ? colors.primary : colors.gray400}
              accessibilityLabel="Aceitar termos de uso"
            />
            <Text variant="body2" color={colors.textSecondary} style={{ flex: 1, marginLeft: 12 }}>
              Li e aceito os{' '}
              <Text variant="body2" color={colors.textLink}>Termos de Uso</Text>
              {' '}e{' '}
              <Text variant="body2" color={colors.textLink}>Política de Privacidade</Text>
            </Text>
          </View>
          {errors.termos && (
            <Text variant="caption" color={colors.error} style={{ marginTop: 4, marginLeft: 48 }}>
              {errors.termos}
            </Text>
          )}

          <View style={[styles.switchRow, { marginTop: spacing.md }]}>
            <Switch
              value={consentMarketing}
              onValueChange={setConsentMarketing}
              trackColor={{ false: colors.gray300, true: colors.primaryLight }}
              thumbColor={consentMarketing ? colors.primary : colors.gray400}
              accessibilityLabel="Consentimento de marketing"
            />
            <Text variant="body2" color={colors.textSecondary} style={{ flex: 1, marginLeft: 12 }}>
              Desejo receber ofertas e novidades por e-mail e push (LGPD - consentimento marketing)
            </Text>
          </View>

          <Button
            title="Criar conta"
            onPress={handleCadastro}
            loading={isLoading}
            fullWidth
            size="lg"
            style={{ marginTop: spacing.xl }}
          />

          {(googleAvailable || appleAvailable || facebookAvailable) && (
            <>
              <View style={styles.dividerRow}>
                <Divider style={{ flex: 1 }} />
                <Text variant="caption" color={colors.textDisabled} style={{ marginHorizontal: 12 }}>
                  ou cadastre-se com
                </Text>
                <Divider style={{ flex: 1 }} />
              </View>

              <View style={styles.socialRow}>
                {googleAvailable && (
                  <Button
                    title="Google"
                    onPress={() => handleSocialAction('google', signInWithGoogle)}
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
                    onPress={() => handleSocialAction('apple', signInWithApple)}
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
                    onPress={() => handleSocialAction('facebook', signInWithFacebook)}
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
            <Text variant="body2" color={colors.textSecondary}>Já tem conta? </Text>
            <TouchableOpacity onPress={() => router.back()} accessibilityLabel="Fazer login">
              <Text variant="body2" color={colors.textLink}>Fazer login</Text>
            </TouchableOpacity>
          </View>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  content: { paddingHorizontal: 24 },
  backBtn: { marginBottom: 24 },
  errorBox: { marginTop: 16, padding: 12, borderRadius: 8, marginBottom: 8 },
  switchRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
  },
  dividerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginVertical: 24,
  },
  socialRow: {
    flexDirection: 'row',
    marginBottom: 8,
  },
  footerRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginTop: 24,
  },
});
