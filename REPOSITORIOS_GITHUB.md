# Repositórios GitHub e pastas (PDV Ibix)

Este ficheiro evita confusão entre **monorepo na VPS**, **app mobile no GitHub** e fluxos de sincronização.

## Fontes de verdade (regra fixa)

| Área | Fonte canónica | Notas |
|------|----------------|--------|
| **`mobile_marketplace/`** (Expo / Ibix Market) | **GitHub** [`jkhons/IBIX_mobile`](https://github.com/jkhons/IBIX_mobile) | Na GitHub, o código do app está na **raiz** do repositório. Nesta VPS, o mesmo código vive em **`mobile_marketplace/`**. |
| **Resto do monorepo** (`app/`, Python, `MAPA_SISTEMA/`, etc.) | **Este servidor (VPS)** | O backend e documentação do PDV não são substituídos a partir do GitHub neste fluxo. |

**Direcção de atualização do mobile:** GitHub → pasta `mobile_marketplace/` nesta máquina (não o contrário quando o remoto já está à frente).

## SSH — chave pública desta VPS (cadastrar no GitHub)

1. GitHub → **Settings** → **SSH and GPG keys** → **New SSH key**.
2. Cole **uma linha** (chave pública):

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPNEZ4TLERUPOXryuELRiwUEAFt3MFuMIz9niGp9UYTJ pdv_solumatica-vps-ibix-2026
```

3. Teste no servidor: `ssh -T git@github.com` (deve identificar o utilizador).

Ficheiros locais (não versionados): privado `~/.ssh/id_ed25519_ibix`, config em `~/.ssh/config` com `IdentityFile` para `github.com` (`IdentitiesOnly yes`). Há fallback para `~/.ssh/id_ed25519_github` na mesma entrada `Host github.com`.

**Nunca** commite a chave **privada**.

## Sincronizar `mobile_marketplace/` com o GitHub

Após a chave SSH estar aceite pelo GitHub:

```bash
cd /central_solumatica/pdv_solumatica
./scripts/sync_mobile_from_github.sh
```

O script faz `git clone --depth 1` de `git@github.com:jkhons/IBIX_mobile.git` (branch `main`) e **rsync** para `mobile_marketplace/`, excluindo `node_modules`, `.expo`, builds e `.git`.

Depois, revê e commita no monorepo:

```bash
git status
git add mobile_marketplace
git commit -m "sync: mobile_marketplace desde IBIX_mobile"
```

Volta a instalar dependências se necessário: `cd mobile_marketplace && npm install`.

## Git remoto neste monorepo

O `origin` do repositório Git na raiz pode apontar para `IBIX_mobile`; isso reflete histórico antigo. O importante é a **regra da tabela acima**: para **conteúdo** do app, seguir o script / clone desde **`IBIX_mobile`** após SSH válido.

## Documentação relacionada

- [`mobile_marketplace/ALINHAR_OUTRO_PC.md`](mobile_marketplace/ALINHAR_OUTRO_PC.md) — clone, credenciais, fluxo VPS ↔ GitHub ↔ PC de testes.
- [`mobile_marketplace/AGENTS.md`](mobile_marketplace/AGENTS.md) — stack e normas do app.

---

**Última atualização:** 2026-05-06
