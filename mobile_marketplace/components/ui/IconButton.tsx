import React from 'react';
import { TouchableOpacity, StyleSheet, ViewStyle } from 'react-native';
import * as Haptics from 'expo-haptics';
import { useTheme } from '@/hooks/useTheme';

interface IconButtonProps {
  icon: React.ReactNode;
  onPress: () => void;
  size?: number;
  backgroundColor?: string;
  disabled?: boolean;
  style?: ViewStyle;
  accessibilityLabel: string;
  haptic?: boolean;
}

export function IconButton({
  icon,
  onPress,
  size = 44,
  backgroundColor,
  disabled = false,
  style,
  accessibilityLabel,
  haptic = true,
}: IconButtonProps) {
  const { colors, borderRadius: br, hitSlop: hs } = useTheme();

  const handlePress = () => {
    if (haptic) Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    onPress();
  };

  return (
    <TouchableOpacity
      onPress={handlePress}
      disabled={disabled}
      activeOpacity={0.6}
      hitSlop={hs}
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel}
      accessibilityState={{ disabled }}
      style={[
        {
          width: size,
          height: size,
          borderRadius: size / 2,
          backgroundColor: backgroundColor ?? colors.transparent,
          alignItems: 'center',
          justifyContent: 'center',
          opacity: disabled ? 0.4 : 1,
        },
        style,
      ]}
    >
      {icon}
    </TouchableOpacity>
  );
}
