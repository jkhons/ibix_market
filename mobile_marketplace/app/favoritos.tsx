import React from 'react';
import { View, StyleSheet, TouchableOpacity } from 'react-native';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { FlashList } from '@shopify/flash-list';
import { Image } from 'expo-image';
import { Text, EmptyState, Skeleton } from '@/components/ui';
import { useTheme } from '@/hooks/useTheme';
import favoriteService from '@/services/favoriteService';
import { QUERY_KEYS } from '@/constants/config';
import { formatCurrency } from '@/utils/format';

export default function FavoritosScreen() {
  const { colors, spacing, borderRadius: br } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: [QUERY_KEYS.FAVORITES],
    queryFn: () => favoriteService.getFavorites(),
  });

  const removeMutation = useMutation({
    mutationFn: (produtoId: number) => favoriteService.removeFavorite(produtoId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.FAVORITES] });
    },
  });

  return (
    <View style={[styles.container, { backgroundColor: colors.background, paddingTop: insets.top + spacing.md }]}>
      <View style={[styles.header, { paddingHorizontal: spacing.lg }]}>
        <TouchableOpacity onPress={() => router.back()} accessibilityLabel="Voltar">
          <Text variant="body1" color={colors.textSecondary}>← Voltar</Text>
        </TouchableOpacity>
        <Text variant="h3" color={colors.textPrimary} style={{ marginTop: spacing.md }}>
          Favoritos
        </Text>
      </View>

      {isLoading ? (
        <View style={{ padding: spacing.lg }}>
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} width="100%" height={80} style={{ marginBottom: 12 }} />
          ))}
        </View>
      ) : !data?.items?.length ? (
        <EmptyState
          title="Nenhum favorito"
          description="Salve seus produtos favoritos para encontrá-los facilmente"
          actionTitle="Explorar"
          onAction={() => router.push('/(tabs)')}
        />
      ) : (
        <FlashList
          data={data.items}
          estimatedItemSize={90}
          contentContainerStyle={{ paddingHorizontal: spacing.lg }}
          renderItem={({ item }) => (
            <TouchableOpacity
              onPress={() => router.push(`/produto/${item.produto_id}`)}
              style={[styles.row, { borderBottomColor: colors.divider }]}
              accessibilityLabel={item.produto_nome}
            >
              {item.produto_imagem && (
                <Image
                  source={{ uri: item.produto_imagem }}
                  style={[styles.thumb, { borderRadius: br.md }]}
                  contentFit="cover"
                />
              )}
              <View style={{ flex: 1, marginLeft: spacing.md }}>
                <Text variant="body1" color={colors.textPrimary} numberOfLines={2}>
                  {item.produto_nome}
                </Text>
                <Text variant="priceSmall" color={colors.success} style={{ marginTop: 4 }}>
                  {formatCurrency(item.produto_preco)}
                </Text>
              </View>
              <TouchableOpacity
                onPress={() => removeMutation.mutate(item.produto_id)}
                hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
                accessibilityLabel="Remover dos favoritos"
              >
                <Text variant="body2" color={colors.error}>✕</Text>
              </TouchableOpacity>
            </TouchableOpacity>
          )}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: {},
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  thumb: { width: 64, height: 64 },
});
