import React from 'react';
import { View, ViewStyle } from 'react-native';
import { useTheme } from '@/hooks/useTheme';

interface DividerProps {
  style?: ViewStyle;
  vertical?: boolean;
  thickness?: number;
  color?: string;
}

export function Divider({ style, vertical = false, thickness = 1, color }: DividerProps) {
  const { colors } = useTheme();

  return (
    <View
      style={[
        vertical
          ? { width: thickness, alignSelf: 'stretch' }
          : { height: thickness, width: '100%' },
        { backgroundColor: color ?? colors.divider },
        style,
      ]}
    />
  );
}
