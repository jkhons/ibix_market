# AGENTS.md — Ibix Market (App Mobile Marketplace)

> Arquivo de contexto persistente para a **IA Cursor** e desenvolvedores que clonarem este diretório.
> **Leia este arquivo antes de qualquer alteração** — ele define stack, padrões, identidade visual, regras de negócio e o backend que o app consome.

---

## 1. O que é este projeto

App **React Native (Expo SDK 52)** para o consumidor final do **PDV Ibix Marketplace**. O backend é **FastAPI (Python)** localizado em `../app/` (mesmo monorepo do PDV), expondo `/api/v1/loja/*` e `/api/v1/marketing-vitrine/*`.

- **Plataformas:** iOS, Android, Web (PWA leve)
- **Identidade comercial:** *Ibix Market* (vitrine pública do marketplace PDV Ibix)
- **Bundle/Package:** `com.ibix.market`
- **Scheme:** `ibixmarket://` (deep links)
- **Domínio universal:** `https://www.ibix.com.br/loja/...` (universal/applinks)

Documentação macro vive em `../MAPA_SISTEMA/PLANO_APP_MOBILE_MARKETPLACE.md` (plano por fases) e `../MAPA_SISTEMA/MAPA_DO_SISTEMA.md` (sistema completo).

---

## 2. Pré-requisitos para rodar localmente

Quando você (IA ou humano) **clonar este projeto na máquina local** (Windows/Linux/macOS):

| Ferramenta | Versão mínima | Instalação |
|------------|---------------|------------|
| Node.js | 18 LTS (recomendado 20) | https://nodejs.org |
| npm | 9+ (vem com Node) | — |
| Git | qualquer recente | — |
| Expo Go (no celular) | App da App Store / Play Store | iPhone/Android |
| Android Studio (opcional) | Hedgehog+ | Para emulador Android |
| Xcode (apenas macOS) | 15+ | Para simulador iOS |
| Cursor IDE | atual | Edição com IA |

> **Não precisa instalar `expo-cli` global.** Use `npx expo` (vem com o pacote `expo`).

---

## 3. Setup local (passo a passo)

```bash
# 1. Entre no diretório
cd mobile_marketplace

# 2. Configure o .env (crie a partir do exemplo)
cp .env.example .env
# Edite .env e ajuste EXPO_PUBLIC_API_BASE_URL para o backend que você vai usar:
#   - Backend rodando no MESMO PC (Expo Go no celular):  http://<IP_DO_PC>:8000/api/v1
#   - Emulador Android (backend no host):                http://10.0.2.2:8000/api/v1
#   - Simulador iOS (backend no host):                   http://127.0.0.1:8000/api/v1
#   - Backend em produção/staging:                       https://staging-api.ibix.com.br/api/v1

# 3. Instale dependências (instala todos os pacotes Expo na versão correta)
npm install

# 4. Rode em desenvolvimento
npx expo start
# - Tecla "a"  → abre Android (emulador ou dispositivo)
# - Tecla "i"  → abre iOS Simulator (apenas macOS)
# - Tecla "w"  → abre versão web no navegador
# - Escaneie o QR code com o app Expo Go (Android) ou câmera (iOS)
```

Se aparecer erro de versão de pacotes, rode:

```bash
npx expo install --fix
```

> **Importante:** o backend FastAPI (`../app/`) precisa estar rodando **antes** de abrir o app, ou o app exibirá erros de rede. Para subir o backend: `cd .. && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`.

---

## 4. Stack e versões (já fixadas em `package.json`)

### Core
- **React 18.3** + **React Native 0.76** (New Architecture habilitada)
- **Expo SDK ~52** + **Expo Router ~4** (file-based routing)

### Estado e dados
- **Zustand ~5** — estado global (auth, cart, geo, notifications, recentlyViewed)
- **@tanstack/react-query ~5** — cache de API e sincronização
- **Axios ~1.7** — cliente HTTP com interceptors
- **react-native-mmkv ~3** — storage local rápido (recentes, geo, etc.)
- **expo-secure-store ~14** — tokens JWT (criptografado)

### UI e UX
- **react-native-reanimated ~3.16** + **react-native-gesture-handler ~2.20**
- **@gorhom/bottom-sheet ~5** — bottom sheets nativos (filtros, seletor de cidade)
- **@shopify/flash-list ~1.7** — listas de alta performance
- **expo-image ~2** — imagens com cache, transitions e BlurHash
- **react-native-svg ~15** — ícones SVG (componente `Icon`)
- **lottie-react-native ~7** — animações premium
- **react-native-qrcode-svg ~6** — QR code do PIX

### Auth
- **expo-apple-authentication ~7** — Sign in with Apple (obrigatório iOS)
- **expo-auth-session ~6** — Google/Facebook OAuth
- **expo-local-authentication ~15** — biometria (Face ID, Touch ID, fingerprint)

### Notificações e geo
- **expo-notifications ~0.29** — push (FCM/APNS)
- **expo-location ~18** — GPS para "Perto de você"

### Telemetria
- **@sentry/react-native ~6.1** — crashes e performance
- **@react-native-community/netinfo** — detecção de offline

---

## 5. Estrutura de pastas (relevante para a IA)

```
mobile_marketplace/
├── app/                          # Expo Router (rotas = arquivos)
│   ├── _layout.tsx               # Layout raiz (provider, hidratação dos stores)
│   ├── (tabs)/                   # Bottom tabs (home, categorias, carrinho, pedidos, perfil)
│   ├── (auth)/                   # Login, cadastro, esqueci senha (modal)
│   ├── produto/[id].tsx          # PDP — detalhes + parcelas + similares
│   ├── categoria/[id].tsx
│   ├── loja/[slug].tsx           # Página da loja
│   ├── busca.tsx                 # Busca + autocomplete + "Mais perto de você que vendem isso"
│   ├── checkout/                 # endereco → frete → pagamento → confirmacao
│   ├── pedido/[numero].tsx       # Detalhe do pedido + timeline
│   ├── chat/                     # Lista + thread (consumidor ↔ loja)
│   ├── conta/enderecos.tsx
│   ├── favoritos.tsx
│   └── notificacoes.tsx
├── components/
│   ├── ui/                       # Design system base (Button, Text, Card, Chip, Icon, ...)
│   ├── product/                  # ProductCard, BannerCarousel, CategoryCard, FilterSheet
│   ├── checkout/                 # AddressCard, InstallmentPicker, PixPayment, ...
│   ├── cart/, order/, chat/, common/
│   └── geo/                      # LocationChip, CitySelectorSheet, NearbyAdsCarousel
├── services/                     # API clients (axios) — UM service por domínio do backend
│   ├── api.ts                    # axios + interceptor 401 + refresh token
│   ├── authService.ts            # /loja/login, /loja/cadastro, /loja/auth/social/*
│   ├── catalogService.ts         # /loja/anuncios, /loja/categorias, /loja/parcelamento
│   ├── checkoutService.ts        # /loja/checkout, /loja/checkout-unificado
│   ├── orderService.ts           # /loja/meus-pedidos, /loja/pedido/meu
│   ├── chatService.ts            # /loja/conversas
│   ├── addressService.ts         # /loja/minha-conta/enderecos
│   ├── consumerService.ts        # /loja/minha-conta
│   ├── favoriteService.ts        # /loja/favoritos
│   ├── couponService.ts          # /loja/cupons/*
│   ├── notificationService.ts    # /loja/notificacoes
│   ├── marketingService.ts       # /marketing-vitrine/vitrine-home
│   └── geoService.ts             # /loja/geo/*, /loja/anuncios/perto-de-voce, /loja/anuncios/proximos
├── store/                        # Zustand stores (todos hidratados em _layout.tsx)
│   ├── authStore.ts              # session + JWT
│   ├── cartStore.ts              # carrinho persistente
│   ├── notificationStore.ts      # contador de não-lidas
│   ├── recentlyViewedStore.ts    # últimos 20 produtos vistos
│   └── geoStore.ts               # lat/lng/cidade/uf (MMKV "ibix_geo_location")
├── hooks/
│   ├── useTheme.tsx              # acesso ao tema (cores/spacing/typography)
│   ├── useDebounce.ts
│   ├── useNetworkStatus.ts
│   ├── useForceUpdate.ts         # bloqueia versões antigas (consulta /loja/app-version)
│   ├── useWebSocket.ts           # /ws/loja/consumidor (eventos em tempo real)
│   ├── useSocialAuth.ts          # Google + Apple + Facebook (encapsula o fluxo OAuth)
│   └── useGeo.ts                 # permissão de localização + reverse geocoding
├── theme/                        # tokens (cores, tipografia, spacing, shadows)
├── utils/                        # format.ts, storage.ts, validators.ts, sentry.ts
├── constants/config.ts           # ENV, QUERY_KEYS, STORAGE_KEYS, PAGINATION
├── assets/                       # fonts (Inter), images (ícone, splash), animations (Lottie)
├── app.json                      # config Expo (plugins, infoPlist, intentFilters)
├── eas.json                      # perfis de build (development, preview, production)
├── package.json
└── tsconfig.json
```

---

## 6. Identidade visual (Design System)

> **Fonte única de verdade:** `theme/colors.ts`, `theme/typography.ts`, `theme/spacing.ts`, `theme/shadows.ts`. **Não hardcode cores, tamanhos ou fontes em telas/componentes** — sempre use `useTheme()`.

### 6.1 Paleta principal

| Token | Hex | Uso |
|-------|-----|-----|
| **`primary`** (Azul Ibix) | `#2980b9` | Botões CTA, links, destaque, status bar dark, ícone do app |
| `primaryDark` | `#1a5276` | Botões pressionados, splash screen background |
| `primaryLight` | `#5dade2` | Hover/focus, dark mode primary |
| `primarySurface` | `#eaf2f8` | Backgrounds suaves de bloco "informativo" |
| **`secondary` / `success`** | `#27ae60` | Confirmações, "Pago", "Entregue" |
| `secondarySurface` | `#e8f8f0` | Background de banners de sucesso |
| **`accent` / `error`** | `#e74c3c` | Promoções (-X% OFF), erros, "Cancelar" |
| `accentSurface` | `#fdedec` | Fundo de mensagens de erro suaves |
| **`warning`** | `#f39c12` | Alertas, "Pendente", "Aguardando pagamento" |
| `warningSurface` | `#fef9e7` | Fundo de avisos |

### 6.2 Neutros e estados

| Token | Light | Dark | Uso |
|-------|-------|------|-----|
| `background` | `#f5f5f5` | `#121212` | Fundo da tela |
| `surface` | `#ffffff` | `#1e1e1e` | Cards, sheets, inputs |
| `surfaceVariant` | `#fafafa` | `#2c2c2c` | Chips, faixas alternadas |
| `textPrimary` | `#212121` | `#e0e0e0` | Texto principal |
| `textSecondary` | `#757575` | `#a0a0a0` | Texto auxiliar |
| `textDisabled` | `#bdbdbd` | `#666666` | Placeholders, desabilitado |
| `textInverse` | `#ffffff` | `#212121` | Texto sobre cor primária |
| `textLink` | `#2980b9` | (igual primary) | Links inline |
| `border` | `#e0e0e0` | `#333333` | Bordas de inputs/cards |
| `divider` | `#eeeeee` | `#2a2a2a` | Separadores horizontais |
| `overlay` | `rgba(0,0,0,0.5)` | `rgba(0,0,0,0.7)` | Backdrop de modais |

> **Status PIX:** `warning` (pendente) → `success` (pago) → `error` (recusado/expirado).
> **Tab bar:** ativo `primary`, inativo `gray500`.

### 6.3 Tipografia (família **Inter**, em `assets/fonts/`)

| Variante | Peso/Tamanho | Uso |
|----------|--------------|-----|
| `h1` | Bold 36 / 44 | Tela "ops, deu erro", onboarding |
| `h2` | Bold 30 / 38 | Headers de fluxos críticos (checkout) |
| `h3` | Bold 24 / 32 | Títulos de tela ("Ibix Market", "Meus Pedidos") |
| `h4` | SemiBold 20 / 28 | Seções, modais |
| `subtitle1` | SemiBold 17 / 24 | Nome de produto, item de menu |
| `subtitle2` | Medium 15 / 22 | Subtítulos secundários |
| `body1` | Regular 15 / 22 | Texto corrido |
| `body2` | Regular 13 / 18 | Descrições, captions de UI |
| `button` | SemiBold 15 / 22 | Texto de botões |
| `caption` | Regular 11 / 16 | Microtexto, status, badges |
| `overline` | Medium 11 / 16 (UPPERCASE letter-spacing 1.2) | Etiquetas |
| `price` | Bold 20 / 28 | Preço grande no PDP |
| `priceSmall` | SemiBold 15 / 22 | Preço em listagens |
| `priceStrike` | Regular 13 / 18 (line-through) | Preço cheio riscado |

### 6.4 Spacing (escala de 4px)

```
2xs=2 · xs=4 · sm=8 · md=12 · lg=16 · xl=20 · 2xl=24 · 3xl=32 · 4xl=40 · 5xl=48 · 6xl=64
```

Padding padrão de tela: `paddingHorizontal: spacing.lg` (16px). Gap entre cards de produto: `spacing.sm` (8px).

### 6.5 Border radius

```
sm=4 · md=8 · lg=12 · xl=16 · 2xl=20 · full=999 (pílula)
```

- Cards de produto: `lg` (12)
- Bottom sheets: `2xl` (20) no topo
- Chips e tags: `full`
- Botões grandes: `lg`; botões pequenos: `md`

### 6.6 Ícones

`components/ui/Icon.tsx` é um **SVG inline** (paths em `PATHS`). Para adicionar um ícone novo, edite `PATHS` (não use libs externas como `lucide-react-native` para manter o bundle pequeno e visual consistente).

Tamanhos padrão: `iconSize = { xs:16, sm:20, md:24, lg:28, xl:32 }`.

### 6.7 Sombras

Use `shadow('sm' | 'md' | 'lg')` do tema. **Não escreva sombra inline** — perde paridade entre iOS e Android.

### 6.8 Splash e ícones do app

- Splash background: `#2980b9` (primary)
- Ícone do app: `assets/images/icon.png` (1024×1024 com fundo)
- Adaptive icon Android: `assets/images/adaptive-icon.png` + background `#2980b9`
- Notification icon: `assets/images/notification-icon.png` + tint `#2980b9`

---

## 7. Backend consumido (resumo)

> **Regra de ouro:** o backend é a **fonte única da verdade**. O app **não duplica regras**, **não cria fallbacks**, **não hardcoda preços/parcelas/marketing/cupons**.

Endpoints principais (todos sob `EXPO_PUBLIC_API_BASE_URL`, ex.: `http://10.0.2.2:8000/api/v1`):

### Auth e dispositivo
- `POST /loja/login`, `POST /loja/cadastro`
- `POST /loja/refresh-token` ← usado pelo interceptor do `api.ts`
- `POST /loja/auth/social/login` (Google), `POST /loja/auth/social/apple`, `POST /loja/auth/social/config`
- `POST /loja/forgot-password`, `POST /loja/redefinir-senha`
- `GET /loja/app-version` (force update)
- `POST/DELETE /loja/push-token`

### Catálogo
- `GET /loja/anuncios` (lista/busca, cursor-based)
- `GET /loja/anuncios/{id}` (detalhe + `parcelas[]` + `favorito`)
- `GET /loja/anuncios/{id}/avaliacoes`, `GET /loja/anuncios/{id}/semelhantes`
- `GET /loja/categorias`, `GET /loja/lojas`, `GET /loja/{slug}`
- `GET /loja/busca/autocomplete`, `GET /loja/busca/populares`
- `GET /loja/parcelamento?valor=...` (simula 1x–12x com config do gateway)

### Geo (Perto de você)
- `GET /loja/geo/cidades`, `GET /loja/geo/cidade-proxima`, `GET /loja/geo/reverso`
- `GET /loja/anuncios/perto-de-voce` ← carrossel da home
- `GET /loja/anuncios/proximos?q=...` ← faixa pós-busca

### Conta
- `GET/PATCH /loja/minha-conta`
- `GET/POST/PATCH/DELETE /loja/minha-conta/enderecos`
- `GET /loja/meus-pedidos`, `GET /loja/pedido/meu?numero=...`, `GET /loja/pedido/consultar?numero&email`

### Checkout
- `POST /loja/checkout` (loja única) e `POST /loja/checkout-unificado` (multi-loja)
- `GET /loja/{loja_id}/frete?cep=...`
- `POST /loja/pedidos/{id}/nova-tentativa-pagamento`

### Pós-venda
- `POST /loja/pedidos/{id}/cancelar`, `POST /loja/pedidos/{id}/avaliar`, `POST /loja/pedidos/{id}/devolucao`
- `GET /loja/conversas`, `POST /loja/conversas`, `GET/POST /loja/conversas/{id}/mensagens`, `PATCH /loja/conversas/{id}/lida`

### Marketing e cupons
- `GET /marketing-vitrine/vitrine-home` (banners, destaques, ofertas da semana)
- `POST /loja/cupons/validar`, `GET /loja/cupons/disponiveis`

### LGPD
- `GET /loja/minha-conta/dados-exportar`
- `POST /loja/minha-conta/excluir-conta`
- `GET/PATCH /loja/minha-conta/consentimentos`

### WebSocket
- `WS /ws/loja/consumidor?token=<jwt>` — eventos: `pedido.status_atualizado`, `pagamento.confirmado`, `mensagem.nova`, `notificacao.nova`

> Tudo isso já está mapeado em `services/*.ts`. **Não chame `axios` direto em telas — sempre passe por um service.**

---

## 8. Regras de ouro (para a IA seguir)

Estas regras vêm de `../.cursor/skills/saas-golden-rules/SKILL.md` (multi-tenant SaaS) e do `MAPA_DE_REGRAS.md`. **Sempre respeitar:**

1. **Sem fallback silencioso.** Dado obrigatório ausente → erro explícito (toast com `extractApiError(err)`), nunca substituir por valor inventado. Ex.: se `/loja/parcelamento` falhar, o `InstallmentPicker` mostra estado de erro, **não** "1x sem juros".
2. **Sem dados hardcoded.** Categorias, produtos, preços, parcelas, status, motivos de cancelamento, banners, cupons — tudo vem da API.
3. **Validade jurídica do pagamento.** Confirmação só quando `status_pagamento === "pago"`. Sem exceção. Polling em `confirmacao.tsx` deve seguir esse contrato.
4. **Multi-tenant via JWT.** O token (`loja_consumidor_token`) carrega o consumidor. **Nunca** envie `tenant_id`/`loja_id` "do front" para autenticação ou listagens privadas.
5. **Segurança.**
   - JWT em **`expo-secure-store`** (criptografado), nunca `AsyncStorage` plano nem MMKV.
   - HTTPS obrigatório em produção (configurado em `eas.json`).
   - `ENABLE_CERTIFICATE_PINNING` = `!__DEV__` (já em `constants/config.ts`).
   - Dados de cartão **nunca** trafegam pelo app — sempre redirect para o gateway (Mercado Pago / PagBank).
6. **LGPD/CDC.**
   - Consentimento explícito no cadastro (`aceite_politica_privacidade` no checkout obrigatório).
   - Botões de exportar/excluir conta sempre acessíveis em `(tabs)/perfil.tsx`.
   - Direito de arrependimento de 7 dias informado nas devoluções.
7. **i18n e moeda.** Português Brasil, **`pt-BR`**, BRL. Use `formatCurrency` de `utils/format.ts`. **Nunca** componha `R$ ${valor}` manualmente.
8. **Acessibilidade.** Sempre passe `accessibilityLabel` em `TouchableOpacity` e ícones interativos. Hit-slop mínimo 8 (`hitSlop` do tema). Contraste AA.
9. **Performance.**
   - Listas longas → `FlashList` ou `FlatList` com `keyExtractor` correto.
   - Imagens → `expo-image` com `recyclingKey` e `transition`.
   - Funções de render em `useCallback`/`useMemo` quando passadas para componentes filhos.
10. **Testes manuais antes de commit.** Sempre verificar pelo menos 1 fluxo Android (emulador ou device) e, se em macOS, 1 iOS.

### Padrões de código
- TypeScript estrito (`tsc --noEmit` deve passar).
- **Zero comentários óbvios** ("// importa o módulo"). Comente apenas trade-offs e regras de negócio.
- Novos componentes: PascalCase em arquivo individual (`ProductCard.tsx`), e re-exportados em `components/<grupo>/index.ts`.
- Hooks: prefixo `use` (`useGeo`, `useSocialAuth`).
- Imports absolutos via alias `@/*` (configurado em `tsconfig.json`).

---

## 9. Variáveis de ambiente

Edite **`.env`** (não versionado). Modelo completo em `.env.example`:

| Variável | Obrigatória | Quando | Exemplo |
|----------|-------------|--------|---------|
| `EXPO_PUBLIC_API_BASE_URL` | sim | sempre | `http://10.0.2.2:8000/api/v1` |
| `EXPO_PUBLIC_WS_BASE_URL` | sim | chat/notif tempo real | `ws://10.0.2.2:8000` |
| `EXPO_PUBLIC_SENTRY_DSN` | não | crashes em produção | `https://...@sentry.io/...` |
| `EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID` | sim para login Google | dev e prod | `xxxx.apps.googleusercontent.com` |
| `EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID` | iOS | iOS | idem |
| `EXPO_PUBLIC_GOOGLE_ANDROID_CLIENT_ID` | Android | Android | idem |

> Para staging/produção, as URLs já vêm de `eas.json` (perfis `preview` e `production`). **Não duplique** essas URLs no `.env` ao buildar com EAS.

---

## 10. Comandos úteis

```bash
# Desenvolvimento
npx expo start                   # menu interativo
npx expo start --android         # abre direto no Android
npx expo start --ios             # macOS only
npx expo start --web             # navegador
npx expo start --clear           # limpa cache do Metro

# Sanidade
npm run typecheck                # tsc --noEmit
npm run lint                     # eslint
npx expo install --fix           # alinha versões com SDK

# Builds (EAS)
npx eas login
npx eas build --platform android --profile development     # APK dev
npx eas build --platform android --profile preview         # APK staging interno
npx eas build --platform all --profile production          # AAB iOS+Android

# OTA updates (depois do init)
npx eas update --branch production --message "fix Y"

# Submissão automática
npx eas submit --platform ios
npx eas submit --platform android
```

---

## 11. Como testar features-chave

| Feature | Como validar local |
|---------|--------------------|
| **Login social** | Configure os `GOOGLE_*_CLIENT_ID` no `.env`. Apple Sign-In requer iOS real ou simulador macOS. Facebook precisa de App ID no Facebook Developers. |
| **Push** | Use device físico ou Android Emulator com Google APIs. Em Expo Go funciona com `ExpoPushToken`. |
| **Geo "Perto de você"** | Emulador Android: *Extended Controls → Location*. iOS Simulator: *Features → Location → Custom*. |
| **PIX** | Backend em sandbox Mercado Pago. App copia BR Code via `expo-clipboard` e exibe QR via `react-native-qrcode-svg`. |
| **WebSocket** | Faça um pedido com `payment_method: pix`, abra `confirmacao.tsx`, e dispare `confirmar` no painel da loja → status muda em tempo real. |
| **Force update** | Subir versão mínima > `1.0.0` na tabela `app_versao_config` → `useForceUpdate()` bloqueia o app. |

---

## 12. Quando a IA Cursor for editar este projeto

**Prioridade:**

1. **Leia primeiro** `MAPA_DE_API.md` (endpoints disponíveis), depois o `MAPA_DO_SISTEMA.md` (regras), depois este AGENTS.md.
2. Antes de criar um endpoint novo, **verifique se já existe** em `services/*.ts`. Se existir, reuse — não duplique.
3. Antes de hardcodar texto/preço/cor, **veja se existe token** em `theme/` ou em `constants/config.ts`.
4. Antes de criar um componente, **veja `components/ui/`** — provavelmente já existe (`Button`, `Card`, `EmptyState`, `Skeleton`, `Toast`, ...).
5. Sempre que adicionar uma nova rota/feature, atualize o `Stack.Screen` em `app/_layout.tsx` e este AGENTS.md (seção de estrutura).
6. Após mudanças, rode mentalmente: `npm run typecheck` + ver se algo precisa de `npx expo install --fix`.
7. **Atualize a documentação macro** (`../MAPA_SISTEMA/PLANO_APP_MOBILE_MARKETPLACE.md` e `../MAPA_SISTEMA/MAPA_DO_SISTEMA.md`) quando adicionar um endpoint novo, mudar contrato ou criar tela importante.

**Não faça:**
- Não rode `npm install <pacote>@latest` cegamente — Expo SDK 52 fixa versões. Use `npx expo install <pacote>`.
- Não mexa em `package-lock.json` manualmente.
- Não comite `.env`, `google-services.json`, `GoogleService-Info.plist`, certificados, secrets.
- Não crie um novo `axios` em outro lugar — use o `api` exportado por `services/api.ts`.

---

## 13. Referências cruzadas

- **Repositórios GitHub (monorepo vs app só-mobile):** `../MAPA_SISTEMA/REPOSITORIOS_GITHUB.md`
- **Plano completo do app:** `../MAPA_SISTEMA/PLANO_APP_MOBILE_MARKETPLACE.md`
- **Sistema completo (PDV + marketplace):** `../MAPA_SISTEMA/MAPA_DO_SISTEMA.md`
- **APIs do backend:** `../MAPA_SISTEMA/MAPA_DE_API.md`
- **Regras de negócio (golden rules):** `../MAPA_SISTEMA/MAPA_DE_REGRAS.md`
- **RBAC e tenants:** `../MAPA_SISTEMA/MAPA_RBAC.md`
- **Pagamento:** `../MAPA_SISTEMA/MAPA_PAGAMENTO.md`
- **Frete e geo:** `../MAPA_SISTEMA/MAPA_Frete_Transporte.md`

---

**Última atualização:** 2026-04-27
**Maintainer:** Time PDV Ibix
**Bug reports / sugestões:** preferencialmente no monorepo remoto `ibix_market` (ver `REPOSITORIOS_GITHUB.md`); app mobile espelhado em `IBIX_mobile`.
