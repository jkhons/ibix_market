# Ibix Market — App Mobile Marketplace

## Pré-requisitos

- Node.js **>= 18**
- npm ou yarn
- Para builds na nuvem: `npm install -g eas-cli` (opcional em dev; use `npx eas`)
- Xcode (macOS) para iOS; Android Studio para emulador Android

## 1. Instalação

```bash
cd mobile_marketplace
cp .env.example .env
# Edite .env: em celular físico, use o IP do PC na rede, não 127.0.0.1
npm install
```

## 2. Fontes, ícones e licença

As fontes **Inter** (OFL) e os PNGs de ícone/splash/notificação já vêm no repositório em `assets/fonts/` e `assets/images/`. A licença da Inter está em `assets/fonts/Inter-LICENSE.txt`.

## 3. Executar (desenvolvimento)

Com o **backend** FastAPI acessível na URL definida em `EXPO_PUBLIC_API_BASE_URL` (padrão `http://127.0.0.1:8000/api/v1`):

```bash
npx expo start
```

- Pressione **a** (Android), **i** (iOS, só macOS) ou escaneie o QR com **Expo Go**.
- **Emulador Android:** o host do PC costuma ser `10.0.2.2` (ex.: `http://10.0.2.2:8000/api/v1` no `.env`).

## 4. Web (opcional)

```bash
npm run web
# ou: npx expo start --web
```

## 5. Typecheck e bundle de verificação

```bash
npm run typecheck
npx expo export --platform web
```

## 6. Build com EAS

```bash
eas build --platform android --profile development
eas build --platform all --profile production
```

- Na primeira vez com EAS, execute `eas login` e `eas init` (cria o projeto e permite **OTA updates** no futuro).
- Variáveis `EXPO_PUBLIC_*` de produção/staging vêm de `eas.json` nos perfis `production` e `preview`.

## Variáveis de ambiente (`.env`)

| Variável | Uso |
|----------|-----|
| `EXPO_PUBLIC_API_BASE_URL` | Base da API (ex.: `.../api/v1`) |
| `EXPO_PUBLIC_WS_BASE_URL` | WebSocket base |
| `EXPO_PUBLIC_SENTRY_DSN` | Opcional — crash reports |
| `EXPO_PUBLIC_GOOGLE_*_CLIENT_ID` | Login Google (tela de auth) |

O arquivo `.env` não é versionado (use `.env.example` como modelo).
