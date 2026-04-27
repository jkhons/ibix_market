# XML NF-e e padrão do governo brasileiro

**Objetivo:** Esclarecer se o sistema envia o XML no modo padronizado pelo governo e o que é necessário para conformidade.

---

## 1. Situação atual: o sistema NÃO envia XML à SEFAZ

| Aspecto | Situação |
|--------|----------|
| **Geração de XML** | O sistema **não gera** arquivo XML da NF-e. Não existe módulo que monte o XML no layout oficial (NF-e 4.0). |
| **Envio à SEFAZ** | O sistema **não envia** nada diretamente à SEFAZ. Quem recebe os dados é um **provedor** (provider). Hoje só existe o **ProvedorFiscalStub**, que simula sucesso sem chamar SEFAZ e sem produzir XML. |
| **Payload interno** | O serviço de emissão monta um **dicionário (payload)** com dados da nota, empresa, destinatário e itens e repassa esse payload ao provedor. Esse payload é interno (JSON-like); **não é o XML oficial** da NF-e. |

**Conclusão:** Hoje **não** está sendo enviado XML no formato padronizado pelo governo, porque não há geração nem envio de XML; há apenas simulação via stub.

---

## 2. Padrão do governo (NF-e 4.0)

- **Layout:** NF-e 4.0 (Manual de Orientação do Contribuinte, NT 2016.002).
- **Formato:** XML conforme XSD da SEFAZ (ex.: `leiauteNFe_v4.00.xsd`).
- **Estrutura:** Raiz `NFe`, bloco `infNFe` (ide, emit, dest, det, total, etc.), namespaces oficiais.
- **Comunicação:** Web Service SOAP (ou API REST de gateway), TLS 1.2+, certificado digital A1/A3.
- **Itens:** Cada `det` com NCM, CFOP, CST/CSOSN, quantidade, valores, impostos (ICMS, PIS, COFINS, etc.).

Para “enviar corretamente o modo XML padronizado pelo governo”, é necessário que **alguém** (o sistema ou o provedor) gere o **XML no layout 4.0** e o envie à SEFAZ (ou ao gateway que fala com a SEFAZ).

---

## 2.1 Leitura/importação de XML de NF-e (entrada de compras)

O módulo de **entrada de notas** (`app/services/fiscal/nfe_entrada_parser.py`) **lê** XML de NF-e no **layout oficial brasileiro 4.0**:

| Aspecto | Implementação |
|--------|----------------|
| **Namespace** | `http://www.portalfiscal.inf.br/nfe` |
| **Estrutura** | Raiz `NFe` > `infNFe` (ide, emit, dest, det, total) |
| **Totais** | `total` > `ICMSTot` > `vProd`, `vNF`, etc. (conforme XSD) |
| **Itens** | `det` com atributo `nItem`, filho `prod` (cProd, xProd, NCM, CFOP, uCom, qCom, vUnCom, vProd, …) e `imposto` (ICMS, IPI, ICMS ST) |
| **Chave 44** | Do atributo `Id` do `infNFe` (ex.: `NFe` + 44 dígitos) ou montagem a partir de ide+emit (cUF, AAMM, CNPJ, mod, serie, nNF) |

Assim, arquivos XML de NF-e gerados pela SEFAZ ou por sistemas conformes ao leiaute 4.0 são corretamente interpretados na importação.

---

## 3. O que o sistema já faz (e o que falta)

### 3.1 Payload enviado ao provedor

O `FiscalEmissaoService` monta um payload e chama `provedor.enviar_nfe(empresa_id, nota_id, payload)`. Esse payload precisa conter **todos os dados** que serão usados para montar o XML 4.0.

- **Antes:** O payload da nota (`_payload_nota_fiscal` em `app/services/fiscal/emissao_service.py`) era **mínimo**: id, numero, serie, tipo, modelo, valor_total, cliente_id, itens só com item_numero, descricao, quantidade, valor_unitario, valor_total. Faltavam NCM, CFOP, CST, origem, impostos, natureza da operação, etc.
- **Agora:** O payload foi **estendido** em `emissao_service._payload_nota_fiscal` para incluir:
  - **Capa (ide + totais):** data_emissao, data_saida, natureza_operacao, ambiente, valor_produtos, valor_frete, valor_seguro, valor_desconto, valor_outros, valor_icms, valor_icms_desonerado, valor_icms_st, valor_ipi, valor_pis, valor_cofins, forma_pagamento, tipo_pagamento, observacoes, informacoes_complementares.
  - **Itens (det):** por item: ncm, cest, cfop, unidade, extipi, valor_desconto, origem, cst_icms, csosn, aliquota_icms, valor_icms, valor_base_icms, ICMS ST (modalidade_bc, aliquota, base, valor), PIS/COFINS (cst, aliquota, base, valor), IPI (quando aplicável), informacoes_adicionais.
  - **Emitente e destinatário:** continuam em `payload["empresa"]` e `payload["destinatario"]` (montados com `_empresa_para_payload` e `_cliente_destinatario_para_payload`).

Assim, quando o provedor real for integrado (ou um gerador de XML interno for implementado), os dados necessários para o “modo XML padronizado” já estão disponíveis no payload.

### 3.2 Responsabilidade do provedor

- **Provedor real (ex.: Focus NFE, gateway SEFAZ):** Deve receber esse payload (ou equivalente), montar o **XML no layout 4.0**, assinar com o certificado do CA e enviar ao ambiente da SEFAZ (homologação/produção). A conformidade com o “modo XML padronizado pelo governo” é responsabilidade desse provedor (e da documentação/API dele).
- **Stub:** Não gera XML e não fala com o governo; só simula sucesso para desenvolvimento.

---

## 4. Checklist para envio no padrão governo

| Item | Responsável | Status |
|------|-------------|--------|
| Payload interno com todos os campos necessários ao XML 4.0 | Nosso sistema | ✅ Passou a incluir emitente, dest, ide, totais, itens (NCM, CFOP, CST, impostos). |
| Geração do XML no layout NF-e 4.0 (XSD SEFAZ) | Provedor ou módulo nosso | ❌ Não implementado (stub não gera XML). |
| Assinatura digital do XML (certificado A1/A3) | Provedor ou módulo nosso | ❌ Fora do stub. |
| Envio ao Web Service da SEFAZ (ou gateway) | Provedor ou módulo nosso | ❌ Stub não envia. |
| Tratamento do retorno (protocolo, chave, evento) | Provedor + nosso serviço | Parcial: nosso serviço já grava chave/protocolo/status a partir do resultado do provedor. |

---

## 5. Próximos passos para “enviar corretamente o modo XML padronizado”

1. **Integrar um provedor real** que:
   - Receba o payload completo (emitente, destinatário, itens com NCM/CFOP/CST, totais, etc.),
   - Gere o XML no **layout 4.0** (padrão governo),
   - Assine com o certificado do CA,
   - Envie à SEFAZ e devolva protocolo/chave/XML de retorno.
2. **Ou** implementar no nosso sistema um **gerador de XML NF-e 4.0** (respeitando o XSD oficial) e um cliente SOAP (ou REST do gateway), usando o mesmo payload já preenchido; nesse caso, a responsabilidade de estar “no modo XML padronizado pelo governo” seria nossa (validação contra o XSD e manual da SEFAZ).

Enquanto não houver provedor real ou gerador próprio, o sistema **não** está enviando XML no padrão do governo; apenas deixa o payload pronto para que esse XML seja gerado e enviado de forma padronizada.
