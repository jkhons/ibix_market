# Processo completo — SEO Google (Ibix)

Este documento junta **tudo o que o projeto precisa** para o Search Console e sitemaps funcionarem. Parte é **no servidor e no Google** (não automatizável pelo repositório).

---

## A) O que já está no código (você só precisa publicar)

- Rotas `GET` de `robots.txt`, `sitemap.xml` e sub-sitemaps.
- Rotas **`HEAD`** nas mesmas URLs (+ `merchant-feed.xml`), para o Google não receber **405** ao validar o sitemap.
- Arquivo: [`main.py`](../main.py).

**Sem deploy no servidor**, o Search Console pode continuar mostrando *“Não foi possível buscar o sitemap”* mesmo com o XML abrindo no navegador.

---

## B) Deploy no servidor (obrigatório para “fechar” o processo)

No servidor onde roda o PDV (ex.: `/central_solumatica/pdv_solumatica`):

```bash
cd /central_solumatica/pdv_solumatica
git pull   # ou o fluxo de deploy que vocês usam

# Reiniciar a aplicação (nome típico do unit — ajuste se for outro)
sudo systemctl restart pdv_solumatica
```

Confirme `.env` em produção:

- `APP_URL=https://www.ibix.com.br` (sem barra no final)
- `HTTPS=true`
- `ENV=production`

---

## C) Verificação após o deploy

O script `scripts/verify_seo_public.sh` foi removido do repositório. Verificar manualmente (ou automatizar fora do repo), por exemplo:

```bash
BASE_URL=https://www.ibix.com.br
curl -sS -o /dev/null -w "%{http_code}" -I "$BASE_URL/"
curl -sS -o /dev/null -w "%{http_code}" "$BASE_URL/sitemap.xml"
```

**Esperado:** `200` em HEAD/GET para a home e GET em `/sitemap.xml` (ajustar paths conforme o ambiente).

---

## D) DNS (Search Console — propriedade “Domínio”)

Se usou verificação por **TXT** no `ibix.com.br`:

1. Registro **TXT** no `@` com `google-site-verification=...` (pode coexistir com o SPF).
2. Aguardar propagação; no Search Console clicar em **Verificar**.

*(Feito uma vez — não precisa repetir a cada deploy.)*

---

## E) Google Search Console (painel web)

1. Propriedade: `https://www.ibix.com.br` ou domínio `ibix.com.br` (conforme já configurado).
2. **Sitemaps** → adicionar: `sitemap.xml` (ou URL completa `https://www.ibix.com.br/sitemap.xml`).
3. Se antes apareceu erro: **remover** o sitemap antigo e **enviar de novo** após o deploy da correção **HEAD**.
4. **Inspecionar URL** em `https://www.ibix.com.br/sitemap.xml` → testar URL publicada (opcional).
5. Em alguns dias: **Desempenho** / **Páginas** para ver dados.

Não é possível executar estes passos pelo Git; só quem tem acesso à conta Google.

---

## F) Checklist estendido e revisão em 30 dias

- [Checklist detalhado e pós-indexação](CHECKLIST_GOOGLE_INDEXACAO_IBIX.md)
- [SEO da vitrine / APP_URL](SEO_LANDING.md)

---

## Resumo

| Etapa | Quem / Onde |
|--------|-------------|
| Código + HEAD | Repositório (`main.py`) — **deploy necessário** |
| `curl` / inspeção HTTP | Sua máquina ou servidor, após deploy |
| TXT DNS | Painel DNS (ex.: Hostinger) — uma vez |
| GSC: sitemap, inspeção | Conta Google — você |

**Última atualização:** 2026-04-06
