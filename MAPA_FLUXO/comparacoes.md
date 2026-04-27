# Webhook Mercado Pago – Manifest e HMAC (comparações)

## Manifest montado pelo sistema (a partir da requisição recebida)

```
id:123456;request-id:3687d52117370456a28a2aea7a0ff336;ts:1773145547776;
```

- `id`: valor de `data.id` da URL (query) = `123456`
- `request-id`: valor do header `x-request-id` = `3687d52117370456a28a2aea7a0ff336`
- `ts`: valor extraído do header `x-signature` = `1773145547776`

## HMAC recebido (v1 do header x-signature)

Valor enviado pelo Mercado Pago no header `x-signature` (campo `v1`):

```
046046e8c1f85b7aca8213b799487cb0bebf2553ea17dadd2053e369cc9b0685
```

Header completo (exemplo do log):  
`x-signature: ts=1773145547776,v1=046046e8c1f85b7aca8213b799487cb0bebf2553ea17dadd2053e369cc9b0685`

---

## HMAC calculado com a chave configurada

Chave usada (secret do webhook):

```
c712abb9caf5e4e57e16d152cadeafafe2c90bc250a28384aac1e88abb6e5ce8
```

Manifest (mesmo do sistema):  
`id:123456;request-id:3687d52117370456a28a2aea7a0ff336;ts:1773145547776;`

**HMAC-SHA256(secret, manifest) em hex:**

```
07730140ffed226aa481ed16eae3ee6a0114e8f217d9b9f7ba81ac3d3d3e4979
```

### Comparação

| Origem   | Valor (início)   |
|----------|------------------|
| MP (v1)  | `046046e8c1...`  |
| Calculado| `07730140ff...`  |

Os valores são diferentes → **digest_mismatch** (o secret no painel do MP não é o mesmo que essa chave, ou o MP assina com outro formato de manifest no teste).

---

## Análise do retorno do Mercado Pago (suporte)

O suporte do MP reforça o checklist: valores do template iguais aos recebidos, ordem correta, chave do painel da aplicação correta (produção vs teste), sem encoding/transformação errada antes do HMAC.

### Diferença importante no formato do template

O suporte descreve o template assim (com **espaços** entre as partes):

```
id:[data.id_url] request-id:[x-request-id_header] ts:[ts_header]
```

Exemplo dado pelo suporte:  
`id:123456 request-id:bb56... ts:1704908010`

No sistema local e em parte da documentação do MP usa-se **ponto e vírgula** e ponto e vírgula final:

```
id:[data.id_url];request-id:[x-request-id_header];ts:[ts_header];
```

Exemplo no sistema:  
`id:123456;request-id:3687d52117370456a28a2aea7a0ff336;ts:1773145547776;`

Ou seja: há divergência **espaços** (suporte) vs **ponto e vírgula** (código/doc).

### Teste com o formato com espaços (mesma chave)

Com a chave `c712abb9...` e o manifest **com espaços** (sem `;`):

- Manifest: `id:123456 request-id:3687d52117370456a28a2aea7a0ff336 ts:1773145547776`
- HMAC obtido: `9de358596e581a4fcbe74a98245f7c272a713ca77d69ce1e8dd08c334260ba30`

Continua diferente do v1 enviado pelo MP (`046046e8c1...`). Foram testadas também variantes (sem `request-id`, `ts` em segundos, com/sem espaços): **nenhuma** produz o hash que o MP enviou com essa chave.

### Conclusão da análise

- **Template**: O suporte fala em espaços; o sistema usa ponto e vírgula. Vale alinhar com o que o MP considera oficial (e testar com webhook real).
- **Chave**: Como nenhuma combinação de formato testada com a chave atual gera o `v1` recebido, o mais provável é que o **secret usado pelo MP** no envio (ex.: para a URL de teste) **seja outro** que não o configurado no sistema. Confirmar no painel da aplicação (ambiente teste/produção) qual chave está associada à URL que recebe o webhook e garantir que essa mesma chave está no sistema.



