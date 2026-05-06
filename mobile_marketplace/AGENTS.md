# AGENTS.md — Ibix Market (App Mobile Marketplace)

> Arquivo de contexto persistente para a **IA Cursor** e desenvolvedores que clonarem este diretório.
> **Leia este arquivo antes de qualquer alteração** — ele define stack, padrões, identidade visual, regras de negócio e o backend que o app consome.

---

## 1. O que é este projeto

App **React Native (Expo SDK 52)** para o consumidor final do **Ibix Marketplace**. O backend é **FastAPI (Python)** em `../app/` na **mesma VPS** (cópia de trabalho — **sem** repositório Git próprio para o PDV), expondo `/api/v1/loja/*` e `/api/v1/marketing-vitrine/*`.

- **Plataformas:** iOS, Android, Web (PWA leve)
- **Display name nas lojas (App Store / Play Store / springboard):** **`Ibix`** (curto, marca-mãe — `expo.name` no `app.json`)
- **Brand visível dentro do app e na vitrine pública:** **`Ibix Market`** (logo `cab.png` no header via `<BrandLogo>`)
- **Bundle/Package:** `com.ibix.market` (não muda)
- **Scheme:** `ibixmarket://` (deep links)
- **Domínio universal:** `https://www.ibix.com.br/loja/...` (universal/applinks)

> **Por que dois nomes?** Nas lojas o "Ibix" curto reforça a marca-mãe e cabe no espaço limitado do springboard. Dentro do app o usuário vê "Ibix Market" como produto, em paridade total com o `<title>` da vitrine (`{block} | Ibix`) e com o logo `cab.png`.

Documentação macro vive em `../MAPA_SISTEMA/PLANO_APP_MOBILE_MARKETPLACE.md` (plano por fases) e `../MAPA_SISTEMA/MAPA_DO_SISTEMA.md` (sistema completo).

### 1.1 Fluxo oficial de trabalho (método definitivo)

| Etapa | Onde | O quê |
|-------|------|--------|
| Desenvolvimento | **VPS** | Alterações em `mobile_marketplace/` e no backend em `../app/` (PDV **sem** repo Git remoto). |
| Publicar código Expo | **VPS** → **GitHub** | Pasta **`mobile_marketplace/`** é o **único** directório com Git; **`git pull` / `git push`** sempre **lá dentro**. Ver [`PUBLICAR_IBIX_MOBILE.md`](PUBLICAR_IBIX_MOBILE.md). |
| **Pull** e testes | **PC Windows** (clone **`IBIX_mobile`**) | `git pull origin main` e validação com Expo. |

**DIRETRIZ (obrigatória): UMA ÚNICA CÉLULA de desenvolvimento = VPS.** O PC Windows é **tester** e só valida o que está em **`IBIX_mobile`** no GitHub (`origin/main` **desse** clone).

- **Proibido hotfix no PC tester:** não corrigir “por fora” no Windows sem subir para o Git.
- **Teste válido = commit publicado:** o tester sempre faz `git pull origin main` no clone **`IBIX_mobile`** antes de validar.
- **Feedback do tester tem que vir com evidência:** print + passos + log de rede/console quando aplicável.

Pormenores (clone, SSH, credenciais, checklist): **`ALINHAR_OUTRO_PC.md`**.

---

## 2. Pré-requisitos para rodar localmente

Quando você (IA ou humano) **clonar este projeto na máquina local** (Windows/Linux/macOS):

| Ferramenta | Versão mínima | Instalação |
|------------|---------------|------------|
| Node.js | **20 LTS** (ou 18 LTS) | https://nodejs.org |
| npm | 9+ (vem com Node) | — |
| Git | qualquer recente | — |
| Expo Go (no celular) | App da App Store / Play Store | iPhone/Android |
| Android Studio (opcional) | Hedgehog+ | Para emulador Android |
| Xcode (apenas macOS) | 15+ | Para simulador iOS |
| Cursor IDE | atual | Edição com IA |

> **Não precisa instalar `expo-cli` global.** Use `npx expo` (vem com o pacote `expo`).

> **Diretriz do tester (obrigatória):** não usar Node 22 no PC de testes. Expo SDK 52 + Metro pode ficar “pendurado” no bundling.
> Padronize o PC tester com **Node 20 LTS** (preferível) ou **Node 18 LTS**.

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

> **Web dev e HTTP 502:** no navegador, as requisições passam pelo proxy `/__ibix_api/` do Metro. Um **502** quase sempre significa que o FastAPI não está acessível em `EXPO_PUBLIC_API_BASE_URL` ou o Metro não foi reiniciado após mudar o `.env`. Passo a passo: secção *Erro 502 em `/__ibix_api`* em [`SETUP.md`](SETUP.md).

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

> **REGRA OBRIGATÓRIA — paridade total com a vitrine web.** Fonte canônica é `app/static/css/loja.css` (tokens `--ibix-*`) e `app/static/img/ibix/cab.png` (logo). O app **espelha** a vitrine: mudanças visuais começam pela vitrine; o app segue. Brand assets são copiados bit-a-bit, NUNCA recriados.
>
> **Fonte única de verdade no código:** `theme/colors.ts`, `theme/typography.ts`, `theme/spacing.ts`, `theme/shadows.ts`. **Não hardcode cores, tamanhos ou fontes em telas/componentes** — sempre use `useTheme()`.

### 6.1 Paleta principal (espelho de `loja.css:9-18`)

| Token | Hex | Uso |
|-------|-----|-----|
| **`primary`** (verde-musgo `--ibix-action`) | `#5C6E4A` | Botões CTA, links de ação, "Pago", "Entregue", ícone do app |
| `primaryDark` (`--ibix-action-hover`) | `#4E5F40` | Botões pressionados |
| `primaryLight` | `#D9B48B` | Hover/focus suave (dourado) |
| `primarySurface` | `#E6EDDF` | Backgrounds suaves de "Pago"/"Sucesso" |
| **`accent`** (terracota `--ibix-hover`) | `#C47A44` | Hover, ativo, destaque, **focus-ring**, links inline |
| `accentDark` | `#B16A38` | Pressed do accent |
| `accentSurface` | `#FBE6DD` | Fundo de erros suaves |
| **`premium`** (`--ibix-premium`) | `#D9B48B` | Detalhes mínimos (dourado suave) |
| **`warning`** | `#C47A44` | Alertas, "Pendente", "Aguardando pagamento" (mesmo terracota) |
| `warningSurface` | `#FBEDD9` | Fundo de avisos |
| **`success`** | `#5C6E4A` | Mesmo verde-musgo do `primary` |
| **`error`** | `#B5453A` | Erros, "Cancelar" |

### 6.2 Neutros e estados

| Token | Light | Dark | Uso |
|-------|-------|------|-----|
| `background` (`--ibix-bg`) | `#FEF7F1` | `#1B1F22` | Fundo da tela (off-white) |
| `surface` | `#FFFFFF` | `#262B30` | Cards, sheets, inputs |
| `surfaceVariant` | `#F5EDE3` | `#30363B` | Chips, faixas alternadas |
| `textPrimary` (`--ibix-text-strong`) | `#2F3A44` | `#ECE4D9` | Headings (azul-ardósia escuro) |
| `textSecondary` (`--ibix-text`) | `#4A627A` | `#C7C0B5` | Texto base (azul-ardósia) |
| `textSoft` | `#3B5166` | `#A9A296` | Variante intermediária |
| `textDisabled` | `rgba(47,58,68,0.45)` | `rgba(236,228,217,0.45)` | Desabilitado |
| `textInverse` | `#FFFFFF` | `#2F3A44` | Texto sobre `primary` |
| `textLink` | `#C47A44` | `#D9B48B` | Links inline (terracota) |
| `border` (`--ibix-border`) | `rgba(47,58,68,0.14)` | `rgba(236,228,217,0.16)` | Bordas |
| `divider` | `rgba(47,58,68,0.08)` | `rgba(236,228,217,0.10)` | Separadores |
| `overlay` | `rgba(47,58,68,0.55)` | `rgba(0,0,0,0.65)` | Backdrop |
| `focusRing` | `#C47A44` | `#D9B48B` | Outline accessível (paridade `loja-header *:focus-visible`) |

> **Status PIX:** `warning` (pendente) → `success` (pago) → `error` (recusado/expirado).
> **Tab bar:** ativo `primary` (verde-musgo), inativo `textSecondary`.

### 6.3 Tipografia: **Poppins** (paridade com `loja.css:1394`)

Carregada via `@expo-google-fonts/poppins` em `_layout.tsx` (sem arquivos físicos em `assets/fonts/`).

| Variante | Peso/Tamanho | Uso |
|----------|--------------|-----|
| `h1` | Bold 36 / 44 | Tela "ops, deu erro", onboarding |
| `h2` | Bold 30 / 38 | Headers de fluxos críticos (checkout) |
| `h3` | Bold 24 / 32 | Títulos de tela ("Meus Pedidos", "Carrinho") |
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

### 6.5 Border radius (paridade com `loja.css`)

```
sm=8 · md=10 · lg=14 · xl=18 · 2xl=22 · full=999 (pílula)
```

- **`sm` (8)** → botões e chips (`btn-primary`, `loja.css:79`)
- **`md` (10)** → inputs e search bar (`loja-search-form`, `loja.css:137`)
- **`lg` (14)** → cards e blocos de seção (`loja-section-block`, `loja.css:175`)
- **`xl` (18)** → bottom sheets
- **`full`** → chips arredondados, badges

### 6.6 Focus-ring acessível (paridade com `loja.css:111-113`)

```
outline: 2px solid #C47A44; outline-offset: 2px
```

No app: token `focusRing = { width: 2, offset: 2 }` + `colors.focusRing` aplicado em `Pressable`/`TouchableOpacity` no estado `accessibilityState.focused` ou `pressed`.

### 6.7 Ícones

`components/ui/Icon.tsx` é um **SVG inline** (paths em `PATHS`). Para adicionar um ícone novo, edite `PATHS` (não use libs externas como `lucide-react-native` para manter o bundle pequeno e visual consistente).

Tamanhos padrão: `iconSize = { xs:16, sm:20, md:24, lg:28, xl:32 }`.

### 6.8 Sombras (paridade com `loja.css`)

| Nível | Equivalente vitrine | Uso |
|-------|---------------------|-----|
| `shadow('sm')` | `--loja-shadow-sm` (`0 1px 3px rgba(0,0,0,0.06)`) | Cards de produto |
| `shadow('md')` | `--loja-shadow-block` (`0 4px 12px rgba(0,0,0,0.08)`) | Blocos de seção, bottom bars |
| `shadow('lg')` | `--loja-shadow-hero` (`0 8px 24px rgba(0,0,0,0.10)`) | Hero/destaques |

**Não escreva sombra inline** — perde paridade entre iOS e Android.

### 6.9 Brand assets — logo Ibix Market

Os logos vivem em `assets/brand/` e são **cópia bit-a-bit** da vitrine web:

| Arquivo | Origem (vitrine) | Uso |
|---------|------------------|-----|
| `cab.png` | `app/static/img/ibix/cab.png` | Logo do header (`<BrandLogo>`) |
| `rodape.png` | `app/static/img/ibix/rodape.png` | Variante para fundos escuros |
| `logoSfundo.png` | `app/static/img/landing/logoSfundo.png` | Logo institucional → fonte do `icon.png` |

**Como usar:** importe `<BrandLogo>` de `components/common/BrandLogo.tsx`. Esse é o ÚNICO ponto de renderização do logo. **Nunca** use texto "Ibix Market" como brand visível.

```tsx
import { BrandLogo } from '@/components/common/BrandLogo';
// no header:
<BrandLogo height={36} />
// em fundo escuro:
<BrandLogo height={28} variant="footer" />
```

**Quando a vitrine atualizar `cab.png`,** copiar o novo arquivo para `assets/brand/cab.png` no mesmo PR. Nunca edite o logo no Figma/PS local — sempre puxe da vitrine.

### 6.10 Splash e ícones do app

- **Splash background:** `#FEF7F1` (off-white, paridade com `theme-color` da vitrine — `base_loja.html:14`)
- **Splash image:** `assets/images/splash-icon.png` (gerado a partir de `cab.png`)
- **Ícone do app:** `assets/images/icon.png` (1024×1024, gerado a partir de `logoSfundo.png` sobre fundo `#FEF7F1`)
- **Adaptive icon Android:** foreground monocromático verde-musgo (`#5C6E4A`) sobre background `#FEF7F1` (configurado em `app.json`)
- **Notification icon Android:** silhueta branca em `notification-icon.png` (192×192) com tint `#5C6E4A` aplicado pelo plugin `expo-notifications`

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

### 8.1 Identidade visual = vitrine web (REGRA CRÍTICA)

O app DEVE seguir 100% a identidade visual da vitrine pública.

- **Fonte canônica de cores, tipografia e radii:** `app/static/css/loja.css` (tokens `--ibix-*`).
- **Fonte canônica do logo:** `app/static/img/ibix/cab.png` (header) e `app/static/img/landing/logoSfundo.png` (institucional).
- **Mudanças visuais começam pela vitrine.** O app NUNCA introduz uma cor, fonte ou logo que não exista na vitrine. Se algo precisa mudar visualmente, o time muda primeiro em `loja.css`/`base_loja.html`, e o app espelha em seguida.
- **Brand assets são copiados bit-a-bit** de `app/static/img/ibix/*` para `mobile_marketplace/assets/brand/`. NUNCA recriar o logo no Figma/PS local.
- **Logo nunca é texto.** O componente `<BrandLogo>` (`components/common/BrandLogo.tsx`) é o único ponto de renderização. Onde antes havia "Ibix Market" como texto (header da home, login), agora aparece o logo gráfico.
- **Display name nas lojas é `Ibix`** (curto). Brand visível dentro do app é `Ibix Market` (logo). Os dois coexistem por design — não tente unificar.
- **Painel admin (PDV) tem identidade própria** (azul institucional do `base.html`). Não misture as duas — o PDV é para lojistas, o app é para consumidor final.

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

- **Plano completo do app:** `../MAPA_SISTEMA/PLANO_APP_MOBILE_MARKETPLACE.md`
- **Sistema completo (PDV + marketplace):** `../MAPA_SISTEMA/MAPA_DO_SISTEMA.md`
- **APIs do backend:** `../MAPA_SISTEMA/MAPA_DE_API.md`
- **Regras de negócio (golden rules):** `../MAPA_SISTEMA/MAPA_DE_REGRAS.md`
- **RBAC e tenants:** `../MAPA_SISTEMA/MAPA_RBAC.md`
- **Pagamento:** `../MAPA_SISTEMA/MAPA_PAGAMENTO.md`
- **Frete e geo:** `../MAPA_SISTEMA/MAPA_Frete_Transporte.md`

---

**Última atualização:** 2026-04-27
**Maintainer:** Time Ibix Market  
**Bug reports / sugestões:** issues em [`github.com/jkhons/IBIX_mobile`](https://github.com/jkhons/IBIX_mobile).
