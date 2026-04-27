import React, { useEffect } from 'react';
import { View, StyleSheet, ViewStyle } from 'react-native';
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withTiming,
  interpolate,
} from 'react-native-reanimated';
import { useTheme } from '@/hooks/useTheme';

interface SkeletonProps {
  width?: number | string;
  height?: number;
  borderRadius?: number;
  radius?: number;
  style?: ViewStyle;
}

export function Skeleton({ width = '100%', height = 16, borderRadius = 8, radius, style }: SkeletonProps) {
  const effectiveRadius = radius ?? borderRadius;
  const { colors } = useTheme();
  const shimmer = useSharedValue(0);

  useEffect(() => {
    shimmer.value = withRepeat(withTiming(1, { duration: 1200 }), -1, true);
  }, []);

  const animatedStyle = useAnimatedStyle(() => ({
    opacity: interpolate(shimmer.value, [0, 1], [0.5, 1]),
  }));

  return (
    <Animated.View
      style={[
        {
          width: width as any,
          height,
          borderRadius: effectiveRadius,
          backgroundColor: colors.skeleton,
        },
        animatedStyle,
        style,
      ]}
      accessibilityLabel="Carregando"
    />
  );
}

export function SkeletonCard({ style }: { style?: ViewStyle }) {
  const { colors, borderRadius: br, spacing } = useTheme();
  return (
    <View style={[styles.card, { backgroundColor: colors.surface, borderRadius: br.lg, padding: spacing.md }, style]}>
      <Skeleton width="100%" height={160} borderRadius={br.md} />
      <View style={{ marginTop: spacing.sm }}>
        <Skeleton width="70%" height={14} />
        <Skeleton width="40%" height={12} style={{ marginTop: 8 }} />
        <Skeleton width="50%" height={18} style={{ marginTop: 8 }} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    overflow: 'hidden',
  },
});
