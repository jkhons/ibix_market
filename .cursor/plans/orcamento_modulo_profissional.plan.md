# Plano: módulo Orçamento alinhado a Venda/OS e conversões

## Decisão explícita (confirmada pelo produto)

- **Conversão do orçamento em Ordem de serviço:** é **obrigatório** informar o **tipo de OS** (`tipo_id`) **no momento da conversão**, via **modal** (mesma necessidade do fluxo “Nova OS”). A UI deve listar os tipos a partir da **API já usada** pela tela de Ordem de serviço (ex.: tipos de OS do tenant). Sem `tipo_id` válido → não converte; erro **4xx** claro no backend.

## Contexto do modelo (não confundir FKs)

| Conceito | Orçamento (API) | Venda / OS |
|----------|-----------------|------------|
| Loja / catálogo (`produtos_cliente`) | `cliente_id` | implícito no escopo + `cliente_id` na URL de produtos |
| Consumidor | `destinatario_id` | `cliente_id` na venda e na OS |

Conversões **OS** e **Venda** devem usar `orcamento.destinatario_id` como consumidor na entidade destino (`OrdemServico.cliente_id`, `Venda.cliente_id`), exceto se o produto permitir venda sem cliente (alinhado ao modal de venda).

## 1. Formulário `/negocio/orcamentos/novo` e edição

**Arquivo:** [app/templates/meu_negocio/orcamentos/form.html](app/templates/meu_negocio/orcamentos/form.html)

- Primeiro na UX: **Cliente / Consumidor** → `destinatario_id` (padrão Nova venda / Nova OS: busca ou select via API com permissões corretas).
- **Estabelecimento (unidade):** campo para `cliente_id`; obrigatório para catálogo e API; sem fallback silencioso “primeiro do escopo” (regra SaaS: ver skill golden rules).
- Carregar produtos com `cliente_id` = estabelecimento escolhido.
- Ajustar textos de validação (“selecione a unidade” ao adicionar item, etc.).

## 2. Itens: peças/serviços (incl. tipo “Ordem de serviço”)

- Garantir listagem completa (limite/paginação ou busca no modal).
- Opcional profissional: filtro por `tipo_material_id` / abas, dados vindos da API (sem listas hardcoded no JS).

## 3. Backend: conversões

**Arquivos:** [app/api/v1/orcamentos.py](app/api/v1/orcamentos.py), novo serviço ou extensão, [app/models/orcamento.py](app/models/orcamento.py)

- Manter `POST .../converter` → pedido.
- **Novo:** converter → **OS** (body com `tipo_id` obrigatório + validações de escopo/status/validade; copiar itens; marcar orçamento convertido).
- **Novo:** converter → **Venda** (itens + totais; observações com referência ao orçamento).
- Modelo: FKs ou campos de rastreio para OS/venda convertida (e regra: **uma** conversão por orçamento, como hoje com pedido).
- RBAC: permissões novas se necessário; alinhar ao MAPA_RBAC.

## 4. Lista de orçamentos

**Arquivo:** [app/templates/meu_negocio/orcamentos/index.html](app/templates/meu_negocio/orcamentos/index.html)

- Ações: Emitir, Converter (submenu: Pedido | **OS com modal de tipo** | Venda), PDF, e-mail/WhatsApp onde já existir na API.
- Colunas úteis: cliente/destinatário, vínculo “convertido em …”.
- Filtro por estabelecimento para multi-unidade.

## 5. PDF e refinamentos

- PDF: clareza entre nome da loja e consumidor ([_dados_orcamento_para_pdf](app/api/v1/orcamentos.py)).
- Rodapé de totais no formulário; links pós-conversão quando aplicável.

## Fora de escopo até nova decisão

- Comportamento pós-conversão para venda (abrir `/negocio/vendas` vs só registrar): **não fixado** neste plano; implementar o padrão já usado ao criar venda por API.
