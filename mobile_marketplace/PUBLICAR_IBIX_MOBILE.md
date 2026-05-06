# Git só do mobile (`IBIX_mobile`)

O **único** controlo de versão Git do projeto está nesta pasta:

**`/central_solumatica/pdv_solumatica/mobile_marketplace/.git`**

A pasta **pai** (`pdv_solumatica/`) **não tem `.git`**. O backend (`../app/`, `main.py`, etc.) **não é versionado em Git** aqui — continua no disco e **o sistema corre igual**; apenas deixa de entrar em commits.

> Histórico antigo (monorepo): se existir `../.git.backup_full_repo`, é cópia de segurança do Git antigo na raiz — podes apagar quando já não precisares.

## Dia a dia na VPS (programador do app)

```bash
cd /central_solumatica/pdv_solumatica/mobile_marketplace

git pull origin main
# … alterações …
git status
git add -A
git commit -m "descreva a mudança"
git push origin main
```

## Tester (outro PC)

```bash
git clone git@github.com:jkhons/IBIX_mobile.git
cd IBIX_mobile
git pull origin main
npm install
npx expo start --web --clear --port 8082
```

Detalhes de ambiente: [`SETUP.md`](SETUP.md), fluxo da equipa: [`ALINHAR_OUTRO_PC.md`](ALINHAR_OUTRO_PC.md).
