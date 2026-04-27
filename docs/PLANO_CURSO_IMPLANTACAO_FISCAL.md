# Plano do Curso para Implantação – Módulo Fiscal (NF-e / Faturamento)

**Objetivo:** Servir como **plano de curso** e **roteiro de implantação** do módulo de faturamento e emissão de nota fiscal, no modelo Cliente Administrador (CA), até o envio no padrão do governo (XML NF-e 4.0).

**Público:** Equipe técnica (desenvolvimento, integração, operação) e gestores do projeto.

**Documentos de apoio:**  
- [PLANO_FATURAMENTO_NOTA_FISCAL.md](./PLANO_FATURAMENTO_NOTA_FISCAL.md)  
- [MODELO_VENDA_SERVICO_FISCAL.md](./MODELO_VENDA_SERVICO_FISCAL.md)  
- [PADRONIZACAO_NOTA_FISCAL.md](./PADRONIZACAO_NOTA_FISCAL.md)  
- [XML_NFE_PADRAO_GOVERNO.md](./XML_NFE_PADRAO_GOVERNO.md)

---

## Visão geral do curso / implantação

| Módulo | Nome | Duração estimada | Pré-requisito |
|--------|------|------------------|---------------|
| **M0** | Contexto e modelo CA | 0,5 dia | Nenhum |
| **M1** | Ambiente atual e padrões (modelo, schema, formulário) | 1 dia | M0 |
| **M2** | Provedor real e certificado do CA (Fase 1 – parte 1) | 1–2 semanas | M1 |
| **M3** | Dados fiscais nos itens e validação (Fase 1 – parte 2) | 1 semana | M1 |
| **M4** | Rastreabilidade e UX (Fase 2) | 1–2 semanas | M2, M3 |
| **M5** | XML padronizado e homologação SEFAZ | 1 semana | M2, M3 |
| **M6** | Go-live e venda do serviço | contínuo | M4, M5 |

**Carga total estimada:** 4–6 semanas (desenvolvimento) + tempo de homologação e go-live.

---

## Módulo 0 – Contexto e modelo Cliente Administrador (CA)

**Objetivo:** Entender o modelo de negócio e de produto antes de implementar.

**Conteúdo:**
- O que é o CA (Cliente Administrador) e por que cada CA gerencia apenas suas notas.
- Fluxo: CA insere certificado válido → sistema emite NF-e em nome do CNPJ do CA.
- Isolamento de dados (multi-tenant por CA) e escopo nas APIs/telas.
- Documentos: trecho “Modelo de venda: CA” do [PLANO_FATURAMENTO_NOTA_FISCAL.md](./PLANO_FATURAMENTO_NOTA_FISCAL.md) e [MODELO_VENDA_SERVICO_FISCAL.md](./MODELO_VENDA_SERVICO_FISCAL.md).

**Atividades:**
- Leitura dos documentos de modelo CA e checklist comercial.
- Reunião curta para alinhar: “quem é o CA no nosso sistema?” e “onde o certificado será configurado?”.

**Critério de conclusão:** Equipe consegue explicar o modelo CA e o fluxo certificado → emissão.

**Duração:** 0,5 dia.

---

## Módulo 1 – Ambiente atual e padrões (modelo, schema, formulário)

**Objetivo:** Conhecer o que já existe no código e garantir que modelo, API e formulário estejam padronizados.

**Conteúdo:**
- Modelo de dados: `NotaFiscal`, `NotaFiscalItem`, enums (status, origem, ambiente).
- Schemas Pydantic: `NotaFiscalCreate`, `NotaFiscalResponse`, status (rascunho, enviada), `pedido_id`, `origem_documento`, `CancelarNotaBody`.
- Formulário “Nova Nota”: capa (empresa, destinatário, tipo, número, data), itens (descrição, unidade, qtd, valor); cancelamento com body JSON.
- Payload completo enviado ao provedor: ver `_payload_nota_fiscal` e `_empresa_para_payload`, `_cliente_destinatario_para_payload` em `app/services/fiscal/emissao_service.py`.
- Documento: [PADRONIZACAO_NOTA_FISCAL.md](./PADRONIZACAO_NOTA_FISCAL.md).

**Atividades:**
- Rodar o sistema, criar uma nota manual em rascunho, validar e “enviar” (stub).
- Verificar na API que a listagem retorna `pedido_id` e `origem_documento` quando existirem.
- Conferir checklist do PADRONIZACAO: o que já está ✅ e o que ainda é ⚠️ (ex.: NCM/CFOP nos itens do formulário).

**Critério de conclusão:** Todos sabem onde estão modelo, schema, formulário e payload; conseguem explicar o fluxo “nova nota → rascunho → enviar (stub)”.

**Duração:** 1 dia.

---

## Módulo 2 – Provedor real e certificado do CA (Fase 1 – parte 1)

**Objetivo:** Integrar um provedor fiscal real e permitir que o CA configure o certificado para emissão.

**Conteúdo:**
- Interface `IProvedorFiscal`: `enviar_nfe`, `cancelar_nfe`, etc.; payload que o provedor recebe (já completo para layout 4.0).
- Escolha do provedor: Focus NFE, NFS-e Nacional, ou outro; documentação e credenciais (certificado A1/A3, API key quando aplicável).
- Onde o CA configura o certificado: por empresa (tela/API); armazenamento seguro (ex.: campos já existentes `provedor_*_encrypted` ou upload de .pfx + senha).
- Factory de provedores: `get_provedor_fiscal(db, empresa)` retornando stub ou provedor real conforme configuração (global ou por empresa).
- Isolamento: cada CA só enxerga e usa suas empresas e certificados (escopo por `cliente_id` da empresa).

**Atividades:**
- Implementar adapter do provedor escolhido (ex.: `ProvedorFiscalFocusNFe`) implementando `IProvedorFiscal`.
- Implementar tela/API para o CA cadastrar certificado (ou credenciais do provedor) por empresa; persistir de forma segura.
- Trocar o stub pelo provedor real em ambiente de homologação (configuração).
- Testar: criar nota em rascunho → enviar → verificar se o provedor recebe o payload e retorna protocolo/chave (homologação).

**Critério de conclusão:** Em homologação, ao clicar “Enviar”, a chamada vai ao provedor real; o CA consegue configurar certificado/credenciais na sua empresa.

**Duração:** 1–2 semanas.

**Referência:** [PLANO_FATURAMENTO_NOTA_FISCAL.md](./PLANO_FATURAMENTO_NOTA_FISCAL.md) – tarefa 1.1.

---

## Módulo 3 – Dados fiscais nos itens e validação (Fase 1 – parte 2)

**Objetivo:** Garantir que, ao faturar pedido e ao criar nota manual, os itens tenham NCM, CFOP, CST/CSOSN e impostos preenchidos; validação pré-envio alinhada ao provedor/SEFAZ.

**Conteúdo:**
- Cadastro de produtos: onde fica NCM, CFOP (e opcionalmente CST/CSOSN, unidade); uso de `ProdutoCliente` ou tabela equivalente.
- `faturar_pedido`: ao montar `NotaFiscalItem`, preencher NCM, CFOP, origem (0–8), CST ou CSOSN, bases e valores de ICMS/PIS/COFINS (ou zerados conforme regime); unidade do produto.
- Série padrão: uso de `empresa.serie_padrao_nfe` (e `serie_padrao_nfce` se aplicável) no faturamento; fallback "1".
- `validar_nota_fiscal`: exigir NCM/CFOP por item quando obrigatório; validar CPF/CNPJ do destinatário para NF-e; mensagens claras.

**Atividades:**
- Garantir que o cadastro de produto (ou equivalente) tenha NCM e CFOP; ajustar `faturar_pedido` para preencher todos os campos fiscais dos itens.
- Ajustar `faturar_pedido` para usar série padrão da empresa.
- Reforçar `validar_nota_fiscal` com as regras acima; exibir erros na tela antes de “Enviar”.
- Testar: faturar um pedido → abrir a nota gerada → validar → enviar (provedor real em homologação).

**Critério de conclusão:** Nota gerada pelo faturamento possui itens com NCM, CFOP e tributação preenchidos; validação impede envio com dados incompletos quando configurado.

**Duração:** 1 semana.

**Referência:** [PLANO_FATURAMENTO_NOTA_FISCAL.md](./PLANO_FATURAMENTO_NOTA_FISCAL.md) – tarefas 1.2, 1.3, 1.4.

---

## Módulo 4 – Rastreabilidade e UX (Fase 2)

**Objetivo:** Melhorar rastreabilidade pedido ↔ nota e a experiência pós-faturamento.

**Conteúdo:**
- API: listagem e detalhe da nota já retornam `pedido_id` e `origem_documento`; adicionar filtro por `pedido_id` no GET de notas.
- Front: após faturar, exibir link “Ver nota #X” (e opcionalmente “Enviar para SEFAZ”); na listagem de notas, coluna “Origem” e link “Pedido #Y” quando houver `pedido_id`.

**Atividades:**
- Implementar query param `pedido_id` na listagem de notas; testar filtro.
- Na tela de confirmação pós-faturar (ou na lista de pedidos), adicionar botão/link “Ver nota #X” que abre a nota na tela de notas fiscais.
- Na tabela de notas, adicionar coluna “Origem” e, quando existir, “Pedido #” com link para o pedido.

**Critério de conclusão:** Usuário consegue filtrar notas por pedido e, após faturar, acessar a nota criada e ver a origem na listagem.

**Duração:** 1–2 semanas.

**Referência:** [PLANO_FATURAMENTO_NOTA_FISCAL.md](./PLANO_FATURAMENTO_NOTA_FISCAL.md) – Fase 2.

---

## Módulo 5 – XML padronizado e homologação SEFAZ

**Objetivo:** Garantir que o envio utilize XML no padrão do governo (NF-e 4.0) e que o fluxo seja aprovado em homologação.

**Conteúdo:**
- Documento [XML_NFE_PADRAO_GOVERNO.md](./XML_NFE_PADRAO_GOVERNO.md): quem gera o XML (provedor vs. nosso sistema); payload já completo para o layout 4.0.
- Provedor real: ele deve gerar o XML no layout 4.0 (XSD SEFAZ), assinar com o certificado do CA e enviar à SEFAZ; nosso sistema já envia todos os dados necessários no payload.
- Homologação: ambiente de testes da SEFAZ; certificado de homologação; fluxo completo (emitir, consultar, cancelar) e guardar XML/retorno para auditoria.

**Atividades:**
- Confirmar com o provedor escolhido que a geração e o envio seguem o layout NF-e 4.0 (e documentação oficial).
- Executar fluxo completo em homologação: cadastrar certificado de teste → faturar pedido (ou criar nota manual) → validar → enviar → baixar XML e DANFE → cancelar (se aplicável).
- Registrar em documento interno: versão do layout, provedor, data da última homologação bem-sucedida.

**Critério de conclusão:** Pelo menos uma NF-e autorizada em homologação; XML disponível e compatível com o padrão governo (conforme documentação do provedor/XSD).

**Duração:** 1 semana (depende de disponibilidade do ambiente e certificado de homologação).

---

## Módulo 6 – Go-live e venda do serviço

**Objetivo:** Colocar o serviço em produção e iniciar a venda no modelo CA.

**Conteúdo:**
- Checklist comercial: [MODELO_VENDA_SERVICO_FISCAL.md](./MODELO_VENDA_SERVICO_FISCAL.md) – certificado válido, cadastro da empresa, produtos com NCM/CFOP.
- Produção: trocar ambiente de homologação para produção (certificado e configuração do provedor); comunicar CAs sobre o que configurar.
- Monitoramento: erros de envio, rejeições SEFAZ, logs em `fiscal_evento` e `fiscal_download_log`; suporte ao CA.

**Atividades:**
- Validar checklist comercial com o time de vendas/operação.
- Definir processo de ativação do módulo para novo CA (cadastro de empresa, certificado, séries).
- Publicar guia rápido para o CA: “Como configurar o certificado” e “Como emitir NF-e a partir do pedido”.
- Go-live com um ou poucos CAs piloto; coletar feedback e ajustar documentação/processo.

**Critério de conclusão:** Serviço disponível em produção; pelo menos um CA emite NF-e real; documentação e checklist de venda utilizados pela equipe.

**Duração:** Contínuo (operações e melhorias).

---

## Cronograma sugerido (exemplo)

| Semana | Módulos / Entregas |
|--------|---------------------|
| 1 | M0 + M1 (contexto, padrões, conhecimento do código) |
| 2–3 | M2 (provedor real + certificado do CA) |
| 3–4 | M3 (dados fiscais nos itens + validação + série) |
| 4–5 | M4 (rastreabilidade + UX) + M5 (homologação SEFAZ) |
| 5–6 | Ajustes pós-homologação; preparação go-live |
| 6+ | M6 (go-live e venda do serviço) |

---

## Checklist geral de implantação

- [ ] M0 – Modelo CA e fluxo certificado entendidos pela equipe.
- [ ] M1 – Modelo, schema e formulário padronizados; payload completo conhecido.
- [ ] M2 – Provedor real integrado; CA consegue configurar certificado por empresa.
- [ ] M3 – Faturamento preenche NCM, CFOP, CST e impostos; validação reforçada; série padrão usada.
- [ ] M4 – Filtro por pedido; link “Ver nota” pós-faturar; coluna Origem e link Pedido na listagem.
- [ ] M5 – Homologação SEFAZ ok; XML no padrão governo confirmado (via provedor).
- [ ] M6 – Go-live em produção; checklist comercial e guia do CA publicados; primeiro CA emitindo NF-e real.

---

*Documento único do plano do curso para implantação do módulo fiscal. Atualizar conforme conclusão de cada módulo.*
