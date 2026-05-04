import React, { useState, useCallback } from 'react';
import { View, StyleSheet, ScrollView, TextInput, Alert } from 'react-native';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import { Text, Button, Skeleton, Input } from '@/components/ui';
import { AddressCard } from '@/components/checkout';
import { useTheme } from '@/hooks/useTheme';
import addressService, { type Address, type AddressPayload } from '@/services/addressService';
import { extractApiError } from '@/services/api';
import { QUERY_KEYS } from '@/constants/config';

export default function CheckoutEnderecoScreen() {
  const { colors, spacing, borderRadius: br } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const queryClient = useQueryClient();

  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [cepLookupLoading, setCepLookupLoading] = useState(false);
  const [form, setForm] = useState<AddressPayload>({
    logradouro: '', numero: '', complemento: '', bairro: '', cidade: '', uf: '', cep: '', apelido: '',
  });
  const [formError, setFormError] = useState('');

  const addressesQuery = useQuery({
    queryKey: [QUERY_KEYS.ADDRESSES],
    queryFn: addressService.list,
  });

  React.useEffect(() => {
    if (addressesQuery.data && !selectedId) {
      const defaultAddr = addressesQuery.data.find((a) => a.principal);
      if (defaultAddr) setSelectedId(defaultAddr.id);
      else if (addressesQuery.data.length > 0) setSelectedId(addressesQuery.data[0].id);
    }
  }, [addressesQuery.data]);

  const createMutation = useMutation({
    mutationFn: (payload: AddressPayload) => addressService.create(payload),
    onSuccess: (newAddr) => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.ADDRESSES] });
      setSelectedId(newAddr.id);
      setShowForm(false);
      resetForm();
    },
    onError: (err) => setFormError(extractApiError(err)),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => addressService.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.ADDRESSES] });
      if (selectedId && addressesQuery.data?.find((a) => a.id === selectedId) === undefined) {
        setSelectedId(null);
      }
    },
  });

  const resetForm = () => {
    setForm({ logradouro: '', numero: '', complemento: '', bairro: '', cidade: '', uf: '', cep: '', apelido: '' });
    setFormError('');
  };

  const handleCepBlur = useCallback(async () => {
    const cleanCep = (form.cep ?? '').replace(/\D/g, '');
    if (cleanCep.length !== 8) return;
    setCepLookupLoading(true);
    try {
      const result = await addressService.lookupCep(cleanCep);
      setForm((prev) => ({
        ...prev,
        logradouro: result.logradouro || prev.logradouro,
        bairro: result.bairro || prev.bairro,
        cidade: result.localidade || prev.cidade,
        uf: result.uf || prev.uf,
      }));
    } catch {
      setFormError('CEP não encontrado');
    } finally {
      setCepLookupLoading(false);
    }
  }, [form.cep]);

  const handleSaveAddress = () => {
    if (!form.logradouro || !form.numero || !form.bairro || !form.cidade || !form.uf || !form.cep) {
      setFormError('Preencha todos os campos obrigatórios');
      return;
    }
    createMutation.mutate(form);
  };

  const handleDelete = (id: number) => {
    Alert.alert('Excluir endereço', 'Tem certeza?', [
      { text: 'Cancelar', style: 'cancel' },
      { text: 'Excluir', style: 'destructive', onPress: () => deleteMutation.mutate(id) },
    ]);
  };

  const handleContinue = () => {
    if (!selectedId) {
      Alert.alert('Endereço obrigatório', 'Selecione ou adicione um endereço de entrega.');
      return;
    }
    router.push({ pathname: '/checkout/frete', params: { endereco_id: String(selectedId) } } as any);
  };

  const addresses = addressesQuery.data ?? [];

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <ScrollView
        contentContainerStyle={{ padding: spacing.lg, paddingBottom: 120 }}
        showsVerticalScrollIndicator={false}
      >
        {addressesQuery.isLoading ? (
          Array.from({ length: 2 }).map((_, i) => (
            <Skeleton key={i} width="100%" height={100} radius={12} style={{ marginBottom: 12 }} />
          ))
        ) : (
          <>
            {addresses.map((addr) => (
              <AddressCard
                key={addr.id}
                address={addr}
                selected={selectedId === addr.id}
                onPress={() => setSelectedId(addr.id)}
                onDelete={() => handleDelete(addr.id)}
                style={{ marginBottom: spacing.sm }}
              />
            ))}

            {!showForm ? (
              <Button
                title="+ Novo endereço"
                onPress={() => setShowForm(true)}
                variant="outline"
                fullWidth
                style={{ marginTop: spacing.md }}
              />
            ) : (
              <View style={[styles.formCard, { backgroundColor: colors.surface, borderRadius: br.lg, padding: spacing.lg, marginTop: spacing.md }]}>
                <Text variant="subtitle2" color={colors.textPrimary}>
                  Novo endereço
                </Text>

                <Input
                  label="CEP"
                  value={form.cep ?? ''}
                  onChangeText={(t) => setForm((p) => ({ ...p, cep: t }))}
                  onBlur={handleCepBlur}
                  placeholder="00000-000"
                  keyboardType="numeric"
                  maxLength={9}
                  containerStyle={{ marginTop: spacing.md }}
                />
                {cepLookupLoading && <Text variant="caption" color={colors.textSecondary}>Buscando CEP...</Text>}

                <Input
                  label="Logradouro"
                  value={form.logradouro ?? ''}
                  onChangeText={(t) => setForm((p) => ({ ...p, logradouro: t }))}
                  containerStyle={{ marginTop: spacing.sm }}
                />
                <View style={styles.row}>
                  <Input
                    label="Número"
                    value={form.numero ?? ''}
                    onChangeText={(t) => setForm((p) => ({ ...p, numero: t }))}
                    containerStyle={{ flex: 1, marginRight: 8 }}
                  />
                  <Input
                    label="Complemento"
                    value={form.complemento ?? ''}
                    onChangeText={(t) => setForm((p) => ({ ...p, complemento: t }))}
                    containerStyle={{ flex: 1.5 }}
                  />
                </View>
                <Input
                  label="Bairro"
                  value={form.bairro ?? ''}
                  onChangeText={(t) => setForm((p) => ({ ...p, bairro: t }))}
                  containerStyle={{ marginTop: spacing.sm }}
                />
                <View style={styles.row}>
                  <Input
                    label="Cidade"
                    value={form.cidade ?? ''}
                    onChangeText={(t) => setForm((p) => ({ ...p, cidade: t }))}
                    containerStyle={{ flex: 2, marginRight: 8 }}
                  />
                  <Input
                    label="UF"
                    value={form.uf ?? ''}
                    onChangeText={(t) => setForm((p) => ({ ...p, uf: t }))}
                    maxLength={2}
                    autoCapitalize="characters"
                    containerStyle={{ flex: 1 }}
                  />
                </View>
                <Input
                  label="Apelido (opcional)"
                  value={form.apelido ?? ''}
                  onChangeText={(t) => setForm((p) => ({ ...p, apelido: t }))}
                  containerStyle={{ marginTop: spacing.sm }}
                />

                {formError !== '' && (
                  <Text variant="caption" color={colors.error} style={{ marginTop: spacing.sm }}>
                    {formError}
                  </Text>
                )}

                <View style={[styles.row, { marginTop: spacing.lg }]}>
                  <Button
                    title="Cancelar"
                    onPress={() => { setShowForm(false); resetForm(); }}
                    variant="ghost"
                    style={{ flex: 1, marginRight: 8 }}
                  />
                  <Button
                    title="Salvar"
                    onPress={handleSaveAddress}
                    loading={createMutation.isPending}
                    style={{ flex: 2 }}
                  />
                </View>
              </View>
            )}
          </>
        )}
      </ScrollView>

      <View style={[styles.bottomBar, { backgroundColor: colors.surface, borderTopColor: colors.divider, paddingBottom: insets.bottom + spacing.sm }]}>
        <Button
          title="Continuar para frete"
          onPress={handleContinue}
          fullWidth
          size="lg"
          disabled={!selectedId}
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  formCard: {},
  row: {
    flexDirection: 'row',
    marginTop: 8,
  },
  bottomBar: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    paddingHorizontal: 16,
    paddingTop: 12,
    borderTopWidth: StyleSheet.hairlineWidth,
  },
});
