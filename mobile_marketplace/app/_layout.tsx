import React, { useCallback, useEffect, useState } from 'react';
import { View, StyleSheet } from 'react-native';
import { Stack } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import * as Font from 'expo-font';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider, useTheme } from '@/hooks/useTheme';
import { useAuthStore } from '@/store/authStore';
import { useCartStore } from '@/store/cartStore';
import { useRecentlyViewedStore } from '@/store/recentlyViewedStore';
import { useGeoStore } from '@/store/geoStore';
import { useForceUpdate } from '@/hooks/useForceUpdate';
import { OfflineBanner } from '@/components/common/OfflineBanner';
import { initSentry } from '@/utils/sentry';

SplashScreen.preventAutoHideAsync();

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,
      gcTime: 1000 * 60 * 30,
      retry: 2,
      refetchOnWindowFocus: false,
    },
  },
});

function AppStartupEffects() {
  const { updateRequired } = useForceUpdate();

  useEffect(() => {
    useAuthStore.getState().hydrate();
    useCartStore.getState().hydrate();
    useRecentlyViewedStore.getState().hydrate();
    useGeoStore.getState().hydrate();
  }, []);

  return null;
}

function InnerLayout() {
  const { colors, isDark } = useTheme();

  return (
    <>
      <StatusBar style={isDark ? 'light' : 'dark'} />
      <AppStartupEffects />
      <OfflineBanner />
      <Stack
        screenOptions={{
          headerShown: false,
          contentStyle: { backgroundColor: colors.background },
          animation: 'slide_from_right',
        }}
      >
        <Stack.Screen name="(tabs)" options={{ animation: 'none' }} />
        <Stack.Screen name="(auth)" options={{ animation: 'slide_from_bottom' }} />
        <Stack.Screen name="produto/[id]" options={{ animation: 'slide_from_right' }} />
        <Stack.Screen name="loja/[slug]" options={{ animation: 'slide_from_right' }} />
        <Stack.Screen name="categoria/[id]" options={{ animation: 'slide_from_right' }} />
        <Stack.Screen name="busca" options={{ animation: 'slide_from_bottom' }} />
        <Stack.Screen name="favoritos" options={{ animation: 'slide_from_right' }} />
        <Stack.Screen name="notificacoes" options={{ animation: 'slide_from_right' }} />
        <Stack.Screen name="checkout" options={{ animation: 'slide_from_right', gestureEnabled: false }} />
        <Stack.Screen name="pedido/[numero]" options={{ animation: 'slide_from_right' }} />
        <Stack.Screen name="chat/index" options={{ animation: 'slide_from_right' }} />
        <Stack.Screen name="chat/[id]" options={{ animation: 'slide_from_right' }} />
        <Stack.Screen name="conta/enderecos" options={{ animation: 'slide_from_right' }} />
      </Stack>
    </>
  );
}

export default function RootLayout() {
  const [appReady, setAppReady] = useState(false);

  useEffect(() => {
    initSentry();

    async function prepare() {
      try {
        await Font.loadAsync({
          Inter_400Regular: require('@/assets/fonts/Inter-Regular.ttf'),
          Inter_500Medium: require('@/assets/fonts/Inter-Medium.ttf'),
          Inter_600SemiBold: require('@/assets/fonts/Inter-SemiBold.ttf'),
          Inter_700Bold: require('@/assets/fonts/Inter-Bold.ttf'),
        });
      } catch (e) {
        console.warn('Font loading failed:', e);
      } finally {
        setAppReady(true);
      }
    }
    prepare();
  }, []);

  const onLayoutRootView = useCallback(async () => {
    if (appReady) {
      await SplashScreen.hideAsync();
    }
  }, [appReady]);

  if (!appReady) return null;

  return (
    <GestureHandlerRootView style={styles.root}>
      <SafeAreaProvider>
        <QueryClientProvider client={queryClient}>
          <ThemeProvider>
            <View style={styles.root} onLayout={onLayoutRootView}>
              <InnerLayout />
            </View>
          </ThemeProvider>
        </QueryClientProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
});
