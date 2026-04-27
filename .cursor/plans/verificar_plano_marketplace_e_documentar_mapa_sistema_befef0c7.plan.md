---
name: Verificar plano marketplace e documentar MAPA_SISTEMA
overview: Verificar se o plano marketplace está funcional e alinhado com o sistema; garantir que não haja lacunas e que tudo que já existe (tabelas, modelos, APIs, telas) esteja inventariado para não ser criado novamente; documentar todas as informações em MAPA_SISTEMA (MAPA_DO_SISTEMA, MAPA_DE_API, INDICE).
todos:
  - id: verificar-alinhamento
    content: Verificar plano marketplace vs código e anotar divergências
    status: pending
  - id: inventario-mapa-sistema
    content: Inserir em MAPA_DO_SISTEMA § 12 inventário (tabelas, modelos, APIs, telas) e tabela não duplicar
    status: pending
  - id: mapa-api-secao19
    content: Revisar MAPA_DE_API Seção 19 e referência ao inventário
    status: pending
  - id: indice-palavras
    content: Atualizar INDICE com palavras-chave e última atualização
    status: pending
isProject: false
---

# Plano: Verificação do plano marketplace e documentação MAPA_SISTEMA

## 1. Objetivo

- Confirmar que [.cursor/plans/plano_marketplace.md](.cursor/plans/plano_marketplace.md) está **funcional e alinhado** com o que existe no código e nas tabelas.
- Identificar **lacunas** e garantir que **não se crie novamente** o que já existe (tabelas, modelos, APIs, telas).
- **Documentar** em [MAPA_SISTEMA/](MAPA_SISTEMA/) todas as informações: inventário do que já existe, tabelas, endpoints, planos e regras de "não duplicar".

---

## 2. Verificação: plano marketplace vs sistema

### 2.1 O que o plano marketplace descreve (e deve estar implementado)

- **1.0** Integração 100% pelo front (Minha loja: ativar, dados, anúncios, pedidos, extrato) — **já implementado** em [app/templates/marketplace/minha_loja.html](app/templates/marketplace/minha_loja.html) e APIs em [app/api/v1/marketplace.py](app/api/v1/marketplace.py).
- **1.1** Fonte única: `produtos_cliente`, `anuncios_plataforma`, `pedidos_marketplace`, `extrato_loja` — **existem** (modelos e migrações).
- **1.3** Cadastro/compra: `consumidores_marketplace`, POST cadastro/login, POST checkout — **APIs existem** em [app/api/v1/loja.py](app/api/v1/loja.py).
- **1.4** NF-e comprador: `pedido_marketplace_id`, VENDA_MARKETPLACE, task `emitir_nfe_pedido_marketplace` — **implementado** (modelo, migration nfe06, emissao_service, loja.py, tasks).
- **1.5** Notificação CA: task `notificar_ca_novo_pedido` — **implementado** em [app/worker/tasks.py](app/worker/tasks.py).
- **1.6** Baixa no checkout; PATCH pedidos (status) — **implementado**.
- **1.7** Minha loja (CA): listagem pedidos + extrato + PATCH status — **implementado** (minha_loja.html).
- **Revisão estilo Amazon:** Lacunas (pagamento real, gateway CA, carrinho multi-loja) já descritas no plano; não exigem criação de tabelas novas.

**Conclusão da verificação:** O plano está **alinhado** com o sistema. Nenhuma tabela ou fluxo do plano está "por implementar" em duplicidade — NF-e e notificação já estão no código. O que falta é apenas: (a) vitrine front (plano vitrine funcional) e (b) evoluções (pagamento no checkout, gateway por CA, carrinho multi-loja).

### 2.2 Lacunas a evitar

- **Não criar:** nova tabela de estoque (usar `produtos_cliente`); nova tabela de pedidos do consumidor (usar `pedidos_marketplace`); tabela de "envios" (status em `pedidos_marketplace.status_pedido`); tabela `clientes` por comprador (destinatário vem de `PedidoMarketplace`); segunda tabela financeira para valor da loja (usar `extrato_loja` + `faturamento_total`). O plano 1.8 já lista isso; a documentação deve repetir para quem for implementar.

---

## 3. Inventário do que já existe (não criar de novo)

### 3.1 Tabelas e migrações


| Tabela                                                         | Migração | Uso                                                                                                                           |
| -------------------------------------------------------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `lojas_marketplace`                                            | mk01     | 1:1 com cliente; status, slug, nome_loja, descricao, tipo_entrega, taxas, faturamento_total                                   |
| `categorias_plataforma`                                        | mk01     | nome, slug, ordem, ativa, categoria_pai_id                                                                                    |
| `consumidores_marketplace`                                     | mk01     | email, senha_hash, nome, telefone, documento (cadastro consumidor)                                                            |
| `enderecos_consumidor`                                         | mk01     | consumidor_id, cep, logradouro, numero, cidade, uf, etc.                                                                      |
| `anuncios_plataforma`                                          | mk01     | loja_id, produto_ca_id, categoria_id, status, titulo, preco_original/promocional, tipo_estoque, estoque_atual                 |
| `sync_controle`                                                | mk01     | Controle de sync estoque anúncios                                                                                             |
| `pedidos_marketplace`                                          | mk01     | loja_id, comprador_*, total, status_pedido, status_pagamento, endereco_entrega, gateway_pagamento, transaction_id, split_info |
| `pedido_itens_marketplace`                                     | mk01     | pedido_id, anuncio_id, quantidade, preco_unitario, preco_total                                                                |
| `avaliacoes_marketplace`                                       | mk01     | anuncio_id, consumidor_id, pedido_id, nota, comentario                                                                        |
| `extrato_loja`                                                 | mk01     | loja_id, pedido_id, tipo, valor_bruto, valor_liquido, status                                                                  |
| `notas_fiscais.pedido_marketplace_id` + enum VENDA_MARKETPLACE | nfe06    | NF-e de venda marketplace                                                                                                     |


### 3.2 Modelos (app/models/)

- LojaMarketplace, CategoriaPlataforma, AnuncioPlataforma, ConsumidorMarketplace, EnderecoConsumidor, PedidoMarketplace, PedidoItemMarketplace, AvaliacaoMarketplace, ExtratoLoja, SyncControle; NotaFiscal (com pedido_marketplace_id).

### 3.3 APIs já existentes

- **Gestão (marketplace):** GET/POST categorias, GET/PATCH categorias/{id}; GET loja (por cliente_id), POST loja, PATCH loja/{id}; GET/POST/PATCH anuncios, POST sync/estoque; GET loja/{id}/pedidos, PATCH pedidos/{id}; GET loja/{id}/extrato.
- **Vitrine (loja):** GET categorias, GET anuncios (filtros, paginação), GET anuncios/{id}; POST cadastro, POST login, POST logout; GET/PUT minha-conta, GET/POST endereços, GET meus-pedidos; POST pedidos/{id}/avaliar, GET anuncios/{id}/avaliacoes; POST checkout.

### 3.4 Telas e fluxos já implementados

- **Minha loja (CA):** [app/templates/marketplace/minha_loja.html](app/templates/marketplace/minha_loja.html) — ativar loja, dados da loja (PATCH), anúncios (listar, publicar, editar, pausar, sync estoque), pedidos (listar, PATCH status), extrato. Rota `/negocio/marketplace/minha-loja`; contexto `minha_loja_cliente_id`.
- **Vitrine (HTML):** Rotas em main.py para `/loja`, `/loja/categoria/{slug}`, `/loja/produto/{id}`, `/loja/busca`, `/loja/cadastro`, `/loja/login`, `/loja/carrinho`, `/loja/checkout`, `/loja/obrigado`, `/loja/minha-conta`, `/loja/meus-pedidos`. Templates em [app/templates/loja/](app/templates/loja/) — hoje esqueletos (sem JS/formulários); API por trás pronta.
- **Tasks Celery:** `emitir_nfe_pedido_marketplace`, `notificar_ca_novo_pedido` em [app/worker/tasks.py](app/worker/tasks.py).

---

## 4. Documentação a inserir em MAPA_SISTEMA

### 4.1 MAPA_DO_SISTEMA.md

- Na **seção 12 (Módulo Marketplace e Vitrine)**, adicionar subseção **"Inventário: o que já existe (não duplicar)"** com:
  - Lista das **tabelas** (nome, migração, propósito em uma linha).
  - Lista dos **modelos** (arquivo em app/models/).
  - Resumo dos **endpoints** (gestão em marketplace.py; vitrine em loja.py) com referência à Seção 19 do MAPA_DE_API.
  - **Telas implementadas:** Minha loja (minha_loja.html, rota, contexto); vitrine (rotas e templates existentes; front funcional no plano vitrine).
  - **Regra "não duplicar":** repetir a tabela do plano 1.8 (fonte única vs onde não criar) para visibilidade na documentação central.
- Garantir que **planos de referência** (plano_unificado, plano_marketplace, plano_vitrine_loja_funcional) estejam citados e que o plano marketplace seja descrito como **funcional e alinhado** com o sistema atual.

### 4.2 MAPA_DE_API.md

- Na **Seção 19**, conferir se todos os endpoints de [app/api/v1/marketplace.py](app/api/v1/marketplace.py) e [app/api/v1/loja.py](app/api/v1/loja.py) estão listados (GET/POST/PATCH com path e propósito).
- Se faltar algum endpoint, adicionar; caso contrário, apenas adicionar uma linha de "Referência: inventário completo em MAPA_DO_SISTEMA § 12".

### 4.3 INDICE.md

- Na tabela de palavras-chave, incluir entradas que levem ao inventário e à regra "não duplicar": ex. **"tabelas marketplace, inventário marketplace, não duplicar marketplace"** → MAPA_DO_SISTEMA § 12.
- Manter "Última atualização" com menção à documentação do inventário e alinhamento do plano marketplace.

---

## 5. Checklist de execução

1. **Verificação:** Ler plano_marketplace.md e confirmar item a item com o código (já resumido acima); anotar qualquer divergência (nenhuma esperada).
2. **MAPA_DO_SISTEMA:** Inserir subseção "Inventário: o que já existe (não duplicar)" no § 12; tabela de tabelas/modelos/APIs/telas; tabela "não duplicar" (1.8); texto que o plano marketplace está funcional e alinhado.
3. **MAPA_DE_API:** Revisar Seção 19; completar lista de endpoints se necessário; referência ao inventário no § 12.
4. **INDICE:** Adicionar palavras-chave (tabelas marketplace, inventário, não duplicar) e atualizar "Última atualização".

---

## 6. Arquivos envolvidos


| Ação   | Arquivo                                                                   |
| ------ | ------------------------------------------------------------------------- |
| Editar | [MAPA_SISTEMA/MAPA_DO_SISTEMA.md](MAPA_SISTEMA/MAPA_DO_SISTEMA.md) — § 12 |
| Editar | [MAPA_SISTEMA/MAPA_DE_API.md](MAPA_SISTEMA/MAPA_DE_API.md) — Seção 19     |
| Editar | [MAPA_SISTEMA/INDICE.md](MAPA_SISTEMA/INDICE.md)                          |


Nenhum código do projeto é alterado; apenas documentação.