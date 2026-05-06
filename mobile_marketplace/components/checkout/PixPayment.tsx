import React, { useEffect, useState, useCallback } from 'react';
import { View, StyleSheet, ViewStyle } from 'react-native';
import * as Clipboard from 'expo-clipboard';
import { Text, Button } from '@/components/ui';
import { notifySuccess } from '@/utils/haptics';
import { useTheme } from '@/hooks/useTheme';

interface PixPaymentProps {
  copiaCola: string;
  expiracaoMinutos: number;
  onExpired?: () => void;
  style?: ViewStyle;
}

export function PixPayment({ copiaCola, expiracaoMinutos, onExpired, style }: PixPaymentProps) {
  const { colors, spacing, borderRadius: br } = useTheme();
  const [secondsLeft, setSecondsLeft] = useState(expiracaoMinutos * 60);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const timer = setInterval(() => {
      setSecondsLeft((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          onExpired?.();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const formatTime = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
  };

  const handleCopy = useCallback(async () => {
    await Clipboard.setStringAsync(copiaCola);
    notifySuccess();
    setCopied(true);
    setTimeout(() => setCopied(false), 3000);
  }, [copiaCola]);

  const isExpired = secondsLeft <= 0;
  const isUrgent = secondsLeft < 300;

  return (
    <View style={[styles.container, { backgroundColor: colors.surface, borderRadius: br.lg, padding: spacing.xl }, style]}>
      <Text variant="h4" color={colors.textPrimary} align="center">
        Pague com PIX
      </Text>

      <Text variant="caption" color={colors.textSecondary} align="center" style={{ marginTop: spacing.sm }}>
        Copie o código abaixo e cole no app do seu banco
      </Text>

      {/* Timer */}
      <View style={[styles.timerContainer, { marginTop: spacing.lg }]}>
        <Text variant="caption" color={isUrgent ? colors.error : colors.textSecondary}>
          {isExpired ? 'Código expirado' : `Expira em ${formatTime(secondsLeft)}`}
        </Text>
      </View>

      {/* Code display */}
      <View
        style={[
          styles.codeBox,
          { backgroundColor: colors.surfaceVariant, borderRadius: br.md, padding: spacing.md, marginTop: spacing.md },
        ]}
      >
        <Text variant="body2" color={colors.textPrimary} selectable style={{ lineHeight: 20 }}>
          {copiaCola}
        </Text>
      </View>

      <Button
        title={copied ? 'Copiado!' : 'Copiar código PIX'}
        onPress={handleCopy}
        variant={copied ? 'secondary' : 'primary'}
        fullWidth
        size="lg"
        disabled={isExpired}
        style={{ marginTop: spacing.lg }}
      />

      <Text variant="caption" color={colors.textSecondary} align="center" style={{ marginTop: spacing.lg }}>
        Assim que o pagamento for confirmado, você receberá uma notificação.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {},
  timerContainer: {
    alignItems: 'center',
  },
  codeBox: {},
});
