import React from 'react';
import { View, StyleSheet, ViewStyle } from 'react-native';
import { Image } from 'expo-image';
import { Text } from './Text';
import { useTheme } from '@/hooks/useTheme';
import { resolveRemoteAssetUrl } from '@/constants/config';

type AvatarSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl';

interface AvatarProps {
  uri?: string | null;
  name?: string;
  size?: AvatarSize;
  style?: ViewStyle;
}

const SIZE_MAP: Record<AvatarSize, number> = {
  xs: 28,
  sm: 36,
  md: 48,
  lg: 64,
  xl: 96,
};

function getInitials(name: string): string {
  return name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join('');
}

export function Avatar({ uri, name = '', size = 'md', style }: AvatarProps) {
  const { colors, borderRadius: br } = useTheme();
  const dim = SIZE_MAP[size];

  const containerStyle: ViewStyle = {
    width: dim,
    height: dim,
    borderRadius: dim / 2,
    backgroundColor: colors.primarySurface,
    overflow: 'hidden',
  };

  const resolvedUri = resolveRemoteAssetUrl(uri);
  if (resolvedUri) {
    return (
      <View style={[containerStyle, style]} accessibilityLabel={name || 'Avatar'}>
        <Image
          source={{ uri: resolvedUri }}
          style={{ width: dim, height: dim }}
          contentFit="cover"
          transition={200}
          recyclingKey={resolvedUri}
        />
      </View>
    );
  }

  const initials = getInitials(name);
  const fontSizeMap: Record<AvatarSize, number> = { xs: 10, sm: 12, md: 16, lg: 22, xl: 32 };

  return (
    <View style={[containerStyle, styles.initialsContainer, style]} accessibilityLabel={name || 'Avatar'}>
      <Text variant="button" color={colors.primary} style={{ fontSize: fontSizeMap[size] }}>
        {initials || '?'}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  initialsContainer: {
    alignItems: 'center',
    justifyContent: 'center',
  },
});
