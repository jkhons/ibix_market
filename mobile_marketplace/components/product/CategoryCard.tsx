import React from 'react';
import { TouchableOpacity, StyleSheet, View } from 'react-native';
import { Image } from 'expo-image';
import { useRouter } from 'expo-router';
import { Text } from '@/components/ui';
import { useTheme } from '@/hooks/useTheme';
import type { Category } from '@/services/catalogService';

interface CategoryCardProps {
  category: Category;
  size?: 'sm' | 'md';
}

export function CategoryCard({ category, size = 'md' }: CategoryCardProps) {
  const { colors, spacing, borderRadius: br } = useTheme();
  const router = useRouter();

  const dim = size === 'sm' ? 64 : 80;

  return (
    <TouchableOpacity
      onPress={() => router.push(`/categoria/${category.id}`)}
      style={styles.container}
      accessibilityLabel={category.nome}
    >
      <View
        style={[
          styles.iconContainer,
          { width: dim, height: dim, borderRadius: dim / 2, backgroundColor: colors.primarySurface },
        ]}
      >
        {category.icone_url ? (
          <Image
            source={{ uri: category.icone_url }}
            style={{ width: dim * 0.6, height: dim * 0.6 }}
            contentFit="contain"
          />
        ) : (
          <Text variant="h4" color={colors.primary}>
            {category.nome.charAt(0)}
          </Text>
        )}
      </View>
      <Text
        variant="caption"
        color={colors.textPrimary}
        align="center"
        numberOfLines={2}
        style={{ marginTop: spacing.xs, width: dim + 16 }}
      >
        {category.nome}
      </Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    marginRight: 12,
  },
  iconContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
  },
});
