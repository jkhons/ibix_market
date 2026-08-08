# AIM / Gerenciador de Cenas — ponte com o plano

Fonte: validado pelo operador em 02/08/2026. Ferramenta **fora** deste repositório PDV.

## O que é
Editor de vídeo por cenas (timeline 9:16). O AIM monta e anima beats em sequência e exporta **MP4 1080×1920 @ 30 fps (H.264)** — Reels / Shorts / Stories. Studio separado só para PNG do mascote. **Sem** Feed 1:1 / 4:5 hoje.

## Identidade (tema IBIX default)
| Item | Valor |
|------|--------|
| Mascote | `assets/mascote-trust-*.png` — poses: hero, guide, peek, offer, deliver, cashback, approve |
| bg | `#FEF7F1` |
| accent | `#E67E22` |
| text / slate | `#3D4A56` |
| ouro | `#F1C40F` |
| oliva | `#5D6346` |
| Título | Anton (ou Archivo Black) |
| Corpo/kicker | DM Sans |
| Logo | `assets/escrita-ibix.png` + `assets/arte-ibix.png` |

## Tradução marketing → AIM
| Marketing | AIM |
|-----------|-----|
| 1 corte / beat | **1 cena** (`scenes[]`) |
| Post “cheio” 4 cortes | **4 cenas** na timeline |
| Post “leve” 2–3 cortes | **2–3 cenas** |
| Reuso | Recorte / republicação — não é `type` no AIM |
| Tipos de cena | `cover` · `hero` · `product` · `card` · `counter` · `cta` (+ master logo/deco) |

**Não** usar no JSON os nomes cheio/leve/reuso — só `type` + campos.

## Brief daqui → AIM (ordem preferida)
1. JSON version 6 (`theme` + `master` + `scenes[]`) no schema `models/ibix-vem-ai.json`
2. Ou lista: label · type · duration · textos · image/spotlightImages · transição · pills/preço
3. Assets: `Produtos/*.png` (RGBA) ou `assets/mascote-trust-*.png`

## Regras de conteúdo (plano)
- Sem inventar números de lojas/pedidos/preços se não forem reais.
- UI da vitrine: só se anexar **print** como imagem.
- Até o Dia D: discurso **em breve** (não “já abriu”).
- Evitar linguagem tipo iFood (“pedir”); preferir comprar / lojas / vitrine.

## Post 1 — ver `aim_post_1.json` / seção em `copies_bloco_a.md`
