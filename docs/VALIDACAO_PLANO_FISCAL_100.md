# Validação 100% – Plano Fiscal NF-e (módulo_local_nf-e_saas_250fcba4)

Data da validação: conforme checklist do plano único (seções 3, 4, 5, 7 e 14).

---

## ✅ Implementado (conforme plano)

### Backend – Módulo local (Seções 3, 7)

| Item | Arquivo/Referência | Status |
|------|--------------------|--------|
| ProvedorFiscalLocal | `app/services/fiscal/provedor_local.py` | ✅ init(db), enviar_nfe, cancelar_nfe, stubs NFS-e/NFC-e |
| Carregador certificado | `app/services/fiscal/certificado.py` | ✅ blob/path + senha, validar_validade_certificado, sem log |
| Gerador XML NF-e 4.0 | `app/services/fiscal/nfe_xml_builder.py` | ✅ ide, emit, dest, det, total; chave 44 dígitos |
| Assinador XML | `app/services/fiscal/nfe_assinador.py` | ✅ signxml, RSA-SHA256, C14N, Signature irmão de infNFe |
| Cliente SEFAZ | `app/services/fiscal/sefaz_client.py` | ✅ URLs por UF, SOAP autorização e evento, parse retorno |
| get_provedor_fiscal | `emissao_service.py` | ✅ retorna ProvedorFiscalLocal se empresa.provedor_fiscal == "local" |
| Persistência xml_path | `emissao_service.py` + `provedor_local.py` | ✅ resultado.xml_path e xml_retorno_path gravados na nota |
| Isolamento tenant | provedor_local usa apenas empresa_id | ✅ |

### Backend – APIs e regras de negócio (Seção 14.1)

| Item | Referência | Status |
|------|------------|--------|
| API upload certificado | POST `/fiscal/empresa/{id}/certificado` (File + Form senha) | ✅ escopo CA, atualiza blob e certificado_validade |
| GET notas com pedido_id | `notas_fiscais.py` | ✅ query param pedido_id |
| faturar_pedido | `pedido_service.py` | ✅ serie_padrao_nfe, NCM do ProdutoCliente, origem_documento |
| validar_nota_fiscal | `emissao_service.py` | ✅ exige NCM por item para envio SEFAZ |
| Senha/certificado não expostos | `empresa.py` converter_empresa_para_dict | ✅ senha_certificado = None na resposta |

### Frontend (Seção 14.2 – parcial)

| Item | Referência | Status |
|------|------------|--------|
| Form Nova Nota – capa | `notas_fiscais.html` + `.js` | ✅ série, natureza_operacao, ambiente, data_saida |
| Form Nova Nota – itens | `notas_fiscais.html` + `.js` | ✅ NCM, CFOP, origem, CST/CSOSN; payload status rascunho |
| Listagem notas | `notas_fiscais.js` | ✅ filtro pedido_id, coluna Origem, link "Pedido #X" |
| Modal detalhe | `notas_fiscais.js` | ✅ mensagem_retorno (retorno SEFAZ) exibida |
| Cancelar com body | API + front já enviavam body justificativa | ✅ |
| Tela empresa (certificado) | `fiscal/empresa.html` | ✅ campos .pfx, senha, validade (form existente) |

### Multitenancy e RBAC (Seções 14.3, 14.4)

| Item | Referência | Status |
|------|------------|--------|
| Escopo CA em notas e empresa | APIs filtram por Empresa.cliente_id / scope | ✅ |
| Upload certificado só no escopo | _scope_allows_empresa no POST /certificado | ✅ |
| forbid_contador_edit | rotas put/cancelar/enviar nota | ✅ |
| fiscal:baixar_xml / fiscal:baixar_pdf | Depends(require_permission(...)) nos downloads | ✅ |

---

## ⚠️ Parcial ou pendente (não 100%)

### 1. Pós-faturamento – link "Ver nota #X" (Seção 14.2)

- **Onde:** `app/templates/meu_negocio/pedidos/faturar.html`
- **Atual:** Após faturar, `alert('... NF em rascunho: #' + data.nota_fiscal_id)` e redirecionamento para `/negocio/pedidos`.
- **Faltando:** Botão/link "Ver nota #X" (por ex. para `/fiscal/notas-fiscais` ou abrir detalhe da nota) em vez de só o alert e voltar à listagem de pedidos.

### 2. Tela empresa – uso do novo endpoint de certificado (Seção 5 / 14.2)

- **Onde:** `app/templates/fiscal/empresa.html` + `app/static/js/empresa_fiscal.js`
- **Atual:** Form com arquivo .pfx e senha; submissão provavelmente via PUT empresa (base64 no JSON).
- **Faltando:** Integrar ao **POST `/fiscal/empresa/{id}/certificado`** (multipart + senha) quando houver arquivo e senha, para usar o fluxo dedicado e atualizar `certificado_validade` pelo backend. Opcional: dropdown **provedor (local/gateway)** e exibir **validade do certificado** já salva.

### 3. Senha do certificado em repouso (Seção 6)

- **Onde:** `app/api/v1/empresa.py` – upload_certificado_empresa
- **Atual:** Comentário `# TODO: criptografar em repouso (chave de env)`; senha gravada em texto no campo.
- **Faltando:** Criptografar `senha_certificado` em repouso (ex.: chave de ambiente + Fernet, como em `services/payments/credentials.py`) e descriptografar só no carregador de certificado.

### 4. Permissões na UI – download XML/PDF (Seção 14.2)

- **Onde:** `app/static/js/notas_fiscais.js` – exibição dos botões de download
- **Atual:** Botões de download aparecem por `podeDownload` (nota autorizada ou com chave); permissão é aplicada só no backend (403).
- **Faltando:** Esconder os botões de download quando o usuário não tiver `fiscal:baixar_xml` / `fiscal:baixar_pdf` (ex.: usar flags vindas do backend ou de permissões carregadas na página).

### 5. Testes automatizados – módulo fiscal (Seções 7, 14.3, 14.5)

- **Onde:** `tests/test_tenant_isolation.py` (e eventualmente novos arquivos de teste)
- **Atual:** Existe teste de listagem de notas sem token; não há cenários específicos de isolamento fiscal (CA1 não vê/usa notas/empresa/certificado do CA2).
- **Faltando:**
  - Testes de isolamento: dois CAs, duas empresas; usuário CA1 não lista/nem acessa nota/empresa do CA2; não pode fazer upload de certificado em empresa do CA2.
  - Testes unitários: carregador de certificado (mock empresa), gerador XML (payload fixo), assinador (mock cert), cliente SEFAZ (mock resposta).
  - Teste de integração: rascunho → enviar_nfe → retorno e persistência de chave, protocolo e paths.

### 6. Documentação e operação (Seção 14.6)

- **Onde:** Conteúdo referenciado no plano (M6, go-live)
- **Atual:** Não há documentos no repositório dedicados a esses guias.
- **Faltando:**
  - Guia do CA: "Como configurar o certificado" (upload, senha, ambiente, UF).
  - Guia do CA: "Como emitir NF-e a partir do pedido" (faturar → validar → enviar).
  - Documentação interna: versão do layout NF-e, provedor em uso, data da última homologação.
  - Observação: monitoramento (erros, rejeições SEFAZ, logs) depende de uso de `fiscal_evento` e `fiscal_download_log` já existentes.

---

## Resumo

- **Implementado em linha com o plano:** módulo local (provedor, certificado, XML, assinador, SEFAZ), configuração do provedor por empresa, API de upload de certificado, filtro e coluna Origem por pedido, form Nova Nota completo, faturar_pedido com NCM/série/origem, validação NCM, persistência de xml_path, multitenancy e RBAC no backend.
- **Não 100%:** (1) link "Ver nota" pós-faturar, (2) formulário empresa integrado ao POST /certificado e opcionalmente provedor/validade, (3) senha do certificado criptografada em repouso, (4) UI de downloads condicionada às permissões, (5) testes de isolamento e unitários/integração do módulo fiscal, (6) guias do CA e documentação interna.

Para fechar **100%** em relação ao plano, basta implementar os itens listados na seção “Parcial ou pendente” acima.
