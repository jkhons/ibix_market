import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Platform } from 'react-native';
import * as WebBrowser from 'expo-web-browser';
import * as Google from 'expo-auth-session/providers/google';
import * as Facebook from 'expo-auth-session/providers/facebook';
import * as AppleAuthentication from 'expo-apple-authentication';
import { useQuery } from '@tanstack/react-query';

import authService, { type SocialConfig } from '@/services/authService';
import { useAuthStore } from '@/store/authStore';
import { QUERY_KEYS } from '@/constants/config';
import ENV from '@/constants/config';

WebBrowser.maybeCompleteAuthSession();

export type SocialAuthOutcome =
  | { status: 'authenticated' }
  | { status: 'pending_link'; linkToken: string; requiresPassword?: boolean }
  | { status: 'cancelled' }
  | { status: 'unsupported' }
  | { status: 'error'; message: string };

export function useSocialAuth() {
  const { socialLogin, appleSignIn } = useAuthStore();

  const configQuery = useQuery<SocialConfig>({
    queryKey: [QUERY_KEYS.CONSUMER_PROFILE, 'social-config'],
    queryFn: () => authService.getSocialConfig(),
    staleTime: 5 * 60 * 1000,
  });

  const googleClientIds = useMemo(
    () => ({
      androidClientId:
        ENV.GOOGLE_ANDROID_CLIENT_ID ||
        configQuery.data?.google_client_id ||
        undefined,
      iosClientId:
        ENV.GOOGLE_IOS_CLIENT_ID ||
        configQuery.data?.google_client_id ||
        undefined,
      webClientId:
        ENV.GOOGLE_WEB_CLIENT_ID ||
        configQuery.data?.google_client_id ||
        undefined,
    }),
    [configQuery.data],
  );

  const [, googleResponse, googlePromptAsync] = Google.useIdTokenAuthRequest({
    clientId: googleClientIds.webClientId,
    iosClientId: googleClientIds.iosClientId,
    androidClientId: googleClientIds.androidClientId,
    selectAccount: true,
  });

  const [, fbResponse, fbPromptAsync] = Facebook.useAuthRequest({
    clientId: configQuery.data?.facebook_app_id ?? undefined,
  });

  const googleResolverRef = useRef<((outcome: SocialAuthOutcome) => void) | null>(null);
  const facebookResolverRef = useRef<((outcome: SocialAuthOutcome) => void) | null>(null);

  useEffect(() => {
    const resolver = googleResolverRef.current;
    if (!resolver || !googleResponse) return;
    googleResolverRef.current = null;
    if (googleResponse.type === 'success') {
      const idToken = (googleResponse.params as { id_token?: string }).id_token;
      const accessToken = (googleResponse.authentication?.accessToken) ?? undefined;
      socialLogin({ provider: 'google', id_token: idToken, access_token: accessToken })
        .then((res) => {
          if (res.status === 'authenticated') resolver({ status: 'authenticated' });
          else
            resolver({
              status: 'pending_link',
              linkToken: res.link_token ?? '',
              requiresPassword: res.requires_password ?? false,
            });
        })
        .catch((err: unknown) => resolver({ status: 'error', message: String(err) }));
    } else if (googleResponse.type === 'cancel' || googleResponse.type === 'dismiss') {
      resolver({ status: 'cancelled' });
    } else if (googleResponse.type === 'error') {
      resolver({ status: 'error', message: googleResponse.error?.message ?? 'Google error' });
    }
  }, [googleResponse, socialLogin]);

  useEffect(() => {
    const resolver = facebookResolverRef.current;
    if (!resolver || !fbResponse) return;
    facebookResolverRef.current = null;
    if (fbResponse.type === 'success') {
      const accessToken = fbResponse.authentication?.accessToken;
      if (!accessToken) {
        resolver({ status: 'error', message: 'Facebook não retornou token' });
        return;
      }
      socialLogin({ provider: 'facebook', access_token: accessToken })
        .then((res) => {
          if (res.status === 'authenticated') resolver({ status: 'authenticated' });
          else
            resolver({
              status: 'pending_link',
              linkToken: res.link_token ?? '',
              requiresPassword: res.requires_password ?? false,
            });
        })
        .catch((err: unknown) => resolver({ status: 'error', message: String(err) }));
    } else if (fbResponse.type === 'cancel' || fbResponse.type === 'dismiss') {
      resolver({ status: 'cancelled' });
    } else if (fbResponse.type === 'error') {
      resolver({ status: 'error', message: fbResponse.error?.message ?? 'Facebook error' });
    }
  }, [fbResponse, socialLogin]);

  const [appleAvailable, setAppleAvailable] = useState(false);
  useEffect(() => {
    if (Platform.OS !== 'ios') return;
    AppleAuthentication.isAvailableAsync()
      .then(setAppleAvailable)
      .catch(() => setAppleAvailable(false));
  }, []);

  const signInWithGoogle = useCallback(async (): Promise<SocialAuthOutcome> => {
    if (!googleClientIds.webClientId && !googleClientIds.androidClientId && !googleClientIds.iosClientId) {
      return { status: 'unsupported' };
    }
    return new Promise<SocialAuthOutcome>((resolve) => {
      googleResolverRef.current = resolve;
      googlePromptAsync().catch((err: unknown) => {
        googleResolverRef.current = null;
        resolve({ status: 'error', message: String(err) });
      });
    });
  }, [googleClientIds, googlePromptAsync]);

  const signInWithFacebook = useCallback(async (): Promise<SocialAuthOutcome> => {
    if (!configQuery.data?.facebook_app_id) {
      return { status: 'unsupported' };
    }
    return new Promise<SocialAuthOutcome>((resolve) => {
      facebookResolverRef.current = resolve;
      fbPromptAsync().catch((err: unknown) => {
        facebookResolverRef.current = null;
        resolve({ status: 'error', message: String(err) });
      });
    });
  }, [configQuery.data?.facebook_app_id, fbPromptAsync]);

  const signInWithApple = useCallback(async (): Promise<SocialAuthOutcome> => {
    if (Platform.OS !== 'ios' || !appleAvailable) return { status: 'unsupported' };
    try {
      const credential = await AppleAuthentication.signInAsync({
        requestedScopes: [
          AppleAuthentication.AppleAuthenticationScope.FULL_NAME,
          AppleAuthentication.AppleAuthenticationScope.EMAIL,
        ],
      });
      if (!credential.identityToken) {
        return { status: 'error', message: 'Apple não retornou identityToken' };
      }
      const nome = credential.fullName
        ? [credential.fullName.givenName, credential.fullName.familyName].filter(Boolean).join(' ').trim() || undefined
        : undefined;
      await appleSignIn({
        id_token: credential.identityToken,
        authorization_code: credential.authorizationCode ?? undefined,
        nome,
      });
      return { status: 'authenticated' };
    } catch (err: unknown) {
      const code = (err as { code?: string })?.code;
      if (code === 'ERR_REQUEST_CANCELED') return { status: 'cancelled' };
      return { status: 'error', message: String(err) };
    }
  }, [appleAvailable, appleSignIn]);

  return {
    config: configQuery.data,
    isConfigLoading: configQuery.isLoading,
    googleAvailable: !!(
      googleClientIds.webClientId ||
      googleClientIds.androidClientId ||
      googleClientIds.iosClientId
    ),
    facebookAvailable: !!configQuery.data?.facebook_app_id,
    appleAvailable: Platform.OS === 'ios' && appleAvailable,
    signInWithGoogle,
    signInWithFacebook,
    signInWithApple,
  };
}
