# Ibix Market — App Mobile Marketplace

Desenvolvimento e **`git push`** para o GitHub são feitos no ambiente principal da equipe; **`git pull`** e os **testes com Expo** (web / celular / emulador) costumam ocorrer noutro local — método oficial na secção **1.1** de [`AGENTS.md`](AGENTS.md), checklist do tester em [`ALINHAR_OUTRO_PC.md`](ALINHAR_OUTRO_PC.md).

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

### Erro 502 em `/__ibix_api` (web em desenvolvimento)

No navegador, em modo dev, a API é chamada via proxy no Metro sob o prefixo `/__ibix_api/` (mesmo host/porta do Expo, ex.: `http://192.168.x.x:8082/__ibix_api/api/v1/...`). O destino real é `EXPO_PUBLIC_API_BASE_URL` definido no `.env` ([`metro.config.js`](metro.config.js)).

**Importante:** abrir o app em `http://192.168.0.7:8082` só muda o host **do bundle**; quem precisa alcançar a API é o **processo Node do Metro na mesma máquina** onde corre `expo start`. Se o `.env` tiver `http://127.0.0.1:8000/api/v1`, tem de haver FastAPI **nessa máquina** na porta 8000 — caso contrário todos os pedidos (categorias, anúncios, fotos) falham com **502**.

1. **Resposta no DevTools (Network):** corpo JSON `{ "detail": "Proxy error", ... }` indica que o Metro não conseguiu conectar ao backend (ex.: `ECONNREFUSED` se o FastAPI não estiver rodando ou a porta estiver errada).
2. **Terminal do Expo:** em desenvolvimento (`NODE_ENV !== 'production'`), falhas do proxy são impressas como `[__ibix_api proxy] falha ao falar com o upstream:` seguidas da URL-alvo e da mensagem de erro.
3. **Teste rápido no shell** (na máquina onde roda o Expo), ajustando host/porta ao seu `.env`:

   ```bash
   curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/api/v1/loja/categorias
   ```

   Código **000** ou erro de conexão → o proxy também retornará 502. **401/200** → backend alcançável (401 é esperado em algumas rotas sem token).

4. Após alterar `.env`, **reinicie** o Metro (`npx expo start --clear`).

5. Rotas como `/loja/notificacoes` falham da mesma forma quando o upstream está inacessível; o problema é infraestrutura/proxy, não um bug isolado da tela.

**Opcional:** `EXPO_PUBLIC_DISABLE_WEB_PROXY=true` faz o web chamar a API direto pela URL do `.env`; exige CORS configurado no backend para o origin do dev.

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
