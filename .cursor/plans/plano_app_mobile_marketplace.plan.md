# Plano-Guia — App Mobile Marketplace (Vitrine PDV Ibix)

**Versão:** 2.1
**Data:** 2026-05-04
**Objetivo:** Criar app mobile nativo (iOS + Android) para consumidor final comprar na vitrine do marketplace PDV Ibix, com nível profissional comparável a grandes players (Mercado Livre, Shopee, Amazon).

**Stack escolhida:** React Native (Expo) — codebase único para iOS e Android.

**Princípio:** O app consome as APIs REST existentes em `/api/v1/loja` e `/api/v1/marketing-vitrine`. O backend (FastAPI) é a fonte única de verdade. Nenhum dado é hardcoded no app. Seguem-se todas as regras de `MAPA_DE_REGRAS.md` § 0.

---

## Identidade Visual e Naming (regra OBRIGATÓRIA)

**Fonte canônica:** `app/static/css/loja.css` (paleta, tipografia, radii, focus) e `app/static/img/ibix/cab.png` (logo). O app mobile espelha esses tokens — **mudanças visuais começam pela vitrine, o app segue.**

| Aspecto | Vitrine web | App mobile |
|---|---|---|
| **Display name** | `Ibix` (`<title>...| Ibix`) | `Ibix` (`expo.name` no `app.json`, exibido nas lojas e no springboard) |
| **Brand visível** | `Ibix Market` (logo `cab.png` no header) | `Ibix Market` (logo `cab.png` via `<BrandLogo>`) |
| **Paleta** | tokens `--ibix-*` em `loja.css:9-18` | `mobile_marketplace/theme/colors.ts` (light + dark) |
| **Fundo** | `#FEF7F1` (off-white) | `colors.background` = `#FEF7F1` |
| **Texto** | `#4A627A` / `#2F3A44` | `textSecondary` / `textPrimary` |
| **CTA** | verde-musgo `#5C6E4A` | `colors.primary` |
| **Hover/destaque** | terracota `#C47A44` | `colors.accent` |
| **Premium** | dourado `#D9B48B` | `colors.premium` |
| **Tipografia** | Poppins / DM Sans (`loja.css:1394`) | Poppins (`@expo-google-fonts/poppins`) |
| **Radius** | 8 (botões), 10 (search), 14 (cards) | `borderRadius.sm/md/lg` = 8/10/14 |
| **Focus** | `outline 2px #C47A44` | `colors.focusRing` + `focusRing.width=2, offset=2` |
| **Splash** | `theme-color: #FEF7F1` | `splash.backgroundColor = #FEF7F1` + `splash-icon.png` (cab.png) |
| **Logo** | `app/static/img/ibix/cab.png` | `mobile_marketplace/assets/brand/cab.png` (cópia bit-a-bit) |

**Regra CRÍTICA:** O logo NUNCA é recriado no app — sempre copiado da vitrine. O componente `<BrandLogo />` (`components/common/BrandLogo.tsx`) é o ÚNICO lugar onde o logo é renderizado.

---

## Índice de Fases

| Fase | Nome | Descrição | Estimativa |
|------|------|-----------|------------|
| **0** | Preparação do Backend | Adaptar e criar APIs para consumo mobile | 2-3 semanas |
| **1** | Fundação do App | Projeto Expo, navegação, design system, auth, infra | 2-3 semanas |
| **2** | Vitrine e Catálogo | Home, categorias, busca avançada, produto com parcelas | 3-4 semanas |
| **3** | Carrinho e Checkout | Carrinho, cupons, endereços, frete, parcelamento, pagamento | 3-4 semanas |
| **4** | Pós-Venda e Conta | Pedidos, cancelamento, devolução, chat vendedor, avaliações, perfil, LGPD | 3-4 semanas |
| **5** | Notificações e Engajamento | Push, favoritos, deep links, WebSocket real-time, compartilhamento | 2-3 semanas |
| **6** | Performance e Polish | Otimização, acessibilidade, animações, tablet, offline | 2 semanas |
| **7** | Testes e Publicação | QA, ASO, builds, submissão Apple/Google, correções | 2-3 semanas |

**Total estimado:** 19-26 semanas

---

## Fase 0 — Preparação do Backend

**Objetivo:** Garantir que as APIs existentes estejam prontas para consumo mobile nativo e criar os endpoints que faltam, sem quebrar a vitrine web.

### 0.1 Autenticação Mobile

| Tarefa | Detalhes |
|--------|----------|
| **Refresh Token para consumidor** | Hoje `loja_consumidor_token` é JWT via cookie. Para mobile, expor o token no body do login (`POST /api/v1/loja/login`) e criar endpoint `POST /api/v1/loja/refresh-token`. O app envia `Authorization: Bearer {token}`. |
| **Apple Sign-In** | Novo endpoint `POST /api/v1/loja/auth/social/apple` — validar `identityToken` com chave pública Apple (JWKS). Criar/vincular `consumidores_marketplace` com `provider=apple`. Obrigatório para App Store quando há login social. |
| **Token biométrico** | Não é backend — o app armazena o JWT em Secure Storage e usa biometria local para desbloqueio. |

**APIs existentes que já suportam Bearer (sem alteração):**
- `POST /api/v1/loja/login` — retorna token no body ✅
- `POST /api/v1/loja/cadastro` ✅
- `POST /api/v1/loja/auth/social/login` (Google) ✅
- `POST /api/v1/loja/auth/social/config` ✅

### 0.2 Novos Endpoints Necessários

#### Autenticação e Dispositivo

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/v1/loja/refresh-token` | POST | Refresh do JWT do consumidor |
| `/api/v1/loja/auth/social/apple` | POST | Login/cadastro via Apple Sign-In |
| `/api/v1/loja/push-token` | POST | Registrar token FCM/APNS do dispositivo |
| `/api/v1/loja/push-token` | DELETE | Remover token ao logout |
| `/api/v1/loja/app-version` | GET | Retorna versão mínima exigida do app (para force update) |

#### Favoritos

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/v1/loja/favoritos` | GET | Listar favoritos do consumidor (paginado) |
| `/api/v1/loja/favoritos` | POST | Adicionar anúncio aos favoritos |
| `/api/v1/loja/favoritos/{anuncio_id}` | DELETE | Remover favorito |

#### Notificações In-App

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/v1/loja/notificacoes` | GET | Listar notificações do consumidor (paginado, `?lida=false` para badge) |
| `/api/v1/loja/notificacoes/{id}/lida` | PATCH | Marcar como lida |
| `/api/v1/loja/notificacoes/todas-lidas` | PATCH | Marcar todas como lidas |

#### Cupons do Consumidor

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/v1/loja/cupons/validar` | POST | Validar código de cupom. Body: `{ codigo, itens: [...], valor_total }`. Retorna: `{ valido, desconto, tipo_desconto, mensagem }` |
| `/api/v1/loja/cupons/disponiveis` | GET | Listar cupons ativos para o consumidor (públicos ou vinculados ao consumidor) |

#### Endereços (CRUD completo)

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/v1/loja/minha-conta/enderecos` | GET | Listar ✅ (existe) |
| `/api/v1/loja/minha-conta/enderecos` | POST | Criar ✅ (existe) |
| `/api/v1/loja/minha-conta/enderecos/{id}` | PATCH | **NOVO** — Editar endereço |
| `/api/v1/loja/minha-conta/enderecos/{id}` | DELETE | **NOVO** — Excluir endereço |
| `/api/v1/loja/minha-conta/enderecos/{id}/padrao` | PATCH | **NOVO** — Definir como padrão |

#### Cancelamento e Devolução (comprador)

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/v1/loja/pedidos/{id}/cancelar` | POST | Consumidor cancela pedido (permitido apenas antes do envio; backend valida `status_pedido`). Body: `{ motivo }` |
| `/api/v1/loja/pedidos/{id}/devolucao` | POST | Solicitar devolução/reembolso. Body: `{ motivo, tipo: "devolucao" | "reembolso", fotos: [...] }` |
| `/api/v1/loja/pedidos/{id}/devolucao` | GET | Status da solicitação de devolução |
| `/api/v1/loja/motivos-cancelamento` | GET | Lista de motivos padronizados (vem do banco, não hardcoded) |
| `/api/v1/loja/motivos-devolucao` | GET | Lista de motivos de devolução padronizados |

#### Chat / Perguntas ao Vendedor

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/v1/loja/conversas` | GET | Listar conversas do consumidor (paginado) |
| `/api/v1/loja/conversas` | POST | Iniciar conversa com vendedor. Body: `{ loja_id, anuncio_id?, mensagem }` |
| `/api/v1/loja/conversas/{id}/mensagens` | GET | Mensagens da conversa (paginado, cursor-based) |
| `/api/v1/loja/conversas/{id}/mensagens` | POST | Enviar mensagem. Body: `{ texto, imagem_url? }` |
| `/api/v1/loja/conversas/{id}/lida` | PATCH | Marcar conversa como lida |

#### Busca Avançada

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/v1/loja/busca/autocomplete` | GET | Autocomplete de busca. `?q={termo}&limit=8`. Retorna: `{ sugestoes: ["termo1", ...], categorias: [...] }` |
| `/api/v1/loja/busca/populares` | GET | Termos mais buscados (cache 1h) |

#### Parcelamento

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/v1/loja/parcelamento` | GET | Simular parcelas. `?valor={valor}`. Retorna: `{ parcelas: [{ qtd: 3, valor: 33.33, juros: false }, ...] }`. Baseado na config do gateway ativo (MP, PagBank). |

#### WebSocket (Real-Time)

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/ws/loja/consumidor` | WebSocket | Conexão persistente. Auth via query param `?token={jwt}`. Eventos: `pedido.status_atualizado`, `pagamento.confirmado`, `mensagem.nova`, `notificacao.nova`. |

#### LGPD

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/v1/loja/minha-conta/dados-exportar` | GET | Exportar dados pessoais do consumidor (JSON). Prazo legal: 15 dias. |
| `/api/v1/loja/minha-conta/excluir-conta` | POST | Solicitar exclusão de conta. Body: `{ senha, motivo? }`. Marca para exclusão em 30 dias (período de arrependimento). |
| `/api/v1/loja/minha-conta/consentimentos` | GET | Listar consentimentos ativos |
| `/api/v1/loja/minha-conta/consentimentos` | PATCH | Atualizar consentimentos (marketing, analytics, etc.) |

### 0.3 Tabelas Novas (migrations)

| Tabela | Colunas principais | FK | Migration |
|--------|-------------------|-----|-----------|
| `consumidor_push_tokens` | id, consumidor_id, token, plataforma (ios/android), device_id, ativo, criado_em | consumidores_marketplace.id | `mob01_push_tokens` |
| `consumidor_favoritos` | id, consumidor_id, anuncio_id, criado_em | consumidores_marketplace.id, anuncios_plataforma.id | `mob02_favoritos` |
| `consumidor_notificacoes` | id, consumidor_id, tipo, titulo, mensagem, dados_json, lida, criado_em | consumidores_marketplace.id | `mob03_notificacoes` |
| `cupons_marketplace` | id, codigo, tipo_desconto (percentual/fixo), valor_desconto, valor_minimo_pedido, uso_maximo, uso_atual, valido_ate, ativo, loja_id (null=plataforma), criado_por, criado_em | lojas_marketplace.id (nullable) | `mob04_cupons` |
| `cupons_consumidor` | id, cupom_id, consumidor_id, usado_em, pedido_id | cupons_marketplace.id, consumidores_marketplace.id | `mob04_cupons` |
| `devolucoes_marketplace` | id, pedido_id, consumidor_id, motivo_id, descricao, tipo (devolucao/reembolso), status (aberta/em_analise/aprovada/recusada/finalizada), fotos_json, valor_reembolso, resposta_loja, criado_em, atualizado_em | pedidos_marketplace.id | `mob05_devolucoes` |
| `motivos_cancelamento` | id, descricao, tipo (cancelamento/devolucao), ativo, ordem | — | `mob05_devolucoes` |
| `conversas_marketplace` | id, consumidor_id, loja_id, anuncio_id (nullable), status (ativa/arquivada), ultima_mensagem_em, criado_em | consumidores_marketplace.id, lojas_marketplace.id | `mob06_chat` |
| `mensagens_conversa` | id, conversa_id, remetente_tipo (consumidor/loja), remetente_id, texto, imagem_url, lida, criado_em | conversas_marketplace.id | `mob06_chat` |
| `consumidor_consentimentos` | id, consumidor_id, tipo (marketing/analytics/terceiros), aceito, ip, criado_em, atualizado_em | consumidores_marketplace.id | `mob07_lgpd` |
| `app_versao_config` | id, plataforma (ios/android), versao_minima, versao_recomendada, url_loja, mensagem, atualizado_em | — | `mob08_versao` |
| `termos_buscados` | id, termo, contagem, atualizado_em | — | `mob09_busca` |

### 0.4 Ajustes em APIs Existentes

| API | Ajuste |
|-----|--------|
| `GET /api/v1/loja/anuncios` | Adicionar paginação cursor-based (`after_id` + `limit`) como alternativa a `skip/limit` para infinite scroll. Incluir campo `parcela_sem_juros` (ex.: `"3x R$ 33,33"`) calculado a partir da config do gateway. |
| `GET /api/v1/loja/anuncios/{id}` | Incluir array `parcelas` no response (simulação completa: 1x a 12x com/sem juros). Incluir `favorito: true/false` se consumidor logado. |
| `GET /api/v1/marketing-vitrine/vitrine-home` | Adicionar campo `imagem_url_mobile` nos cards (resolução otimizada) |
| `POST /api/v1/loja/checkout` | Aceitar `cupom_codigo` no body. Aceitar `parcelas` no body (qtd de parcelas). Garantir que `back_urls` aceite deep links (`ibixmarket://`) quando `origin=mobile`. Retornar `parcelas_info` na resposta. |
| `POST /api/v1/loja/checkout-unificado` | Idem acima |
| `GET /api/v1/loja/meus-pedidos` | Adicionar paginação cursor. Incluir campo `pode_cancelar` (boolean) e `pode_devolver` (boolean) por pedido. |
| `GET /api/v1/loja/pedido/consultar` | Incluir timeline de eventos, dados de devolução (se houver), dados de entrega (logística local). |
| Respostas de erro | Padronizar formato `{ "detail": "...", "code": "ERRO_CODE" }` com códigos enumerados para tratamento no app |

### 0.5 Infraestrutura

| Item | Ação |
|------|------|
| **Firebase Cloud Messaging** | Configurar projeto Firebase. Variáveis: `FIREBASE_CREDENTIALS_JSON` (service account) no `.env` |
| **Firebase Analytics** | Mesmo projeto Firebase. SDK no app; backend registra eventos server-side quando necessário. |
| **Apple Push Notification** | Configurar certificado APNS no Firebase (automatic via FCM) |
| **Deep Links** | Configurar `assetlinks.json` (Android) e `apple-app-site-association` (iOS) como rotas no FastAPI ou arquivos estáticos no Nginx |
| **CDN de imagens** | Endpoint ou middleware para servir thumbnails otimizados (WebP, múltiplas resoluções: 150px, 300px, 600px, original) |
| **WebSocket** | Endpoint `/ws/loja/consumidor` usando Starlette WebSocket nativo do FastAPI. Auth via JWT no query param. Redis pub/sub para broadcast entre workers. |
| **Sentry DSN** | Conta Sentry (gratuito até 5k eventos/mês). Variável `SENTRY_DSN_MOBILE` no `.env` para o app. |

---

## Fase 1 — Fundação do App

**Objetivo:** Criar o projeto Expo, sistema de navegação, design system profissional, fluxo de autenticação completo e infraestrutura de monitoramento.

### 1.1 Setup do Projeto

```
mobile_marketplace/
├── app/                          # Expo Router (file-based routing)
│   ├── (tabs)/                   # Tab Navigator principal
│   │   ├── index.tsx             # Home
│   │   ├── categorias.tsx        # Explorar categorias
│   │   ├── carrinho.tsx          # Carrinho
│   │   ├── pedidos.tsx           # Meus Pedidos
│   │   └── conta.tsx             # Minha Conta
│   ├── (auth)/                   # Stack de autenticação
│   │   ├── onboarding.tsx
│   │   ├── login.tsx
│   │   ├── cadastro.tsx
│   │   ├── esqueci-senha.tsx
│   │   └── completar-cadastro.tsx
│   ├── produto/[id].tsx          # Detalhe do produto
│   ├── categoria/[id].tsx        # Listagem por categoria
│   ├── loja/[slug].tsx           # Página da loja
│   ├── busca.tsx                 # Busca com autocomplete
│   ├── checkout/                 # Fluxo de checkout
│   │   ├── endereco.tsx
│   │   ├── frete.tsx
│   │   ├── pagamento.tsx
│   │   └── confirmacao.tsx
│   ├── pedido/[id].tsx           # Detalhe do pedido
│   ├── pedido/[id]/cancelar.tsx  # Cancelamento
│   ├── pedido/[id]/devolver.tsx  # Devolução
│   ├── pedido/[id]/avaliar.tsx   # Avaliação
│   ├── chat/index.tsx            # Lista de conversas
│   ├── chat/[id].tsx             # Conversa
│   ├── favoritos.tsx             # Lista de favoritos
│   ├── notificacoes.tsx          # Central de notificações
│   ├── conta/                    # Subpáginas de conta
│   │   ├── dados-pessoais.tsx
│   │   ├── enderecos.tsx
│   │   ├── privacidade.tsx       # LGPD / consentimentos
│   │   └── ajuda.tsx
│   └── _layout.tsx               # Layout raiz
├── components/                   # Componentes reutilizáveis
│   ├── ui/                       # Design system (30+ componentes)
│   │   ├── Button.tsx
│   │   ├── Card.tsx
│   │   ├── Input.tsx
│   │   ├── Badge.tsx
│   │   ├── Chip.tsx
│   │   ├── Divider.tsx
│   │   ├── Skeleton.tsx
│   │   ├── BottomSheet.tsx
│   │   ├── Toast.tsx
│   │   ├── EmptyState.tsx
│   │   ├── ErrorBoundary.tsx
│   │   ├── ForceUpdateModal.tsx
│   │   ├── NetworkBanner.tsx
│   │   └── ...
│   ├── product/                  # Componentes de produto
│   │   ├── ProductCard.tsx       # Card com parcela e favorito
│   │   ├── ProductGrid.tsx
│   │   ├── ProductGallery.tsx
│   │   ├── PriceDisplay.tsx      # Preço + parcelas
│   │   ├── InstallmentBadge.tsx  # "12x R$ 8,25"
│   │   └── RatingStars.tsx
│   ├── cart/
│   │   ├── CartItem.tsx
│   │   ├── CartSummary.tsx
│   │   ├── CouponInput.tsx       # Campo de cupom
│   │   └── QuantityStepper.tsx
│   ├── checkout/
│   │   ├── AddressCard.tsx
│   │   ├── ShippingOption.tsx
│   │   ├── PaymentMethodPicker.tsx
│   │   ├── InstallmentPicker.tsx # Seletor de parcelas
│   │   ├── PixPayment.tsx        # QR code + copy paste + timer
│   │   └── OrderSummary.tsx
│   ├── order/
│   │   ├── OrderCard.tsx
│   │   ├── OrderTimeline.tsx
│   │   ├── CancelModal.tsx
│   │   └── ReturnFlow.tsx
│   ├── chat/
│   │   ├── ChatBubble.tsx
│   │   ├── ChatInput.tsx
│   │   └── ConversationCard.tsx
│   ├── geo/                       # Componentes de geolocalização
│   │   ├── LocationChip.tsx       # Chip cidade/UF (header)
│   │   ├── CitySelectorSheet.tsx  # BottomSheet (GPS + lista de cidades)
│   │   └── NearbyAdsCarousel.tsx  # Carrossel "Perto de você"
│   └── common/
│       ├── Header.tsx
│       ├── SearchBar.tsx
│       ├── TabBar.tsx
│       └── ConsentBanner.tsx     # LGPD
├── hooks/
│   ├── useAuth.ts
│   ├── useCart.ts
│   ├── useApi.ts
│   ├── useWebSocket.ts          # WebSocket hook
│   ├── useForceUpdate.ts        # Verificação de versão
│   ├── useRecentlyViewed.ts     # Produtos vistos
│   ├── useDebounce.ts           # Para autocomplete
│   └── useNetworkStatus.ts
├── services/
│   ├── api.ts                    # Cliente HTTP com interceptors (retry, 401, certificate pinning)
│   ├── auth.service.ts
│   ├── catalog.service.ts
│   ├── cart.service.ts
│   ├── checkout.service.ts
│   ├── order.service.ts
│   ├── notification.service.ts
│   ├── chat.service.ts
│   ├── coupon.service.ts
│   ├── return.service.ts         # Devoluções
│   ├── geo.service.ts            # Cidades, cidade-próxima, perto-de-voce, proximos
│   ├── websocket.service.ts      # WebSocket client
│   └── analytics.service.ts      # Wrapper Firebase Analytics
├── store/                        # Estado global (Zustand)
│   ├── auth.store.ts
│   ├── cart.store.ts
│   ├── notification.store.ts
│   ├── chat.store.ts
│   ├── recentlyViewed.store.ts
│   └── geo.store.ts              # lat/lng/cidade/uf persistido em MMKV
├── theme/
│   ├── colors.ts
│   ├── typography.ts
│   ├── spacing.ts
│   ├── shadows.ts
│   ├── breakpoints.ts            # Responsive: phone vs tablet
│   └── index.ts
├── utils/
│   ├── format.ts                 # Moeda, data, CEP, parcelas
│   ├── storage.ts                # SecureStore wrapper
│   ├── validators.ts
│   ├── analytics.ts              # Track events
│   └── sentry.ts                 # Crash reporting setup
├── constants/
│   ├── api.ts                    # Base URL, timeouts
│   ├── events.ts                 # Nomes de eventos analytics
│   └── errors.ts                 # Códigos de erro mapeados
├── assets/
│   ├── fonts/
│   ├── images/
│   ├── icons/
│   └── animations/               # Lottie files
├── app.json
├── eas.json
├── package.json
└── tsconfig.json
```

### 1.2 Dependências Principais

| Pacote | Uso |
|--------|-----|
| `expo` ~52 | Framework base |
| `expo-router` | Navegação file-based |
| `expo-secure-store` | Armazenamento seguro de tokens |
| `expo-image` | Carregamento otimizado de imagens |
| `expo-notifications` | Push notifications |
| `expo-local-authentication` | Biometria |
| `expo-linking` | Deep links |
| `expo-haptics` | Feedback tátil |
| `expo-clipboard` | Copiar código PIX |
| `expo-sharing` | Compartilhar produtos |
| `expo-location` | Geolocalização (faixa "Perto de você", busca por proximidade) |
| `expo-updates` | OTA updates |
| `react-native-reanimated` | Animações fluidas |
| `react-native-gesture-handler` | Gestos nativos |
| `@shopify/flash-list` | Lista de alto desempenho |
| `zustand` | Estado global leve |
| `@tanstack/react-query` | Cache e sync de dados da API |
| `axios` | Cliente HTTP |
| `react-native-mmkv` | Storage local rápido |
| `lottie-react-native` | Animações (splash, loading, sucesso) |
| `react-native-svg` | Ícones SVG |
| `react-native-qrcode-svg` | Gerar QR code PIX |
| `@sentry/react-native` | Crash reporting e performance monitoring |
| `@react-native-firebase/analytics` | Analytics |
| `@react-native-firebase/messaging` | Push (nativo) |
| `react-native-ssl-pinning` | Certificate pinning |

### 1.3 Design System

**Identidade visual = paridade total com a vitrine web.** Fonte canônica: `app/static/css/loja.css` (tokens `--ibix-*`).

**Paleta (light)** — espelhada de `loja.css:9-18`:

| Token | Hex | Uso |
|-------|-----|-----|
| `primary` (action) | `#5C6E4A` | CTA primário (verde-musgo) |
| `primaryDark` | `#4E5F40` | Pressed state |
| `accent` (terracota) | `#C47A44` | Hover, destaque, focus-ring |
| `premium` | `#D9B48B` | Detalhes mínimos (dourado suave) |
| `background` | `#FEF7F1` | Fundo da página (off-white) |
| `surface` | `#FFFFFF` | Cards, sheets, inputs |
| `surfaceVariant` | `#F5EDE3` | Faixas alternadas |
| `textPrimary` | `#2F3A44` | Headings (azul-ardósia escuro) |
| `textSecondary` | `#4A627A` | Texto base |
| `textSoft` | `#3B5166` | Variante intermediária |
| `border` | `rgba(47,58,68,0.14)` | Bordas sutis |
| `divider` | `rgba(47,58,68,0.08)` | Divisores horizontais |
| `success` | `#5C6E4A` | Confirmações |
| `warning` | `#C47A44` | Alertas, "Pendente" |
| `error` | `#B5453A` | Erros, "Cancelar" |
| `focusRing` | `#C47A44` | Outline accessível (paridade `loja-header *:focus-visible`) |

**Dark mode:** `colors.ts` exporta `darkColors` com tokens equivalentes (texto claro, surface escura, primary mais luminoso). Estrutura pronta — lançamento do dark fica para fase futura.

**Tipografia:** **Poppins** — paridade com vitrine (`loja.css:1394`). Carregada via `@expo-google-fonts/poppins`.

| Estilo | Tamanho | Peso | Uso |
|--------|---------|------|-----|
| `h1` | 36px | Bold (700) | Onboarding |
| `h2` | 30px | Bold (700) | Headers de fluxo (checkout, login) |
| `h3` | 24px | Bold (700) | Títulos de tela |
| `h4` | 20px | SemiBold (600) | Seções, modais |
| `subtitle1` | 17px | SemiBold (600) | Nome do produto, item de menu |
| `subtitle2` | 15px | Medium (500) | Subtítulos |
| `body1` | 15px | Regular (400) | Texto corrido |
| `body2` | 13px | Regular (400) | Descrições, captions |
| `button` | 15px | SemiBold (600) | Botões |
| `caption` | 11px | Regular (400) | Microtexto |
| `overline` | 11px | Medium UPPERCASE | Etiquetas |
| `price` | 20px | Bold (700) | Preço grande no PDP |
| `priceSmall` | 15px | SemiBold (600) | Preço em listagens |
| `priceStrike` | 13px | Regular line-through | Preço cheio riscado |

**Border radius (paridade vitrine):**
- `radius.sm` = 8 → botões e chips (`btn-primary`, `loja.css:79`)
- `radius.md` = 10 → inputs e search bar (`loja-search-form`, `loja.css:137`)
- `radius.lg` = 14 → cards e blocos de seção (`loja-section-block`, `loja.css:175`)
- `radius.xl` = 18 → bottom sheets

**Sombras (paridade vitrine):**
- `shadow('sm')` → cards de produto (`--loja-shadow-sm`)
- `shadow('md')` → blocos de seção (`--loja-shadow-block`)
- `shadow('lg')` → hero (`--loja-shadow-hero`)

**Focus-ring acessível (paridade `loja.css:111-113`):**
```
outline: 2px solid #C47A44; outline-offset: 2px
```
Aplicado em botões/inputs com `accessibilityState.focused` via `colors.focusRing` + `focusRing.width/offset`.

**Brand assets (logo Ibix Market):**
- `mobile_marketplace/assets/brand/cab.png` — cópia bit-a-bit de `app/static/img/ibix/cab.png` (header).
- `mobile_marketplace/assets/brand/rodape.png` — variante para fundos escuros.
- `mobile_marketplace/assets/brand/logoSfundo.png` — logo institucional (fonte do `icon.png` 1024×1024).
- Renderização via `<BrandLogo height={36} />` (`components/common/BrandLogo.tsx`) — único ponto onde o logo aparece no app.

**Componentes do design system (30+):**
- **Buttons:** Primary, Secondary, Outline, Ghost, Icon, FAB — com estados loading, disabled, pressed
- **Cards:** ProductCard (com parcela e coração), CategoryCard, BannerCard, OrderCard, AddressCard, ConversationCard
- **Inputs:** Text, Search (com autocomplete), Select, QuantityStepper, CouponInput, PinInput (código)
- **Feedback:** Toast, BottomSheet, Modal, Skeleton loaders, EmptyState (ilustração + CTA), ErrorBoundary
- **Navigation:** TabBar customizado (com badge), Header (variantes: busca, voltar, título), SegmentedControl (filtros)
- **Data Display:** PriceDisplay (preço + parcela), RatingStars, Badge, Chip, Timeline, ProgressBar
- **Overlays:** ForceUpdateModal, ConsentBanner (LGPD), NetworkBanner (offline)

**Layout responsivo (phone vs tablet):**

| Breakpoint | Colunas grid | Card width | Aplicação |
|-----------|-------------|-----------|-----------|
| < 600px (phone) | 2 | ~50% | Padrão |
| ≥ 600px (tablet portrait) | 3 | ~33% | iPad, tablets Android |
| ≥ 900px (tablet landscape) | 4 | ~25% | Landscape |

### 1.4 Autenticação (telas e fluxo)

| Tela | Funcionalidade | API |
|------|---------------|-----|
| **Onboarding** | 3 slides com benefícios + animações Lottie, botão "Começar", "Já tenho conta" | — |
| **Login** | Email + senha, "Esqueci senha", social login (Google + Apple) | `POST /loja/login` |
| **Login Social** | Google Sign-In + Apple Sign-In (obrigatório iOS) | `POST /loja/auth/social/login`, `POST /loja/auth/social/apple` |
| **Cadastro** | Nome, email, telefone, senha (validação em tempo real), termos + checkbox LGPD | `POST /loja/cadastro` |
| **Esqueci Senha** | Email → token → nova senha (2 telas) | `POST /loja/forgot-password`, `POST /loja/redefinir-senha` |
| **Completar Cadastro** | Dados adicionais pós-social | `POST /loja/completar-cadastro` |

**Fluxo de token:**
1. Login → recebe JWT (`loja_consumidor_token`) + `refresh_token`
2. Armazena access token em `expo-secure-store`, refresh em SecureStore separado
3. Todas as requests enviam `Authorization: Bearer {access_token}`
4. Access token expirando (interceptor 401) → `POST /loja/refresh-token` com refresh token
5. Refresh falhou → limpa tudo → redireciona para login
6. Logout → `POST /loja/logout` + `DELETE /loja/push-token` + limpa SecureStore

**LGPD no cadastro:**
- Checkbox obrigatório: "Li e aceito os Termos de Uso e Política de Privacidade"
- Checkbox opcional: "Aceito receber comunicações de marketing"
- Registrar consentimentos via `PATCH /loja/minha-conta/consentimentos`

### 1.5 Infraestrutura de Monitoramento

| Ferramenta | Setup | Eventos críticos rastreados |
|-----------|-------|----------------------------|
| **Sentry** | `Sentry.init()` no `_layout.tsx` com `dsn`, `tracesSampleRate: 0.2` | Crashes, erros de API, exceções não tratadas, performance de navegação |
| **Firebase Analytics** | `analytics().logEvent()` wrapper em `analytics.service.ts` | `view_item`, `add_to_cart`, `begin_checkout`, `purchase`, `search`, `sign_up`, `login`, `share` |
| **Custom events** | Via analytics wrapper | `coupon_applied`, `favorite_toggle`, `chat_started`, `return_requested`, `payment_method_selected` |

### 1.6 Force Update

| Componente | Detalhes |
|-----------|----------|
| **Backend** | `GET /api/v1/loja/app-version` retorna `{ ios: { min: "1.0.0", recommended: "1.2.0" }, android: { min: "1.0.0", recommended: "1.2.0" } }` |
| **App** | Hook `useForceUpdate()` checa na abertura e a cada volta do background. Compara com `expo-constants.expoConfig.version`. |
| **Modal bloqueante** | Se versão < `min` → modal sem dismiss com botão "Atualizar" (abre a loja). |
| **Modal sugestivo** | Se versão < `recommended` → modal com "Atualizar" e "Depois". Máximo 1x por sessão. |

### 1.7 Certificate Pinning

| Item | Detalhes |
|------|----------|
| **Produção** | Pinnar certificado do servidor API (SHA-256 do public key). Usar `react-native-ssl-pinning` ou `TrustKit` (iOS). |
| **Dev/Staging** | Desabilitar pinning para facilitar debug com proxy (Charles/mitmproxy). |
| **Rotação** | Incluir pin do certificado atual + próximo (backup pin) para evitar lock-out durante renovação. |

### 1.8 Navegação

```
App
├── ForceUpdateCheck               # Wrapper: verifica versão antes de tudo
├── ConsentCheck                    # Wrapper: LGPD consent banner se necessário
│
├── (auth)                          # Stack — sem tab bar
│   ├── onboarding
│   ├── login
│   ├── cadastro
│   ├── esqueci-senha
│   └── completar-cadastro
│
├── (tabs)                          # Tab Navigator — 5 abas
│   ├── Home         🏠             # Vitrine principal
│   ├── Categorias   📂             # Explorar categorias
│   ├── Carrinho     🛒 (badge)    # Carrinho de compras
│   ├── Pedidos      📦             # Meus pedidos
│   └── Conta        👤 (dot)      # Perfil e configurações
│
├── produto/[id]                    # Stack push sobre tabs
├── categoria/[id]
├── loja/[slug]
├── busca                           # Com autocomplete
├── favoritos
├── notificacoes
├── chat/                           # Lista + conversa
│   ├── index
│   └── [id]
├── checkout/                       # Stack sem tabs
│   ├── endereco
│   ├── frete
│   ├── pagamento                   # Parcelas + cupom
│   └── confirmacao
├── pedido/[id]                     # Detalhe com timeline
├── pedido/[id]/cancelar
├── pedido/[id]/devolver
├── pedido/[id]/avaliar
└── conta/
    ├── dados-pessoais
    ├── enderecos
    ├── privacidade                  # LGPD
    └── ajuda
```

**Regras de navegação:**
- Usuário não logado pode navegar vitrine, buscar, ver produtos, adicionar ao carrinho
- Ao tentar: comprar / favoritar / avaliar / chatear / ver pedidos → redireciona para login com `returnTo`
- Após login → retorna ao ponto anterior
- Tab "Pedidos" e "Conta" requerem login (exibem tela "Faça login" se não autenticado)

---

## Fase 2 — Vitrine e Catálogo

**Objetivo:** Implementar a experiência de descoberta de produtos comparável a grandes marketplaces, incluindo parcelamento e busca inteligente.

### 2.1 Home (Tab Principal)

| Seção | Dados | API |
|-------|-------|-----|
| **Header fixo** | Logo, barra de busca (tap → tela de busca), ícone sino (notificações com badge), ícone chat (com badge) | — |
| **Localização ativa** | Chip de cidade/UF abaixo do header. Tap abre `CitySelectorSheet` (lista de cidades com loja ativa + botão "Usar GPS"). Estado persistido em MMKV (`ibix_geo_location`). | `GET /loja/geo/cidades`, `GET /loja/geo/reverso`, `GET /loja/geo/cidade-proxima` |
| **Banners rotativos** | Auto-play 5s, indicadores, tap → deep link. Configurados pelo Superadmin. | `GET /marketing-vitrine/vitrine-home` → `tipo_bloco: cabecalho_ofertas` |
| **Categorias em destaque** | Ícones circulares, scroll horizontal, "Ver todas" | `GET /loja/categorias` |
| **Perto de você** | Carrossel horizontal de anúncios das lojas mais próximas, com badge de distância (km) e tempo (min) por rota real, cidade/UF e nome da loja. CTA quando ainda sem localização. | `GET /loja/anuncios/perto-de-voce?lat&lng&limit=12` |
| **Destaques** | Cards de produtos com preço + parcela + coração | `GET /marketing-vitrine/vitrine-home` → `tipo_bloco: destaques` |
| **Ofertas da semana** | Grid com badge "X% OFF", timer se houver validade | `GET /marketing-vitrine/vitrine-home` → `tipo_bloco: oferta_semana` |
| **Vistos recentemente** | Carrossel horizontal (últimos 20 produtos, local) | Store `recentlyViewed` (MMKV) |
| **Produtos recentes** | Infinite scroll de anúncios com parcela | `GET /loja/anuncios?sort=recentes` (cursor-based) |
| **Bloco de confiança** | 4 cards: Compra segura, Entrega rápida, Devolução fácil, Acompanhe pedidos | Estático (alinhado ao padrão web: ícones Feather, cores suaves) |

**Comportamento:**
- Pull-to-refresh recarrega todos os blocos (incluindo "Perto de você")
- Cache com `react-query` (staleTime: 5min para marketing, 1min para anúncios e geo)
- Skeleton loaders em todos os pontos de carregamento
- Lazy loading de imagens com placeholder blur (BlurHash)
- Tablet: 3-4 colunas no grid em vez de 2

**Geolocalização (paridade com vitrine web):**
- Permissões via `expo-location` (`NSLocationWhenInUseUsageDescription` no iOS, `ACCESS_FINE_LOCATION` no Android)
- `useGeo()` (hook em `hooks/useGeo.ts`) encapsula `requestForegroundPermissionsAsync` + `getCurrentPositionAsync`
- Resolve cidade/UF via `GET /loja/geo/reverso` (Nominatim) com fallback `GET /loja/geo/cidade-proxima`
- Estado global em `useGeoStore` (Zustand) persistido em MMKV (`ibix_geo_location`); chave `STORAGE_KEYS.GEO_LOCATION`
- Sem localização → exibe card CTA "Compre perto de você" com botão para abrir o seletor

### 2.2 Categorias

| Tela | Funcionalidade | API |
|------|---------------|-----|
| **Grid de Categorias** | Todas as categorias ativas com imagem/ícone, layout grid responsivo | `GET /loja/categorias` |
| **Listagem por Categoria** | Produtos filtrados, barra de filtros sticky no topo | `GET /loja/anuncios?categoria_ids={id}` |

**Filtros disponíveis (BottomSheet):**
- Ordenar: Relevância, Menor preço, Maior preço, Mais recentes, Mais vendidos
- Faixa de preço: slider duplo (min/max)
- Só promoções: toggle (`somente_promocao=true`)
- Frete grátis: toggle
- Avaliação mínima: seletor de estrelas
- Loja específica: select
- Botão "Limpar filtros" + "Aplicar" (X resultados)

### 2.3 Busca Avançada

| Componente | Funcionalidade | API |
|------------|---------------|-----|
| **Barra de busca** | Autofocus ao entrar, ícone "X" para limpar, ícone microfone (futuro) | — |
| **Autocomplete** | Debounce 300ms, dropdown com sugestões de texto e categorias | `GET /loja/busca/autocomplete?q={termo}` |
| **Termos populares** | Chips clicáveis quando barra vazia | `GET /loja/busca/populares` |
| **Histórico** | Últimas 15 buscas (MMKV local), ícone "X" para remover, "Limpar histórico" | Local |
| **Localização ativa** | `LocationChip` no header de resultados; tap abre `CitySelectorSheet`. | mesmas APIs `loja/geo/*` |
| **Mais perto de você que vendem isso** | Carrossel horizontal logo acima do grid quando há localização e termo (>=2 chars). Mostra distância de rota + cidade da loja. | `GET /loja/anuncios/proximos?q&lat&lng&limit=10` |
| **Resultados** | Grid de produtos com filtros (mesmo componente da categoria) | `GET /loja/anuncios?q={termo}` |
| **Sem resultados** | Ilustração Lottie + "Nenhum resultado para '{termo}'" + sugestões | — |

**Analytics:** Registrar `search` event com termo e quantidade de resultados.

### 2.4 Página do Produto

| Seção | Dados | API |
|-------|-------|-----|
| **Galeria** | Swipe horizontal com zoom (pinch-to-zoom), indicador de posição, fullscreen ao tap | `anuncio.imagens[]` |
| **Preço** | Preço cheio (riscado), preço promocional em destaque, badge "X% OFF" | `anuncio.preco`, `preco_promocional` |
| **Parcelas** | "em até **12x de R$ 8,25** sem juros" ou "em até **10x de R$ 10,50** (com juros)" em destaque abaixo do preço | `anuncio.parcelas[]` do response ou `GET /loja/parcelamento?valor={preco}` |
| **Tabela de parcelas** | BottomSheet com todas as opções (1x a 12x), valor da parcela, total, com/sem juros | `GET /loja/parcelamento?valor={preco}` |
| **Título** | Até 3 linhas, expansível | `anuncio.titulo` |
| **Descrição** | Expansível com "ver mais" (trunca em 4 linhas) | `anuncio.descricao` |
| **Variações** | Seletor visual (cor, tamanho) se houver | `anuncio.variacoes` |
| **Loja** | Card: logo, nome, avaliação, cidade, "Ver loja" | `anuncio.loja` |
| **Perguntar ao vendedor** | Botão "Perguntar" → abre chat com loja pré-vinculado ao anúncio | `POST /loja/conversas` com `anuncio_id` |
| **Frete** | Input CEP + "Calcular", resultado: prazo + valor, badge "Frete grátis" quando aplicável | `GET /loja/{loja_id}/frete?cep={cep}` |
| **Avaliações** | Nota média (estrelas), distribuição (barra por estrela), lista paginada com fotos | `GET /loja/anuncios/{id}/avaliacoes` |
| **Similares** | Carrossel horizontal | `GET /loja/anuncios/{id}/semelhantes` |
| **Ações** | Botão coração (favoritar), botão compartilhar | `POST /loja/favoritos` |

**Sticky bottom bar:** "Adicionar ao carrinho" (outline) + "Comprar agora" (primary, filled) — sempre visível. Ao adicionar, animação do item voando para a tab carrinho + badge bounce.

**Analytics:** `view_item` com `item_id`, `item_name`, `price`, `item_category`.

### 2.5 Página da Loja

| Seção | Dados | API |
|-------|-------|-----|
| **Header parallax** | Banner + logo + nome + avaliação média + qtd avaliações + cidade | Dados da loja |
| **Métricas** | "Vendas no mês", "Tempo médio de envio", "% aprovação" | Dados da loja (quando disponíveis) |
| **Categorias da loja** | Chips filtráveis | Derivado dos anúncios |
| **Produtos** | Grid com infinite scroll, filtros | `GET /loja/anuncios?loja_slug={slug}` |
| **Info** | BottomSheet: descrição, políticas, horário, contato | Dados da loja |
| **Ação** | "Conversar com vendedor" | `POST /loja/conversas` com `loja_id` |

---

## Fase 3 — Carrinho e Checkout

**Objetivo:** Fluxo de compra fluido, seguro, com cupons, parcelamento e múltiplas formas de pagamento.

### 3.1 Carrinho

| Funcionalidade | Detalhes |
|----------------|----------|
| **Persistência** | Zustand + MMKV (por consumidor logado: `cart_{consumidor_id}`, ou anônimo: `cart_anon`) |
| **Estrutura do item** | `{ anuncio_id, loja_id, quantidade, preco_unitario, preco_promocional, titulo, imagem_url, loja_nome, estoque_disponivel }` |
| **Agrupamento** | Itens agrupados por loja (seções com header da loja, como Mercado Livre) |
| **Ações por item** | QuantityStepper (+/-), Remover (swipe left ou ícone lixeira), Mover para favoritos |
| **Preços** | Subtotal por loja, frete estimado por loja (se CEP salvo), desconto de cupom, total geral |
| **Cupom** | Input "Inserir cupom" com botão "Aplicar" → validação via API → desconto exibido no resumo | `POST /loja/cupons/validar` |
| **Cupons disponíveis** | Link "Ver cupons disponíveis" → BottomSheet com lista | `GET /loja/cupons/disponiveis` |
| **Badge** | Quantidade total de itens no ícone da tab (atualiza em tempo real) |
| **Carrinho vazio** | EmptyState com ilustração + "Explore produtos" CTA |
| **Migração** | Ao fazer login, mesclar carrinho anônimo com carrinho do consumidor (maior quantidade prevalece) |
| **Validação** | Antes de ir para checkout: verificar estoque, preço atualizado, anúncio ativo. Se algo mudou → alerta + ajustar. |

### 3.2 Checkout — Endereço

| Funcionalidade | API |
|----------------|-----|
| **Listar endereços** | `GET /loja/minha-conta/enderecos` |
| **Endereço padrão** pré-selecionado | Campo `padrao=true` |
| **Adicionar endereço** | Inline: CEP → busca ViaCEP → preenche campos → salvar | `POST /loja/minha-conta/enderecos` |
| **Editar endereço** | BottomSheet com form preenchido | `PATCH /loja/minha-conta/enderecos/{id}` |
| **Excluir endereço** | Confirmação + delete | `DELETE /loja/minha-conta/enderecos/{id}` |
| **Definir padrão** | Toggle | `PATCH /loja/minha-conta/enderecos/{id}/padrao` |

### 3.3 Checkout — Frete

| Funcionalidade | API |
|----------------|-----|
| **Cálculo por loja** | Automático ao selecionar endereço | `GET /loja/{loja_id}/frete?cep={cep}` |
| **Opções** | Entrega padrão (prazo + valor), entrega expressa (se disponível), retirada na loja (se disponível) |
| **Prazo** | "Chega entre {data_min} e {data_max}" |
| **Frete grátis** | Badge verde quando `valor_pedido >= entrega_gratis_apos` da loja |
| **Múltiplas lojas** | Frete calculado e exibido separadamente por loja |

### 3.4 Checkout — Pagamento e Parcelas

| Funcionalidade | Detalhes |
|----------------|----------|
| **Métodos disponíveis** | PIX, Cartão de crédito (com parcelas), Boleto — conforme gateway ativo da loja ou da plataforma |
| **Seleção** | Cards clicáveis com ícone do método. Destaque: "PIX: 5% de desconto" (se configurado) |

#### PIX
| Item | Detalhes |
|------|----------|
| QR Code | Renderizado com `react-native-qrcode-svg` |
| Código copia-e-cola | Botão "Copiar código" com `expo-clipboard` + toast "Copiado!" |
| Timer | Contagem regressiva da expiração (ex.: 30 min) |
| Polling | A cada 5s consulta status. Quando `pago` → tela de sucesso |

#### Cartão de crédito
| Item | Detalhes |
|------|----------|
| Parcelas | Seletor: "1x de R$ 100,00 (sem juros)" até "12x de R$ 9,50 (com juros - total R$ 114,00)". Dados de `GET /loja/parcelamento?valor={valor}` |
| Gateway | Redirect para Checkout Pro MP (browser externo via `expo-linking`) ou WebView in-app |
| Deep links | `back_urls.success` = `ibixmarket://pagamento/sucesso`, `failure` = `ibixmarket://pagamento/falha`, `pending` = `ibixmarket://pagamento/pendente` |

#### Boleto
| Item | Detalhes |
|------|----------|
| Código | Exibir linha digitável + botão "Copiar" |
| PDF | Botão "Abrir boleto" → abre no browser |
| Prazo | "Seu boleto vence em {data}. O pedido será confirmado após a compensação (1-3 dias úteis)." |

**Fluxo completo:**
1. App monta resumo: itens + endereço + frete + cupom (se houver) + método + parcelas
2. App envia `POST /loja/checkout` (loja única) ou `POST /loja/checkout-unificado` (multi-loja)
3. Body: `{ endereco_id, itens: [...], metodo_pagamento, parcelas, cupom_codigo, observacao, origin: "mobile" }`
4. Backend: valida estoque → valida cupom → cria pedido(s) → calcula parcelas → cria preferência MP → retorna
5. Resposta:
   - `checkout_type: "redirect"` → abrir `redirect_url` no browser
   - `checkout_type: "pix"` → exibir QR code + código no app
   - `checkout_type: "boleto"` → exibir linha digitável
6. Confirmação real via webhook (backend atualiza `status_pagamento`) e WebSocket push para o app
7. App recebe evento `pagamento.confirmado` via WebSocket → navega para tela de sucesso

**Regra CRÍTICA (validade jurídica — MAPA_DE_REGRAS § 0.10):** App NÃO exibe "Compra finalizada" até `status_pagamento = "pago"`. Se retorno de gateway for ambíguo, exibir "Aguardando confirmação de pagamento" com animação de loading. Polling como fallback se WebSocket desconectar.

### 3.5 Checkout — Confirmação

| Estado | Tela |
|--------|------|
| **Pagamento aprovado** | Animação Lottie confetti + "Pedido realizado com sucesso!" + número do pedido + resumo + "Ver meus pedidos" + "Continuar comprando" |
| **Aguardando pagamento (cartão)** | Spinner + "Seu pagamento está sendo processado..." + polling/WebSocket |
| **PIX pendente** | QR code grande + código + timer + "Copiar código" + polling + "Assim que o pagamento for confirmado, você receberá uma notificação" |
| **Boleto pendente** | Linha digitável + "Copiar" + "Abrir boleto" + "Prazo: {data}" + "Você receberá uma notificação quando o pagamento for compensado" |
| **Pagamento recusado** | Ícone de erro + mensagem específica (cartão recusado, saldo insuficiente, etc.) + "Tentar com outro método" / "Tentar novamente" |

**Analytics:** `purchase` event com `transaction_id`, `value`, `items`, `payment_method`, `coupon`.

---

## Fase 4 — Pós-Venda e Conta

**Objetivo:** Acompanhamento completo de pedidos, cancelamento, devolução, chat com vendedor, avaliações e gestão de conta com LGPD.

### 4.1 Meus Pedidos

| Funcionalidade | API |
|----------------|-----|
| **Listagem** | Cards: thumb, título do primeiro item, "+X itens", status (badge colorido), data, valor total | `GET /loja/meus-pedidos` (cursor-based) |
| **Filtros** | SegmentedControl: Todos \| Em andamento \| Entregues \| Cancelados | Query param `status_grupo` |
| **Detalhe** | Tela completa: timeline, itens, endereço, pagamento, ações | `GET /loja/pedido/consultar?numero={n}` |
| **Ações contextuais** | Botões aparecem conforme `pode_cancelar` e `pode_devolver` do response |
| **Pedido vazio** | EmptyState "Você ainda não fez nenhum pedido" + "Explorar produtos" |

### 4.2 Timeline do Pedido

```
● Pedido realizado          12/04 14:30    ✓
● Pagamento confirmado      12/04 14:32    ✓
● Em preparação             12/04 15:00    ✓
● Saiu para entrega         13/04 09:00    ← atual (pulsando)
○ Entregue                  Previsão: 14/04
```

- Cada step: ícone + título + data/hora + descrição opcional
- Step atual: indicador pulsante (Reanimated)
- Baseado em `status_pedido_marketplace` (configurável pelo Superadmin)
- Integra com `entregas_marketplace` e `entrega_eventos` quando logística local ativa
- Atualização em tempo real via WebSocket (`pedido.status_atualizado`)

### 4.3 Cancelamento de Pedido (pelo comprador)

| Tela | Funcionalidade | API |
|------|---------------|-----|
| **Botão "Cancelar pedido"** | Visível apenas quando `pode_cancelar = true` (antes do envio) | — |
| **Seleção de motivo** | Lista de motivos vindos da API (não hardcoded) | `GET /loja/motivos-cancelamento` |
| **Confirmação** | "Tem certeza? Esta ação não pode ser desfeita." com detalhes do reembolso | — |
| **Envio** | Cancela e exibe status | `POST /loja/pedidos/{id}/cancelar` com `{ motivo_id, descricao_adicional? }` |
| **Resultado** | "Pedido cancelado. O reembolso será processado em até X dias úteis." | — |

**Regras de cancelamento (backend):**
- Permitido apenas em status `pendente`, `pago`, `em_preparacao` (antes do envio)
- Após envio → direcionar para devolução
- Reembolso segue a política da plataforma (automático para PIX/cartão; manual para boleto)

### 4.4 Devolução e Reembolso

| Tela | Funcionalidade | API |
|------|---------------|-----|
| **Botão "Devolver produto"** | Visível quando `pode_devolver = true` (após entrega, dentro do prazo) | — |
| **Tipo** | "Quero devolver o produto" ou "Quero reembolso sem devolver" (se aplicável) | — |
| **Motivo** | Lista de motivos da API | `GET /loja/motivos-devolucao` |
| **Fotos** | Upload de até 5 fotos do produto (câmera ou galeria) | — |
| **Descrição** | Campo de texto livre (mín. 20 caracteres) | — |
| **Envio** | Submete solicitação | `POST /loja/pedidos/{id}/devolucao` |
| **Acompanhamento** | Status da devolução na tela do pedido | `GET /loja/pedidos/{id}/devolucao` |

**Status da devolução:**
```
Aberta → Em análise → Aprovada → [Produto devolvido] → Reembolso processado → Finalizada
                    → Recusada (com justificativa)
```

**Prazo:** 7 dias após entrega para solicitar (CDC / política da plataforma). Backend valida.

### 4.5 Chat / Perguntas ao Vendedor

| Tela | Funcionalidade | API |
|------|---------------|-----|
| **Lista de conversas** | Cards: foto da loja, nome, última mensagem, horário, badge não lidas | `GET /loja/conversas` |
| **Conversa** | Bolhas de chat (estilo WhatsApp), input de texto + botão enviar + botão foto | `GET /loja/conversas/{id}/mensagens`, `POST /loja/conversas/{id}/mensagens` |
| **Iniciar conversa** | A partir do produto ("Perguntar ao vendedor") ou da loja ("Conversar") | `POST /loja/conversas` |
| **Contexto** | Se iniciada a partir de produto, exibir card do produto no topo da conversa | `anuncio_id` na conversa |
| **Tempo real** | Mensagens novas via WebSocket (`mensagem.nova`). Indicador "digitando..." (futuro). | WebSocket |
| **Push** | Notificação push quando recebe resposta do vendedor | FCM |

**Regras:**
- Consumidor pode ter múltiplas conversas (uma por loja ou por anúncio)
- Vendedor responde pelo painel web `/negocio/marketplace/mensagens` (endpoint separado com auth PDV)
- Imagens: upload para storage, enviar URL na mensagem

### 4.6 Avaliações

| Funcionalidade | API |
|----------------|-----|
| **Avaliar produto** | Estrelas (1-5) + comentário (mín. 10 chars) + fotos (até 5) | `POST /loja/pedidos/{id}/avaliar` |
| **Ver avaliações** | Na página do produto: nota média, distribuição por estrela (barra visual), lista paginada com fotos expandíveis | `GET /loja/anuncios/{id}/avaliacoes` |
| **Pendentes** | Badge em "Meus Pedidos" nos pedidos entregues sem avaliação | Derivado do status |
| **Push** | "Pedido entregue! Avalie sua compra e ajude outros compradores." | FCM |

### 4.7 Minha Conta

| Seção | Funcionalidade | API |
|-------|---------------|-----|
| **Header** | Avatar (iniciais), nome, email | — |
| **Dados pessoais** | Nome, email, telefone, CPF. Editar inline. | `GET/PATCH /loja/minha-conta` |
| **Endereços** | Lista, adicionar, editar, excluir, definir padrão | `/loja/minha-conta/enderecos/*` |
| **Favoritos** | Lista de produtos salvos | `GET /loja/favoritos` |
| **Notificações** | Lista de notificações in-app com badge | `GET /loja/notificacoes` |
| **Conversas** | Acesso rápido ao chat | `GET /loja/conversas` |
| **Configurações** | Toggle: notificações push, email marketing | Local (MMKV) + `PATCH /loja/minha-conta/consentimentos` |
| **Privacidade (LGPD)** | Ver/editar consentimentos, "Exportar meus dados", "Excluir minha conta" | `/loja/minha-conta/consentimentos`, `dados-exportar`, `excluir-conta` |
| **Ajuda** | FAQ (accordion), "Falar com suporte" (link WhatsApp/email), termos de uso, política de privacidade | Telas estáticas + links web |
| **Sobre** | Versão do app, licenças open source | Local |
| **Sair** | Confirmação → logout | `POST /loja/logout` |

### 4.8 Tela de Privacidade (LGPD)

| Funcionalidade | Detalhes |
|----------------|----------|
| **Meus consentimentos** | Toggles: "Comunicações de marketing" (on/off), "Compartilhamento com terceiros" (on/off), "Cookies de analytics" (on/off) |
| **Exportar meus dados** | Botão → confirmação → API gera JSON → email com link para download (ou download direto) |
| **Excluir minha conta** | Botão vermelho → confirmação com senha → modal "Sua conta será excluída em 30 dias. Você pode cancelar entrando novamente antes do prazo." → `POST /loja/minha-conta/excluir-conta` |
| **Política de privacidade** | Link para página web |
| **Termos de uso** | Link para página web |

---

## Fase 5 — Notificações e Engajamento

**Objetivo:** Manter o usuário engajado e informado em tempo real.

### 5.1 Push Notifications (Firebase Cloud Messaging)

| Evento (backend Celery task) | Notificação push | Deep link |
|------------------------------|-----------------|-----------|
| Pedido confirmado | "Pedido #{numero} confirmado!" | `ibixmarket://pedido/{id}` |
| Pagamento aprovado | "Pagamento aprovado! Seu pedido #{numero} está sendo preparado." | `ibixmarket://pedido/{id}` |
| Em preparação | "Seu pedido #{numero} está sendo preparado pelo vendedor." | `ibixmarket://pedido/{id}` |
| Saiu para entrega | "Seu pedido #{numero} saiu para entrega!" | `ibixmarket://pedido/{id}` |
| Entregue | "Pedido #{numero} entregue! Avalie sua compra." | `ibixmarket://pedido/{id}/avaliar` |
| Cancelamento aprovado | "Pedido #{numero} cancelado. Reembolso em processamento." | `ibixmarket://pedido/{id}` |
| Devolução atualizada | "Atualização na sua devolução do pedido #{numero}." | `ibixmarket://pedido/{id}` |
| Resposta do vendedor | "Nova mensagem de {loja_nome}" | `ibixmarket://chat/{conversa_id}` |
| Promoção (marketing) | Título e mensagem configurados pelo Superadmin | `ibixmarket://produto/{id}` ou deep link customizado |
| Carrinho abandonado (24h) | "Seus itens estão esperando! Complete sua compra." | `ibixmarket://carrinho` |
| Preço baixou (favorito) | "O produto '{titulo}' baixou de preço! Agora por R$ {preco}." | `ibixmarket://produto/{id}` |

**Implementação backend:**
- Celery task `enviar_push_notification(consumidor_id, tipo, dados)`
- Consulta `consumidor_push_tokens` do consumidor (pode ter múltiplos devices)
- Envia via `firebase-admin` SDK (batch para múltiplos tokens)
- Registra em `consumidor_notificacoes` (para tela de notificações in-app)
- Respeita consentimento: se `marketing=false`, não envia promoções/carrinho abandonado

### 5.2 WebSocket (Atualizações em Tempo Real)

| Evento | Payload | Ação no app |
|--------|---------|-------------|
| `pedido.status_atualizado` | `{ pedido_id, status_novo, data }` | Atualizar timeline, toast, atualizar lista de pedidos |
| `pagamento.confirmado` | `{ pedido_id, metodo, valor }` | Navegar para tela de sucesso (se na tela de aguardando) |
| `mensagem.nova` | `{ conversa_id, remetente, texto, data }` | Atualizar chat, badge na tab/ícone, toast |
| `notificacao.nova` | `{ id, tipo, titulo, dados }` | Badge no sino, toast se app em foreground |
| `devolucao.atualizada` | `{ pedido_id, status_novo }` | Atualizar tela do pedido |

**Implementação:**
- Conexão WebSocket ao `/ws/loja/consumidor?token={jwt}` na abertura do app
- Reconexão automática com backoff exponencial (1s, 2s, 4s, 8s, max 30s)
- Heartbeat a cada 30s para manter conexão viva
- Se WebSocket indisponível, fallback para polling (pedidos: 30s, pagamento: 5s)
- Backend: FastAPI WebSocket + Redis pub/sub para broadcast entre workers Gunicorn

### 5.3 Favoritos (Wishlist)

| Funcionalidade | Detalhes |
|----------------|----------|
| **Adicionar** | Ícone coração no ProductCard e na página do produto. Animação pulse + cor | `POST /loja/favoritos` |
| **Remover** | Toggle do coração | `DELETE /loja/favoritos/{anuncio_id}` |
| **Lista** | Tela "Favoritos": grid de produtos como catálogo, com "Remover" e "Adicionar ao carrinho" | `GET /loja/favoritos` |
| **Optimistic UI** | Mudança visual imediata, revert se API falhar |
| **Alerta de preço** | Push quando preço de um favorito baixa (Celery job diário) | FCM |

### 5.4 Deep Links e Universal Links

| Link | Destino no app |
|------|---------------|
| `ibixmarket://produto/{id}` | Página do produto |
| `ibixmarket://loja/{slug}` | Página da loja |
| `ibixmarket://pedido/{id}` | Detalhe do pedido |
| `ibixmarket://pedido/{id}/avaliar` | Tela de avaliação |
| `ibixmarket://categoria/{id}` | Listagem da categoria |
| `ibixmarket://carrinho` | Tela do carrinho |
| `ibixmarket://chat/{id}` | Conversa |
| `ibixmarket://pagamento/sucesso` | Confirmação de pagamento |
| `ibixmarket://pagamento/falha` | Erro de pagamento |
| `ibixmarket://pagamento/pendente` | Aguardando pagamento |
| `https://ibix.com.br/loja/produto/{id}` | Universal link → abre no app se instalado, senão web |
| `https://ibix.com.br/loja/{slug}` | Universal link → loja |

**Configuração:**
- Android: `assetlinks.json` servido em `/.well-known/` com fingerprint SHA-256 do app
- iOS: `apple-app-site-association` servido em `/.well-known/` com `applinks` e `webcredentials`
- Ambos servidos pelo Nginx com `Content-Type: application/json`

### 5.5 Compartilhamento

| Funcionalidade | Detalhes |
|----------------|----------|
| **Compartilhar produto** | `expo-sharing` com link universal + título + preço. Preview do link (Open Graph já implementado no backend — `MAPA_DO_SISTEMA` Marketing/SEO). |
| **Compartilhar loja** | Link da loja com preview |

**Analytics:** `share` event com `content_type`, `item_id`.

---

## Fase 6 — Performance e Polish

**Objetivo:** App rápido, acessível, com experiência premium e suporte a tablets.

### 6.1 Performance

| Otimização | Implementação | Meta |
|------------|---------------|------|
| **Imagens** | `expo-image` com cache em disco. Thumbnails: 150px (lista compacta), 300px (grid), 600px (detalhe). BlurHash placeholder. | LCP < 1.5s |
| **Listas** | `FlashList` (Shopify) para todas as listagens com `estimatedItemSize` calibrado | 60fps scroll |
| **Cache API** | React Query: marketing 5min, categorias 10min, produtos 1min, pedidos 30s, chat 0 (real-time) | Reduzir requests 60% |
| **Bundle** | Hermes engine, tree shaking, lazy imports via `React.lazy` para telas pesadas (checkout, chat) | Bundle < 15MB |
| **Startup** | Splash screen nativa (expo-splash-screen), pré-carrega home em paralelo, dados essenciais em cache MMKV | Cold start < 2s |
| **Offline** | Tela "Sem conexão" com animação + botão retry. Dados em cache continuam navegáveis (catálogo, favoritos). Carrinho offline. | Graceful degradation |
| **Skeleton** | Skeleton loaders com shimmer em todos os pontos de carregamento | Perceived performance |
| **Prefetch** | Ao navegar para detalhe do produto, prefetch de similares e avaliações | Navegação instantânea |
| **Memory** | Limpar cache de imagens quando app vai para background em low-memory | Sem OOM crashes |

### 6.2 Animações

| Local | Animação | Lib |
|-------|----------|-----|
| **Adicionar ao carrinho** | Item "voa" para a tab carrinho (shared element) | Reanimated |
| **Badge do carrinho** | Bounce scale quando incrementa | Reanimated |
| **Pull-to-refresh** | Lottie customizado com logo | Lottie |
| **Splash** | Lottie com logo (fade + scale) | Lottie |
| **Sucesso de compra** | Confetti + checkmark | Lottie |
| **Favoritar** | Coração: scale up + cor (branco → vermelho) | Reanimated |
| **Transição lista→detalhe** | Shared element: imagem do card → galeria | Reanimated |
| **Skeleton shimmer** | Gradiente animado da esquerda para direita | Reanimated |
| **Tab switch** | Cross-fade suave | Reanimated |
| **BottomSheet** | Spring animation com gesture handler | Gesture + Reanimated |
| **Toast** | Slide-in do topo + fade out | Reanimated |
| **Timeline pedido** | Step atual pulsando | Reanimated loop |

### 6.3 Acessibilidade

| Item | Implementação |
|------|---------------|
| **VoiceOver / TalkBack** | `accessibilityLabel` em todos os botões, imagens, campos. `accessibilityRole` correto. `accessibilityState` para toggles e checkboxes. |
| **Contraste** | Mínimo 4.5:1 texto normal, 3:1 texto grande (WCAG AA). Verificar com Accessibility Inspector. |
| **Tamanho de toque** | Mínimo 44x44 pontos (iOS) / 48x48dp (Android). |
| **Escalamento de fonte** | `allowFontScaling={true}` (default). Testar com fonte 200%. Usar `maxFontSizeMultiplier` onde layout quebra. |
| **Reduzir movimento** | Respeitar `AccessibilityInfo.isReduceMotionEnabled()`. Desabilitar animações cosmético-puras. |
| **Screen reader order** | Ordem lógica de leitura, especialmente na página do produto e checkout. |
| **Modo escuro** | Suporte a `Appearance.getColorScheme()`. Tokens dark mode no theme. (Fase futura, mas estrutura pronta.) |

### 6.4 Layout Responsivo (Tablet)

| Componente | Phone | Tablet |
|-----------|-------|--------|
| **Grid de produtos** | 2 colunas | 3-4 colunas |
| **Página do produto** | Stack vertical | Split: galeria esquerda + info direita (master-detail) |
| **Checkout** | Full screen steps | Side panel com resumo permanente |
| **Chat** | Full screen | Split: lista esquerda + conversa direita |
| **Meus pedidos** | Full screen | Split: lista esquerda + detalhe direita |
| **Banners** | Full width | Max-width 900px centralizado |

**Implementação:** Hook `useBreakpoint()` baseado em `useWindowDimensions()`. Componentes usam conditional layout.

---

## Fase 7 — Testes, ASO e Publicação

### 7.1 Testes

| Tipo | Ferramenta | Cobertura |
|------|-----------|-----------|
| **Unitários** | Jest | Services, utils, formatters, stores, validators |
| **Componentes** | React Native Testing Library | Componentes UI, interações, estados |
| **E2E** | Maestro | Fluxos críticos (ver abaixo) |
| **Snapshot** | Jest | Componentes visuais estáveis |
| **Performance** | Flashlight (Shopify) | FPS, startup time |
| **Acessibilidade** | axe-react-native + manual | Screen readers, contraste |

**Fluxos E2E obrigatórios (Maestro):**
1. Onboarding → Cadastro (com LGPD consent) → Login → Navegar home
2. Login Social (Google)
3. Busca → Autocomplete → Filtrar → Produto → Ver parcelas → Adicionar ao carrinho
4. Carrinho → Aplicar cupom → Checkout → Endereço → Frete → PIX → Confirmação
5. Carrinho → Checkout → Cartão 3x → Redirect MP → Deep link retorno → Sucesso
6. Meus Pedidos → Detalhe → Timeline → Cancelar pedido
7. Meus Pedidos → Detalhe → Solicitar devolução (com foto)
8. Produto → Perguntar ao vendedor → Chat → Enviar mensagem
9. Favoritar → Lista de favoritos → Remover
10. Conta → Privacidade → Exportar dados
11. Esqueci senha → Redefinir
12. Force update modal (simular versão antiga)
13. Offline → Exibir banner → Reconectar → Dados atualizados

### 7.2 App Store Optimization (ASO)

> **Naming nas lojas:** o display name é **`Ibix`** (curto, reforça a marca-mãe). Dentro do app o usuário vê **`Ibix Market`** como brand visível (logo `cab.png` no header), em paridade com a vitrine web servida em `ibix.com.br`.

| Item | Apple App Store | Google Play |
|------|----------------|-------------|
| **Nome** | "Ibix" (4 chars) | "Ibix" (4 chars) |
| **Subtítulo** | "Marketplace local — comércio que você conhece" (30 chars) | — (usa short description) |
| **Short description** | — | "Compre nas lojas perto de você. PIX, cartão, boleto. Frete grátis." (80 chars) |
| **Descrição longa** | Benefícios → Features → Segurança → CTA. 4000 chars. Keywords naturais. | Idem, 4000 chars. |
| **Keywords** | "compras,marketplace,ofertas,promoção,frete grátis,pix,loja online,cupom" (100 chars) | — (extrai da descrição) |
| **Categoria** | Shopping | Shopping |
| **Screenshots** | 5-8 por device (6.7" obrigatório, 5.5" obrigatório). Contextuais com texto overlay. | 4-8 por device. Phone obrigatório. |
| **Vídeo preview** | 15-30s mostrando fluxo de compra (opcional mas recomendado) | YouTube link (opcional) |
| **Ícone** | 1024x1024, fundo `#FEF7F1`, logo Ibix Market (`logoSfundo.png` adaptado), sem texto extra | 512x512 (adaptive icon: foreground monocromático verde-musgo `#5C6E4A` sobre `#FEF7F1`) |
| **Feature graphic** | — | 1024x500 com paleta da vitrine (off-white + verde-musgo + dourado) e logo Ibix Market |

**Screenshots estratégicos (ordem):**
> Todas as capturas devem mostrar o **header com o logo Ibix Market** (componente `<BrandLogo>`) e a paleta da vitrine — o usuário deve reconhecer instantaneamente que app e vitrine web são o mesmo produto.

1. Home com banners e produtos (mostrar variedade) — header com logo Ibix Market visível
2. Produto com preço e parcelas (mostrar economia) — CTA verde-musgo
3. Busca com resultados (mostrar facilidade)
4. Checkout PIX (mostrar conveniência)
5. Meus Pedidos com timeline (mostrar confiança)
6. Chat com vendedor (mostrar suporte)

### 7.3 Builds (EAS Build)

| Plataforma | Conta | Custo |
|-----------|-------|-------|
| **iOS** | Apple Developer Program | $99/ano |
| **Android** | Google Play Console | $25 (único) |

**Configuração EAS:**
- `eas.json` com profiles: `development` (simulator), `preview` (TestFlight/Internal), `production`
- `app.json`: `bundleIdentifier: "com.ibix.market"` (iOS), `package: "com.ibix.market"` (Android)
- Signing: certificados Apple (provisioning profile auto-managed) e keystore Android (EAS managed)
- OTA Updates: `expo-updates` com canal `production` para hotfixes sem re-publicar

### 7.4 Submissão

**Apple App Store:**
1. Screenshots (6.7" iPhone 15 Pro Max e 5.5" iPhone 8 Plus — obrigatórios) + iPad se suportar
2. Metadata: nome, subtítulo, descrição, keywords, URLs (suporte, marketing, privacidade)
3. App Privacy Labels: Email, Nome, Endereço, Dados de pagamento, Dados de uso (analytics)
4. App Review: Conta demo para reviewer, notas explicativas sobre marketplace (bens físicos = pode usar gateway externo ✅)
5. Content Rating: 4+ (sem conteúdo adulto)
6. Primeira revisão: 7-14 dias (garantir compliance total para evitar rejeição)

**Google Play:**
1. Screenshots phone (obrigatório) + tablet (recomendado) + feature graphic (obrigatório)
2. Short description + full description + changelogs
3. Data Safety Section: declarar coleta/compartilhamento de dados (email, endereço, pagamento, device ID, crash logs)
4. Content rating: questionário IARC (resultado: "Everyone")
5. Teste interno → Teste aberto (mínimo 20 testers, 14 dias) → Produção (obrigatório para contas novas)
6. Primeira revisão: 1-7 dias

### 7.5 Compliance e Legal

| Item | Requisito | Status |
|------|-----------|--------|
| **LGPD** | Política de privacidade acessível, consentimento no cadastro, exportação/exclusão de dados | Implementado na Fase 4.8 |
| **CDC (Código de Defesa do Consumidor)** | Direito de arrependimento 7 dias, informação clara de preço/frete | Implementado na Fase 4.4 |
| **Apple Guidelines** | Sem compra in-app (bens físicos isentos), login Apple obrigatório se tem login social | Implementado nas Fases 0/1 |
| **Google Play Policies** | Data Safety Section preenchida, target API level atualizado, privacy policy URL | Implementado na Fase 7.4 |
| **PCI-DSS** | Dados de cartão NUNCA passam pelo app (redirect para gateway MP/PagBank) | By design |
| **Acessibilidade** | WCAG AA mínimo | Implementado na Fase 6.3 |

### 7.6 Checklist Pré-Publicação

**Funcional:**
- [ ] Testes E2E (13 fluxos) passando em iOS e Android
- [ ] Checkout completo testado com sandbox (PIX, cartão, boleto)
- [ ] Deep links funcionando em ambas plataformas
- [ ] Universal links testados (web → app)
- [ ] Push notifications testadas em device real (iOS + Android)
- [ ] WebSocket conecta e recebe eventos em tempo real
- [ ] Cupom aplica desconto corretamente
- [ ] Cancelamento e devolução funcionam
- [ ] Chat envia/recebe mensagens
- [ ] Force update modal aparece para versão antiga
- [ ] LGPD: exportação e exclusão de conta funcionam
- [ ] Offline: banner aparece, dados em cache navegáveis, reconecta

**Performance:**
- [ ] Cold start < 2s (iOS e Android)
- [ ] Scroll 60fps em todas as listas (medir com Flashlight)
- [ ] Bundle size < 25MB (iOS), < 15MB (Android APK)
- [ ] Imagens carregam com placeholder blur, sem flash branco
- [ ] Sem memory leaks (testar com Instruments/Android Profiler)

**Qualidade:**
- [ ] Acessibilidade: VoiceOver/TalkBack navegação completa
- [ ] Tablet: layout adapta corretamente (iPad + Android tablet)
- [ ] Sentry configurado e reportando (testar com crash intencional)
- [ ] Analytics: events chegando no Firebase (purchase, add_to_cart, search)
- [ ] Certificate pinning ativo em produção
- [ ] Sem console.log no build de produção
- [ ] Sem dados de teste/mock

**Publicação:**
- [ ] App icons em todas as resoluções (1024, 512, adaptive)
- [ ] Splash screen nativa configurada
- [ ] Screenshots ASO prontos (todos os devices obrigatórios)
- [ ] Descrições e keywords otimizados
- [ ] Política de privacidade URL acessível
- [ ] Termos de uso URL acessível
- [ ] Conta demo para App Review (Apple)
- [ ] Certificados de assinatura armazenados com segurança (EAS managed ou cofre)

---

## Resumo: APIs Existentes vs. Novas

### APIs que o app consome SEM ALTERAÇÃO (27 endpoints)

| API | Uso |
|-----|-----|
| `POST /loja/login` | Login |
| `POST /loja/cadastro` | Cadastro |
| `POST /loja/auth/social/login` | Google Sign-In |
| `POST /loja/auth/social/config` | Config OAuth |
| `POST /loja/logout` | Logout |
| `POST /loja/forgot-password` | Esqueci senha |
| `POST /loja/redefinir-senha/valida` | Validar token de redefinição |
| `POST /loja/redefinir-senha` | Redefinir senha |
| `GET /loja/categorias` | Categorias |
| `GET /loja/anuncios` | Listagem/busca (ajustar para cursor-based) |
| `GET /loja/anuncios/{id}` | Detalhe (ajustar para incluir parcelas e favorito) |
| `GET /loja/anuncios/{id}/semelhantes` | Similares |
| `GET /loja/anuncios/{id}/avaliacoes` | Avaliações |
| `GET /loja/anuncios/perto-de-voce` | Faixa "Perto de você" da home |
| `GET /loja/anuncios/proximos` | Faixa "Mais perto de você" pós-busca |
| `GET /loja/geo/cidades` | Lista de cidades com loja ativa (CitySelectorSheet) |
| `GET /loja/geo/cidade-proxima` | Cidade mais próxima às coordenadas (fallback) |
| `GET /loja/geo/reverso` | Reverse geocoding cidade/UF (Nominatim server-side) |
| `GET /loja/minha-conta` | Perfil |
| `PATCH /loja/minha-conta` | Atualizar perfil |
| `GET /loja/minha-conta/enderecos` | Listar endereços |
| `POST /loja/minha-conta/enderecos` | Novo endereço |
| `GET /loja/meus-pedidos` | Pedidos |
| `POST /loja/pedidos/{id}/avaliar` | Avaliar |
| `POST /loja/checkout` | Checkout loja única (ajustar para cupom e parcelas) |
| `POST /loja/checkout-unificado` | Checkout multi-loja (idem) |
| `POST /loja/completar-cadastro` | Completar cadastro |
| `GET /loja/{loja_id}/frete` | Calcular frete |
| `POST /loja/pedidos/{id}/nova-tentativa-pagamento` | Retentativa |
| `GET /loja/pedido/consultar` | Consultar pedido |
| `GET /loja/pedido/meu` | Meu pedido |
| `GET /marketing-vitrine/vitrine-home` | Home marketing |

### APIs COM AJUSTES (6 endpoints)

| API | Ajuste |
|-----|--------|
| `GET /loja/anuncios` | + cursor-based, + `parcela_sem_juros` |
| `GET /loja/anuncios/{id}` | + `parcelas[]`, + `favorito` |
| `POST /loja/checkout` | + `cupom_codigo`, + `parcelas`, + deep links |
| `POST /loja/checkout-unificado` | + `cupom_codigo`, + `parcelas`, + deep links |
| `GET /loja/meus-pedidos` | + cursor, + `pode_cancelar`, + `pode_devolver` |
| `GET /loja/pedido/consultar` | + timeline, + devolução, + logística |

### APIs NOVAS (33 endpoints)

| Grupo | Endpoints | Qtd |
|-------|-----------|-----|
| Auth/Dispositivo | refresh-token, apple, push-token (POST/DELETE), app-version | 5 |
| Favoritos | GET, POST, DELETE | 3 |
| Notificações | GET, PATCH lida, PATCH todas-lidas | 3 |
| Cupons | validar, disponiveis | 2 |
| Endereços | PATCH, DELETE, PATCH padrao | 3 |
| Cancelamento/Devolução | cancelar, devolucao (POST/GET), motivos-cancelamento, motivos-devolucao | 5 |
| Chat | conversas (GET/POST), mensagens (GET/POST), lida | 5 |
| Busca | autocomplete, populares | 2 |
| Parcelamento | simulação | 1 |
| WebSocket | /ws/loja/consumidor | 1 |
| LGPD | dados-exportar, excluir-conta, consentimentos (GET/PATCH) | 4 |
| **Total** | | **34** |

### Tabelas NOVAS (12 migrações)

| Tabela | Migration |
|--------|-----------|
| `consumidor_push_tokens` | `mob01_push_tokens` |
| `consumidor_favoritos` | `mob02_favoritos` |
| `consumidor_notificacoes` | `mob03_notificacoes` |
| `cupons_marketplace` | `mob04_cupons` |
| `cupons_consumidor` | `mob04_cupons` |
| `devolucoes_marketplace` | `mob05_devolucoes` |
| `motivos_cancelamento` | `mob05_devolucoes` |
| `conversas_marketplace` | `mob06_chat` |
| `mensagens_conversa` | `mob06_chat` |
| `consumidor_consentimentos` | `mob07_lgpd` |
| `app_versao_config` | `mob08_versao` |
| `termos_buscados` | `mob09_busca` |

---

## Dependências Externas

| Serviço | Custo | Necessário em |
|---------|-------|---------------|
| Apple Developer Program | $99/ano | Fase 7 (publicação iOS) |
| Google Play Console | $25 (único) | Fase 7 (publicação Android) |
| Firebase (Analytics + FCM) | Gratuito (Spark plan) | Fases 1 (analytics) e 5 (push) |
| Sentry | Gratuito (5k eventos/mês) ou $26/mês (50k) | Fase 1 (crash reporting) |
| Expo Application Services (EAS) | Gratuito (30 builds/mês) ou $99/mês (ilimitado) | Fase 7 (builds) |
| Mercado Pago (sandbox) | Gratuito | Fase 3 (testes de pagamento) |

---

## Sequência de Implementação Recomendada

```
Semana 01-03:  Fase 0 — Backend
               - Semana 1: Auth (refresh, Apple), push tokens, favoritos, notificações, app-version
               - Semana 2: Cupons, endereços CRUD, cancelamento, devolução, motivos, parcelamento
               - Semana 3: Chat, busca (autocomplete, populares), WebSocket, LGPD, ajustes APIs existentes

Semana 04-06:  Fase 1 — Fundação
               - Semana 4: Expo setup, theme, design system base (20 componentes), Sentry, Analytics
               - Semana 5: Auth completo (login, cadastro, social, esqueci senha, LGPD consent)
               - Semana 6: Navegação completa, force update, certificate pinning, API service layer

Semana 07-10:  Fase 2 — Vitrine
               - Semana 7: Home (marketing, banners, categorias)
               - Semana 8: Catálogo (listagem, filtros, infinite scroll, parcelas nos cards)
               - Semana 9: Busca (autocomplete, histórico, populares, resultados)
               - Semana 10: Produto (galeria, parcelas, frete, avaliações, similares, perguntar vendedor)

Semana 11-14:  Fase 3 — Checkout
               - Semana 11: Carrinho (persistência, agrupamento, cupom, validação)
               - Semana 12: Checkout endereço + frete
               - Semana 13: Pagamento (PIX, cartão com parcelas, boleto, deep links)
               - Semana 14: Confirmação (polling, WebSocket, estados)

Semana 15-18:  Fase 4 — Pós-Venda
               - Semana 15: Meus pedidos + detalhe + timeline
               - Semana 16: Cancelamento + devolução
               - Semana 17: Chat com vendedor (lista, conversa, WebSocket, push)
               - Semana 18: Conta + LGPD + avaliações

Semana 19-21:  Fase 5 — Engajamento
               - Semana 19: Push notifications (todos os eventos) + notificações in-app
               - Semana 20: Favoritos + compartilhamento + deep links/universal links
               - Semana 21: WebSocket hardening + reconexão + alerta de preço

Semana 22-23:  Fase 6 — Polish
               - Semana 22: Performance (FlashList, prefetch, cache, startup, offline)
               - Semana 23: Animações + acessibilidade + layout tablet

Semana 24-26:  Fase 7 — Publicação
               - Semana 24: Testes E2E (13 fluxos) + fix de bugs
               - Semana 25: ASO (screenshots, descrições, keywords) + builds production
               - Semana 26: Submissão Apple + Google + correções pós-revisão
```

---

## Regras Obrigatórias (alinhamento com MAPA_DE_REGRAS § 0)

1. **Sem fallback:** Dado obrigatório ausente → erro explícito no app (toast com mensagem da API), nunca valor alternativo.
2. **Sem dados hardcoded:** Todos os dados dinâmicos (categorias, produtos, preços, status, marketing, motivos de cancelamento, parcelas) vêm da API.
3. **Validade jurídica:** Confirmação de compra SOMENTE quando `status_pagamento = "pago"`. Sem exceção.
4. **RBAC/Tenant:** O app é consumidor final. Auth via `loja_consumidor_token`. Não expõe dados de outros consumidores.
5. **Segurança:** Token em Secure Storage (criptografado), nunca em AsyncStorage. HTTPS obrigatório. Certificate pinning em produção. Sem tokens em logs. Dados de cartão nunca passam pelo app (redirect para gateway).
6. **LGPD:** Consentimento explícito no cadastro. Exportação e exclusão de dados implementados. Respeitar opt-out de marketing.
7. **CDC:** Direito de arrependimento (7 dias). Informação clara e completa de preço, frete e prazos.
8. **Cards de marketing:** Conteúdo vem exclusivamente de `/api/v1/marketing-vitrine` (gerenciado pelo Superadmin), nunca hardcoded no app.
9. **Identidade visual única:** App mobile DEVE espelhar 100% a vitrine web (`app/static/css/loja.css` é fonte canônica de cores/tipografia/radii; `app/static/img/ibix/cab.png` é fonte canônica do logo). Brand assets são copiados bit-a-bit, NUNCA recriados. Mudanças visuais começam pela vitrine — o app segue.
10. **Naming nas lojas:** display name = `Ibix` (curto, marca-mãe); brand visível dentro do app = `Ibix Market` (logo `cab.png` no header); slug e bundle permanecem `ibix-market` / `com.ibix.market`.

---

**Última atualização:** 2026-05-04
**Status:** Em desenvolvimento — paridade visual total com a vitrine entregue.

---

## Changelog 2026-05-04 — Identidade visual = vitrine web

**Sessão de alinhamento total da identidade visual com a vitrine pública (`mobile_marketplace/`):**

- **Paleta:** `theme/colors.ts` reescrito com tokens `--ibix-*` da `loja.css` (off-white `#FEF7F1`, azul-ardósia `#4A627A`/`#2F3A44`, verde-musgo `#5C6E4A`, terracota `#C47A44`, dourado `#D9B48B`). Light + dark.
- **Tipografia:** Inter trocado por **Poppins** (`@expo-google-fonts/poppins`) em `theme/typography.ts`; `_layout.tsx` carrega Poppins via `useFonts`.
- **Sombras:** `theme/shadows.ts` espelha `--loja-shadow-sm/block/hero` (`0 1px 3px / 0 4px 12px / 0 8px 24px`).
- **Border radius:** `theme/spacing.ts` ajustado (8/10/14/18/22) — paridade com `btn-primary`, `loja-search-form`, `loja-section-block`.
- **Focus-ring:** novo token `focusRing = { width: 2, offset: 2 }` + `colors.focusRing = #C47A44` replicando `loja-header *:focus-visible`.
- **Naming nas lojas:** `app.json` `expo.name` mudou de `"Ibix Market"` para **`"Ibix"`** (display name nas lojas e no springboard); slug, bundle e package mantidos como `ibix-market` / `com.ibix.market`.
- **Splash e ícones:** `app.json` agora usa `#FEF7F1` em `splash.backgroundColor`, `android.adaptiveIcon.backgroundColor` e `expo-splash-screen.backgroundColor`; `expo-notifications.color` agora é `#5C6E4A` (verde-musgo). Os 4 PNGs em `assets/images/` foram regenerados a partir do logo Ibix Market (`cab.png` para splash, `logoSfundo.png` para icon/adaptive/notification).
- **Brand assets:** novo `assets/brand/` com cópia bit-a-bit de `app/static/img/ibix/cab.png`, `rodape.png` e `app/static/img/landing/logoSfundo.png`. Exports tipados via `assets/brand/index.ts`.
- **Logo no app:** novo componente `components/common/BrandLogo.tsx` renderiza `cab.png` em headers (home + login) — substitui texto "Ibix Market" como brand visível.
- **Auditoria de hard-codes:** corrigidas cores literais em `Icon.tsx` (default), `loja/[slug].tsx` (overlays), `endereco.tsx`, `frete.tsx`, `pagamento.tsx`, `(tabs)/carrinho.tsx`, `AddressCard.tsx` (todas as `borderTopColor: '#eee'` agora usam `colors.divider`).
- **Documentação:** Fase 1.3 (Design System) e Fase 7.2 (ASO) reescritas; nova seção "Identidade Visual e Naming" no topo; `mobile_marketplace/AGENTS.md` § 1, § 6 e § 8 atualizados; nova regra em `MAPA_DE_REGRAS.md`.

---

## Changelog 2026-04-27

**Sessão de paridade marketplace + geo + login social no mobile (`mobile_marketplace/`):**

- Auth: corrigido endpoint de refresh (`/loja/refresh-token`) e implementada paridade total de login social (Google + Apple + Facebook) via `hooks/useSocialAuth.ts` (consumindo `/loja/auth/social/config`, `/loja/auth/social/login`, `/loja/auth/social/apple`).
- Checkout: `services/checkoutService.ts` separado em `submitSingleLoja` e `submitUnificado` com payloads alinhados a `PedidoCheckoutCreate` (buyer info, `aceite_politica_privacidade`, `aceite_marketing`, idempotency-key); `checkout/pagamento.tsx` e `checkout/confirmacao.tsx` ajustados para fluxo logado/anônimo (`/loja/pedido/meu` e `/loja/pedido/consultar`).
- Pedidos: `pedidos.tsx` agora consome `/loja/meus-pedidos` e `pedido/[numero].tsx` consome `/loja/pedido/meu`; cancelamento via `motivo_id`.
- Chat: `services/chatService.ts` apontando para `/loja/conversas`; novas telas `chat/index.tsx` e `chat/[id].tsx`.
- Endereços: alinhado `uf`/`apelido`/`principal` em `addressService` + `checkout/endereco.tsx` + `AddressCard` + `conta/enderecos.tsx`.
- Catálogo: `Installment` agora usa `parcelas`/`valor_parcela`/`opcoes` (resposta real de `/loja/parcelamento`).
- Perfil: `(tabs)/perfil.tsx` reflete sessão (`useAuthStore`) e linka pedidos, chat, endereços, LGPD, ajuda e logout.
- **Geo "Perto de você" (paridade vitrine web):**
  - Pacote `expo-location` adicionado e plugin no `app.json` com permissões de localização para iOS/Android.
  - `services/geoService.ts`: `getNearbyAds`, `getNearbyByQuery`, `listCities`, `nearestCity`, `reverseGeo`.
  - `store/geoStore.ts` (Zustand) persistido em MMKV (`STORAGE_KEYS.GEO_LOCATION = 'ibix_geo_location'`); hidratado no `_layout.tsx`.
  - `hooks/useGeo.ts`: permissão `expo-location` + reverse geocoding (servidor) + fallback `cidade-proxima`.
  - `components/geo/`: `LocationChip`, `CitySelectorSheet` (GPS ou seleção manual), `NearbyAdsCarousel` (badge km · min).
  - Home (`app/(tabs)/index.tsx`): chip de localização, faixa "Perto de você em {cidade}" e CTA quando sem localização.
  - Busca (`app/busca.tsx`): chip + faixa "Mais perto de você que vendem isso" sobre o grid.
