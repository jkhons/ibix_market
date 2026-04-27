import React from 'react';
import { TouchableOpacity, StyleSheet, View, ViewStyle } from 'react-native';
import { Text } from './Text';
import { useTheme } from '@/hooks/useTheme';

interface ChipProps {
  label: string;
  selected?: boolean;
  onPress?: () => void;
  icon?: React.ReactNode;
  style?: ViewStyle;
  accessibilityLabel?: string;
}

export function Chip({ label, selected = false, onPress, icon, style, accessibilityLabel }: ChipProps) {
  const { colors, borderRadius: br, spacing } = useTheme();

  const content = (
    <View style={styles.content}>
      {icon && <View style={styles.icon}>{icon}</View>}
      <Text
        variant="body2"
        color={selected ? colors.textInverse : colors.textPrimary}
      >
        {label}
      </Text>
    </View>
  );

  const chipStyle: ViewStyle = {
    backgroundColor: selected ? colors.primary : colors.surfaceVariant,
    borderRadius: br.full,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    borderWidth: selected ? 0 : 1,
    borderColor: colors.borderLight,
  };

  if (onPress) {
    return (
      <TouchableOpacity
        onPress={onPress}
        activeOpacity={0.7}
        style={[chipStyle, style]}
        accessibilityRole="button"
        accessibilityLabel={accessibilityLabel ?? label}
        accessibilityState={{ selected }}
      >
        {content}
      </TouchableOpacity>
    );
  }

  return <View style={[chipStyle, style]}>{content}</View>;
}

const styles = StyleSheet.create({
  content: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  icon: {
    marginRight: 6,
  },
});
