import { useEffect, useState, useCallback } from 'react';
import { Alert, Linking, Platform } from 'react-native';
import Constants from 'expo-constants';
import { api } from '@/services/api';

interface AppVersionResponse {
  versao_minima: string;
  versao_recomendada: string;
  url_atualizacao_ios?: string;
  url_atualizacao_android?: string;
  mensagem?: string;
}

function compareVersions(current: string, target: string): number {
  const a = current.split('.').map(Number);
  const b = target.split('.').map(Number);
  for (let i = 0; i < 3; i++) {
    const diff = (a[i] ?? 0) - (b[i] ?? 0);
    if (diff !== 0) return diff;
  }
  return 0;
}

export function useForceUpdate() {
  const [updateRequired, setUpdateRequired] = useState(false);
  const [updateRecommended, setUpdateRecommended] = useState(false);

  const checkVersion = useCallback(async () => {
    try {
      const currentVersion = Constants.expoConfig?.version ?? '1.0.0';
      const plataforma = Platform.OS === 'ios' ? 'ios' : 'android';

      const { data } = await api.get<AppVersionResponse>(
        `/loja/app/versao?plataforma=${plataforma}`,
      );

      if (compareVersions(currentVersion, data.versao_minima) < 0) {
        setUpdateRequired(true);
        const url = Platform.OS === 'ios' ? data.url_atualizacao_ios : data.url_atualizacao_android;
        Alert.alert(
          'Atualização Obrigatória',
          data.mensagem ?? 'Uma nova versão obrigatória está disponível. Atualize para continuar.',
          [
            {
              text: 'Atualizar',
              onPress: () => {
                if (url) Linking.openURL(url);
              },
            },
          ],
          { cancelable: false },
        );
      } else if (compareVersions(currentVersion, data.versao_recomendada) < 0) {
        setUpdateRecommended(true);
      }
    } catch {
      // Silently fail — don't block user
    }
  }, []);

  useEffect(() => {
    checkVersion();
  }, [checkVersion]);

  return { updateRequired, updateRecommended, checkVersion };
}
