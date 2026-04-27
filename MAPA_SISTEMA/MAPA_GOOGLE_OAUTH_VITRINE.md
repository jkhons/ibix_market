# Google OAuth — Vitrine (/loja) — PDV Ibix

Documentação operacional para **login com Google** do consumidor na vitrine. **Não** confundir com **Google Custom Search** (busca de imagens no cadastro de produto), que usa **API Key** + `cx`, não OAuth.

## Variáveis de ambiente

| Variável | Obrigatório | Uso |
|----------|-------------|-----|
| `LOJA_OAUTH_GOOGLE_CLIENT_ID` | Sim, para login Google | Client ID OAuth (tipo **Aplicativo da Web**). |
| `LOJA_OAUTH_GOOGLE_CLIENT_SECRET` | Opcional no fluxo atual | **Não** é enviado ao navegador. Reservado para troca de token no servidor se o fluxo evoluir. Manter em `.env` só no servidor. |

Leitura em `app/core/config.py`. Exposição pública do **apenas** Client ID: `GET /api/v1/loja/auth/social/config` (`app/api/v1/loja.py`).

## Console Google Cloud (OAuth 2.0 — ID do cliente)

1. **APIs e serviços** → **Credenciais** → **Criar credenciais** → **ID do cliente OAuth** → tipo **Aplicativo da Web**.
2. **Origens JavaScript autorizadas** (sem path, sem curinga; porta explícita se não for 443):
   - `https://www.ibix.com.br`
   - `https://ibix.com.br` (se o site responder sem `www`)
   - Em desenvolvimento: `http://localhost:PORTA` (porta exata do navegador).
3. **URIs de redirecionamento autorizados** (protocolo obrigatório; sem fragmento `#`):
   - `https://www.ibix.com.br`
   - e/ou `https://www.ibix.com.br/loja/login` (e equivalentes sem `www` se aplicável).
4. Copiar **ID do cliente** e **Chave secreta do cliente** para o `.env` do servidor (`LOJA_OAUTH_GOOGLE_CLIENT_ID`, `LOJA_OAUTH_GOOGLE_CLIENT_SECRET`). **Não** commitar `.env`.

## Frontend (referência)

Fluxo atual: Google Identity Services (`initTokenClient`) em `app/static/js/loja-social-auth.js` — token no navegador; backend valida perfil com o access token.

## Segurança

- **Nunca** commitar chave secreta nem colar em documentação versionada.
- O **JSON** `client_secret_*.apps.googleusercontent.com.json` baixado no Console Google é o **mesmo par** OAuth (client_id + client_secret) — use só para copiar valores para o `.env` no servidor; **não** guardar esse arquivo no repositório (ver `.gitignore`: `client_secret*.json`).
- Se a secret vazar, **revogar** e gerar nova credencial no Google Cloud.
