import { Platform } from 'react-native';
import * as Haptics from 'expo-haptics';

function noopSafe(promise: Promise<void>): void {
  void promise.catch(() => {});
}

export function impactLight(): void {
  if (Platform.OS === 'web') return;
  noopSafe(Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light));
}

export function notifySuccess(): void {
  if (Platform.OS === 'web') return;
  noopSafe(Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success));
}
