# Repositórios GitHub — PDV Ibix / Ibix Market

Documentação única para não confundir **dois repositórios** com escopos diferentes. Ambientes podem usar SSH ou HTTPS.

## Pré-requisitos no servidor (VPS)

Os repositórios **`IBIX_mobile`** e **`ibix_market`** são privados ou exigem autenticação: sem **chave SSH** ([deploy keys](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/managing-deploy-keys)) ou token configurado, `git clone` / `git push` falham (`Permission denied (publickey)` ou prompts HTTPS).

Scripts na raiz do projeto (executar no VPS **depois** de configurar SSH para `github.com`):

- **GitHub → pasta local:** [`scripts/sync-mobile-from-github.sh`](../scripts/sync-mobile-from-github.sh)
- **Pasta local → GitHub (espelho mobile):** [`scripts/sync-mobile-to-github.sh`](../scripts/sync-mobile-to-github.sh)

Variáveis opcionais: `IBIX_MOBILE_SSH`, `IBIX_MOBILE_BRANCH`, `IBIX_MOBILE_PUSH_BRANCH`.

### Fingerprints SSH (duas coisas diferentes)

1. **Host key de `github.com` (servidor)** — aparece na primeira conexão SSH (`git clone`, `ssh -T git@github.com`). Deve bater **exatamente** com a lista oficial do GitHub: [SSH key fingerprints](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/githubs-ssh-key-fingerprints). Neste ambiente, `ssh-keyscan github.com` combinou com:

   | Algoritmo | SHA256 |
   |-----------|--------|
   | ED25519 | `+DiY3wvvV6TuJJhbpZisF/zLDA0zPMSvHdkr4UvCOqU` |
   | ECDSA | `p2QAMXNIC1TJYWeIOttrVc98/R1BUFWu3/LiyKgUfQM` |
   | RSA | `uNiVztksCsDhcc0u9e8BujQXVUpKZIDTMczCvj3tD2s` |

   Para fixar sem prompt interativo, use as linhas `github.com ssh-ed25519 …` (e opcionalmente ECDSA/RSA) da própria página oficial no `~/.ssh/known_hosts`.

2. **Fingerprint da *sua* chave (deploy key / conta)** — o GitHub mostra um SHA256 para cada chave **que você cadastrou**. Isso **não** é o mesmo que o fingerprint do host acima. Exemplo anotado pela equipe para o fluxo mobile: `SHA256:JaGjE4hLZJc0nFjv2LScAd/0FoABWfN5nCEA5fAChuk` — trate como identificador da **chave permitida no repo** `IBIX_mobile`; confira no GitHub em **Settings → Deploy keys** ou **SSH keys** se bate com a chave `.pub` local (`ssh-keygen -lf ~/.ssh/sua_chave.pub`).

Se ao conectar em **`github.com`** aparecer um SHA256 que **não** está na tabela oficial do item 1, **não aceite** até investigar (host errado, typo ou interceptação).

## Tabela de referência

| Repositório | HTTPS | SSH | Escopo no disco |
|-------------|-------|-----|-----------------|
| **IBIX_mobile** | `https://github.com/jkhons/IBIX_mobile.git` | `git@github.com:jkhons/IBIX_mobile.git` | Conteúdo da pasta `mobile_marketplace/` deste monorepo. A **raiz** do repo remoto = raiz do app Expo (sem backend Python na raiz). |
| **ibix_market** | `https://github.com/jkhons/ibix_market.git` | `git@github.com:jkhons/ibix_market.git` | Monorepo completo em `/central_solumatica/pdv_solumatica`: backend `app/`, templates, `mobile_marketplace/` como subpasta, scripts, documentação, etc. |

## Estado no disco (importante)

- A pasta `mobile_marketplace/` **não** é um repositório Git separado; ela é versionada pelo Git da **raiz** do projeto (`pdv_solumatica`).
- Sincronizar com `IBIX_mobile` é feita por **clone + cópia/rsync** (ou futuramente `git subtree`), não por `git pull` dentro de `mobile_marketplace/`.

## CI / `.github/`

Não há pasta `.github/` versionada neste projeto (sem GitHub Actions configuradas no repositório). Isso pode ser adicionado depois em `ibix_market` se necessário.

## Segredos

- Raiz: `.gitignore` ignora `.env`, `client_secret*.json`, uploads, etc.
- Mobile: seguir `mobile_marketplace/.env.example`. **Nunca** commitar `.env`, keystores, `google-services.json`, `GoogleService-Info.plist` ou certificados.

## Fluxo contínuo adotado (Opção A)

- **Fonte do dia a dia:** monorepo (`ibix_market`) — desenvolvimento integrado com backend no mesmo clone.
- **Espelho só-mobile:** `IBIX_mobile` — atualizado quando for necessário release/build focado no app (EAS, revisão só do front mobile).

**Opção B** (alternativa): desenvolver só em `IBIX_mobile` e periodicamente copiar para `mobile_marketplace/` dentro do monorepo. Menos recomendado para quem altera API + app na mesma sprint.

---

## Trazer GitHub → VPS (`mobile_marketplace/`)

Recomendado (preserva `.env` e roda `npm ci` + typecheck):

```bash
cd /central_solumatica/pdv_solumatica
./scripts/sync-mobile-from-github.sh
```

Equivalente manual quando o código mobile mais atual estiver **apenas** em `IBIX_mobile`:

```bash
cd /central_solumatica/pdv_solumatica
ENV_BKP="$(mktemp)"
test -f mobile_marketplace/.env && cp -a mobile_marketplace/.env "$ENV_BKP"

TMP="$(mktemp -d)"
git clone --depth 1 git@github.com:jkhons/IBIX_mobile.git "$TMP/IBIX_mobile"
cd "$TMP/IBIX_mobile"
COMMIT_HASH="$(git rev-parse HEAD)"

cd /central_solumatica/pdv_solumatica
rsync -a --delete \
  --exclude '.env' \
  "$TMP/IBIX_mobile/" mobile_marketplace/

test -s "$ENV_BKP" && cp -a "$ENV_BKP" mobile_marketplace/.env
rm -rf "$TMP"
rm -f "$ENV_BKP"

cd mobile_marketplace && npm ci && npm run typecheck
```

(Ajuste a branch com `git clone -b <branch> ...` se o default não for `main`.)

---

## Subir monorepo → GitHub (`ibix_market`)

Primeira vez (remoto vazio):

```bash
cd /central_solumatica/pdv_solumatica
git remote add ibix_market git@github.com:jkhons/ibix_market.git   # se já existir, use outro nome
git push -u ibix_market main
```

Se `origin` já estiver ocupado por outro remote, mantenha `ibix_market` como nome do remote para este destino.

---

## Espelhar VPS → `IBIX_mobile` (após mudanças no monorepo)

Recomendado:

```bash
cd /central_solumatica/pdv_solumatica
./scripts/sync-mobile-to-github.sh
```

Equivalente manual quando `mobile_marketplace/` foi alterado aqui e o repo só-mobile precisa igualar:

```bash
cd /central_solumatica/pdv_solumatica
TMP="$(mktemp -d)"
git clone git@github.com:jkhons/IBIX_mobile.git "$TMP/IBIX_mobile"
rsync -a --delete \
  --exclude '.git' \
  --exclude '.env' \
  --exclude 'node_modules' \
  mobile_marketplace/ "$TMP/IBIX_mobile/"

cd "$TMP/IBIX_mobile"
git status
git add -A
git commit -m "sync: espelha mobile_marketplace do monorepo ($(date -I))"
git push origin HEAD
rm -rf "$TMP"
```

Revise `git status` antes do commit para não publicar arquivos sensíveis. Para subtrees no futuro, ver [Subtree merging](https://git-scm.com/book/en/v2/Git-Tools-Subtree-Merging).

---

## Diagrama

```mermaid
flowchart LR
  subgraph local [Workspace pdv_solumatica]
    root[Raiz monorepo]
    mob[mobile_marketplace]
    root --> mob
  end
  GHmobile[IBIX_mobile]
  GHmono[ibix_market]
  mob <-->|espelho| GHmobile
  root -->|push completo| GHmono
```

---

**Última atualização:** 2026-05-06 — fingerprints de host conferidos com `ssh-keyscan` / doc oficial GitHub.
