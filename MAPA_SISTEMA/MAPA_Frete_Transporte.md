# MAPA DE FRETE E TRANSPORTE — PDV Ibix

## Visão Geral e Escopo

Este documento é a **fonte única de verdade** sobre frete e transporte no PDV Ibix no contexto de **venda**: valores de frete, formato de entrega, integrações com sistemas de transporte de terceiros e eventual sistema de transporte interno.

**Importante:** Este módulo **não** se refere ao **frete de recebimento** (notas de entrada/compras). O frete de entrada está no **Módulo Entrada de Notas NFe** (ver `MAPA_DO_SISTEMA.md`): lá o valor de frete do XML (`vfrete_xml`) é lido, rateado no custo dos itens e lançado no estoque. O escopo aqui é:

- **Cliente Administrador (CA)** — quando o CA vende (pedidos internos, NF-e de saída).
- **Loja (Marketplace/Vitrine)** — quando o consumidor compra na vitrine e escolhe entrega ou retirada.

**Referências cruzadas:** Marketplace e vitrine em `MAPA_DO_SISTEMA.md` (§ 12); endpoints em `MAPA_DE_API.md` (Seção 19 — Loja/checkout; Seção 18 — Pedidos); modelo e fluxo em `vitrine_raiz/FLUXO_E_MODELO_MARKETPLACE.md`.

---

## 1. Resumo do que existe hoje

| Área | Implementado | Observação |
|------|--------------|------------|
| **Loja (config)** | `formato_frete`, taxas, áreas (`LojaAreaEntrega`), override por anúncio | Cálculo no checkout via `marketplace_frete_checkout.py`; **edição** de `formato_frete`/taxas na API restrita a **Superadmin** (ver § 2.0) |
| **Pedido marketplace** | Tipo de entrega, endereço, taxa no pedido | `tipo_entrega`, `endereco_entrega`, `taxa_entrega`; total = subtotal − desconto + taxa_entrega |
| **Checkout vitrine** | Formulário tipo de entrega + endereço; cálculo de frete | Front `checkout.html` envia `tipo_entrega` e `taxa_entrega` conforme regras carregadas (API frete da loja / cálculo no cliente); ver `app/api/v1/loja.py` e `marketplace_frete_checkout.py` |
| **NF-e saída** | Campo valor_frete no modelo e no payload; tag transporte no XML | `valor_frete` na nota; XML com `vFrete` e `<transp><modFrete>9</modFrete></transp>` (sem frete / por conta do destinatário) |
| **Pedido interno (orçamento/pedido)** | Apenas data prevista de entrega | `data_prevista_entrega`; sem valor de frete nem modalidade de transporte |
| **Cálculo por CEP** | Não | Nenhuma integração com Correios, transportadora ou API de CEP |
| **Integração transportadora terceira** | Não | Sem correio, Jadlog, etc. |
| **Sistema de transporte interno** | Não | Sem gestão de frota, rotas ou entregas internas |
| **Rastreio** | Não | Sem código de rastreamento ou evento de entrega |

---

## 2. Loja (Marketplace) — configuração e pedido

### 2.0 Governança: quem altera o transporte da loja (UI × API)

**Módulo dedicado:** desde 2026-05, todo o fluxo de transporte foi extraído em `app/api/v1/transporte.py` (com `app/services/transporte/config_service.py` e `regras_service.py`, schemas em `app/schemas/transporte.py`). `marketplace.py` **não aceita mais** campos de transporte em `POST /loja` nem `PATCH /loja/{id}`: rejeição em dois níveis — (a) `model_validator(mode="before")` em `LojaMarketplaceBase`/`LojaMarketplaceUpdate` devolve **422** com mensagem `"Campos de transporte não são mais aceitos aqui: ... Use PATCH /api/v1/transporte/loja/{loja_id}"`; (b) helper `_bloquear_campos_transporte` em `marketplace.py` devolve **400** caso o schema mude e volte a aceitar. O legado `GET /api/v1/loja/{id}/frete` continua válido como **alias deprecado** (`deprecated=True` no OpenAPI) para `GET /api/v1/transporte/loja/{id}/regras`.

| Aspecto | Comportamento atual (código) |
|---------|------------------------------|
| **Campos na loja** | `formato_frete` (`sem_frete`, `gratis`, `taxa_fixa`, `plataforma`), `taxa_entrega_fixa`, `entrega_gratis_apos`, `tipo_entrega`, `raio_entrega_km` (ver modelo `LojaMarketplace`). **Não há colunas novas**: a UI com modo/submodo é **tradução** feita em `services/transporte/config_service.py`. |
| **Modo (UI) ↔ formato_frete (banco)** | `retirada` ⇄ `sem_frete`; `ambos + propria_gratis` ⇄ `gratis`; `ambos + propria_valor` ⇄ `taxa_fixa` (`taxa_entrega_fixa` ≥ 0 obrigatório; `entrega_gratis_apos` opcional); `ambos + plataforma` ⇄ `plataforma`. |
| **PATCH `/api/v1/transporte/loja/{loja_id}`** | Requer `marketplace:configurar_loja` + escopo da loja. **CA** salva só a própria loja; **Superadministrador** / Administrador com escopo amplo salva qualquer loja. SEO avançado e demais campos continuam em `PATCH /api/v1/marketplace/loja/{id}`. |
| **Tela única** (`/negocio/marketplace/areas-entrega`) | Rebatizada **«Transporte»** (também acessível pelo botão **«Configuração de entregas»** em `/negocio/marketplace`). Card de modo + CRUD de áreas + **card Plataforma — gestão de entregas** (atalhos para `/admin/entregadores` e `/negocio/financeiro#row-transportes`) **somente para Superadministrador** — o CA não vê esse card, mesmo escolhendo submodo `plataforma`. O CRUD de áreas continua com **`require_superadmin()`** em POST/PATCH/DELETE — sem mudança de permissão. |
| **Minha loja & SEO global** | `app/templates/marketplace/minha_loja.html` e `app/templates/admin/marketplace_seo_lojas.html` deixaram de exibir campos de frete; ambos linkam para a tela única de Transporte. |
| **Regra por item** | `app/services/marketplace_frete_checkout.py` — `resolver_regra_frete_anuncio`: anúncio com `frete_sobrescrever_loja` usa `formato_frete_produto` / taxas do produto; senão usa a regra da **loja**. |
| **Área × taxa fixa** | Com **cidade + UF** na entrega e linha ativa em `loja_areas_entrega` para essa cidade, o valor cobrado é **`LojaAreaEntrega.taxa_entrega`** (prevalece sobre `loja.taxa_entrega_fixa`). Sem área para a cidade mas com **alguma** área na loja → entrega indisponível naquela localidade. **Sem nenhuma área** → usa só `taxa_entrega_fixa` da loja. |

**Evoluções futuras** (prazos de entrega, SLAs por região, custo do entregador por categoria, regras de cobertura avançadas) devem entrar em `app/api/v1/transporte.py` + `app/services/transporte/` — **não** em `marketplace.py`.

Referência cruzada: **§ 12** em `MAPA_DO_SISTEMA.md` («Minha loja — `cliente_id`…»).

### 2.1 Modelo e banco (lojas_marketplace)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `formato_frete` | String(20) | `sem_frete` \| `gratis` \| `taxa_fixa` \| `plataforma` — define o que o checkout oferece (ex.: só retirada vs retirada+entrega). Migração **`ft01_frete_transp`**. |
| `tipo_entrega` | String(20) | `"retirada"` ou `"entrega"` — preferência/informativo da loja; o checkout usa sobretudo **`formato_frete`** (ver texto de ajuda em Minha loja). |
| `raio_entrega_km` | Integer, nullable | Raio em km (pouco usado no fluxo atual) |
| `taxa_entrega_fixa` | Numeric(10,2), nullable | Taxa fixa quando formato exige |
| `entrega_gratis_apos` | Numeric(10,2), nullable | Pedido acima deste valor → frete grátis (quando aplicável) |

**Migrações:** `mk01_marketplace_tables.py` (base); **`ft01_frete_transp`** (`formato_frete` + snapshots em pedido); **`mp05_frete_por_produto_override`** (campos por anúncio). Modelo: `app/models/loja_marketplace.py` e `app/models/anuncio_plataforma.py` (override).

**API:** `PATCH /api/v1/transporte/loja/{loja_id}` (schema `TransporteConfigUpdate` em `app/schemas/transporte.py`) é o único caminho para alterar `formato_frete`, `taxa_entrega_fixa`, `entrega_gratis_apos`, `tipo_entrega`, `raio_entrega_km`. `PATCH /api/v1/marketplace/loja/{id}` rejeita esses campos com HTTP 400.

### 2.2 Pedido marketplace (pedidos_marketplace)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `tipo_entrega` | String(20) | `"retirada"` ou `"entrega"` |
| `endereco_entrega` | Text, nullable | Endereço completo em texto livre (ex.: "Rua, número, bairro, CEP, cidade - UF") |
| `taxa_entrega` | Numeric(10,2) | Valor do frete no pedido; default 0 |
| `total` | Numeric(10,2) | `subtotal - desconto + taxa_entrega` |

**Modelo:** `app/models/pedido_marketplace.py`. **Checkout:** POST `/api/v1/loja/checkout` — body `PedidoCheckoutCreate` com `endereco_entrega`, `tipo_entrega`, `taxa_entrega` (ver `app/api/v1/loja.py`). O front da vitrine (`app/templates/loja/checkout.html`) calcula/exibe frete conforme regras da loja/anúncio e envia `taxa_entrega` no fechamento (não é mais fluxo fixo «sempre zero» quando há entrega e regra configurada).

### 2.3 Vitrine — exibição

- **Checkout:** formulário com tipo de entrega (Retirada / Entrega) e campo de endereço de entrega (textarea); resumo de frete alinhado a `GET /api/v1/loja/{loja_id}/frete` e lógica em `checkout.html` / `vitrine.js`.
- **Card/listagem:** badges de frete grátis quando a API de anúncios expõe `frete_gratis` / formato efetivo (ver `loja.py` e templates `produto.html` / `index.html`).
- **Documentação de fluxo:** `vitrine_raiz/FLUXO_E_MODELO_MARKETPLACE.md` (pode estar parcialmente desatualizado em relação ao cálculo atual — preferir este MAPA e o código).

---

## 3. NF-e de saída (venda) — frete na nota

### 3.1 Modelo e payload

- **NotaFiscal:** `valor_frete` — `app/models/nota_fiscal.py` (DECIMAL 10,2, default 0.00). Schema: `app/schemas/nota_fiscal.py`.
- **Payload para o provedor:** `app/services/fiscal/emissao_service.py` — `_payload_nota_fiscal(nota)` inclui `"valor_frete": _decimal_str(nota.valor_frete)`.
- **Front (Nova Nota):** `app/static/js/notas_fiscais.js` envia `valor_frete: 0` no payload.

### 3.2 XML (provedor interno)

- **nfe_xml_builder.py:** totais com `<vFrete>0.00</vFrete>`; bloco transporte com `<transp><modFrete>9</modFrete></transp>`. Código 9 = Sem frete / por conta do destinatário (padrão governo).
- **Documentação XML:** `docs/XML_NFE_PADRAO_GOVERNO.md` — capa inclui valor_frete nos totais.

### 3.3 Nota a partir de pedido marketplace

- Destinatário da NF-e: montado a partir de `PedidoMarketplace` pelo helper `_destinatario_from_pedido_marketplace(pedido)` em `emissao_service.py`: usa `comprador_nome`, `comprador_documento`, **`endereco_entrega`**, `comprador_email`, `comprador_telefone`. O endereço do comprador na nota é o texto de `endereco_entrega` (não há parse estruturado para cidade/UF/CEP). O valor de frete na nota continua vindo de `nota.valor_frete` (hoje zerado na criação).

---

## 4. Pedido interno (orçamento → pedido)

- **Pedido (fluxo CA):** tabela `pedidos` — campo `data_prevista_entrega` (Date, nullable). Usado em criação/atualização e no PDF do pedido (`app/services/pdf_orcamento_pedido.py`). **Não há** campo de valor de frete nem de modalidade de transporte (retirada/entrega) no pedido interno.
- **API:** POST/PATCH `/api/v1/pedidos` com `PedidoCreate`/`PedidoUpdate` — `data_prevista_entrega` opcional. Ver `MAPA_DE_API.md` Seção 18.

---

## 5. O que não existe (evoluções possíveis)

| Item | Estado |
|------|--------|
| **Cálculo de frete por CEP** | Não implementado. Nenhuma chamada a API de CEP ou de cotação (Correios, etc.). |
| **Integração com transportadora terceira** | Não. Sem API de etiqueta, coleta ou rastreio (Correios, Jadlog, Melhor Envio, etc.). |
| **Uso das regras da loja no checkout** | Implementado parcialmente: `marketplace_frete_checkout.py` + front checkout; **edição** dos campos principais de frete da loja na API só **Superadmin** (§ 2.0). |
| **Exibição de frete no card da vitrine** | Parcial: badges quando a API expõe `frete_gratis` / formato efetivo (ver § 2.3); sem cotação por CEP no card. |
| **Campo tempo de envio / prazo de entrega** | Não existe no modelo `AnuncioPlataforma` nem no schema da vitrine. |
| **Sistema de transporte interno** | **Implementado (2026-03):** Módulo **Logística local (entregador)** — ver § 6 abaixo. Frota/rotas/rastreio GPS continuam fora do escopo. |
| **Rastreio (código de rastreamento)** | Não há campo nem fluxo de rastreio no pedido marketplace. |
| **MDF-e (Manifesto Eletrônico)** | Citado em `docs/MODULO_FATURAMENT_V2.MD` como documento que agrega fiscais em transporte — não implementado no sistema. |

---

## 6. Logística local (entregador) — sistema de transporte interno MVP

**Implementado em 2026-03.** Entrega na cidade por entregador (moto/carro): o tenant (CA) cria e publica a entrega a partir do pedido marketplace; o **entregador** (ator separado, auth própria) vê ofertas, aceita e atualiza status até entregue.

| Aspecto | Implementação |
|---------|----------------|
| **Tabelas** | `entregadores`, `entregas_marketplace` (1 por pedido, UNIQUE pedido_id), `entrega_eventos` (histórico/timeline). Migrações lg01, lg02 (seed entregador teste). |
| **Status** | Constantes em `app/core/constants/entrega_status.py`. Fluxo: aguardando_publicacao → disponivel → aceita → em_retirada → retirada → em_rota → entregue (exceções: cancelada, expirada, falha_entrega). Máquina de estados no service. |
| **Auth entregador** | JWT `tipo=entregador`, cookie `entregador_token`; `create_entregador_token` e `get_current_entregador` (app/core/auth.py e app/api/v1/entregador.py). |
| **API entregador** | POST login; GET entregas-disponiveis; POST aceitar (lock transacional); GET minhas-entregas, GET detalhe; POST status. |
| **API logística (tenant)** | POST criar entrega, POST publicar, GET listar/detalhe, POST cancelar. Escopo por tenant (marketplace:visualizar). |
| **Regra expiração** | `aceita_ate_em < now()` e status disponivel → marcada como expirada (service `marcar_entregas_expiradas`; chamada na listagem disponíveis). |
| **Front entregador** | Rotas `/entregador/login`, `/entregador/disponiveis`, `/entregador/minhas-entregas`, `/entregador/entrega/{id}`. Templates em `app/templates/entregador/`. |
| **Front tenant** | Minha loja: coluna Entrega (Criar, Publicar, Acompanhar). Página `/negocio/marketplace/logistica/entrega/{id}` com timeline e cancelar. |

**Referência completa:** MAPA_DO_SISTEMA.md § 13 (Módulo Frete / Logística local). Plano: `.cursor/plans/módulo_frete_logística_entregador_*.plan.md`.

---

## 7. Referências no sistema

- **MAPA_DO_SISTEMA.md:** § 12 (Marketplace e Vitrine); **§ 13 (Módulo Frete / Logística local — entregador, tabelas, APIs, front)**; Módulo Entrada de Notas NFe (frete de entrada/rateio — fora do escopo deste mapa).
- **MAPA_DE_API.md:** Seção 19 (Loja, checkout, pedidos marketplace); Seção 18 (Pedidos — data_prevista_entrega). Endpoints entregador e logística documentados no MAPA_DO_SISTEMA § 13.
- **vitrine_raiz/FLUXO_E_MODELO_MARKETPLACE.md:** entrega/retirada, configuração da loja, tabela do card (frete parcial), lacunas (cálculo CEP, exibição no card).
- **.cursor/plans/redesign_visual_carrinho_loja_b35495ac.plan.md:** subtotal e total separados no DOM para futura inclusão de frete/cupom/desconto.
- **.cursor/plans/plano_marketplace.md:** destinatário NF-e a partir do pedido marketplace; endereço = `endereco_entrega` (texto).
- **.cursor/plans/módulo_frete_logística_entregador_*.plan.md:** plano do módulo de logística local (entregador, entregas_marketplace, eventos, aceite com lock, front).

---

---

## 8. Formato de frete e validação (implementado 2026-03-17)

### 8.1 Campo `formato_frete` em `lojas_marketplace`

Novo campo `formato_frete` (String 20, default `sem_frete`, CHECK constraint). Valores:

| Valor | Significado | Na vitrine | Quem fica com frete |
|-------|-------------|------------|---------------------|
| `sem_frete` | Apenas retirada | "Apenas retirada" | N/A |
| `gratis` | Entrega grátis (lojista paga) | "Frete grátis" | N/A |
| `taxa_fixa` | Lojista cobra taxa fixa | "Frete R$ X" ou "Grátis acima de R$ Y" | Lojista |
| `plataforma` | Plataforma define frete | "Frete R$ X" | Plataforma |

**API Minha loja:** PATCH `/api/v1/marketplace/loja/{id}` — campo `formato_frete` em `LojaMarketplaceUpdate`.
**API pública:** GET `/api/v1/loja/{loja_id}/frete` (público, sem auth) — retorna `formato_frete`, `tipo_entrega`, `taxa_entrega_fixa`, `entrega_gratis_apos`, `raio_entrega_km`.

### 8.2 Validação backend no checkout

O backend calcula `taxa_entrega` baseado no `formato_frete` da loja. O valor enviado pelo front é **ignorado** (segurança). `desconto` também é forçado a 0 até existir sistema de cupons.

### 8.3 Campos financeiros de frete

| Tabela | Campo | Descrição |
|--------|-------|-----------|
| `pedidos_marketplace` | `formato_frete_snapshot` | Snapshot do formato no momento da compra |
| `pedidos_marketplace` | `custo_frete` | Custo pago ao entregador (preenchido ao criar entrega) |
| `pedidos_marketplace` | `lucro_frete` | `taxa_entrega - custo_frete` (formato plataforma) |
| `extrato_loja` | `valor_frete_cliente` | Frete cobrado do cliente neste extrato |
| `repasses` | `valor_bruto_produto` | Parcela do bruto referente a produtos |
| `repasses` | `valor_bruto_frete` | Parcela do bruto referente a frete |

### 8.4 Entregador com N veículos

Nova tabela `entregador_veiculos`: tipo_veiculo, capacidade_kg, descricao, placa, ativo. CRUD em `/api/v1/entregador/veiculos`.

### 8.5 SuperAdmin — relatório de transportes

Endpoint GET `/api/v1/negocio/financeiro/repasses/transportes` (SuperAdmin only). Retorna entregas com dados completos: tenant, loja, comprador, entregador, formato_frete, valor_frete_cliente, custo_frete, lucro_frete, status. Cards: Total Frete Cobrado, Custo Entregadores, Lucro Frete Plataforma.

### 8.6 NF-e de saída com frete

`nfe_marketplace_service.py` agora preenche `nota.valor_frete` com `pedido.taxa_entrega`.

### 8.7 Migração

`ft01_frete_transporte_completo.py` (revises sp01_status_mk).

### 8.8 Área de Abrangência por Cidade

Nova tabela `loja_areas_entrega` (migração `ft02_areas_entrega_cep`):
- `loja_id`, `cidade`, `uf`, `codigo_ibge`, `taxa_entrega`, `prazo_dias`, `ativo`
- UNIQUE (loja_id, cidade, uf)

Modelo: `app/models/loja_area_entrega.py` — `LojaAreaEntrega`

**Fluxo:**
1. SuperAdmin configura cidades atendidas por loja em `/negocio/marketplace/areas-entrega`
2. Cada cidade tem sua taxa de entrega e prazo opcionais
3. API CRUD (SuperAdmin only): `GET/POST /marketplace/loja/{id}/areas-entrega`, `PATCH/DELETE /marketplace/areas-entrega/{id}`
4. API pública ampliada: `GET /loja/{id}/frete?cidade=X&uf=SP` retorna `entrega_disponivel`, `taxa_entrega_cidade`, `prazo_dias`
5. Checkout backend valida se cidade do comprador está na área; usa taxa da cidade. Se nenhuma área cadastrada, usa `taxa_entrega_fixa` (retrocompatível)
6. Se cidade não está na área e há áreas cadastradas: `HTTPException 400 "Entrega indisponível para esta localidade"`

### 8.9 Checkout com CEP Estruturado + ViaCEP

O checkout (`loja/checkout.html`, `vitrine_raiz/templates/checkout.html`) substitui a textarea de endereço por campos estruturados:
- CEP (com busca ViaCEP no blur), Logradouro (readonly), Número, Complemento, Bairro (readonly), Cidade (readonly), UF (readonly)
- Ao preencher CEP → auto-preenche endereço via `https://viacep.com.br/ws/{cep}/json/`
- Após ViaCEP → chama `GET /loja/{id}/frete?cidade=X&uf=Y` para verificar disponibilidade e obter taxa
- Se indisponível: alerta "Infelizmente não entregamos nessa localidade" e bloqueia frete
- Payload do checkout envia: `endereco_cep`, `endereco_logradouro`, `endereco_numero`, `endereco_complemento`, `endereco_bairro`, `endereco_cidade`, `endereco_uf`
- Backend monta `endereco_entrega` (texto) automaticamente a partir dos campos estruturados para NF-e e logística

**Carrinho** (`loja/carrinho.html`): campo CEP no resumo para consultar frete por cidade por loja em tempo real.

---

### 8.10 Frete por produto (override do anúncio) — 2026-03-26

- **Anúncio agora pode sobrescrever frete da loja** em `anuncios_plataforma`:
  - `frete_sobrescrever_loja` (bool)
  - `formato_frete_produto` (`sem_frete|gratis|taxa_fixa|plataforma`)
  - `taxa_entrega_fixa_produto` (quando aplicável)
  - `entrega_gratis_apos_produto` (quando aplicável)
- **Precedência de regra:** `produto > loja`.
- **Checkout por item:** o backend calcula `taxa_entrega` pela soma de frete item a item (sem fallback), permitindo carrinho misto com produtos de regra diferente.
- **Vitrine:** `/api/v1/loja/anuncios` e `/api/v1/loja/anuncios/{id}` retornam `frete_formato_efetivo`, `frete_origem_regra` e `frete_gratis` para badges e UX.
- **Modal Minha Loja:** anúncio exibe opção de frete por produto com destaque para badge `Frete grátis`.

### 8.11 Restrição RBAC no frete da loja — 2026-03-26

- A alteração de campos sensíveis da loja (`formato_frete`, `taxa_entrega_fixa`, `entrega_gratis_apos`) via `PATCH /api/v1/marketplace/loja/{loja_id}` passou a ser **somente Superadministrador**.
- CA/Admin continuam editando demais dados da loja.
- Frete no **anúncio/produto** continua disponível para CA, Administrador e Superadministrador.

---

### 8.12 Geolocalização e proximidade na vitrine — 2026-04-13

- **Colunas `latitude`/`longitude`** adicionadas em `clientes` e `enderecos_consumidor` (migração `geo01_lat_lng`), com índices parciais WHERE NOT NULL.
- **Geocodificação assíncrona** via Celery (`geocode_endereco`): BrasilAPI (primário) + Nominatim/OSM (fallback), cache Redis 24h, autoretry 3x com backoff.
- **Integração automática:** despacho ao criar/atualizar Cliente e EnderecoConsumidor. Backfill retroativo: enfileirar a task Celery `geocode_endereco` para registros sem coordenadas (`app/worker/geo_tasks.py`).
- **Endpoints públicos:** `GET /loja/geo/cidades` (autocomplete), `GET /loja/geo/cidade-proxima` (Haversine), `GET /loja/geo/reverso` (reverse geocoding server-side). Rate limit: 30/min por IP.
- **Busca por proximidade:** `GET /loja/anuncios` aceita `lat`, `lng`, `geo_cidade`, `geo_uf`; `sort=proximidade` ordena por Haversine SQL; response inclui `distancia_km`, `cidade_loja`, `uf_loja`.
- **Frontend vitrine:** Modal seletor de cidade com autocomplete + `navigator.geolocation`; localStorage (`ibix_geo_location`); seção "Perto de você" (carrossel); opção "Mais perto" na ordenação; badge de distância nos cards.
- **Mobile (paridade):** `expo-location` + `useGeo`/`useGeoStore` (MMKV `ibix_geo_location`); `LocationChip` no header + `CitySelectorSheet` (GPS ou seleção manual via `/loja/geo/cidades`); `NearbyAdsCarousel` consumindo `/loja/anuncios/perto-de-voce` (home) e `/loja/anuncios/proximos` (pós-busca); reverse geocoding via `/loja/geo/reverso` com fallback `/loja/geo/cidade-proxima`.
- **Relação com frete:** a geolocalização complementa a área de entrega por cidade (§ 8.8) ao priorizar produtos de lojas próximas independente da regra de frete. O cálculo de frete no checkout continua sendo feito separadamente com base na configuração da loja/produto.

---

**Última atualização:** 2026-04-13 — **§ 8.12:** Geolocalização e proximidade na vitrine (geocodificação assíncrona, endpoints geo, busca por proximidade, frontend). — 2026-03-26 — **§ 8.10–8.11:** Frete por produto com override `produto > loja`, checkout por item e restrição RBAC para edição de formato de frete da loja. — 2026-03-18: § 8.8–8.9 área por cidade, checkout CEP estruturado + ViaCEP. — 2026-03-17: formato de frete, validação backend, campos financeiros, entregador_veiculos, relatório SuperAdmin, NF-e com frete. — 2026-03-10: logística local (entregador). — 2026-03-09: criação do mapa.
