# Plano — Marketing Estruturado

Banco de informação e linha do tempo de marketing para **soltar a plataforma**.  
Não é documentação técnica, nem backlog de código.

---

## 1. Papel neste espaço

O assistente atua como **consultor e marketeiro**, não como desenvolvedor.

| Faz | Não faz |
|-----|---------|
| Estratégia de lançamento, engajamento, posicionamento, narrativa | Código, módulos, APIs, migrations, bugs |
| Perguntas até o entendimento estar completo | Inventar fatos, números, promessas ou públicos |
| Organizar o que foi **validado** em linha do tempo | Preencher seções “para não ficar vazio” |
| Preservar objetivo e identidade do sistema | Mudar o produto via discurso de marketing |

---

## 2. Diretrizes obrigatórias

### 2.1 Sem inserção sem controle

- **Proibido** gravar neste banco hipótese, chute ou “melhor prática genérica” como se fosse fato.
- Toda entrada nova exige: **origem clara** (você confirmou / documento / decisão registrada) **ou** status explícito `HIPÓTESE — aguardando validação`.
- Em dúvida → **questionar**, não completar.
- Só avança de fase quando o entendimento da fase atual estiver **completo o suficiente** para decidir.

### 2.2 Protocolo de entendimento

Antes de registrar qualquer bloco (público, mensagem, canal, métrica, data):

1. Perguntar o que falta.
2. Confirmar o que foi entendido (espelhar em poucas frases).
3. Só então propor texto para **aprovação**.
4. Só após aprovação → gravar no plano / timeline.

Critério de “entendimento completo”: você consegue responder sem ambiguidade *para quem*, *o quê*, *por quê*, *quando* e *com qual prova de sucesso* — ou marcar conscientemente o que ainda está aberto.

### 2.3 Objetivo e identidade do sistema (âncora)

O marketing **serve** ao produto; não o redefine.

Âncora comercial (referência de produto — não detalhe técnico):

- Plataforma SaaS de **gestão comercial e operacional**: PDV, caixa, estoque, fiscal e, conforme a marca, **marketplace / vitrine**.
- Foco: gestão comercial real (venda, operação, loja online quando aplicável).
- Multi-marca: identidade visual e de oferta **por marca**; sem misturar discurso de uma marca no domínio de outra.
- Promessas de marketing devem ser **verdadeiras** frente ao que a plataforma entrega (sem overclaim jurídico ou operacional).

Qualquer copy, campanha ou pitch que conflite com essa âncora → **parar e questionar** antes de registrar.

### 2.4 Escopo deste diretório

**Dentro:** engajamento → maturidade → lançamento → pós-lançamento; personas; canais; narrativa; calendário; ativos conceituais; métricas de marketing.

**Fora:** implementação, arquitetura, RBAC, tickets de bug, “como fazer no código”.

---

## 3. Natureza do banco: linha do tempo

O plano é uma **linha do tempo de marketing**, do início ao amadurecimento — não uma lista solta de ideias.

```
Descoberta → Posicionamento → Pré-lançamento → Lançamento → Ativação → Retenção / Maturidade
```

Cada fase só recebe conteúdo **validado** (ou hipótese marcada). Fases futuras podem existir como estrutura vazia com status `aguardando`.

| Fase | Pergunta-guia | Status |
|------|---------------|--------|
| 0. Descoberta | Quem somos, o que soltamos, para quem, por quê agora? | em aberto |
| 1. Posicionamento | Que lugar ocupamos na cabeça do público? | aguardando |
| 2. Pré-lançamento | Como aquecer, lista, expectativa, prova social? | aguardando |
| 3. Lançamento | Dia D: mensagem, canais, CTA, oferta | aguardando |
| 4. Ativação | Primeiro uso / primeira compra / primeiro valor | aguardando |
| 5. Maturidade | Rotina, conteúdo, campanhas, indicadores | aguardando |

Detalhamento de cada fase será preenchido **somente** após as rodadas de perguntas correspondentes.

---

## 4. O que será construído (quando validado)

Estrutura prevista do banco (pastas/arquivos futuros — criar sob demanda, não antecipar conteúdo):

- `plano.md` — este arquivo (contrato + índice da timeline)
- decisões validadas de posicionamento e identidade
- mapa de públicos / personas (só com evidência ou confirmação)
- calendário e narrativa de lançamento
- checklist de canais e ativos (conceito, não código)
- métricas e definição de “lançamento bem-sucedido”

Nada disso é preenchido automaticamente.

---

## 5. Como trabalhamos nas próximas sessões

1. Consultor pergunta (uma leva focada por vez).
2. Você responde; consultor espelha o entendimento.
3. Você corrige ou confirma.
4. Só então registramos no plano / timeline.
5. Avançamos de fase quando a atual estiver estável.

**Regra de ouro deste espaço:** melhor uma seção vazia com status honesto do que um plano cheio de inventado.

---

## 6. Estado atual

- **Data:** 2026-08-03  
- **Reagendamento:** calendário 27/07→04/09 **não foi executado** → novo: **03/08/2026 → 11/09/2026** (+7 dias, mesmo ritmo).  
- **Status:** ritmo meio-termo **fechado** · Post 1 aprovado · aguarda OK dos posts **2, 3, 4, 6, 7** (5 = reuso)  
- **Semente de perfil (03/08):** **10 posts** de grade com info real do plano — arquivo `semente_perfil_10_posts.md` · status `PROPOSTA — ajuste um a um` · não substitui o calendário 40 dias · não há modo “publicar sem notificar” a base (~500).  
- **Campanha:** 03/08/2026 → 11/09/2026  
- **Arquivos:** `calendario_40_dias.md` · `copies_bloco_a.md` · `semente_perfil_10_posts.md` · `plano.md` · `aim_gerenciador_cenas.md` · `aim_post_1.json`  
- **Produção visual:** AIM (fora deste repo) — timeline 9:16; 1 corte = 1 cena; Post 1 = JSON em `aim_post_1.json`  
- **Operação (equipe / Superadmin):** painel PDV [`/admin/marketing-ibix-lancamento`](/admin/marketing-ibix-lancamento) — exibe **roteiro operacional** (legenda, cortes, duração, telas) do Bloco A + status de copy/produção/publicação. Blocos B–D sem copies no UI até existirem no plano (sem inventar).  
- **Próximo passo (03/08):** (1) revisar/ajustar semente **S1–S10** · (2) montar **Post 1** do calendário (telas + gravação) · metas: **3.000 seguidores** + **10 lojas** · depois posts 2–3 · aprovar copies 2–7 → Bloco B  
- **Aberto:** CTA do Bloco D (decidir no Bloco D). Dia D = **fim do plano 40 dias**, não lançamento do produto; lançamento real = etapa seguinte.

---

## 7. Registro da Fase 0 — FECHADA

### 7.1 O que estamos soltando
- Fase de **propagação + bastidores** até a publicação final (**40 dias**).
- Discurso: **marketplace** (venda de lojistas locais + entrega local). Foco inicial: **Lençóis Paulista – SP**.

### 7.2 Para quem
- Lojista local e consumidor.
- Ordem da narrativa: objetivo da ferramenta → benefício do lojista → benefício do consumidor.

### 7.3 Objetivo do pré-lançamento
- Propagar; mostrar desenvolvimento; rotina de postagens até a publicação final **deste plano**.
- **Atrair os dois públicos** ao longo dos 40 dias: **lojista** e **consumidor** (narrativa em fases A→B→C, mas o objetivo de audiência é **ambos** até o fim do plano).
- **Metas numéricas (validadas 02/08/2026):**
  - **3.000 seguidores** (Instagram `@ibixmarket` — canal principal de contagem; Facebook acompanha o mesmo conteúdo).
  - **10 lojas** (lojistas de Lençóis Paulista interessados / alinhados para a vitrine).
- Critério de sucesso **deste plano**: bater ou superar essas duas metas até **11/09/2026**, sem inventar prova social nos posts.

### 7.3.1 O que é o Dia D (11/09) — validado 02/08/2026
- **Não é** o lançamento oficial do produto/marketplace.
- **É** o **fim deste plano de 40 dias** (fecho da campanha de propagação + bastidores).
- CTA exato do post 28 / Bloco D: **decidir no Bloco D** (ainda aberto).
- **Depois do Dia D:** organizar o **lançamento real** em etapa seguinte (fora do escopo fechado destes 40 dias — não inventar data/oferta agora).

### 7.4 Formato e canais
- **Formato principal:** Stories / Reels (vídeo vertical 9:16).
- **Tom de referência:** ritmo Americanas (gancho → benefício → corte rápido → CTA) — **não** copiar visual/cores da Americanas.
- **Não fazer:** post “informativo/ficha técnica” como peça principal.
- Linha de gancho inicial: **B — curiosidade**.
- Instagram `@ibixmarket` · Facebook **Ibix Market** (mesmo conteúdo).
- Responsável: você (posta e aprova).

### 7.5 Frase-âncora
> Marketplace que organiza a venda de lojistas locais e a entrega local com prazo curto.  
> Inicialmente focado em Lençóis Paulista.

### 7.6 Prazo curto (discurso)
- Mesmo dia · cerca de **duas horas** **ou** **agendar**.  
- Cumprimento depende da operação local (integridade comercial).

### 7.7 Linha editorial
1. Objetivo da ferramenta  
2. Benefício do lojista (Lençóis Paulista)  
3. Benefício do consumidor  

### 7.8 Operação — ritmo meio-termo (validado)
| Item | Valor |
|------|--------|
| Canais | Instagram `@ibixmarket`, Facebook Ibix Market |
| Conteúdo | **Mesmo** nos dois canais |
| Quem posta / aprova | Você |
| Prazo | 40 dias |
| Presença | **5× por semana** (Seg, Qua, Sex, Sáb, Dom) |
| Produção nova pesada | **3×** — Seg, Qua, Sex (Reels “cheios”, 4 cortes) |
| Produção nova leve | **1×** — Sáb (Reels/Stories curto, 2–3 cortes) |
| Reuso | **1×** — Dom (melhor da semana → Stories + opcional Reels) |
| Todo Reels novo | Também no **Stories** no mesmo dia |

### 7.9 Política de reuso (validada)
**Pode**
- Stories no mesmo dia do Reels novo  
- Domingo: republicar/recortar o **melhor** da semana (mais view, save ou comentário)  
- Após 10–14 dias: repetir um ganhador com **legenda nova**  
- Mensagem-âncora (local / Lençóis / em breve) repetir ao longo da campanha, mudando o gancho  

**Não**
- Subir o mesmo Reels no feed no dia seguinte  
- Fingir conteúdo novo quando for só cópia idêntica sem recorte/legenda  

---

## 8. Rotina 40 dias — APROVADA (estrutura)

| Bloco | Dias (aprox.) | Foco |
|-------|----------------|------|
| A — Apresentar | 1–10 | Objetivo + “estamos construindo” |
| B — Lojista | 11–22 | Benefício do lojista (Lençóis Paulista) |
| C — Consumidor + entrega | 23–32 | Consumidor + prazo (mesmo dia / 2h ou agendar) |
| D — Aceleração | 33–40 | Contagem + fecho **deste plano** (não = lançamento do produto) |

Detalhamento por post: ver **`calendario_40_dias.md`**.  
**Dia 1:** 03/08/2026 · **Fim deste plano (Dia D):** 11/09/2026.  
*(Reagendado em 02/08/2026 — janela anterior não executada.)*  
**Lançamento real do marketplace:** etapa **após** o Dia D — a organizar; CTA do Bloco D definido no próprio Bloco D.