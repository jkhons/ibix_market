# Checklist Técnico – Rejeição 290 (Certificado Assinatura inválido)

Rejeição 290: certificado usado para assinar a NF-e considerado inválido pela SEFAZ.
NT 2011.003 regra E01: inexistência do certificado, versão ≠ 3, Basic Constraint, KeyUsage sem Assinatura Digital/Não Recusa.

---

## 1. Fluxo: nfe_xml_builder → nfe_assinador → sefaz_client

| Etapa | Responsável | Verificação |
|-------|-------------|-------------|
| Montagem XML | `nfe_xml_builder.py` | `infNFe` com `Id="NFe"` + 44 dígitos; CNPJ do emitente correto; XML bem-formado UTF-8 |
| Assinatura | `nfe_assinador.py` | Mesmo cert usado em mTLS; rsa-sha1 + sha1; Reference URI = #Id infNFe; Signature irmão de infNFe |
| Envio | `provedor_local.py` + `sefaz_client.py` | Nada altera o XML após assinar; enviNFe com NFe sem declaração `<?xml?>`; cert mTLS = cert assinatura |

---

## 2. Certificado (mesmo para assinatura e transporte)

| Campo | Onde checar | Esperado |
|-------|-------------|----------|
| subject | `cert_diag.json` | CN com nome/CNPJ; sem caracteres inválidos |
| serial | `cert_diag.json` | Numérico; igual em assinatura e mTLS |
| notBefore / notAfter | `cert_diag.json` | Dentro da validade |
| CNPJ | `cert_diag.json` | `cnpj_match_ok: true` (cert = emitente) |
| fingerprint_sha256 | `cert_diag.json` | Hash SHA-256 do cert |
| **version** | `cert_diag.json` → `nt_e01.version` | `"3"` (NT E01) |
| **KeyUsage** | `cert_diag.json` → `nt_e01.key_usage` | Contém `digitalSignature` e `nonRepudiation` |
| **Basic Constraint** | `cert_diag.json` → `nt_e01.basic_constraint_ca` | `false` (não pode ser certificado de AC) |

---

## 3. Assinatura XML (estrutura)

| Campo | Onde checar | Esperado |
|-------|-------------|----------|
| id_infnfe | `assinatura_diag.json` | `NFe` + 44 dígitos |
| reference_uri | `assinatura_diag.json` | `#` + id_infnfe (ex.: `#NFe35202...`) |
| signature_method_algorithm | `assinatura_diag.json` | `http://www.w3.org/2000/09/xmldsig#rsa-sha1` |
| digest_method_algorithm | `assinatura_diag.json` | `http://www.w3.org/2000/09/xmldsig#sha1` |
| canonicalization_method | `assinatura_diag.json` | `http://www.w3.org/TR/2001/REC-xml-c14n-20010315` |
| qtd_signatures | `assinatura_diag.json` | `1` |
| x509_certificate_presente | `assinatura_diag.json` | `true` |
| Posição Signature | XML | Irmão de `infNFe` (filho de `NFe`), não dentro de `infNFe` |

---

## 4. XML não alterado após assinar

| Verificação | Como |
|-------------|------|
| Hash NFe no enviNFe | `nfe_sem_decl` = xml_apos sem `<?xml?>`; hash deve refletir apenas remoção da declaração |
| Sem pretty-print | Nenhum `etree.tostring(..., pretty_print=True)` após assinar |
| Sem reordenação de atributos | Serialização preserva ordem original |
| Encoding UTF-8 | Todo o fluxo em UTF-8 |
| Sem inclusão de namespace após assinar | `NFe` já tem `xmlns`; não adicionar depois |

---

## 5. Cadeia e validade (290–296)

| Causa possível | Ação |
|----------------|------|
| Certificado vencido | Checar `notAfter` em `cert_diag.json` |
| Cadeia ICP-Brasil incorreta | Validar contra CAs oficiais; `certifi_icpbr` no cliente |
| Certificado revogado | Consultar LCR da AC Certisign |
| A1 corrompido | Reexportar PFX; testar em outro ambiente |
| Senha incorreta | Carregamento falharia antes do envio |
| Chave privada não corresponde | Erro em assinatura ou mTLS |

---

## 6. Arquivos de diagnóstico (por tentativa)

Em `logs/nfe/YYYY-MM-DD/nota_{id}/`:

- `cert_diag.json` – certificado + nt_e01 (version, key_usage, basic_constraint)
- `assinatura_diag.json` – estrutura da assinatura
- `xml_antes_assinatura.xml` – XML antes de assinar
- `xml_apos_assinatura.xml` – XML logo após assinar
- `enviNFe_enviado.xml` – payload exato enviado
- `diag_meta.json` – hashes para conferir alteração pós-assinatura

---

## 7. Suspeitos comuns

1. **Certificado diferente** em assinatura vs mTLS → neste fluxo usa o mesmo `(key, cert)`.
2. **CNPJ cert ≠ emitente** → `cert_diag.json` → `cnpj_match_ok`.
3. **KeyUsage incompleto** → `cert_diag.json` → `nt_e01.key_usage_ok`.
4. **Alteração pós-assinatura** → comparar `xml_apos_assinatura.xml` com o NFe dentro de `enviNFe_enviado.xml`.
5. **Caracteres especiais** (SEFAZ/MT) → verificar acentos e encoding no corpo assinado.
