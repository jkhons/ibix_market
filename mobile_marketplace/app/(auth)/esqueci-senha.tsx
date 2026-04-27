import React, { useState } from 'react';
import {
  View,
  ScrollView,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  TouchableOpacity,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Text, Button, Input } from '@/components/ui';
import { useTheme } from '@/hooks/useTheme';
import authService from '@/services/authService';
import { extractApiError } from '@/services/api';

export default function EsqueciSenhaScreen() {
  const { colors, spacing } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();

  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async () => {
    if (!email.trim() || !email.includes('@')) {
      setError('Informe um e-mail válido');
      return;
    }
    setError('');
    setLoading(true);
    try {
      await authService.forgotPassword({ email: email.trim() });
      setSent(true);
    } catch (err) {
      setError(extractApiError(err));
    } finally {
      setLoading(false);
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

        <Text variant="h2" color={colors.textPrimary}>Esqueci minha senha</Text>
        <Text variant="body2" color={colors.textSecondary} style={{ marginTop: spacing.sm }}>
          {sent
            ? 'Se este e-mail estiver cadastrado, você receberá um link para redefinir sua senha.'
            : 'Informe seu e-mail e enviaremos um link para redefinir sua senha.'}
        </Text>

        {!sent ? (
          <View style={{ marginTop: spacing['2xl'] }}>
            {error ? (
              <View style={[styles.errorBox, { backgroundColor: colors.errorSurface }]}>
                <Text variant="body2" color={colors.error}>{error}</Text>
              </View>
            ) : null}
            <Input
              label="E-mail"
              placeholder="seu@email.com"
              keyboardType="email-address"
              autoCapitalize="none"
              autoComplete="email"
              value={email}
              onChangeText={setEmail}
              returnKeyType="done"
              onSubmitEditing={handleSubmit}
            />
            <Button
              title="Enviar link"
              onPress={handleSubmit}
              loading={loading}
              fullWidth
              size="lg"
              style={{ marginTop: spacing.md }}
            />
          </View>
        ) : (
          <Button
            title="Voltar ao login"
            onPress={() => router.back()}
            variant="outline"
            fullWidth
            size="lg"
            style={{ marginTop: spacing['2xl'] }}
          />
        )}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  content: { paddingHorizontal: 24 },
  backBtn: { marginBottom: 24 },
  errorBox: { marginTop: 16, padding: 12, borderRadius: 8, marginBottom: 8 },
});
