import { Stack } from 'expo-router';
import { useTheme } from '@/hooks/useTheme';

export default function CheckoutLayout() {
  const { colors } = useTheme();

  return (
    <Stack
      screenOptions={{
        headerStyle: { backgroundColor: colors.surface },
        headerTintColor: colors.textPrimary,
        headerShadowVisible: false,
        animation: 'slide_from_right',
        gestureEnabled: false,
      }}
    >
      <Stack.Screen name="endereco" options={{ title: 'Endereço de Entrega' }} />
      <Stack.Screen name="frete" options={{ title: 'Frete' }} />
      <Stack.Screen name="pagamento" options={{ title: 'Pagamento' }} />
      <Stack.Screen name="confirmacao" options={{ title: 'Confirmação', headerShown: false }} />
    </Stack>
  );
}
