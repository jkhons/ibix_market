# Análise: seleção de produtos na faixa «Perto de você» (vitrine)

Documento apenas descritivo — sem alterações de código. Data da análise: 2026-04-27.

---

## 1. Onde está na interface

- Template: `app/templates/loja/index.html`
- Seção `#loja-perto-voce`, inicialmente com `style="display:none;"`.
- Subtítulo padrão: «Mostrando produtos das lojas mais próximas da sua localização.»

---

## 2. Quando a faixa aparece

A função `loadPertoDeVoce()` só prossegue se:

1. Existirem os elementos DOM da seção e do grid.
2. `Vitrine.getAnuncios` estiver disponível.
3. A geolocalização em `Vitrine.getGeoLocation()` tiver **pelo menos** `lat` **ou** `cidade`  
   (condição: `geo.lat != null` **ou** `geo.cidade`).

Se não houver esse contexto geo, a seção permanece oculta.

Se a API retornar lista vazia, a seção também fica oculta (`.catch` idem).

---

## 3. Origem dos dados de localização

- Chave no `localStorage`: `ibix_geo_location` (definida em `app/static/js/vitrine.js`).
- `getGeoLocation()` apenas lê e faz `JSON.parse`; não obtém GPS por si só (quem grava é outro fluxo da UI ao definir localização).

---

## 4. Parâmetros da requisição (faixa «Perto de você»)

Em `loadPertoDeVoce()`:

| Parâmetro   | Valor |
|------------|--------|
| `skip`     | `0` |
| `limit`    | `12` |
| `sort`     | `"proximidade"` |

Além disso, se existir no objeto geo:

- `lat` / `lng` quando `geo.lat != null` (e tipicamente `lng` acompanha).
- `geo_cidade` / `geo_uf` quando houver cidade (e UF).

Comportamento extra em `getAnuncios` (`vitrine.js`):

- Mescla automaticamente geo do `localStorage` com os `params` (lat/lng/cidade/UF podem vir dos params explícitos ou do storage).
- Se existir `window.LOJA_SLUG_CONTEXT` e **não** houver filtro `cliente_ids`, adiciona `loja_slug` à query — ou seja, **numa vitrine de uma loja específica**, a faixa «Perto de você» restringe-se aos anúncios **daquela loja** (a ordenação por proximidade continua sendo entre usuário e o cadastro da loja).

---

## 5. Endpoint e filtros base

- Rota: `GET` … `/anuncios` — implementação em `app/api/v1/loja.py`, função `listar_anuncios_vitrine`.

Filtros sempre aplicados na query principal:

- `AnuncioPlataforma.status == "publicado"`
- `LojaMarketplace.status == "ativo"`

Não há, neste endpoint, filtro por **raio máximo em km** ou exclusão de produtos «longe demais»: a lógica é **ordenar** (e, sem GPS, **priorizar** região), não cortar por distância.

---

## 6. Como `sort=proximidade` funciona no backend

### 6.1 Com latitude e longitude do usuário

- Condição interna: `has_geo = lat is not None and lng is not None`.
- Ordenação: distância em linha reta (fórmula haversine, raio 6371 km) entre `(lat, lng)` do usuário e `(Cliente.latitude, Cliente.longitude)` da **loja** dona do anúncio.
- Lojas **sem** `latitude`/`longitude` no cadastro do cliente: tratadas como distância muito grande (`999999` na ordenação), ficando **por último**.
- Desempate: `AnuncioPlataforma.id`.

### 6.2 Pedido `sort=proximidade` mas **sem** lat/lng

- O backend **altera** `sort` para `"recent"` (comportamento documentado no próprio endpoint: proximidade «requer lat+lng»).
- Como `sort` deixa de ser `proximidade`, cai no ramo «default» da ordenação.
- Se houver join com `Cliente` e foram passados `geo_cidade` e/ou `geo_uf`, aplica-se **priorização regional** (não é distância em km):

  1. Prioridade **0**: mesma cidade **e** mesma UF que a loja (`Cliente.cidade` / `Cliente.uf`).
  2. Prioridade **1**: mesmo UF (se `geo_uf` informado).
  3. Prioridade **2**: demais casos.

- Dentro do mesmo nível de prioridade: `updated_at` descendente, depois `id`.

Ou seja: **só com cidade no geo (sem GPS), «Perto de você» não ordena por quilometragem**; ordena por coincidência cidade/UF e recência dos anúncios.

---

## 7. Resumo executivo

| Cenário | Seleção / ordenação dos produtos na faixa |
|---------|-------------------------------------------|
| Usuário com **lat + lng** | Até **12** anúncios publicados de lojas ativas; ordenados pela **distância** até o endereço geocodificado da loja (`Cliente`). Sem raio máximo. |
| Usuário com **cidade** (e tipicamente UF) mas **sem** lat/lng | Mesmo conjunto base de elegibilidade; ordenação por **prioridade regional** (cidade/UF iguais à do usuário primeiro) + **mais recentes**, **não** por km. |
| Sem geo válida | Faixa **não** é exibida. |
| Página com **slug de loja** no contexto | Resultados limitados a anúncios dessa loja; «perto» reflete ordenação em cima desse subconjunto. |

---

## 8. Referências rápidas de código

- Front (faixa + chamada): `app/templates/loja/index.html` — `loadPertoDeVoce`, `window._geoOnChange`.
- Client API: `app/static/js/vitrine.js` — `getGeoLocation`, `getAnuncios`.
- Backend: `app/api/v1/loja.py` — `listar_anuncios_vitrine` (`has_geo`, `sort == "proximidade"`, bloco `geo_priority`).

---

## 9. Melhor «projeção» de quem está perto quando o foco é o comércio **da cidade**

Contexto: com **apenas cidade + UF**, todos os estabelecimentos da mesma cidade ficam no mesmo patamar de «próximo»; não há como distinguir bairro, malha viária ou CEP **sem** alguma forma de posição ou zona mais fina.

### 9.1 Modelo recomendado (linha de base)

**Dois pontos no mapa + distância** continua sendo o modelo mais simples e que melhor reflete «perto de mim» para vitrine e entrega urbana:

1. **Usuário**: obter um par `(lat, lng)` confiável **dentro da cidade** — não só o nome da cidade (que pode ser um ponto único gigante no mapa).
2. **Loja**: manter `(lat, lng)` no cadastro do cliente/endereço da loja (geocodificação do endereço completo ou do CEP quando o restante não existir).
3. **Ordenação**: distância em linha reta (**Haversine**, como já existe na API) ou, se o produto precisar refletir tempo de deslocamento, **tempo/distância roteirizada** (API de roteamento ou matriz OD — maior custo e latência).

Esse conjunto é o «melhor modelo» no sentido de **custo/benefício**: interpretável, auditável e alinhado ao texto «perto de você».

### 9.2 Como preencher o ponto do usuário sem GPS

Quando o usuário não quiser compartilhar localização do navegador:

| Abordagem | Prós | Contras |
|-----------|------|---------|
| **CEP** (consulta ViaCEP ou similar + geocodificação do logradouro/bairro quando possível) | Familiar no Brasil; refina bem dentro da cidade em muitos casos | Alguns CEPs são amplos; precisão varia |
| **Bairro + cidade** escolhidos em lista ou mapa | Bom para UX sem expor endereço completo | Dependência de base de bairros/normalização |
| **Centroide da cidade** só pelo nome | Simples | Ruim para «perto»: todos na cidade ficam à mesma distância do centro |

Para **comércio da cidade**, CEP ou bairro costumam ser o melhor complemento à cidade quando não há GPS.

### 9.3 Modelo em camadas (fallback hierárquico)

Útil quando nem todo cadastro de loja tem coordenadas ou CEP válido:

1. **Camada A** — usuário e loja com **lat/lng**: ordenar por distância (Haversine ou rota).
2. **Camada B** — sem coords do usuário, mas com **CEP do usuário** geocodificado e loja com coords: mesmo critério de distância a partir do ponto do CEP.
3. **Camada C** — usuário sem ponto, mas **mesmo bairro** (campo normalizado na loja e no perfil): priorizar match de bairro **antes** de recência dentro da cidade.
4. **Camada D** — apenas **mesma cidade + UF**: priorização regional + recência (comportamento próximo ao atual sem GPS).

Isso evita «buraco» quando uma parte dos dados é espacial e outra não.

### 9.4 Infraestrutura de dados (escala)

- Índice **espacial** (PostGIS `Geography`, ou ao menos índice em `(latitude, longitude)` com bounding box pré-filtro + Haversine) para não ordenar milhões de linhas na aplicação.
- Opcional: **geohash / H3** para agregações («lojas nesta célula») e cache.

### 9.5 Quando ir além da linha reta

- **Entrega urbana**: tempo estimado de carro/moto (**Distance Matrix**, OSRM, etc.) pode ordenar melhor que Haversine em áreas com rios, vias rápidas ou sentidos únicos — troca-se precisidade por custo operacional da API e SLA.
- **Raio máximo**: opcionalmente **filtrar** estabelecimentos além de X km ou X minutos para não misturar «perto» com «mesma cidade mas longe».

### 9.6 Resumo da recomendação

| Objetivo | Modelo preferível |
|----------|-------------------|
| Melhor sensação de «perto» dentro da cidade | **Coordenadas** usuário + loja + ordenação por distância (e opcionalmente rota). |
| Usuário sem GPS | **CEP ou bairro** → gerar coords aproximadas do usuário; lojas já geocodificadas. |
| Enquanto o cadastro não está completo | **Fallback em camadas** (coords → bairro → cidade/recência). |

---

*Seção adicionada em 2026-04-27 — orientação de produto/arquitetura, sem implementação neste documento.*

---

## 10. Implementação concluída em 2026-04-27

Esta seção descreve **o que foi efetivamente implementado** após a análise das seções anteriores. Todas as mudanças preservam o comportamento legado quando não há coordenadas precisas do morador.

### 10.1 Captura precisa do ponto do morador

Modal `#geo-modal` em `app/templates/loja/base_loja.html` ganhou os campos:

- **CEP** (8 dígitos, máscara automática)
- **Número do imóvel**
- **Complemento** (opcional)

Ao confirmar, o front chama `Vitrine.geocodeAddress({ cep, numero, complemento })` que aciona o endpoint **`GET /api/v1/loja/geo/geocodificar`**. O resultado (lat/lng + cidade/UF + bairro + `precision`) é gravado no `localStorage` (`ibix_geo_location`). Endereços que retornam apenas precisão `locality` (cidade) são **rejeitados** com HTTP 422 — o usuário é avisado a conferir o número.

O botão "Usar minha localização" (GPS do navegador) e a busca por cidade continuam funcionando como antes; o novo bloco de endereço aparece **acima** dessas opções porque é o caminho mais certeiro.

### 10.2 Geocodificação das lojas (`Cliente`)

- **Migration** `aa78cc680p7z3_add_geocoding_precision_clientes`: nova coluna `clientes.geocoding_precision VARCHAR(20)` + índice. Auditoria de qualidade: `rooftop` / `range_interpolated` / `geometric_center` / `approximate` / `locality` / `manual`.
- **Modelo** `app/models/cliente.py` recebeu o campo e o índice.
- **Service** `app/services/geo_service.py` ganhou `geocode_address(cep, numero, complemento, cidade=None, uf=None)` retornando um `GeocodeResult`. Provedores em ordem:
  1. **Google Geocoding API** (se `GOOGLE_MAPS_API_KEY` estiver configurada) — precisão `rooftop`/`range_interpolated`.
  2. **BrasilAPI v2** (logradouro/cidade/UF do CEP) + **Nominatim/OSM** (refino com logradouro + número).
  3. Fallback: BrasilAPI isolado → Nominatim só por cidade/UF.
- **Cache Redis** por chave `geo:addr:{cep}:{numero}:{complemento}`, TTL 30 dias (configurável via `GEO_ADDR_CACHE_TTL`).
- **Hook automático** em `app/services/cliente_service.py`: ao criar/atualizar `Cliente`, dispara a Celery task `geocode_endereco`. A task agora extrai número via regex do `endereco` (campo livre), chama `geocode_address`, grava `latitude`/`longitude`/`geocoding_precision` e registra `audit_action`.
- **Backfill** `scripts/backfill_geocode_clientes.py`: roda contra clientes sem coords ou com precisão `locality`. Suporta `--dry-run`, `--apenas-faltantes`, `--limite`, `--sleep-ms`.

### 10.3 Distância de rota real (`routing_service.py`)

Novo módulo `app/services/routing_service.py`:

- API pública: `distance_matrix(origin, destinations) -> List[RouteLeg]`.
- **Provedor 1**: **Google Distance Matrix** (`GOOGLE_MAPS_API_KEY`) — modo `driving`, idioma pt-BR, region br.
- **Provedor 2**: **OSRM público** (`router.project-osrm.org`) — gratuito, "best effort".
- **Fallback**: Haversine com flag `is_estimate=True` quando provedores falham (resposta nunca quebra a UI).
- **Cache Redis** por geohash da origem (precisão ~150 m, configurável) — moradores na mesma quadra reutilizam respostas para as mesmas lojas; TTL 24h.
- **Lote** de 25 destinos por chamada; campos retornados: `distance_km`, `duration_min`, `provider`, `is_estimate`.

### 10.4 Endpoint da home — produtos aleatórios + ordenados por rota

`GET /api/v1/loja/anuncios/perto-de-voce` (em `app/api/v1/loja.py`):

1. Recebe `lat`, `lng` (obrigatórios), `limit` (default 12), `pool` (default 40), `bbox_km` (default 50).
2. Pré-filtra anúncios publicados de lojas ativas com `Cliente.latitude/longitude` dentro da bounding box `bbox_km` (caixa em graus indexada).
3. Sorteia aleatoriamente até `pool` anúncios, **diversificando por loja** (no máximo 2 anúncios da mesma loja na seleção).
4. Chama `distance_matrix` com a origem do morador e os destinos das lojas.
5. **Ordena por duração de rota** ascendente (fallback distância) e corta em `limit`.
6. Devolve `AnuncioVitrineResponse` com `distancia_rota_km`, `duracao_rota_min`, `rota_estimada` e mantém `distancia_km` (Haversine) para compatibilidade.

No front, `loja-perto-voce-grid` agora usa `Vitrine.getAnunciosPertoDeVoce` quando há lat/lng. Se o usuário só tem cidade/UF, mantém o fluxo antigo (`sort=proximidade`). O subtítulo da seção muda para "Produtos diversos, ordenados pela distância de carro até cada loja." quando o cálculo é por rota.

### 10.5 Endpoint pós-busca — lojas mais próximas que vendem o produto

`GET /api/v1/loja/anuncios/proximos?q=&lat=&lng=&limit=&max_km=`:

1. Filtra anúncios publicados de lojas ativas dentro da bounding box (`bbox_km` default 80).
2. Casa o termo `q` em **título/descrição/atributos do anúncio + nome/descrição/código do produto + nome/descrição da categoria** (cada token = AND, OR entre campos).
3. Agrupa por loja (uma melhor oferta por loja, ranking por preço efetivo ascendente).
4. Pega o **top-N lojas mais próximas (Haversine)** — default 50, configurável.
5. Refina com `distance_matrix` (rota real) e ordena por duração/distância.
6. Aplica filtro opcional `max_km`.

Na home (template `app/templates/loja/index.html`), aparece a nova seção `#loja-busca-proximas` **abaixo da listagem padrão** quando `busca_ativa` e há `lat/lng`. O JS é `loadBuscaProximas()` invocado também por `_geoOnChange`.

### 10.6 Cards com km/min de rota

A função `cardHtml()` em `index.html` agora prioriza `distancia_rota_km` no badge geo:

- `12.4 km · 18 min` quando vem de Google/OSRM (`rota_estimada=false`).
- `~12 km` quando é Haversine (estimativa).
- Mantém badge antigo `~X km` quando o backend não retornou rota (compatibilidade com `/anuncios` legado).

### 10.7 Variáveis de ambiente novas

Todas opcionais — defaults preservam comportamento antigo:

| Variável | Default | Função |
|----------|---------|--------|
| `GOOGLE_MAPS_API_KEY` | (vazio) | Habilita Google Geocoding + Distance Matrix |
| `GEO_ADDR_CACHE_TTL` | `2592000` (30d) | TTL do cache de geocodificação por endereço |
| `ROUTING_CACHE_TTL` | `86400` (24h) | TTL do cache de rotas |
| `ROUTING_BATCH` | `25` | Tamanho do lote de destinos por chamada de matriz |
| `ROUTING_HTTP_TIMEOUT` | `15` | Timeout HTTP em segundos |
| `ROUTING_GEOHASH_PRECISION` | `7` | Precisão (~150 m) do geohash da origem para cache |

### 10.8 Observabilidade

- Logs `INFO` por provedor/falha em `geo_service` e `routing_service` (`provider falhou erro=...`).
- Auditoria em `audit_log` quando coords de cliente são atualizadas (com `precision`, `fonte`, `tem_numero`).
- Resposta dos endpoints expõe `rota_estimada` para o front sinalizar precisão ao usuário.

### 10.9 Compatibilidade

- O endpoint legado `GET /loja/anuncios` continua devolvendo `distancia_km` (Haversine) — nada quebra.
- Lojas sem `latitude`/`longitude` ficam fora dos novos endpoints; o backfill resolve em uma execução.
- A faixa antiga "Perto de você" continua respondendo a usuários que só escolheram cidade no modal.

*Seção adicionada em 2026-04-27 — implementação concluída.*
