# Plano: Resolução das Pendências do Módulo de Faturamento e Emissão de Nota Fiscal

**Objetivo:** Resolver todas as pendências identificadas e definir um modelo de oferta do serviço para começar a vender (B2B / cliente final).

---

## 0. Modelo de venda: Cliente Administrador (CA)

**A partir de agora, a venda do serviço de faturamento e emissão de nota segue o modelo CA:**

- **CA = Cliente Administrador:** cada cliente que adquire o sistema é um CA. Ele gerencia **apenas** as suas notas e os seus sistemas, dentro do próprio escopo (multi-tenant por CA).
- **Autogestão:** todo o gerenciamento das notas fiscais, empresas e emissões fica **por dentro do ambiente do CA** — sem depender de configuração centralizada pela operação para cada cliente.
- **Certificado válido:** o CA (ou usuário com permissão) apenas **insere o certificado digital válido para emissão de nota** na sua empresa fiscal. Com isso, o sistema emite NF-e/NFC-e em nome desse CNPJ, usando esse certificado.
- **Isolamento:** dados e notas de um CA não são visíveis nem acessíveis por outro CA.

**Resumo:** Vendemos para o CA; o CA configura seu certificado; o CA gerencia suas notas e sistemas só dentro do seu ambiente.

---

## 1. Visão do produto/serviço

| Oferta | Descrição | Pré-requisito |
|--------|-----------|----------------|
| **Fase 0 (atual)** | Faturamento de pedidos → NF em rascunho; emissão manual de NF-e/NFC-e em ambiente simulado (stub). | Nenhum; já disponível. |
| **Fase 1 – MVP vendável** | Mesmo fluxo + integração real com um provedor (ex.: Focus NFE ou NFS-e Nacional); emissão e cancelamento reais. | Provedor real + dados fiscais mínimos nos itens. |
| **Fase 2 – Produto completo** | Rastreabilidade pedido↔nota, filtros, link “Ver nota” pós-faturar, série por empresa, validações reforçadas. | Conclusão Fase 1. |
| **Fase 3 – Diferenciação** | Relatórios fiscais, DANFE/PDF automático, múltiplos provedores, NFS-e por ordem de serviço. | Conclusão Fase 2. |

---

## 2. Pendências e tarefas por fase

### Fase 1 – MVP vendável (prioridade para venda)

| # | Pendência | Tarefas | Responsável sugerido |
|---|-----------|---------|------------------------|
| 1.1 | **Provedor fiscal real + certificado do CA** | 1) Escolher provedor (Focus NFE, NFS-e Nacional, outro). 2) Criar adapter implementando `IProvedorFiscal`. 3) O **CA** configura na sua empresa: **certificado digital válido para emissão de nota** (arquivo .pfx/.p12 + senha, ou token A3 conforme provedor). 4) Armazenar certificado/credenciais por empresa (já existe `provedor_api_key_encrypted`, `provedor_api_secret_encrypted`; avaliar campo para certificado ou uso do provedor que aceita certificado). 5) Trocar stub por provedor real; emissão usando o certificado do CA. 6) Garantir que cada CA só acessa e usa **seus** certificados e notas (escopo isolado). | Backend |
| 1.2 | **Dados fiscais nos itens ao faturar** | 1) Garantir que produto/cadastro tenha NCM, CFOP (e opcionalmente CST/CSOSN). 2) No `faturar_pedido`, ao montar `NotaFiscalItem`, preencher NCM, CFOP, origem (0–8), CST ou CSOSN, bases e valores de ICMS/PIS/COFINS (ou zerados conforme regime). 3) Regra: Simples Nacional → CSOSN; regime normal → CST. 4) Unidade: buscar de cadastro do produto quando existir. | Backend |
| 1.3 | **Validação pré-envio** | 1) Em `validar_nota_fiscal`: exigir NCM/CFOP por item quando obrigatório pelo provedor; validar CPF/CNPJ do destinatário para NF-e. 2) Retornar mensagens claras para o usuário. | Backend |
| 1.4 | **Série padrão da empresa** | 1) No `faturar_pedido`, usar `empresa.serie_padrao_nfe` (e `serie_padrao_nfce` se no futuro houver NFC-e no faturamento). 2) Fallback "1" se não configurado. | Backend |

**Entregáveis Fase 1:** Cliente consegue faturar pedido → NF-e gerada com dados fiscais válidos → enviar para SEFAZ via provedor real → autorizar e baixar XML/PDF. Serviço vendável como “emissão de NF-e integrada ao pedido”.

---

### Fase 2 – Produto completo (experiência e rastreabilidade)

| # | Pendência | Tarefas | Responsável sugerido |
|---|-----------|---------|------------------------|
| 2.1 | **API: pedido_id e origem na nota** | 1) Incluir no schema `NotaFiscalResponse` (e onde fizer sentido em `NotaFiscalBase`) os campos `pedido_id` e `origem_documento`. 2) Garantir que a listagem e o detalhe da nota retornem esses campos. 3) Incluir no `NotaFiscalCreate` (e update se aplicável) os opcionais `pedido_id` e `origem_documento`. | Backend |
| 2.2 | **Filtro por pedido na listagem** | 1) No GET de notas fiscais, adicionar query param `pedido_id`. 2) Aplicar filtro na query quando informado. | Backend |
| 2.3 | **UX pós-faturamento** | 1) Após faturar, além do alert, exibir botão/link “Ver nota #X” (abre tela de notas com foco na nota ou redireciona para detalhe). 2) Opcional: “Enviar para SEFAZ” direto na tela de pedidos para a última NF do pedido. | Frontend |
| 2.4 | **Origem na tela de notas** | 1) Na listagem de notas (HTML/JS), exibir coluna “Origem” (manual, orçamento, venda_balcão, ordem_servico). 2) Quando houver `pedido_id`, exibir “Pedido #X” com link para `/negocio/pedidos/{id}` (ou equivalente). | Frontend |

**Entregáveis Fase 2:** Rastreabilidade completa pedido↔nota; usuário encontra a nota pelo pedido e vê de onde a nota veio.

---

### Fase 3 – Diferenciação (opcional para venda inicial)

| # | Pendência | Tarefas | Responsável sugerido |
|---|-----------|---------|------------------------|
| 3.1 | **Múltiplos provedores** | 1) Configuração por empresa (já existe `provedor_fiscal`). 2) Factory de provedores por valor (focus_nfe, nfse_nacional, etc.). 3) Manter stub para testes. | Backend |
| 3.2 | **Relatórios fiscais** | 1) Relatório de notas emitidas por período/empresa. 2) Exportação para contabilidade (ex.: CSV/Excel). | Backend + Frontend |
| 3.3 | **NFC-e no faturamento** | 1) Opção na tela de faturar: emitir NF-e ou NFC-e conforme perfil do cliente. 2) Usar `serie_padrao_nfce` e modelo 65. | Backend + Frontend |

---

## 3. Cronograma sugerido (exemplo)

| Fase | Duração estimada | Marco |
|------|------------------|--------|
| Fase 1 | 2–4 semanas | Primeira NF-e real autorizada via sistema |
| Fase 2 | 1–2 semanas | Link “Ver nota” e filtro por pedido em produção |
| Fase 3 | contínuo | Conforme demanda comercial |

---

## 4. Modelo para vender o serviço

### Público-alvo: Cliente Administrador (CA)

- Cada **CA** compra o serviço e passa a gerenciar **somente** as suas notas e os seus sistemas.
- Tudo ocorre **dentro do ambiente do CA**: cadastro de empresa, certificado, emissão, consulta e download de notas.
- O CA (ou usuário autorizado) **insere o certificado digital válido para emissão de nota** na empresa fiscal; o sistema utiliza esse certificado para assinar e enviar as NF-e à SEFAZ.

### O que pode ser vendido hoje (pós Fase 1)

- **Nome sugerido:** “Emissão de NF-e integrada ao PDV / Pedidos”.
- **Benefícios para o CA:** Faturar pedido com um clique; NF-e com dados fiscais corretos; envio à SEFAZ; download de XML e DANFE; cancelamento; auditoria de downloads; **tudo gerenciado por ele, apenas com o certificado válido cadastrado**.
- **Requisitos do CA:** Cadastro da empresa fiscal (CNPJ, IE, endereço); **certificado digital válido para emissão de nota**; produtos com NCM (e CFOP quando aplicável); contrato/credencial com o provedor escolhido (ex.: Focus NFE), quando aplicável.

### Precificação sugerida (exemplo)

- **Opção A:** Incluso em plano “Fiscal” ou “Completo” do PDV (X reais/mês).
- **Opção B:** Módulo fiscal avulso (Y reais/mês) + custo do provedor repassado ou incluído.
- **Opção C:** Por volume de notas (Z reais por N notas/mês).

### Checklist comercial (antes de fechar venda)

- [ ] Provedor fiscal definido e homologado (Focus NFE, etc.).
- [ ] CA terá cadastro de empresa (CNPJ, IE, endereço) e **certificado digital válido para emissão de nota**.
- [ ] Produtos com NCM (e CFOP quando obrigatório).
- [ ] Ambiente (homologação x produção) alinhado com o CA.
- [ ] Deixar claro: o CA gerencia suas notas e sistemas sozinho, apenas inserindo o certificado válido.

---

## 5. Próximos passos imediatos

1. **Decisão:** Qual provedor usar na Fase 1? (Focus NFE, NFS-e Nacional, outro.)
2. **Backend:** Implementar 1.1 (provedor real + **certificado do CA por empresa**, escopo isolado) e 1.2 (dados fiscais nos itens).
3. **Cadastro CA:** Garantir que o CA possa **inserir o certificado digital válido para emissão de nota** por empresa (tela/API segura; armazenamento criptografado).
4. **Cadastro:** Garantir tela/API para NCM/CFOP (e série padrão) na empresa/produto.
5. **Teste:** Fluxo completo em homologação: CA cadastra certificado → pedido → faturar → enviar → autorizar → baixar XML/PDF.
6. **Documentação:** Guia rápido “Como emitir NF-e a partir do pedido” e “Como o CA configura o certificado” para o cliente.

---

*Documento criado para planejamento do módulo de faturamento e emissão de nota fiscal. Atualizar conforme conclusão das fases.*
