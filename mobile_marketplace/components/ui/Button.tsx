import React from 'react';
import {
  TouchableOpacity,
  ActivityIndicator,
  StyleSheet,
  ViewStyle,
  TextStyle,
  View,
} from 'react-native';
import { Text } from './Text';
import { impactLight } from '@/utils/haptics';
import { useTheme } from '@/hooks/useTheme';

type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
type ButtonSize = 'sm' | 'md' | 'lg';

interface ButtonProps {
  title: string;
  onPress: () => void;
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  disabled?: boolean;
  icon?: React.ReactNode;
  iconRight?: React.ReactNode;
  fullWidth?: boolean;
  style?: ViewStyle;
  textStyle?: TextStyle;
  haptic?: boolean;
  accessibilityLabel?: string;
}

const SIZE_MAP: Record<ButtonSize, { height: number; paddingHorizontal: number; fontSize: number }> = {
  sm: { height: 36, paddingHorizontal: 12, fontSize: 13 },
  md: { height: 48, paddingHorizontal: 20, fontSize: 15 },
  lg: { height: 56, paddingHorizontal: 24, fontSize: 17 },
};

export function Button({
  title,
  onPress,
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled = false,
  icon,
  iconRight,
  fullWidth = false,
  style,
  textStyle,
  haptic = true,
  accessibilityLabel,
}: ButtonProps) {
  const { colors, borderRadius: br, fontFamily } = useTheme();

  const sizeStyle = SIZE_MAP[size];

  const variantStyles = {
    primary: {
      bg: colors.primary,
      text: colors.textInverse,
      border: colors.primary,
      bgDisabled: colors.gray300,
    },
    secondary: {
      bg: colors.primarySurface,
      text: colors.primary,
      border: colors.primarySurface,
      bgDisabled: colors.gray100,
    },
    outline: {
      bg: 'transparent',
      text: colors.primary,
      border: colors.primary,
      bgDisabled: 'transparent',
    },
    ghost: {
      bg: 'transparent',
      text: colors.primary,
      border: 'transparent',
      bgDisabled: 'transparent',
    },
    danger: {
      bg: colors.error,
      text: colors.textInverse,
      border: colors.error,
      bgDisabled: colors.gray300,
    },
  };

  const v = variantStyles[variant];
  const isDisabled = disabled || loading;

  const handlePress = () => {
    if (haptic) impactLight();
    onPress();
  };

  return (
    <TouchableOpacity
      onPress={handlePress}
      disabled={isDisabled}
      activeOpacity={0.7}
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel ?? title}
      accessibilityState={{ disabled: isDisabled }}
      style={[
        styles.container,
        {
          height: sizeStyle.height,
          paddingHorizontal: sizeStyle.paddingHorizontal,
          backgroundColor: isDisabled ? v.bgDisabled : v.bg,
          borderColor: isDisabled ? colors.gray300 : v.border,
          borderRadius: br.lg,
        },
        variant === 'outline' && styles.border,
        fullWidth && styles.fullWidth,
        style,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={v.text} size="small" />
      ) : (
        <View style={styles.content}>
          {icon && <View style={styles.iconLeft}>{icon}</View>}
          <Text
            variant="button"
            color={isDisabled ? colors.textDisabled : v.text}
            style={[{ fontSize: sizeStyle.fontSize }, textStyle]}
          >
            {title}
          </Text>
          {iconRight && <View style={styles.iconRight}>{iconRight}</View>}
        </View>
      )}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  border: {
    borderWidth: 1.5,
  },
  fullWidth: {
    width: '100%',
  },
  content: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  iconLeft: {
    marginRight: 8,
  },
  iconRight: {
    marginLeft: 8,
  },
});
