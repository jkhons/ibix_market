import React, { useCallback, useEffect } from 'react';
import { View, StyleSheet, Dimensions } from 'react-native';
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withTiming,
  withDelay,
  runOnJS,
} from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Text } from './Text';
import { useTheme } from '@/hooks/useTheme';

type ToastType = 'success' | 'error' | 'warning' | 'info';

interface ToastProps {
  message: string;
  type?: ToastType;
  visible: boolean;
  duration?: number;
  onDismiss: () => void;
}

const { width: SCREEN_WIDTH } = Dimensions.get('window');

export function Toast({ message, type = 'info', visible, duration = 3000, onDismiss }: ToastProps) {
  const { colors, borderRadius: br, spacing, shadow: shadowFn } = useTheme();
  const insets = useSafeAreaInsets();
  const translateY = useSharedValue(-100);

  const bgColors: Record<ToastType, string> = {
    success: colors.success,
    error: colors.error,
    warning: colors.warning,
    info: colors.primary,
  };

  useEffect(() => {
    if (visible) {
      translateY.value = withTiming(0, { duration: 250 });
      translateY.value = withDelay(
        duration,
        withTiming(-100, { duration: 250 }, () => {
          runOnJS(onDismiss)();
        }),
      );
    } else {
      translateY.value = withTiming(-100, { duration: 250 });
    }
  }, [visible]);

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ translateY: translateY.value }],
  }));

  if (!visible && translateY.value <= -100) return null;

  return (
    <Animated.View
      style={[
        styles.container,
        {
          top: insets.top + 8,
          backgroundColor: bgColors[type],
          borderRadius: br.lg,
          marginHorizontal: spacing.lg,
          ...shadowFn('lg'),
        },
        animatedStyle,
      ]}
      accessibilityLiveRegion="polite"
      accessibilityLabel={message}
    >
      <Text variant="body2" color={colors.white} numberOfLines={3}>
        {message}
      </Text>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    left: 0,
    right: 0,
    zIndex: 9999,
    paddingHorizontal: 16,
    paddingVertical: 14,
  },
});
