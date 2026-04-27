import React from 'react';
import { View, StyleSheet, ViewStyle } from 'react-native';
import { Text } from './Text';
import { Button } from './Button';
import { useTheme } from '@/hooks/useTheme';

interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  actionTitle?: string;
  actionLabel?: string;
  onAction?: () => void;
  style?: ViewStyle;
}

export function EmptyState({ icon, title, description, actionTitle, actionLabel, onAction, style }: EmptyStateProps) {
  const effectiveActionTitle = actionTitle ?? actionLabel;
  const { colors, spacing } = useTheme();

  return (
    <View style={[styles.container, style]} accessibilityLabel={title}>
      {icon && <View style={styles.icon}>{icon}</View>}
      <Text variant="h4" color={colors.textPrimary} align="center">
        {title}
      </Text>
      {description && (
        <Text
          variant="body2"
          color={colors.textSecondary}
          align="center"
          style={{ marginTop: spacing.sm, maxWidth: 280 }}
        >
          {description}
        </Text>
      )}
      {effectiveActionTitle && onAction && (
        <Button
          title={effectiveActionTitle}
          onPress={onAction}
          variant="primary"
          size="md"
          style={{ marginTop: spacing.xl }}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 32,
    paddingVertical: 48,
  },
  icon: {
    marginBottom: 16,
  },
});
