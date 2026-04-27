import { Platform, ViewStyle } from 'react-native';

type ShadowLevel = 'none' | 'sm' | 'md' | 'lg' | 'xl';

const iosShadows: Record<ShadowLevel, ViewStyle> = {
  none: {},
  sm: { shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.05, shadowRadius: 2 },
  md: { shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.08, shadowRadius: 4 },
  lg: { shadowColor: '#000', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.12, shadowRadius: 8 },
  xl: { shadowColor: '#000', shadowOffset: { width: 0, height: 8 }, shadowOpacity: 0.16, shadowRadius: 16 },
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
