import React from 'react';
import { View, StyleSheet } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Text } from '@/components/ui';
import { useTheme } from '@/hooks/useTheme';
import { useNetworkStatus } from '@/hooks/useNetworkStatus';

export function OfflineBanner() {
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const { isConnected } = useNetworkStatus();

  if (isConnected) return null;

  return (
    <View
      style={[
        styles.banner,
        { backgroundColor: colors.error, paddingTop: insets.top + 4, paddingBottom: 6 },
      ]}
      accessibilityLiveRegion="assertive"
      accessibilityLabel="Sem conexão com a internet"
    >
      <Text variant="caption" color={colors.white} align="center">
        Sem conexão com a internet
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  banner: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    zIndex: 9999,
    paddingHorizontal: 16,
  },
});
