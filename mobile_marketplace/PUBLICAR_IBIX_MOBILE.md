# Publicar o app Expo (`IBIX_mobile`)

O código do **Ibix Market** na VPS vive em **`mobile_marketplace/`** dentro de `/central_solumatica/pdv_solumatica/`.

No GitHub, o repositório **[`jkhons/IBIX_mobile`](https://github.com/jkhons/IBIX_mobile)** deve ter **na raiz** apenas o conteúdo desta pasta (sem backend Python na raiz).

## Como subir (VPS → GitHub)

Na **raiz** do projeto (não dentro de `mobile_marketplace/`):

```bash
cd /central_solumatica/pdv_solumatica
./scripts/sync-mobile-to-github.sh
```

Variáveis opcionais: `IBIX_MOBILE_SSH`, `IBIX_MOBILE_PUSH_BRANCH`.

## PDV (raiz sem mobile) → outro repo

O backend e o resto do monorepo **não** vão para `IBIX_mobile`. Usa:

```bash
./scripts/push_root_sem_mobile_ibix_market.sh
```

## Regras de segurança (fonte de verdade = VPS)

A cópia mais atual está **no servidor**. Antes de qualquer `git pull` na raiz que possa sobrescrever ficheiros em produção, **revê o diff e faz backup**. Ver **[`../REPOSITORIOS_GITHUB.md`](../REPOSITORIOS_GITHUB.md)**.

## Fluxo tester (PC Windows)

Clone **só** `IBIX_mobile`, não o monorepo inteiro:

```bash
git clone git@github.com:jkhons/IBIX_mobile.git
cd IBIX_mobile
git pull origin main
npm install
npx expo start --web --clear --port 8082
```

Detalhes: [`ALINHAR_OUTRO_PC.md`](ALINHAR_OUTRO_PC.md), [`SETUP.md`](SETUP.md).
