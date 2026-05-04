# Alinhar outro computador (mesmo usuário / mesma conta)

> **Monorepo:** este diretório (`mobile_marketplace`) é a mesma base de código do repositório **`https://github.com/jkhons/IBIX_mobile.git`** — sincronize mudanças entre os dois quando publicar o app.

Use este checklist para ter **o mesmo repositório, Git e fluxo** em outra máquina (Windows, macOS ou Linux), mantendo o **mesmo usuário GitHub** (`jkhons`) e o mesmo app **Ibix Market**.

---

## 1. Repositório

| Método | Comando / URL |
|--------|----------------|
| **HTTPS** | `https://github.com/jkhons/IBIX_mobile.git` |
| **SSH** | `git@github.com:jkhons/IBIX_mobile.git` |
| **GitHub CLI** | `gh repo clone jkhons/IBIX_mobile` |

Clonar (escolha um):

```bash
git clone https://github.com/jkhons/IBIX_mobile.git
cd IBIX_mobile
```

```bash
git clone git@github.com:jkhons/IBIX_mobile.git IBIX_mobile
cd IBIX_mobile
```

---

## 2. Identidade Git (autor dos commits)

Alinhe **nome** e **e-mail** com o que você usa no GitHub (em *Settings → Public profile* e *emails*), para que commits e gráfico de contribuições coincidam.

**Opção A — só neste projeto (recomendado se você usa e-mails diferentes por repo):**

```bash
cd IBIX_mobile
git config user.name "Seu Nome completo"
git config user.email "seu-email@exemplo.com"
```

**Opção B — em todas as máquinas, igual:**

```bash
git config --global user.name "Seu Nome completo"
git config --global user.email "seu-email@exemplo.com"
```

Confira:

```bash
git config user.name
git config user.email
# ou: git config --global --list | grep user
```

---

## 3. Autenticação no GitHub (push / pull)

Sem uma das opções abaixo, `git push` e `git pull` falham.

### 3.1 HTTPS + Personal Access Token (PAT)

1. GitHub → **Settings** → **Developer settings** → **Personal access tokens** → crie um token com escopo **`repo`**.
2. Ao fazer `git push` e pedir senha, use o **token** (não a senha da conta).
3. No Windows, o **Git Credential Manager** pode guardar o token; no Linux, considere `git config credential.helper store` (só se a máquina for sua e segura).

### 3.2 SSH

1. Gere uma chave (se ainda não tiver): `ssh-keygen -t ed25519 -C "seu-email@exemplo.com"`.
2. Copie o conteúdo de `~/.ssh/id_ed25519.pub` e cadastre em GitHub → **Settings** → **SSH and GPG keys**.
3. Teste: `ssh -T git@github.com` (deve responder com seu usuário).
4. Use o remote SSH:

```bash
cd IBIX_mobile
git remote set-url origin git@github.com:jkhons/IBIX_mobile.git
git remote -v
```

### 3.3 GitHub CLI (`gh`)

```bash
gh auth login
# GitHub.com → HTTPS ou SSH → autenticar no navegador ou token
gh auth status
```

Depois, `git push` / `git pull` usam a mesma sessão conforme o `gh` estiver configurado.

---

## 4. Ferramentas no novo PC (versões)

| Ferramenta | Notas |
|------------|--------|
| **Git** | Qualquer versão recente; `git --version` |
| **Node.js** | **>= 18** (recomendado 20 LTS): [nodejs.org](https://nodejs.org) |
| **npm** | Vem com o Node: `npm --version` |
| **Expo / EAS** | Em dev: `npx expo`; builds: `npx eas-cli` ou `npm install -g eas-cli` |

Não é obrigatório instalar `expo-cli` global; use `npx expo` conforme o `package.json`.

---

## 5. Dependências e ambiente do app

Na **raiz do repositório clonado** (`IBIX_mobile`):

```bash
cp .env.example .env
# Edite .env: EXPO_PUBLIC_API_BASE_URL, EXPO_PUBLIC_WS_BASE_URL, etc.
npm install
```

- **Celular na mesma rede que o PC:** no `.env`, use o **IP local do PC**, não `127.0.0.1`, na URL da API.
- **Emulador Android:** costuma ser `http://10.0.2.2:8000/api/v1` para o backend no host.
- O arquivo **`.env` não vai para o Git** (está no `.gitignore`); copie valores de forma segura (gerenciador de senhas, variáveis de ambiente da equipe, etc.).

Detalhes de API, EAS e typecheck: **`SETUP.md`**. Regras de produto, stack e pastas: **`AGENTS.md`**.

---

## 6. Sincronizar com o remoto (dia a dia)

```bash
cd IBIX_mobile
git fetch origin
git status
git pull origin main
```

Antes de subir alterações:

```bash
git add -A
git status
git commit -m "Descrição clara do que mudou"
git push origin main
```

Se o GitHub rejeitar push (histórico divergente), não force sem entender: em time, alinhe com `git pull --rebase origin main` ou merge conforme o fluxo combinado.

---

## 7. EAS (build na nuvem) — mesma “conta Expo”

Quem for gerar build precisa da **mesma conta Expo** associada ao projeto (se já existir `eas.json` / projeto EAS):

```bash
npx eas login
# npx eas whoami
```

Na primeira vez neste repo: `npx eas init` só se ainda não existir projeto EAS vinculado (veja `SETUP.md` seção EAS).

---

## 8. Resumo rápido (copiar e marcar)

- [ ] `git clone` com HTTPS ou SSH
- [ ] `git config` **user.name** e **user.email** iguais aos do GitHub
- [ ] PAT (HTTPS) **ou** chave SSH cadastrada no GitHub
- [ ] Node **>= 18**, `npm install`
- [ ] `cp .env.example .env` e URLs da API/WS corretas para **esta** máquina/rede
- [ ] `npx expo start` com backend acessível na URL do `.env`
- [ ] (Opcional) `gh auth login`, `npx eas login` para builds

---

**Última revisão:** documento focado em alinhar **Git + GitHub + ambiente local**; detalhes de negócio e API continuam em `AGENTS.md` e `SETUP.md`.
