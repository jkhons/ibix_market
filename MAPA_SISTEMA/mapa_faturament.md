# MAPA DE FATURAMENTO (NF-e / NFC-e) — PDV Ibix

## Visão Geral

Este documento consolida as informações sobre **emissão de notas fiscais eletrônicas (NF-e modelo 55 e NFC-e modelo 65)** no PDV Ibix: estrutura XML, assinatura, validação local e correções aplicadas com base em diagnóstico SEFAZ (erro cStat 225) e validação contra schemas PL_010b/NT2025.002.

**Referências cruzadas:** MAPA_DO_SISTEMA (Plano Módulo Fiscal NF-e local, Diagnóstico e logging NF-e); emissao_service, nfe_xml_builder, nfe_assinador, provedor_local, sefaz_client.

---

## 1. Contexto do diagnóstico (2026-03-13)

| Item | Descrição |
|------|-----------|
| **Venda** | VENDA-2026-000048 (nota_id 110) — CA Juliano Oliveira |
| **Modelo** | NFC-e modelo 65 |
| **Erro SEFAZ** | cStat 225 — "Rejeição: Falha no Schema XML do lote de NFe" |
| **verAplic SEFAZ SP** | SP_NFCE_PL_009_V400 |
| **Ambiente** | Produção (tpAmb=1); endpoint `https://nfce.fazenda.sp.gov.br/ws/NFeAutorizacao4.asmx` |

---

## 2. Estrutura XML (enviNFe + NFe)

### 2.1 Envelope SOAP

O lote é enviado em envelope SOAP 1.2 com:
- **enviNFe** `versao="4.00"`, `idLote`, `indSinc=1`
- **NFe** contendo: `infNFe` + `infNFeSupl` (NFC-e) + `ds:Signature`
- Sem declaração `<?xml ...?>` **dentro** do NFe
- Sem zeros à esquerda em `serie` e `nNF`

### 2.2 infNFe (NFC-e 65) — ordem e campos obrigatórios

| Grupo | Obrigatório NFC-e | Observação |
|-------|-------------------|------------|
| ide | Sim | mod=65, tpImp=4 (NFC-e) ou 5 (NFC-e eletrônico); serie/nNF sem zeros à esquerda |
| emit | Sim | IE somente dígitos, máx 14 caracteres |
| dest | Sim | indIEDest=9 antes de IE; IE omitido quando consumidor não identificado |
| det | Sim | itens com prod, imposto (ICMS, PIS, COFINS) |
| total | Sim | ICMSTot com vBC, vICMS, vProd, vNF etc. |
| transp | Sim | modFrete (9 = sem frete) |
| cobr | Não | opcional; fat/vLiq quando aplicável |
| **pag** | **Sim** | Obrigatório para NFC-e (NT 2012/004, NT2025.002) |
| infNFeSupl | Sim (NFC-e) | qrCode + urlChave (não urlConsulta na NT2025) |

### 2.3 Grupo pag (dados de pagamento)

Estrutura mínima:

```xml
<pag>
  <detPag>
    <indPag>0</indPag>   <!-- 0=à vista, 1=a prazo -->
    <tPag>99</tPag>     <!-- 01=Dinheiro, 03=Crédito, 04=Débito, 99=Outros -->
    <vPag>21.00</vPag>
  </detPag>
</pag>
```

### 2.4 infNFeSupl (NFC-e)

| Campo | Descrição |
|-------|-----------|
| **qrCode** | URL completa com parâmetro `?p=` (chave\|versão\|tpAmb\|cDest\|hash) |
| **urlChave** | URL base da consulta por chave (NT2025.002: usar `urlChave`, não `urlConsulta`) |

SP exemplo: `https://www.nfce.fazenda.sp.gov.br/NFCeConsultaPublica/Paginas/ConsultaQRCode.aspx`

---

## 3. Assinatura (ds:Signature)

### 3.1 Algoritmos

| Elemento | Valor | Não alterar |
|----------|-------|-------------|
| SignatureMethod | `http://www.w3.org/2001/04/xmldsig-more#rsa-sha256` | Manter SHA-256 (ICP-Brasil) |
| DigestMethod | `http://www.w3.org/2001/04/xmlenc#sha256` | Manter SHA-256 |
| CanonicalizationMethod | `http://www.w3.org/TR/2001/REC-xml-c14n-20010315` | C14N |

### 3.2 KeyInfo — composição exigida

**Formato correto (SEFAZ/SP):**

```xml
<ds:KeyInfo>
  <ds:X509Data>
    <ds:X509Certificate>...</ds:X509Certificate>
  </ds:X509Data>
</ds:KeyInfo>
```

**O que NÃO incluir:**
- `ds:KeyValue` / `ds:RSAKeyValue` — removido para compatibilidade com schema de validação SP

### 3.3 Implementação (nfe_assinador.py)

```python
# signxml: sempre_add_key_value=False
# Gera KeyInfo apenas com X509Data/X509Certificate
signer.sign(
    inf_nfe,
    key=...,
    cert=...,
    reference_uri="#" + inf_nfe.get("Id"),
    always_add_key_value=False,  # SEFAZ/SP: KeyInfo apenas X509Data
)
```

Após remoção de KeyValue, o XML deve ser **reassina**do (a assinatura é gerada a cada emissão).

---

## 4. Validação local (PL_010b_NT2025_002_v1.30)

### 4.1 Pacote de schemas

| Pasta | Uso |
|-------|-----|
| **PL_010b_NT2025_002_v1.30** | Pacote NT2025.002 v1.30 — prioridade para validação |
| scripts/xsd | Fallback quando PL_010b não existir |

Arquivos PL_010b: `enviNFe_v4.00.xsd`, `leiauteNFe_v4.00.xsd`, `tiposBasico_v4.00.xsd`, `DFeTiposBasicos_v1.00.xsd`, `xmldsig-core-schema_v1.01.xsd`, `nfe_v4.00.xsd`. O `enviNFe_v4.00.xsd` foi adicionado ao pacote (originalmente não o incluía).

### 4.2 Validação local (XSD)

O repositório mantém os XSD em `scripts/xsd/` e `scripts/xsd_pl009/` para referência e ferramentas externas. **Não há mais** script `scripts/validar_envinfe.py` no repositório. Para validar um envelope manualmente: extrair `enviNFe` do SOAP para ficheiro XML e usar um validador XML contra `scripts/xsd*/enviNFe_v4.00.xsd` (cadeia `leiauteNFe` → `tiposBasico`) ou equivalente no ambiente de suporte.

### 4.3 Limitação do xmldsig (PL_010b)

O `xmldsig-core-schema_v1.01.xsd` do pacote exige rsa-sha1 e sha1. O sistema usa rsa-sha256 e sha256 (exigido pelo ICP-Brasil). Os erros de assinatura no validador local são esperados; não indicam problema no XML enviado à SEFAZ.

---

## 5. Correções aplicadas

| Correção | Arquivo | Descrição |
|----------|---------|-----------|
| **pag obrigatório** | nfe_xml_builder.py | Inclusão de `<pag><detPag><indPag>0</indPag><tPag>99</tPag><vPag>...</vPag></detPag></pag>` para NFC-e |
| **urlChave** | nfe_xml_builder.py | Substituição de `urlConsulta` por `urlChave` em infNFeSupl (NT2025.002) |
| **KeyInfo sem KeyValue** | nfe_assinador.py | `always_add_key_value=False` no signxml |

---

## 6. Arquivos envolvidos

| Arquivo | Função |
|---------|--------|
| `app/services/fiscal/nfe_xml_builder.py` | Montagem do XML NFe (ide, emit, dest, det, total, transp, cobr, pag, infNFeSupl) |
| `app/services/fiscal/nfe_assinador.py` | Assinatura com certificado A1 (signxml, RSA-SHA256) |
| `app/services/fiscal/provedor_local.py` | Montagem do lote enviNFe, envelope SOAP, envio SEFAZ |
| `app/services/fiscal/sefaz_client.py` | Cliente HTTP, parsing retorno |
| `app/services/fiscal/emissao_service.py` | Orquestração do fluxo de emissão |
| *(removidos do repo)* | Scripts auxiliares de validação/emissão de teste foram retirados; usar fluxo fiscal na aplicação ou ferramentas externas |

---

## 7. Logs e diagnóstico

| Caminho | Conteúdo |
|---------|----------|
| `logs/nfe/YYYY-MM-DD/nota_{id}/` | request.xml, envelope_request.xml, response.raw |
| `logs/nfe/.../enviNFe_extracted.xml` | enviNFe extraído do envelope (para validação) |
| `nfe_tentativa_envio` | Histórico de tentativas, status_http, tipo_resultado |

---

## 8. Próximas checagens (se 225 persistir)

| Ponto | Ação |
|-------|------|
| **Posição de infNFeSupl** | Verificar ordem no schema (TNFe: infNFe, infNFeSupl, Signature) |
| **QR Code NFC-e** | Conferir montagem exata (versão, tpAmb, cDest, hash) conforme NT |
| **Compatibilidade XSD** | Comparar pacote local com Arquivos Vigentes de SP; SP usa verAplic PL_009 |

---

## 9. Validação no portal SP

A página da SEFAZ SP é destinada à **validação do XML de autorização da NFC-e** e ao **cálculo do QR Code**. Recomendado submeter o enviNFe extraído para validação no portal oficial e comparar com os Arquivos Vigentes de SP.

---

## 10. Resumo do fluxo de emissão

1. `emissao_service` → payload + motor tributário
2. `nfe_xml_builder.montar_nfe` → XML NFe (sem assinatura)
3. `nfe_assinador.assinar_nfe` → assina infNFe, insere Signature como irmão de infNFe
4. `provedor_local` → monta enviNFe (idLote, indSinc, NFe), envelope SOAP
5. `sefaz_client` → POST NFeAutorizacao4
6. Parsing retEnviNFe → cStat, protNFe (se autorizado)

---

**Última atualização:** 2026-03-13 — Baseado em diagnóstico cStat 225 e validação PL_010b (pag, urlChave, KeyInfo sem KeyValue).
