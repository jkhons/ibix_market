import React, { useRef, useEffect, useState, useCallback } from 'react';
import {
  View,
  StyleSheet,
  FlatList,
  useWindowDimensions,
  TouchableOpacity,
  ViewToken,
} from 'react-native';
import { Image } from 'expo-image';
import { useRouter } from 'expo-router';
import { useTheme } from '@/hooks/useTheme';
import type { MarketingCard } from '@/services/marketingService';

interface BannerCarouselProps {
  cards: MarketingCard[];
  autoPlayMs?: number;
}

export function BannerCarousel({ cards, autoPlayMs = 5000 }: BannerCarouselProps) {
  const { colors, spacing, borderRadius: br } = useTheme();
  const { width } = useWindowDimensions();
  const router = useRouter();
  const listRef = useRef<FlatList>(null);
  const [activeIndex, setActiveIndex] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval>>();

  const bannerWidth = width - spacing.lg * 2;
  const bannerHeight = bannerWidth * 0.45;

  const onViewableItemsChanged = useCallback(({ viewableItems }: { viewableItems: ViewToken[] }) => {
    if (viewableItems.length > 0 && viewableItems[0].index != null) {
      setActiveIndex(viewableItems[0].index);
    }
  }, []);

  useEffect(() => {
    if (cards.length <= 1) return;
    timerRef.current = setInterval(() => {
      setActiveIndex((prev) => {
        const next = (prev + 1) % cards.length;
        listRef.current?.scrollToIndex({ index: next, animated: true });
        return next;
      });
    }, autoPlayMs);
    return () => clearInterval(timerRef.current);
  }, [cards.length, autoPlayMs]);

  const handlePress = (card: MarketingCard) => {
    if (card.anuncio_id) {
      router.push(`/produto/${card.anuncio_id}`);
    } else if (card.categoria_id) {
      router.push(`/categoria/${card.categoria_id}`);
    } else if (card.link) {
      router.push(card.link as any);
    }
  };

  if (!cards.length) return null;

  return (
    <View style={{ marginTop: spacing.lg }}>
      <FlatList
        ref={listRef}
        data={cards}
        horizontal
        pagingEnabled
        showsHorizontalScrollIndicator={false}
        snapToInterval={bannerWidth + spacing.sm}
        decelerationRate="fast"
        contentContainerStyle={{ paddingHorizontal: spacing.lg }}
        onViewableItemsChanged={onViewableItemsChanged}
        viewabilityConfig={{ itemVisiblePercentThreshold: 50 }}
        keyExtractor={(item) => String(item.id)}
        renderItem={({ item }) => (
          <TouchableOpacity
            onPress={() => handlePress(item)}
            activeOpacity={0.9}
            accessibilityLabel={item.titulo ?? 'Banner promocional'}
          >
            <Image
              source={{ uri: item.imagem_url_mobile ?? item.imagem_url }}
              style={[
                styles.banner,
                { width: bannerWidth, height: bannerHeight, borderRadius: br.lg },
              ]}
              contentFit="cover"
              transition={300}
            />
          </TouchableOpacity>
        )}
        ItemSeparatorComponent={() => <View style={{ width: spacing.sm }} />}
      />

      {cards.length > 1 && (
        <View style={styles.indicators}>
          {cards.map((_, i) => (
            <View
              key={i}
              style={[
                styles.dot,
                {
                  backgroundColor: i === activeIndex ? colors.primary : colors.gray300,
                  width: i === activeIndex ? 20 : 6,
                },
              ]}
            />
          ))}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  banner: {
    overflow: 'hidden',
  },
  indicators: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 10,
    gap: 4,
  },
  dot: {
    height: 6,
    borderRadius: 3,
  },
});
