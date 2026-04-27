import React from 'react';
import { View, StyleSheet, TouchableOpacity, ViewStyle } from 'react-native';
import * as Haptics from 'expo-haptics';
import { Text } from './Text';
import { useTheme } from '@/hooks/useTheme';

interface QuantitySelectorProps {
  value: number;
  min?: number;
  max?: number;
  onChange: (value: number) => void;
  size?: 'sm' | 'md';
  style?: ViewStyle;
}

export function QuantitySelector({
  value,
  min = 1,
  max = 99,
  onChange,
  size = 'md',
  style,
}: QuantitySelectorProps) {
  const { colors, borderRadius: br } = useTheme();

  const buttonSize = size === 'sm' ? 28 : 36;
  const canDecrease = value > min;
  const canIncrease = value < max;

  const handleChange = (delta: number) => {
    const next = value + delta;
    if (next >= min && next <= max) {
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
      onChange(next);
    }
  };

  return (
    <View
      style={[styles.container, { borderColor: colors.border, borderRadius: br.lg }, style]}
      accessibilityLabel={`Quantidade: ${value}`}
    >
      <TouchableOpacity
        onPress={() => handleChange(-1)}
        disabled={!canDecrease}
        style={[styles.button, { width: buttonSize, height: buttonSize }]}
        accessibilityLabel="Diminuir quantidade"
        accessibilityRole="button"
      >
        <Text variant="subtitle1" color={canDecrease ? colors.textPrimary : colors.textDisabled}>
          −
        </Text>
      </TouchableOpacity>
      <View style={[styles.value, { minWidth: buttonSize }]}>
        <Text variant="subtitle2" color={colors.textPrimary}>
          {value}
        </Text>
      </View>
      <TouchableOpacity
        onPress={() => handleChange(1)}
        disabled={!canIncrease}
        style={[styles.button, { width: buttonSize, height: buttonSize }]}
        accessibilityLabel="Aumentar quantidade"
        accessibilityRole="button"
      >
        <Text variant="subtitle1" color={canIncrease ? colors.primary : colors.textDisabled}>
          +
        </Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    overflow: 'hidden',
  },
  button: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  value: {
    alignItems: 'center',
    justifyContent: 'center',
  },
});
