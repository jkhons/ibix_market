# ERRO_TO_Progamer — relatório do testador para o programador

> **Quem edita:** apenas o **PC Windows (testador)** e a **IA no papel de testador**.  
> **Quem corrige o código:** **programador na VPS** (ou fluxo acordado pela equipe); após correção, publicar no GitHub (`origin/main`).  
> **Padronizações e contexto do produto:** ver **`AGENTS.md`** e checklist de ambiente em **`ALINHAR_OUTRO_PC.md`**.

---

## Ciclo oficial

1. Testador: `git pull origin main` → executar testes → registrar falhas **neste arquivo**.
2. Testador: envia **este arquivo** (ou trechos) ao programador pelo **canal acordado** — no PC tester não há obrigatoriedade de `git push` (`TESTER_WINDOWS_DIRETRIZ.md`).
3. Programador: lê este arquivo → corrige na VPS → `git push` para o GitHub.
4. Testador: `git pull` novamente → retestar → atualizar este arquivo (resolver / novos IDs).

---

## Versão sob teste (preencher sempre antes de reportar)

| Campo | Valor |
|--------|--------|
| **Commit testado** | **`6a1362e`** — proxy Metro IPv4-first; `SETUP.md`/502; `catalogService` `icone`→`icone_url` |
| **Data / hora** | 2026-05-05 (atualizado — Web LAN + 502 proxy) |
| **Plataforma** | Windows — Expo Web **`http://192.168.0.7:8082`** (porta **8082**), `.env` típico API HTTPS pública; pedidos passam por **`/__ibix_api/`** (Metro → `EXPO_PUBLIC_API_BASE_URL`) |
| **Node** | 18 ou 20 LTS (preferência projeto) |

---

## Erros abertos (fila para o programador)

_Use uma linha por erro; o programador marca como resolvido mudando o status ou movendo para a seção “Resolvidos”._

| ID | Severidade | Tela / fluxo | Passos para reproduzir | Comportamento esperado | Comportamento atual | Evidência (link print / log) | Status |
|----|------------|--------------|------------------------|------------------------|---------------------|------------------------------|--------|
| E003 | **crítica** | Web dev — **todo** o app (home, categorias, produtos, geo, marketing, versão) | 1. `expo start --web` → abrir **192.168.0.7:8082**. 2. DevTools → **Network**. | `GET .../__ibix_api/api/v1/...` → **200** + JSON. | **502 Bad Gateway** em série (`.../loja/categorias`, `.../anuncios`, `.../marketing-vitrine/vitrine-home`, `.../geo/cidades`, `.../app-version/android`, …). Sem dados ⇒ sem fotos. | Console browser; terminal Expo `[__ibix_api proxy]`; § **E003** | aberto |
| E002 | **alta** | Home, listagens, PDP, banners — Web | *(depois de API estável — ver § E003)* F12 → Img / URLs `static`. | Imagens carregam (`expo-image`). | Sem foto / cinza; ou **404** em `/static/uploads/...` no host público. | § **E002** (checklist DevTools + infra) | aberto |

### Detalhe adicional (opcional — um bloco por ID)

#### E003 — 502 em massa no proxy Web `/__ibix_api/` (bloqueia API e imagens)

- **Fluxo:** em Web dev, `API_BASE_URL` é `/__ibix_api/api/v1`; o **Metro** faz proxy para `EXPO_PUBLIC_API_BASE_URL` ([`SETUP.md`](SETUP.md), [`metro.config.js`](metro.config.js)).

- **Ordem de diagnóstico:**

  1. **Corpo da resposta 502 no DevTools:** se for JSON `detail: "Proxy error"` → Metro **não ligou** ao upstream (`ECONNREFUSED`, DNS, TLS…). Conferir `.env` (ex.: `127.0.0.1:8000` sem uvicorn local); **`npx expo start --clear`** após alterar `.env`.

  2. **Corpo HTML (nginx) ou 502 sem JSON do Metro:** o upstream **respondeu** 502. Teste na máquina do Expo:  
     `curl -sS -o /dev/null -w "%{http_code}\n" "https://www.ibix.com.br/api/v1/loja/categorias"`  
     Se **502** → **VPS/backend/nginx** (serviço, upstream, carga); não é corrigível só no repo mobile até a API voltar **200**.

- **Reteste:** quando `curl` acima for **200** (ou 401 em rota protegida, mas não 502), recarregar Web — lista e URLs de imagem voltam a fluir; aí validar **E002** se ainda houver 404 em `/static/...`.

---

#### E002 — Fotos de produto (e banners) não carregam no Web — diagnóstico consolidado

**Ordem:** tratar **E003** primeiro — sem JSON da API não há `imagens` para mostrar.

**Objetivo para o programador:** discriminar falha de **infra/url estática** vs **app** vs **API indisponível**.

---

**1) Comportamento esperado no app**

- A API devolve `imagens` como paths **relativos**, ex.: `/static/uploads/produtos/...`.
- O app usa **`resolveRemoteAssetUrl`** (`constants/config.ts`): concatena **`PUBLIC_SITE_ORIGIN`** (derivado de `EXPO_PUBLIC_API_BASE_URL`) + path.
- Exemplo: `EXPO_PUBLIC_API_BASE_URL=https://www.ibix.com.br/api/v1` → `PUBLIC_SITE_ORIGIN=https://www.ibix.com.br` → URL final `https://www.ibix.com.br/static/uploads/...`.
- Componentes: **`ProductCard`**, **`BannerCarousel`**, **`NearbyAdsCarousel`**, PDP **`app/produto/[id].tsx`**, etc.

---

**2) Evidência no browser (DevTools)**

1. **Network** → pedidos **XHR/fetch** primeiro: confirmar que **`/__ibix_api/...` não está em 502** (senão é **E003**).
2. Filtro **Img** (ou `static`, `.webp`, `.jpg`): URL completa + código (404, 403, CORS, falhou rede).
3. Abrir URL da imagem noutro separador — se não carrega → **origem/servidor**, não só React.

---

**3) Sintoma ↔ causa provável**

| Rede / sintoma | Causa provável |
|----------------|----------------|
| **`/__ibix_api/...` com 502** | Proxy Metro ou **Ibix a devolver 502** — ver **§ E003**. |
| `https://www.ibix.com.br/static/...` com **404** ou **403** | **`/static`** ou disco de uploads mal exposto no host público (nginx/CDN). |
| Cartão **“Sem foto”** | Array `imagens` vazio na API (dados). |
| API num domínio, assets noutro | Avaliar **`EXPO_PUBLIC_ASSET_ORIGIN`** (`constants/config.ts`). |

---

**4) Testes já referidos pelo testador**

- Em sessões anteriores: **HEAD** a exemplos `https://www.ibix.com.br/static/uploads/produtos/.../** → **404**.
- Em verificação pontual: endpoint público de anúncios/categorias também pode responder **502 (nginx)** — reforça prioridade **E003** / infra.

---

**5) Ações sugeridas ao programador (VPS)**

- Estabilizar API pública (sem **502** em `/api/v1/loja/...`).
- Confirmar nginx/FastAPI/`StaticFiles` e URL canónica dos uploads.
- Se assets forem noutro host, documentar **`EXPO_PUBLIC_ASSET_ORIGIN`** no `.env.example` / [`SETUP.md`](SETUP.md).

---

**6) Reteste E002**

1. API **200** nos endpoints usados pelo app.
2. Repetir §2; esperado **200** nos GET das imagens nos cartões.

---

## Resolvidos (histórico recente)

_Mover para cá após confirmação em `origin/main` + reteste. Manter últimas ~10 entradas._

| ID | Commit da correção | Confirmado pelo tester em |
|----|---------------------|---------------------------|
| E001 | **`d012cee`** — `hooks/useSocialAuth.ts`: `Google.useIdTokenAuthRequest` em todo render (IDs placeholder até os reais); corrige Rules of Hooks no Web quando `configQuery` populava o client id. | _testador: preencher após `git pull` + retestar login Web_ |

---

## Lembrete (alinhado ao `AGENTS.md`)

- Teste válido = código que está em **`origin/main`** (sempre puxar antes).
- Feedback deve vir com **evidência**: prints + passos + logs quando aplicável.
