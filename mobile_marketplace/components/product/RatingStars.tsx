import React from 'react';
import { View, StyleSheet, ViewStyle } from 'react-native';
import { Text } from '@/components/ui';
import { useTheme } from '@/hooks/useTheme';

interface RatingStarsProps {
  rating: number;
  count?: number;
  size?: 'sm' | 'md';
  style?: ViewStyle;
}

export function RatingStars({ rating, count, size = 'md', style }: RatingStarsProps) {
  const { colors } = useTheme();
  const starSize = size === 'sm' ? 12 : 16;

  const stars = [];
  for (let i = 1; i <= 5; i++) {
    if (i <= Math.floor(rating)) {
      stars.push('★');
    } else if (i - 0.5 <= rating) {
      stars.push('★');
    } else {
      stars.push('☆');
    }
  }

  return (
    <View style={[styles.container, style]}>
      <Text
        variant={size === 'sm' ? 'caption' : 'body2'}
        color={colors.warning}
        style={{ fontSize: starSize, letterSpacing: 1 }}
      >
        {stars.join('')}
      </Text>
      {count !== undefined && (
        <Text variant="caption" color={colors.textSecondary} style={{ marginLeft: 4 }}>
          ({count})
        </Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
  },
});
