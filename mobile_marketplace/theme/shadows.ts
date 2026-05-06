import { Platform, ViewStyle } from 'react-native';

/**
 * Sombras Ibix Market — paridade com `loja.css`:
 *   - sm  → cards de produto (`--loja-shadow-sm`, 0 1px 3px rgba(0,0,0,0.06))
 *   - md  → blocos de seção (`--loja-shadow-block`, 0 4px 12px rgba(0,0,0,0.08))
 *   - lg  → hero/destaques (`--loja-shadow-hero`, 0 8px 24px rgba(0,0,0,0.10))
 *   - xl  → modais flutuantes (extensão suave, mantida acima de lg)
 */
type ShadowLevel = 'none' | 'sm' | 'md' | 'lg' | 'xl';

const iosShadows: Record<ShadowLevel, ViewStyle> = {
  none: {},
  sm: { shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.06, shadowRadius: 3 },
  md: { shadowColor: '#000', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.08, shadowRadius: 12 },
  lg: { shadowColor: '#000', shadowOffset: { width: 0, height: 8 }, shadowOpacity: 0.10, shadowRadius: 24 },
  xl: { shadowColor: '#000', shadowOffset: { width: 0, height: 12 }, shadowOpacity: 0.14, shadowRadius: 32 },
};

const androidElevations: Record<ShadowLevel, ViewStyle> = {
  none: { elevation: 0 },
  sm: { elevation: 1 },
  md: { elevation: 3 },
  lg: { elevation: 6 },
  xl: { elevation: 12 },
};

export const shadow = (level: ShadowLevel): ViewStyle => {
  return Platform.OS === 'ios' ? iosShadows[level] : androidElevations[level];
};

export type { ShadowLevel };
