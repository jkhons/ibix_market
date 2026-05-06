import React from 'react';
import { View, ViewStyle } from 'react-native';
import { Image } from 'expo-image';
import { brand } from '@/assets/brand';

interface BrandLogoProps {
  /** Altura em pixels do logo (largura calculada por aspect-ratio do `cab.png`). */
  height?: number;
  /** Variante: header (cabeçalho) ou rodape (fundos escuros). */
  variant?: 'header' | 'footer';
  style?: ViewStyle;
}

const ASPECT = {
  header: 1412 / 436,
  footer: 833 / 336,
};

/**
 * Logo Ibix Market — fonte canônica é `app/static/img/ibix/cab.png` (vitrine web).
 * Substitui qualquer texto "Ibix Market" no app: o usuário SEMPRE vê o logo gráfico,
 * idêntico ao da vitrine. Não use textos como brand — use este componente.
 */
export function BrandLogo({ height = 32, variant = 'header', style }: BrandLogoProps) {
  const aspectRatio = ASPECT[variant];
  const source = variant === 'header' ? brand.cabPng : brand.rodapePng;

  return (
    <View
      accessible
      accessibilityLabel="Ibix Market"
      accessibilityRole="image"
      style={[{ height, aspectRatio }, style]}
    >
      <Image
        source={source}
        style={{ width: '100%', height: '100%' }}
        contentFit="contain"
        transition={120}
      />
    </View>
  );
}
