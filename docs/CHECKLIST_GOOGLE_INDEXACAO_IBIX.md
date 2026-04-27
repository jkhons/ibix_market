# Checklist — Google e indexação (Ibix / www.ibix.com.br)

Use este roteiro após o deploy em produção. Marque cada item quando concluído.

**Processo ponta a ponta (deploy + GSC + script de teste):** veja [PROCESSO_SEO_GOOGLE_COMPLETO.md](PROCESSO_SEO_GOOGLE_COMPLETO.md).

---

## 1. Google Search Console (GSC)

| # | Ação | Notas |
|---|------|--------|
| 1.1 | Criar propriedade **URL prefix** `https://www.ibix.com.br` | Alternativa: propriedade **Domínio** `ibix.com.br` (exige DNS TXT). |
| 1.2 | **Verificar** a propriedade | Método recomendado: registro DNS ou arquivo HTML na raiz do site. |
| 1.3 | Enviar **sitemap**: `https://www.ibix.com.br/sitemap.xml` | Menu **Sitemaps** → adicionar apenas o caminho `sitemap.xml` se a UI pedir URL relativa. |
| 1.4 | **Inspecionar URL** das páginas críticas e, se necessário, **Solicitar indexação** | Sugestão: `/`, `/loja`, `/cadastro`, `/termos-de-uso`, `/politica-privacidade`, `/politica-privacidade-marketplace`. |
| 1.5 | Conferir **Páginas** / **Cobertura** após alguns dias | Corrigir erros 4xx/5xx e “Rastreado, não indexado” conforme o relatório. |
| 1.6 | (Opcional) Associar a propriedade ao **Google Analytics 4** | Admin GA4 → vinculação com Search Console. |

---

## 2. Domínio antigo (se ainda existir)

| # | Ação | Notas |
|---|------|--------|
| 2.1 | Manter **301 permanente** de cada URL do domínio antigo para o equivalente em `https://www.ibix.com.br` | Configurar no **Nginx/DNS/hosting** do domínio antigo, não só no app. |
| 2.2 | Incluir o domínio antigo no GSC e monitorar redirecionamentos | Ferramenta **Mudança de endereço** (quando aplicável) no GSC. |
| 2.3 | Atualizar links externos que ainda apontem para o site antigo | Redes, e-mail marketing, parceiros, Google Perfil de Negócio. |

---

## 3. Verificação técnica em produção (comandos)

Execute no servidor ou na sua máquina (substitua se usar staging):

```bash
# Home: use GET (-X GET) porque HEAD pode retornar 405 neste app
curl -sI -X GET "https://www.ibix.com.br/" | head -n 5

# Sitemap e robots: HEAD deve ser 200 (o Search Console pode testar HEAD)
curl -sI "https://www.ibix.com.br/sitemap.xml" | head -n 8
curl -sI "https://www.ibix.com.br/robots.txt" | head -n 8

# robots.txt: User-agent, Allow/Disallow e linha Sitemap:
curl -sS "https://www.ibix.com.br/robots.txt"

# Índice de sitemaps (deve listar sitemap-pages, produtos, categorias, lojas)
curl -sS "https://www.ibix.com.br/sitemap.xml" | head -n 25

# Redirecionamento apex → www (301)
curl -sI "https://ibix.com.br/" | grep -i location

# HTTP → HTTPS + www (301)
curl -sI "http://www.ibix.com.br/" | grep -i location
```

**Esperado (alinhado ao Nginx em `scripts/deploy/nginx/solumatica.conf`):**

- `http://` e `https://ibix.com.br` redirecionam para `https://www.ibix.com.br` com **301**.
- `robots.txt` contém `Sitemap: https://www.ibix.com.br/sitemap.xml` (o host exato segue o da requisição; com `Host: www.ibix.com.br` fica coerente).

---

## 4. Variáveis de ambiente (produção)

| Variável | Valor esperado |
|----------|----------------|
| `APP_URL` | `https://www.ibix.com.br` (sem barra no final) |
| `HTTPS` | `true` |
| `ENV` | `production` |

Documentado em [`.env.example`](../.env.example). Sem `APP_URL`, canonical/sitemap podem depender só do `Host` do proxy — em produção **defina `APP_URL`**.

---

## 5. O que foi conferido neste repositório (código)

| Item | Status | Onde |
|------|--------|------|
| Rota `GET /robots.txt` | OK | [`main.py`](../main.py) — `Allow`/`Disallow` públicos + linha `Sitemap:` |
| Rota `GET /sitemap.xml` (índice) | OK | [`main.py`](../main.py) — aponta para `sitemap-pages.xml`, `sitemap-produtos.xml`, `sitemap-categorias.xml`, `sitemap-lojas.xml` |
| URLs estáticas no sitemap de páginas | OK | `/`, `/loja`, login, cadastros, termos, privacidade, representantes, help-center, manual |
| Base URL pública | OK | `_landing_base_url()` usa `request.base_url` com fallback em `settings.APP_URL` |
| Nginx: 301 apex e HTTP→HTTPS→www | OK | [`scripts/deploy/nginx/solumatica.conf`](../scripts/deploy/nginx/solumatica.conf) — blocos `server` nas linhas ~21–31 e ~115–124 |
| Documentação SEO do marketplace | OK | [`docs/SEO_LANDING.md`](SEO_LANDING.md) |

**Não verificado aqui (depende do servidor):** certificados SSL válidos, `systemctl` do Gunicorn, firewall, DNS apontando para o IP correto.

---

## 6. Expectativa realista

- Indexação **não é imediata**; pode levar dias ou semanas.
- Aparecer na **primeira página** para termos genéricos exige autoridade, conteúdo e backlinks — o checklist acima **habilita** o Google a rastrear e indexar; não garante ranking.

---

## 7. Google Perfil de Negócio (antigo Google Meu Negócio)

Aplica-se se a Ibix tiver **endereço físico atendendo clientes** ou **área de atendimento** declarável (não é obrigatório para todo SaaS).

| # | Ação | Notas |
|---|------|--------|
| 7.1 | Acessar [Google Business Profile](https://business.google.com/) e localizar ou **criar** a ficha da empresa | Use a conta Google da empresa. |
| 7.2 | **Nome da empresa** | Alinhar à marca **Ibix** (e razão social, se for o caso de exibição secundária). |
| 7.3 | **Site** | `https://www.ibix.com.br` (mesmo domínio canônico do site). |
| 7.4 | **Telefone / WhatsApp** | Igual ao que aparece no site (landing, rodapé, política de privacidade). |
| 7.5 | **Endereço ou área de serviço** | Coerente com o que informa no site e em documentos legais. |
| 7.6 | **Categoria principal** | Escolher a categoria que melhor descreve o negócio (ex.: software, serviços B2B — conforme as opções do Google). |
| 7.7 | **Descrição curta** | Texto único; pode mencionar PDV, gestão, marketplace, sem copiar spam de keywords. |
| 7.8 | **Verificação** da ficha | Cartão postal, telefone ou e-mail, conforme o Google oferecer. |
| 7.9 | Publicar **fotos** (logo, fachada se houver, equipe) e, se fizer sentido, **posts** ou ofertas | Ajuda na confiança e no pacote “Maps + pesquisa”. |

**Consistência NAP (Name, Address, Phone):** o trio nome + endereço + telefone deve ser **idêntico** (ou claramente equivalente) entre Perfil de Negócio, site, rodapé de e-mails e redes — reduz confusão para usuários e para dados estruturados locais.

---

## 8. Outros canais (opcional, mas recomendável)

| # | Ação | Notas |
|---|------|--------|
| 8.1 | **Bing Webmaster Tools** | Adicionar `https://www.ibix.com.br`, verificar e enviar o mesmo `sitemap.xml`. |
| 8.2 | **Redes sociais** | Bio e link “site” apontando para `https://www.ibix.com.br`. |
| 8.3 | **Assinaturas de e-mail** | Link para o site com a marca Ibix. |
| 8.4 | **Rich results / Core Web Vitals** | No GSC, acompanhar **Experiência** e **Melhorias** (erros de produto, mobile, etc.) após indexação inicial. |

---

## 9. Revisão pós-indexação (sugerido: ~30 dias após GSC ativo)

Objetivo: ver se o Google está **enxergando** o site, **quais páginas** aparecem na busca e onde melhorar título/descrição ou conteúdo.

| # | Ação | Onde no GSC / como usar |
|---|------|-------------------------|
| 9.1 | Abrir **Desempenho** (ou relatório equivalente de resultados da pesquisa) | Período: últimos **28 dias** (ou desde a verificação, se for mais curto). |
| 9.2 | Anotar **consultas** com impressões mas **CTR baixo** | Vale testar novo `<title>` ou meta description nas URLs correspondentes (sem keyword stuffing). |
| 9.3 | Anotar **consultas** com boa posição média mas **poucas impressões** | Pode ser nicho estreito; avaliar conteúdo novo (blog, FAQ, página de recurso) só se fizer parte da estratégia. |
| 9.4 | Relatório **Páginas** (mesmo bloco Desempenho) | Identificar URLs com tráfego inesperado ou queda brusca frente à semana anterior. |
| 9.5 | Exportar ou filtrar URLs importantes com **zero impressões** | Conferir se estão no `sitemap.xml`, se retornam **200**, se não estão com `noindex` e se o conteúdo visível menciona a marca/tema buscável. |
| 9.6 | **Páginas** / **Cobertura** (ou “Indexação de páginas”) | Tratar erros novos (404 em massa, “Rastreado — atualmente não indexado”, “Duplicata”). |
| 9.7 | **Sitemaps** | Status “Sucesso”; se houver avisos, corrigir URLs inválidas ou fora do domínio canônico. |
| 9.8 | **Segurança e ações manuais** | Garantir que não há alerta ou penalidade pendente. |
| 9.9 | (Se usar) **GA4** | Comparar sessões **orgânicas** com cliques do GSC — grandes divergências podem indicar filtro, sampling ou tag ausente em parte do site. |

**Cadência sugerida:** repetir a revisão da **§9** a cada **30–60 dias** nos primeiros meses; após estabilizar, trimestral basta na maioria dos casos.

**~90 dias:** reavaliar se objetivos mudaram (ex.: foco em `/loja` vs. landing SaaS), se convém ampliar sitemap/conteúdo para categorias ou cidades, e se backlinks ou parcerias precisam ser priorizados para termos mais competitivos.

---

**Última revisão do checklist:** 2026-04-06 (inclui revisão pós-indexação 30/90 dias)
