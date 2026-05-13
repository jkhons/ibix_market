# Repositórios GitHub — escopos separados (PDV vs mobile)

Este ficheiro define **dois destinos** no GitHub e como publicar **sem misturar** conteúdos nem **sobrescrever a VPS** por engano.

## Regra fixa (o que vai para cada repo)

| Repositório GitHub | Conteúdo que deve existir **na raiz do repo remoto** | Origem na VPS |
|--------------------|------------------------------------------------------|---------------|
| **[`jkhons/ibix_market`](https://github.com/jkhons/ibix_market)** | **Só o PDV** (`app/`, `MAPA_SISTEMA/`, templates, `scripts/`, etc.) **sem** a pasta `mobile_marketplace/` | Disco em `/central_solumatica/pdv_solumatica`, **excluindo** `mobile_marketplace/` |
| **[`jkhons/IBIX_mobile`](https://github.com/jkhons/IBIX_mobile)** | **Só o app Expo** (equivalente ao interior de `mobile_marketplace/`) | Pasta `mobile_marketplace/` |

## Fonte de verdade operacional (⚠️ leitura obrigatória)

| Onde está o código **a correr** e mais atual | O GitHub |
|-----------------------------------------------|----------|
| **Esta VPS** (`/central_solumatica/pdv_solumatica`) | Espelho / backup / colaboração — **não** é o deploy automático da produção só por existir `git push`. |

- **Nunca** faças `git pull` na raiz da VPS a partir de GitHub para “atualizar produção” **sem** rever o diff e backups — podes apagar ou desalinhar o que já está estável no servidor.
- Para publicar **para** o GitHub, usa **sempre** os scripts abaixo (espelho controlado), ou commits conscientes após `git status`.

## Publicar para o GitHub (comandos na VPS)

Após SSH para `github.com` configurado (`ssh -T git@github.com`):

### 1) PDV → `ibix_market` (**sem** `mobile_marketplace/`)

```bash
cd /central_solumatica/pdv_solumatica
./scripts/push_root_sem_mobile_ibix_market.sh
```

Opcional: `IBIX_MARKET_SSH`, `IBIX_MARKET_PUSH_BRANCH` (default `main`).

### 2) App mobile → `IBIX_mobile` (**só** `mobile_marketplace/`)

```bash
cd /central_solumatica/pdv_solumatica
./scripts/sync-mobile-to-github.sh
```

Opcional: `IBIX_MOBILE_SSH`, `IBIX_MOBILE_PUSH_BRANCH` (ver script).

### 3) Trazer mobile do GitHub → pasta local (quando o remoto estiver **à frente** e isso for desejado)

```bash
cd /central_solumatica/pdv_solumatica
./scripts/sync-mobile-from-github.sh
# ou: ./scripts/sync_mobile_from_github.sh
```

Revê `git status` no monorepo antes de commitar qualquer coisa na raiz.

## Remotes Git na pasta da VPS (recomendação)

Evita confusão típica: **`origin` apontado para `IBIX_mobile` enquanto o trabalho é monorepo na raiz**.

Estado **recomendado** (ajusta uma vez, com cuidado):

```bash
cd /central_solumatica/pdv_solumatica
git remote -v
# Exemplo: renomear ou corrigir URLs para ficar explícito:
#   origin      → jkhons/ibix_market.git   (push do monorepo local, se ainda versionares tudo na raiz)
#   IBIX_mobile → jkhons/IBIX_mobile.git   (só via script sync-mobile-to-github.sh)
```

**Importante:** enquanto o Git local na raiz **ainda** versionar `mobile_marketplace/` dentro do mesmo repositório, um `git push` genérico para `ibix_market` pode **voltar** a incluir mobile no histórico. O script `push_root_sem_mobile_ibix_market.sh` **não** depende disso: ele gera um clone limpo e remove `mobile_marketplace/` antes do commit no remoto `ibix_market`.

Passo **opcional** (mudança estrutural, conversar com a equipa antes): `git rm -r --cached mobile_marketplace` + `.gitignore` em `mobile_marketplace/` no monorepo + Git **só** dentro de `mobile_marketplace/` — aí o histórico local fica alinhado ao modelo “dois produtos”.

## SSH — chave pública desta VPS (cadastrar no GitHub)

1. GitHub → **Settings** → **SSH and GPG keys** → **New SSH key**.
2. Cole **uma linha** (chave pública):

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPNEZ4TLERUPOXryuELRiwUEAFt3MFuMIz9niGp9UYTJ pdv_solumatica-vps-ibix-2026
```

3. Teste: `ssh -T git@github.com`

**Nunca** commite chave **privada** nem `.env`.

## Documentação relacionada

- [`mobile_marketplace/PUBLICAR_IBIX_MOBILE.md`](mobile_marketplace/PUBLICAR_IBIX_MOBILE.md) — contexto do app Expo.
- [`mobile_marketplace/ALINHAR_OUTRO_PC.md`](mobile_marketplace/ALINHAR_OUTRO_PC.md) — clone no PC Windows / tester.
- [`MAPA_SISTEMA/REPOSITORIOS_GITHUB.md`](MAPA_SISTEMA/REPOSITORIOS_GITHUB.md) — detalhe SSH e tabela histórica (manter coerente com este ficheiro).

---

**Última atualização:** 2026-05-13 — escopos separados `ibix_market` (sem mobile) vs `IBIX_mobile`; scripts `push_root_sem_mobile_ibix_market.sh` e `sync-mobile-to-github.sh`.
