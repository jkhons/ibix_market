Diagnóstico atual (nível marketplace)
👍 O que ficou bom
1. Variedade visual melhorou
produtos diferentes
nomes coerentes
categorias implícitas

👉 cérebro entende: “tem opção”

2. Grid está saudável
espaçamento bom
alinhamento consistente
leitura confortável
3. Estrutura está pronta para escalar

Você já tem base pra:

ranking
destaque
personalização
⚠️ Problemas que ainda travam conversão

Agora entramos no ponto crítico:

👉 Ainda parece catálogo… não vitrine

1. Falta de hierarquia (continua sendo o maior problema)

Hoje todos os produtos têm o mesmo peso visual.

Exemplo:

produto de R$ 22
produto de R$ 145
produto com desconto

👉 tudo igual

2. Preço ainda não vende

Observe:

pequeno
sem cor forte
sem destaque

👉 preço precisa “gritar”

3. Desconto mal explorado

Você tem:

-86%
-3%

Mas visualmente:
👉 parecem iguais

4. Falta sensação de oportunidade

Mesmo com:

“Últimas unidades”

👉 ainda não gera urgência real

5. Nenhum produto chama mais atenção que outro

Isso é muito importante:

👉 em marketplace SEMPRE existe um “herói”

Hoje:

tudo flat
🧩 Ajustes cirúrgicos (o que você deve fazer agora)
🔥 1. Criar um “card destaque”

Regra:

a cada 6 produtos → 1 destaque

Diferença:

maior
borda leve
sombra mais forte
talvez etiqueta “🔥 Destaque”
💰 2. Transformar preço em protagonista

Faça isso:

.produto-preco-atual {
    font-size: 1.7rem;
    font-weight: 800;
    color: #0f2d4a;
}

.produto-preco-antigo {
    font-size: 0.8rem;
    opacity: 0.6;
}
🟠 3. Melhorar badge de desconto

Hoje está bom, mas pode virar arma de venda:

.produto-badge-desconto {
    background: linear-gradient(135deg, #ff6a00, #ff3d00);
    font-size: 0.8rem;
    font-weight: 800;
}

E regra importante:

<10% → cinza
10–40% → laranja

40% → vermelho forte

⚡ 4. Criar micro emoção

Adicione 1 linha abaixo do preço:

Exemplos:

“🚚 Entrega rápida”
“🔥 Mais vendido”
“⭐ Avaliado”
🧲 5. Melhorar clique

Seu botão:
👉 funciona, mas não chama

Sugestão:

leve glow no hover
crescer 5%
🧱 6. Agrupar produtos repetidos

Ex:
CARNAUBA PLUS:

500ml
3L

👉 isso deve virar:

1 card com variação

Isso é padrão marketplace.

🧭 Comparação direta
Seu sistema agora:

catálogo organizado

Próximo nível:

vitrine com intenção de venda

📌 Conclusão direta

Você saiu de:
👉 “bagunçado”

para:
👉 “limpo e funcional”

Agora falta:
👉 transformar em vendedor




Objetivo da V2

Transformar a experiência de:

catálogo organizado

para:

vitrine que conduz compra

1. Estrutura visual recomendada
Lateral esquerda

Hoje ela já ajuda, mas pode virar uma área mais estratégica.

Blocos ideais
Promoções
Mais vendidos
Últimas unidades

A lateral deve parecer uma curadoria, não só uma coluna secundária.

Área central

Separar em 3 zonas:

A. Faixa de destaque

Logo acima do grid:

1 ou 2 cards maiores
produtos com melhor apelo
banner curto ou “ofertas em destaque”
B. Ofertas da semana

Cards com selo mais forte

C. Todos os produtos

Grid normal

2. O que muda na sensação do usuário

Com essa divisão, o usuário entende imediatamente:

o que está em evidência
o que está promocional
o que é catálogo geral

Hoje ele só vê “muitos produtos”.
Na V2 ele passa a ver “uma loja organizada para vender”.

3. Card V2: estrutura ideal

Cada card precisa ter 5 zonas claras:

topo
selo de desconto
selo extra, se houver
imagem
área maior e mais limpa
fundo suave
título
2 linhas no máximo
legível e com peso médio/forte
preço
preço atual dominante
antigo menor
economia clara
ação
botão carrinho mais forte
hover perceptível
4. Elementos que faltam hoje
A. Card herói

Você precisa de 1 card diferente no grid.

Exemplo:

ocupa altura maior
borda levemente destacada
selo “Destaque”
mais respiro

Isso quebra a monotonia.

B. Selos auxiliares

Além do desconto, você pode usar:

Mais vendido
Últimas unidades
Novo
Oferta

Mas com regra clara.
Não usar em tudo.

C. Hierarquia de desconto

Hoje o usuário vê “-3%” e “-86%” quase do mesmo jeito.

A V2 precisa tratar isso diferente.

Regra sugerida
1% a 9% → selo discreto
10% a 39% → selo médio
40%+ → selo forte
5. Layout visual recomendado
Grid principal

Hoje está bom, mas eu ajustaria:

cards um pouco mais altos
mais respiro interno
imagem ligeiramente maior
rodapé mais firme
Exemplo de proporção
largura mínima do card: 210–230px
altura mínima: 300–330px
6. CSS V2 sugerido

Abaixo está uma base mais madura para seu grid.

/* GRID */
.produtos-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 18px;
}

/* CARD */
.produto-card {
    position: relative;
    background: #fff;
    border: 1px solid #e9edf2;
    border-radius: 18px;
    padding: 14px;
    min-height: 320px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    box-shadow: 0 3px 12px rgba(15, 23, 42, 0.05);
    transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}

.produto-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 10px 24px rgba(15, 23, 42, 0.12);
    border-color: #d8e0e8;
}

/* CARD DESTAQUE */
.produto-card--destaque {
    border: 1px solid #ffd79a;
    box-shadow: 0 8px 24px rgba(245, 158, 11, 0.16);
}

.produto-card--destaque::after {
    content: "Destaque";
    position: absolute;
    top: 12px;
    right: 12px;
    background: #fff3cd;
    color: #9a6700;
    font-size: 0.72rem;
    font-weight: 700;
    padding: 4px 8px;
    border-radius: 999px;
}

/* IMAGEM */
.produto-imagem-wrap {
    height: 132px;
    background: #f8fafc;
    border-radius: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    margin-bottom: 12px;
}

.produto-imagem {
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
    transition: transform 0.22s ease;
}

.produto-card:hover .produto-imagem {
    transform: scale(1.05);
}

/* TÍTULO */
.produto-titulo {
    font-size: 0.92rem;
    line-height: 1.3rem;
    font-weight: 600;
    color: #223548;
    margin-bottom: 10px;
    min-height: 42px;

    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

/* PREÇOS */
.produto-preco-antigo {
    font-size: 0.8rem;
    color: #94a3b8;
    text-decoration: line-through;
    min-height: 18px;
}

.produto-preco-atual {
    font-size: 1.65rem;
    line-height: 1.1;
    font-weight: 800;
    color: #16324f;
    letter-spacing: -0.02em;
}

.produto-preco-atual .centavos {
    font-size: 0.95rem;
    vertical-align: top;
    font-weight: 700;
}

/* TAGS */
.produto-tag {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 8px;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 700;
    margin-top: 8px;
    width: fit-content;
}

.produto-tag--estoque {
    background: #fff3e0;
    color: #b26a00;
}

.produto-tag--vendido {
    background: #eef6ff;
    color: #185aa6;
}

/* BADGE DESCONTO */
.produto-badge-desconto {
    position: absolute;
    top: 12px;
    left: 12px;
    color: #fff;
    font-size: 0.76rem;
    font-weight: 800;
    padding: 5px 9px;
    border-radius: 999px;
    z-index: 2;
    box-shadow: 0 6px 14px rgba(0,0,0,0.14);
}

.produto-badge-desconto.desconto-baixo {
    background: linear-gradient(135deg, #94a3b8, #64748b);
}

.produto-badge-desconto.desconto-medio {
    background: linear-gradient(135deg, #f59e0b, #ea580c);
}

.produto-badge-desconto.desconto-alto {
    background: linear-gradient(135deg, #ef4444, #dc2626);
}

/* RODAPÉ */
.produto-footer {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    gap: 10px;
    margin-top: 14px;
}

/* CTA */
.btn-add-carrinho {
    width: 44px;
    height: 44px;
    border: none;
    border-radius: 50%;
    background: #ffffff;
    color: #16324f;
    box-shadow: 0 4px 12px rgba(15, 23, 42, 0.14);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.18s ease;
}

.btn-add-carrinho:hover {
    background: #16324f;
    color: #fff;
    transform: scale(1.06);
    box-shadow: 0 10px 20px rgba(22, 50, 79, 0.24);
}
7. HTML ideal do card

Estrutura exemplo:

<div class="produto-card produto-card--destaque">
    <span class="produto-badge-desconto desconto-alto">-86%</span>

    <div class="produto-imagem-wrap">
        <img src="..." alt="Produto" class="produto-imagem">
    </div>

    <div class="produto-conteudo">
        <div class="produto-titulo">Cabo Usb 2.0 1.5m</div>

        <div class="produto-preco-antigo">R$ 21,00</div>
        <div class="produto-preco-atual">R$ 3<span class="centavos">,00</span></div>

        <span class="produto-tag produto-tag--estoque">Últimas unidades</span>
    </div>

    <div class="produto-footer">
        <div></div>
        <button class="btn-add-carrinho">
            <i class="fa fa-shopping-cart"></i>
        </button>
    </div>
</div>
8. Regras práticas de negócio visual
Quando aplicar destaque

Use em poucos itens:

1 a cada 8 produtos
ou manual via painel marketing
Quando aplicar “últimas unidades”

Somente quando o estoque realmente estiver baixo

Quando aplicar “mais vendido”

Somente com critério real

Quando aplicar desconto forte

Quando houver preço antigo válido + cálculo real

9. Melhorias que trariam muito resultado
A. Barra de benefícios acima do grid

Uma faixa simples com 3 itens:

Compra segura
Entrega local rápida
Atendimento da cidade

Isso aumenta confiança.

B. Separador visual de seções

Mesmo que a página seja única, use blocos com:

título
subtítulo curto
espaçamento mais generoso
C. Skeleton ou hover mais refinado

Pequenos detalhes assim fazem parecer sistema mais profissional.

A ideia aqui é te entregar uma base já pensada para:

melhorar sensação visual
aumentar hierarquia
destacar preço
manter sua estrutura simples
HTML base do card V2

Adapte os nomes das variáveis para seu template.

<div class="produto-card {% if produto.destaque %}produto-card--destaque{% endif %}">
    
    {% if produto.percentual_desconto %}
        <span class="produto-badge-desconto
            {% if produto.percentual_desconto >= 40 %}desconto-alto
            {% elif produto.percentual_desconto >= 10 %}desconto-medio
            {% else %}desconto-baixo
            {% endif %}">
            -{{ produto.percentual_desconto }}%
        </span>
    {% endif %}

    <a href="/produto/{{ produto.slug or produto.id }}" class="produto-link-imagem">
        <div class="produto-imagem-wrap">
            {% if produto.imagem_url %}
                <img src="{{ produto.imagem_url }}" alt="{{ produto.nome }}" class="produto-imagem">
            {% else %}
                <div class="produto-sem-imagem">Sem imagem</div>
            {% endif %}
        </div>
    </a>

    <div class="produto-conteudo">
        <a href="/produto/{{ produto.slug or produto.id }}" class="produto-titulo-link">
            <div class="produto-titulo">{{ produto.nome }}</div>
        </a>

        {% if produto.descricao_curta %}
            <div class="produto-subinfo">{{ produto.descricao_curta }}</div>
        {% endif %}

        <div class="produto-precos">
            {% if produto.preco_antigo and produto.preco_antigo > produto.preco %}
                <div class="produto-preco-antigo">
                    R$ {{ "%.2f"|format(produto.preco_antigo)|replace('.', ',') }}
                </div>
            {% else %}
                <div class="produto-preco-antigo vazio"></div>
            {% endif %}

            <div class="produto-preco-atual">
                {% set partes = "%.2f"|format(produto.preco)|replace('.', ',').split(',') %}
                <span class="produto-preco-moeda">R$</span>
                <span class="produto-preco-valor">{{ partes[0] }}</span><span class="produto-preco-centavos">,{{ partes[1] }}</span>
            </div>
        </div>

        <div class="produto-tags">
            {% if produto.ultimas_unidades %}
                <span class="produto-tag produto-tag--estoque">Últimas unidades</span>
            {% endif %}

            {% if produto.mais_vendido %}
                <span class="produto-tag produto-tag--vendido">Mais vendido</span>
            {% endif %}

            {% if produto.novo %}
                <span class="produto-tag produto-tag--novo">Novo</span>
            {% endif %}
        </div>
    </div>

    <div class="produto-footer">
        <a href="/produto/{{ produto.slug or produto.id }}" class="produto-btn-detalhes">
            Ver produto
        </a>

        <button class="btn-add-carrinho"
                type="button"
                data-produto-id="{{ produto.id }}"
                aria-label="Adicionar {{ produto.nome }} ao carrinho">
            <i class="fa fa-shopping-cart"></i>
        </button>
    </div>
</div>
CSS completo da V2
/* =========================
   ÁREA PRINCIPAL / GRID
========================= */
.produtos-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 18px;
}

/* =========================
   CARD
========================= */
.produto-card {
    position: relative;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    min-height: 335px;
    background: #ffffff;
    border: 1px solid #e7ebf0;
    border-radius: 18px;
    padding: 14px;
    box-shadow: 0 3px 10px rgba(15, 23, 42, 0.05);
    transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
    overflow: hidden;
}

.produto-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 24px rgba(15, 23, 42, 0.12);
    border-color: #d7dee7;
}

.produto-card--destaque {
    border-color: #ffd38a;
    box-shadow: 0 10px 24px rgba(245, 158, 11, 0.14);
}

.produto-card--destaque::after {
    content: "Destaque";
    position: absolute;
    top: 12px;
    right: 12px;
    background: #fff4d6;
    color: #9a6700;
    font-size: 0.72rem;
    font-weight: 800;
    padding: 4px 8px;
    border-radius: 999px;
    z-index: 3;
}

/* =========================
   IMAGEM
========================= */
.produto-link-imagem {
    text-decoration: none;
}

.produto-imagem-wrap {
    height: 138px;
    background: #f8fafc;
    border-radius: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 10px;
    overflow: hidden;
    margin-bottom: 12px;
}

.produto-imagem {
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
    transition: transform 0.22s ease;
}

.produto-card:hover .produto-imagem {
    transform: scale(1.05);
}

.produto-sem-imagem {
    color: #9aa4af;
    font-size: 0.82rem;
    text-align: center;
}

/* =========================
   BADGE DESCONTO
========================= */
.produto-badge-desconto {
    position: absolute;
    top: 12px;
    left: 12px;
    z-index: 4;
    color: #fff;
    font-size: 0.76rem;
    font-weight: 800;
    padding: 5px 9px;
    border-radius: 999px;
    line-height: 1;
    box-shadow: 0 6px 14px rgba(0, 0, 0, 0.14);
}

.produto-badge-desconto.desconto-baixo {
    background: linear-gradient(135deg, #94a3b8, #64748b);
}

.produto-badge-desconto.desconto-medio {
    background: linear-gradient(135deg, #f59e0b, #ea580c);
}

.produto-badge-desconto.desconto-alto {
    background: linear-gradient(135deg, #ef4444, #dc2626);
}

/* =========================
   CONTEÚDO
========================= */
.produto-conteudo {
    flex: 1;
    display: flex;
    flex-direction: column;
}

.produto-titulo-link {
    text-decoration: none;
}

.produto-titulo {
    color: #1f3448;
    font-size: 0.92rem;
    font-weight: 700;
    line-height: 1.28rem;
    min-height: 42px;
    margin-bottom: 6px;

    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

.produto-titulo-link:hover .produto-titulo {
    color: #15304b;
}

.produto-subinfo {
    color: #7b8794;
    font-size: 0.77rem;
    line-height: 1.15rem;
    min-height: 18px;
    margin-bottom: 8px;

    display: -webkit-box;
    -webkit-line-clamp: 1;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

/* =========================
   PREÇOS
========================= */
.produto-precos {
    margin-top: 4px;
}

.produto-preco-antigo {
    min-height: 18px;
    color: #98a3af;
    font-size: 0.79rem;
    text-decoration: line-through;
    margin-bottom: 2px;
}

.produto-preco-antigo.vazio {
    visibility: hidden;
}

.produto-preco-atual {
    color: #16324f;
    line-height: 1.05;
    display: flex;
    align-items: flex-start;
    gap: 2px;
    flex-wrap: nowrap;
}

.produto-preco-moeda {
    font-size: 0.95rem;
    font-weight: 700;
    margin-top: 7px;
}

.produto-preco-valor {
    font-size: 1.72rem;
    font-weight: 800;
    letter-spacing: -0.03em;
}

.produto-preco-centavos {
    font-size: 0.95rem;
    font-weight: 800;
    margin-top: 4px;
}

/* =========================
   TAGS
========================= */
.produto-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 10px;
    min-height: 28px;
}

.produto-tag {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 4px 8px;
    border-radius: 999px;
    font-size: 0.7rem;
    font-weight: 700;
    white-space: nowrap;
}

.produto-tag--estoque {
    background: #fff3df;
    color: #af6a00;
}

.produto-tag--vendido {
    background: #edf5ff;
    color: #1f5fa8;
}

.produto-tag--novo {
    background: #ecfdf3;
    color: #1d7a46;
}

/* =========================
   RODAPÉ
========================= */
.produto-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    margin-top: 14px;
}

.produto-btn-detalhes {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-height: 40px;
    padding: 0 14px;
    border-radius: 12px;
    background: #f5f8fb;
    color: #23415f;
    text-decoration: none;
    font-size: 0.82rem;
    font-weight: 700;
    transition: background 0.18s ease, color 0.18s ease, transform 0.18s ease;
}

.produto-btn-detalhes:hover {
    background: #eaf1f7;
    color: #173450;
    transform: translateY(-1px);
}

.btn-add-carrinho {
    width: 44px;
    height: 44px;
    border: none;
    border-radius: 50%;
    background: #fff;
    color: #16324f;
    box-shadow: 0 4px 12px rgba(15, 23, 42, 0.14);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.18s ease;
    flex-shrink: 0;
}

.btn-add-carrinho:hover {
    background: #16324f;
    color: #fff;
    transform: scale(1.06);
    box-shadow: 0 10px 20px rgba(22, 50, 79, 0.24);
}

/* =========================
   RESPONSIVO
========================= */
@media (max-width: 768px) {
    .produtos-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 14px;
    }

    .produto-card {
        min-height: 305px;
        padding: 12px;
        border-radius: 16px;
    }

    .produto-imagem-wrap {
        height: 118px;
    }

    .produto-preco-valor {
        font-size: 1.48rem;
    }

    .produto-btn-detalhes {
        padding: 0 10px;
        font-size: 0.76rem;
    }
}

@media (max-width: 480px) {
    .produtos-grid {
        grid-template-columns: 1fr 1fr;
    }

    .produto-titulo {
        font-size: 0.86rem;
    }

    .produto-preco-valor {
        font-size: 1.34rem;
    }

    .btn-add-carrinho {
        width: 40px;
        height: 40px;
    }
}
Bloco de seção acima do grid

Isso ajuda muito na percepção comercial.

<div class="vitrine-topo-bloco">
    <div>
        <h2 class="vitrine-titulo">Todos os produtos</h2>
        <p class="vitrine-subtitulo">Ofertas selecionadas, novidades e itens com entrega local.</p>
    </div>

    <div class="vitrine-beneficios">
        <span class="vitrine-pill">Compra segura</span>
        <span class="vitrine-pill">Entrega local</span>
        <span class="vitrine-pill">Atendimento da cidade</span>
    </div>
</div>
.vitrine-topo-bloco {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
    margin-bottom: 18px;
    flex-wrap: wrap;
}

.vitrine-titulo {
    margin: 0;
    color: #243b53;
    font-size: 1.7rem;
    font-weight: 800;
}

.vitrine-subtitulo {
    margin: 4px 0 0;
    color: #7b8794;
    font-size: 0.92rem;
}

.vitrine-beneficios {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
}

.vitrine-pill {
    background: #f5f8fb;
    color: #33506e;
    border: 1px solid #e3eaf2;
    border-radius: 999px;
    padding: 6px 10px;
    font-size: 0.76rem;
    font-weight: 700;
}
Regra prática para destacar alguns cards

No backend ou template, aplique destaque em poucos itens.

Exemplo de critério:

produtos marcados manualmente
melhores promoções
mais vendidos
1 item a cada 8 no grid

Exemplo simples no template:

<div class="produto-card {% if loop.index in [1, 7, 15] %}produto-card--destaque{% endif %}">

Melhor ainda:
usar flag real do banco, como:

{% if produto.card_destaque %}
O que eu faria na sua ordem de implantação
Etapa 1

Aplicar:

novo card
novo preço
novo badge
novo rodapé
Etapa 2

Aplicar:

barra de benefícios
card destaque
subtítulo da seção
Etapa 3

Aplicar:

seção “Ofertas da semana”
seção “Mais vendidos”
vitrine híbrida controlada pelo painel
Leitura final

Com esse bloco, sua tela sai de:
catálogo simples

para:
vitrine comercial com hierarquia


Abaixo vai a estrutura completa da página V2, já organizada em:

coluna lateral curada
faixa de destaque
ofertas da semana
todos os produtos
mesmo padrão visual

A ideia é te entregar uma base que já pareça vitrine comercial, não só listagem.

Estrutura geral da página
<div class="vitrine-page">

    <!-- TOPO DA VITRINE -->
    <section class="vitrine-hero">
        <div class="vitrine-hero__conteudo">
            <span class="vitrine-hero__tag">Ofertas da semana</span>
            <h1 class="vitrine-hero__titulo">Encontre produtos com entrega local e compra rápida</h1>
            <p class="vitrine-hero__texto">
                Produtos selecionados, promoções e itens com disponibilidade imediata para sua cidade.
            </p>

            <div class="vitrine-hero__acoes">
                <a href="#ofertas-semana" class="btn-hero btn-hero--primario">Ver ofertas</a>
                <a href="#todos-produtos" class="btn-hero btn-hero--secundario">Explorar catálogo</a>
            </div>

            <div class="vitrine-hero__beneficios">
                <span class="hero-pill">Compra segura</span>
                <span class="hero-pill">Entrega local</span>
                <span class="hero-pill">Atendimento da cidade</span>
            </div>
        </div>
    </section>

    <!-- CORPO -->
    <div class="vitrine-layout">

        <!-- LATERAL ESQUERDA -->
        <aside class="vitrine-sidebar">
            <div class="sidebar-bloco">
                <div class="sidebar-bloco__topo">
                    <h3>Promoções</h3>
                    <a href="#ofertas-semana">Ver mais</a>
                </div>

                <div class="sidebar-lista">
                    {% for produto in promocoes[:4] %}
                    <div class="mini-card">
                        {% if produto.percentual_desconto %}
                        <span class="mini-card__badge">-{{ produto.percentual_desconto }}%</span>
                        {% endif %}

                        <a href="/produto/{{ produto.slug or produto.id }}" class="mini-card__imagem-wrap">
                            {% if produto.imagem_url %}
                                <img src="{{ produto.imagem_url }}" alt="{{ produto.nome }}" class="mini-card__imagem">
                            {% else %}
                                <div class="mini-card__sem-imagem">Sem imagem</div>
                            {% endif %}
                        </a>

                        <a href="/produto/{{ produto.slug or produto.id }}" class="mini-card__titulo">
                            {{ produto.nome }}
                        </a>

                        {% if produto.preco_antigo and produto.preco_antigo > produto.preco %}
                        <div class="mini-card__preco-antigo">
                            R$ {{ "%.2f"|format(produto.preco_antigo)|replace('.', ',') }}
                        </div>
                        {% endif %}

                        <div class="mini-card__rodape">
                            <div class="mini-card__preco">
                                R$ {{ "%.2f"|format(produto.preco)|replace('.', ',') }}
                            </div>

                            <button class="mini-card__btn"
                                    type="button"
                                    data-produto-id="{{ produto.id }}"
                                    aria-label="Adicionar {{ produto.nome }} ao carrinho">
                                <i class="fa fa-shopping-cart"></i>
                            </button>
                        </div>

                        {% if produto.ultimas_unidades %}
                        <span class="mini-card__tag">Últimas unidades</span>
                        {% endif %}
                    </div>
                    {% endfor %}
                </div>
            </div>

            <div class="sidebar-bloco">
                <div class="sidebar-bloco__topo">
                    <h3>Mais vendidos</h3>
                </div>

                <div class="sidebar-links">
                    {% for produto in mais_vendidos[:5] %}
                    <a href="/produto/{{ produto.slug or produto.id }}" class="sidebar-link-item">
                        <span class="sidebar-link-item__nome">{{ produto.nome }}</span>
                        <span class="sidebar-link-item__preco">
                            R$ {{ "%.2f"|format(produto.preco)|replace('.', ',') }}
                        </span>
                    </a>
                    {% endfor %}
                </div>
            </div>
        </aside>

        <!-- CONTEÚDO PRINCIPAL -->
        <main class="vitrine-main">

            <!-- DESTAQUES -->
            <section class="secao-vitrine">
                <div class="secao-vitrine__topo">
                    <div>
                        <h2>Destaques</h2>
                        <p>Produtos selecionados com maior apelo comercial.</p>
                    </div>
                </div>

                <div class="cards-destaque">
                    {% for produto in destaques[:2] %}
                    <div class="card-destaque">
                        <div class="card-destaque__conteudo">
                            {% if produto.percentual_desconto %}
                            <span class="card-destaque__badge">-{{ produto.percentual_desconto }}%</span>
                            {% endif %}

                            <h3>{{ produto.nome }}</h3>

                            {% if produto.descricao_curta %}
                            <p>{{ produto.descricao_curta }}</p>
                            {% else %}
                            <p>Produto em destaque com ótima oportunidade para compra local.</p>
                            {% endif %}

                            <div class="card-destaque__precos">
                                {% if produto.preco_antigo and produto.preco_antigo > produto.preco %}
                                <div class="card-destaque__preco-antigo">
                                    R$ {{ "%.2f"|format(produto.preco_antigo)|replace('.', ',') }}
                                </div>
                                {% endif %}

                                <div class="card-destaque__preco-atual">
                                    R$ {{ "%.2f"|format(produto.preco)|replace('.', ',') }}
                                </div>
                            </div>

                            <div class="card-destaque__acoes">
                                <a href="/produto/{{ produto.slug or produto.id }}" class="btn-card-destaque btn-card-destaque--primario">
                                    Ver produto
                                </a>

                                <button class="btn-card-destaque btn-card-destaque--secundario"
                                        type="button"
                                        data-produto-id="{{ produto.id }}">
                                    Adicionar
                                </button>
                            </div>
                        </div>

                        <a href="/produto/{{ produto.slug or produto.id }}" class="card-destaque__imagem-wrap">
                            {% if produto.imagem_url %}
                                <img src="{{ produto.imagem_url }}" alt="{{ produto.nome }}" class="card-destaque__imagem">
                            {% else %}
                                <div class="card-destaque__sem-imagem">Sem imagem</div>
                            {% endif %}
                        </a>
                    </div>
                    {% endfor %}
                </div>
            </section>

            <!-- OFERTAS DA SEMANA -->
            <section class="secao-vitrine" id="ofertas-semana">
                <div class="secao-vitrine__topo">
                    <div>
                        <h2>Ofertas da semana</h2>
                        <p>Itens promocionais com melhor percepção de oportunidade.</p>
                    </div>
                </div>

                <div class="produtos-grid">
                    {% for produto in ofertas_semana %}
                        <div class="produto-card {% if produto.destaque %}produto-card--destaque{% endif %}">
                            
                            {% if produto.percentual_desconto %}
                                <span class="produto-badge-desconto
                                    {% if produto.percentual_desconto >= 40 %}desconto-alto
                                    {% elif produto.percentual_desconto >= 10 %}desconto-medio
                                    {% else %}desconto-baixo
                                    {% endif %}">
                                    -{{ produto.percentual_desconto }}%
                                </span>
                            {% endif %}

                            <a href="/produto/{{ produto.slug or produto.id }}" class="produto-link-imagem">
                                <div class="produto-imagem-wrap">
                                    {% if produto.imagem_url %}
                                        <img src="{{ produto.imagem_url }}" alt="{{ produto.nome }}" class="produto-imagem">
                                    {% else %}
                                        <div class="produto-sem-imagem">Sem imagem</div>
                                    {% endif %}
                                </div>
                            </a>

                            <div class="produto-conteudo">
                                <a href="/produto/{{ produto.slug or produto.id }}" class="produto-titulo-link">
                                    <div class="produto-titulo">{{ produto.nome }}</div>
                                </a>

                                {% if produto.descricao_curta %}
                                    <div class="produto-subinfo">{{ produto.descricao_curta }}</div>
                                {% endif %}

                                <div class="produto-precos">
                                    {% if produto.preco_antigo and produto.preco_antigo > produto.preco %}
                                        <div class="produto-preco-antigo">
                                            R$ {{ "%.2f"|format(produto.preco_antigo)|replace('.', ',') }}
                                        </div>
                                    {% else %}
                                        <div class="produto-preco-antigo vazio"></div>
                                    {% endif %}

                                    <div class="produto-preco-atual">
                                        {% set partes = "%.2f"|format(produto.preco)|replace('.', ',').split(',') %}
                                        <span class="produto-preco-moeda">R$</span>
                                        <span class="produto-preco-valor">{{ partes[0] }}</span><span class="produto-preco-centavos">,{{ partes[1] }}</span>
                                    </div>
                                </div>

                                <div class="produto-tags">
                                    {% if produto.ultimas_unidades %}
                                        <span class="produto-tag produto-tag--estoque">Últimas unidades</span>
                                    {% endif %}

                                    {% if produto.mais_vendido %}
                                        <span class="produto-tag produto-tag--vendido">Mais vendido</span>
                                    {% endif %}
                                </div>
                            </div>

                            <div class="produto-footer">
                                <a href="/produto/{{ produto.slug or produto.id }}" class="produto-btn-detalhes">
                                    Ver produto
                                </a>

                                <button class="btn-add-carrinho"
                                        type="button"
                                        data-produto-id="{{ produto.id }}"
                                        aria-label="Adicionar {{ produto.nome }} ao carrinho">
                                    <i class="fa fa-shopping-cart"></i>
                                </button>
                            </div>
                        </div>
                    {% endfor %}
                </div>
            </section>

            <!-- TODOS OS PRODUTOS -->
            <section class="secao-vitrine" id="todos-produtos">
                <div class="secao-vitrine__topo secao-vitrine__topo--com-acao">
                    <div>
                        <h2>Todos os produtos</h2>
                        <p>Explore o catálogo completo com produtos disponíveis para compra.</p>
                    </div>

                    <div class="ordenacao-wrap">
                        <label for="ordenarProdutos">Ordenar:</label>
                        <select id="ordenarProdutos" class="select-ordenacao">
                            <option value="recentes">Mais recentes</option>
                            <option value="menor_preco">Menor preço</option>
                            <option value="maior_preco">Maior preço</option>
                            <option value="desconto">Maior desconto</option>
                        </select>
                    </div>
                </div>

                <div class="produtos-grid">
                    {% for produto in todos_produtos %}
                        <div class="produto-card {% if produto.card_destaque %}produto-card--destaque{% endif %}">
                            
                            {% if produto.percentual_desconto %}
                                <span class="produto-badge-desconto
                                    {% if produto.percentual_desconto >= 40 %}desconto-alto
                                    {% elif produto.percentual_desconto >= 10 %}desconto-medio
                                    {% else %}desconto-baixo
                                    {% endif %}">
                                    -{{ produto.percentual_desconto }}%
                                </span>
                            {% endif %}

                            <a href="/produto/{{ produto.slug or produto.id }}" class="produto-link-imagem">
                                <div class="produto-imagem-wrap">
                                    {% if produto.imagem_url %}
                                        <img src="{{ produto.imagem_url }}" alt="{{ produto.nome }}" class="produto-imagem">
                                    {% else %}
                                        <div class="produto-sem-imagem">Sem imagem</div>
                                    {% endif %}
                                </div>
                            </a>

                            <div class="produto-conteudo">
                                <a href="/produto/{{ produto.slug or produto.id }}" class="produto-titulo-link">
                                    <div class="produto-titulo">{{ produto.nome }}</div>
                                </a>

                                {% if produto.descricao_curta %}
                                    <div class="produto-subinfo">{{ produto.descricao_curta }}</div>
                                {% endif %}

                                <div class="produto-precos">
                                    {% if produto.preco_antigo and produto.preco_antigo > produto.preco %}
                                        <div class="produto-preco-antigo">
                                            R$ {{ "%.2f"|format(produto.preco_antigo)|replace('.', ',') }}
                                        </div>
                                    {% else %}
                                        <div class="produto-preco-antigo vazio"></div>
                                    {% endif %}

                                    <div class="produto-preco-atual">
                                        {% set partes = "%.2f"|format(produto.preco)|replace('.', ',').split(',') %}
                                        <span class="produto-preco-moeda">R$</span>
                                        <span class="produto-preco-valor">{{ partes[0] }}</span><span class="produto-preco-centavos">,{{ partes[1] }}</span>
                                    </div>
                                </div>

                                <div class="produto-tags">
                                    {% if produto.ultimas_unidades %}
                                        <span class="produto-tag produto-tag--estoque">Últimas unidades</span>
                                    {% endif %}

                                    {% if produto.mais_vendido %}
                                        <span class="produto-tag produto-tag--vendido">Mais vendido</span>
                                    {% endif %}

                                    {% if produto.novo %}
                                        <span class="produto-tag produto-tag--novo">Novo</span>
                                    {% endif %}
                                </div>
                            </div>

                            <div class="produto-footer">
                                <a href="/produto/{{ produto.slug or produto.id }}" class="produto-btn-detalhes">
                                    Ver produto
                                </a>

                                <button class="btn-add-carrinho"
                                        type="button"
                                        data-produto-id="{{ produto.id }}"
                                        aria-label="Adicionar {{ produto.nome }} ao carrinho">
                                    <i class="fa fa-shopping-cart"></i>
                                </button>
                            </div>
                        </div>
                    {% endfor %}
                </div>
            </section>

        </main>
    </div>
</div>
CSS completo da página V2
/* =========================
   BASE DA PÁGINA
========================= */
.vitrine-page {
    padding: 18px;
}

.vitrine-layout {
    display: grid;
    grid-template-columns: 260px minmax(0, 1fr);
    gap: 20px;
    align-items: start;
}

/* =========================
   HERO / TOPO
========================= */
.vitrine-hero {
    margin-bottom: 22px;
    border-radius: 24px;
    background: linear-gradient(135deg, #f7fafc 0%, #eef4f9 100%);
    border: 1px solid #e4ebf2;
    padding: 28px;
}

.vitrine-hero__conteudo {
    max-width: 760px;
}

.vitrine-hero__tag {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 999px;
    background: #fff4d6;
    color: #9a6700;
    font-size: 0.76rem;
    font-weight: 800;
    padding: 6px 10px;
    margin-bottom: 12px;
}

.vitrine-hero__titulo {
    margin: 0;
    color: #1f3448;
    font-size: 2rem;
    font-weight: 800;
    line-height: 1.15;
}

.vitrine-hero__texto {
    margin: 10px 0 0;
    color: #5f6f7f;
    font-size: 1rem;
    line-height: 1.55;
    max-width: 620px;
}

.vitrine-hero__acoes {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    margin-top: 18px;
}

.btn-hero {
    min-height: 44px;
    padding: 0 16px;
    border-radius: 12px;
    text-decoration: none;
    font-weight: 700;
    font-size: 0.9rem;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    transition: all 0.18s ease;
}

.btn-hero--primario {
    background: #173450;
    color: #fff;
}

.btn-hero--primario:hover {
    background: #102a43;
    color: #fff;
    transform: translateY(-1px);
}

.btn-hero--secundario {
    background: #fff;
    color: #173450;
    border: 1px solid #d8e2ec;
}

.btn-hero--secundario:hover {
    background: #f8fbfd;
    color: #173450;
}

.vitrine-hero__beneficios {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 18px;
}

.hero-pill {
    background: #ffffff;
    color: #33506e;
    border: 1px solid #e1e8ef;
    border-radius: 999px;
    padding: 6px 10px;
    font-size: 0.76rem;
    font-weight: 700;
}

/* =========================
   SIDEBAR
========================= */
.vitrine-sidebar {
    display: flex;
    flex-direction: column;
    gap: 18px;
}

.sidebar-bloco {
    background: #fff;
    border: 1px solid #e7ebf0;
    border-radius: 18px;
    padding: 16px;
    box-shadow: 0 3px 10px rgba(15, 23, 42, 0.04);
}

.sidebar-bloco__topo {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    margin-bottom: 14px;
}

.sidebar-bloco__topo h3 {
    margin: 0;
    color: #243b53;
    font-size: 0.95rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

.sidebar-bloco__topo a {
    color: #486581;
    font-size: 0.78rem;
    font-weight: 700;
    text-decoration: none;
}

.sidebar-lista {
    display: flex;
    flex-direction: column;
    gap: 14px;
}

.mini-card {
    position: relative;
    border: 1px solid #edf1f5;
    border-radius: 16px;
    background: #fbfcfd;
    padding: 10px;
}

.mini-card__badge {
    position: absolute;
    top: 8px;
    left: 8px;
    background: linear-gradient(135deg, #f59e0b, #ea580c);
    color: #fff;
    font-size: 0.7rem;
    font-weight: 800;
    border-radius: 999px;
    padding: 4px 7px;
    z-index: 2;
}

.mini-card__imagem-wrap {
    height: 90px;
    background: #fff;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 8px;
    text-decoration: none;
    overflow: hidden;
}

.mini-card__imagem {
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
}

.mini-card__sem-imagem {
    color: #9aa4af;
    font-size: 0.74rem;
}

.mini-card__titulo {
    display: block;
    color: #243b53;
    text-decoration: none;
    font-size: 0.8rem;
    font-weight: 700;
    line-height: 1.2rem;
    margin-bottom: 6px;

    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

.mini-card__preco-antigo {
    color: #9aa5b1;
    font-size: 0.72rem;
    text-decoration: line-through;
    margin-bottom: 2px;
}

.mini-card__rodape {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
}

.mini-card__preco {
    color: #173450;
    font-size: 0.95rem;
    font-weight: 800;
}

.mini-card__btn {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    border: none;
    background: #fff;
    color: #173450;
    box-shadow: 0 4px 10px rgba(15, 23, 42, 0.12);
    cursor: pointer;
}

.mini-card__tag {
    display: inline-flex;
    margin-top: 8px;
    padding: 4px 8px;
    border-radius: 999px;
    background: #fff3df;
    color: #af6a00;
    font-size: 0.68rem;
    font-weight: 700;
}

.sidebar-links {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.sidebar-link-item {
    display: flex;
    justify-content: space-between;
    gap: 10px;
    text-decoration: none;
    color: #243b53;
    border-radius: 12px;
    padding: 10px 12px;
    background: #f8fafc;
    transition: background 0.18s ease;
}

.sidebar-link-item:hover {
    background: #eef4f8;
}

.sidebar-link-item__nome {
    font-size: 0.8rem;
    font-weight: 700;
    line-height: 1.2rem;
}

.sidebar-link-item__preco {
    font-size: 0.78rem;
    font-weight: 800;
    color: #173450;
    white-space: nowrap;
}

/* =========================
   MAIN / SEÇÕES
========================= */
.vitrine-main {
    display: flex;
    flex-direction: column;
    gap: 24px;
}

.secao-vitrine {
    background: #fff;
    border: 1px solid #e7ebf0;
    border-radius: 20px;
    padding: 18px;
    box-shadow: 0 3px 10px rgba(15, 23, 42, 0.04);
}

.secao-vitrine__topo {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 14px;
    margin-bottom: 16px;
    flex-wrap: wrap;
}

.secao-vitrine__topo h2 {
    margin: 0;
    color: #243b53;
    font-size: 1.45rem;
    font-weight: 800;
}

.secao-vitrine__topo p {
    margin: 4px 0 0;
    color: #7b8794;
    font-size: 0.9rem;
}

/* =========================
   ORDENAÇÃO
========================= */
.ordenacao-wrap {
    display: flex;
    align-items: center;
    gap: 8px;
}

.ordenacao-wrap label {
    color: #52606d;
    font-size: 0.82rem;
    font-weight: 700;
}

.select-ordenacao {
    min-width: 160px;
    height: 40px;
    border-radius: 10px;
    border: 1px solid #d9e2ec;
    background: #fff;
    color: #243b53;
    padding: 0 12px;
    font-size: 0.84rem;
    font-weight: 600;
}

/* =========================
   CARDS DESTAQUE
========================= */
.cards-destaque {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 16px;
}

.card-destaque {
    display: grid;
    grid-template-columns: 1.15fr 0.85fr;
    gap: 14px;
    align-items: center;
    background: linear-gradient(135deg, #f8fbfd 0%, #eef4f8 100%);
    border: 1px solid #e2e8f0;
    border-radius: 20px;
    padding: 18px;
    min-height: 260px;
}

.card-destaque__conteudo {
    display: flex;
    flex-direction: column;
}

.card-destaque__badge {
    width: fit-content;
    display: inline-flex;
    border-radius: 999px;
    background: linear-gradient(135deg, #ef4444, #dc2626);
    color: #fff;
    font-size: 0.75rem;
    font-weight: 800;
    padding: 5px 9px;
    margin-bottom: 10px;
}

.card-destaque__conteudo h3 {
    margin: 0;
    color: #1f3448;
    font-size: 1.3rem;
    font-weight: 800;
    line-height: 1.25;
}

.card-destaque__conteudo p {
    margin: 10px 0 0;
    color: #5f6f7f;
    font-size: 0.92rem;
    line-height: 1.5;
}

.card-destaque__precos {
    margin-top: 16px;
}

.card-destaque__preco-antigo {
    color: #9aa5b1;
    font-size: 0.86rem;
    text-decoration: line-through;
    margin-bottom: 2px;
}

.card-destaque__preco-atual {
    color: #173450;
    font-size: 1.85rem;
    font-weight: 800;
    line-height: 1.1;
}

.card-destaque__acoes {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    margin-top: 18px;
}

.btn-card-destaque {
    min-height: 42px;
    padding: 0 14px;
    border-radius: 12px;
    border: none;
    text-decoration: none;
    font-weight: 700;
    font-size: 0.88rem;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
}

.btn-card-destaque--primario {
    background: #173450;
    color: #fff;
}

.btn-card-destaque--secundario {
    background: #fff;
    color: #173450;
    border: 1px solid #d8e2ec;
}

.card-destaque__imagem-wrap {
    height: 210px;
    border-radius: 18px;
    background: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    text-decoration: none;
    padding: 14px;
}

.card-destaque__imagem {
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
}

.card-destaque__sem-imagem {
    color: #9aa4af;
    font-size: 0.86rem;
}

/* =========================
   GRID DE PRODUTOS
========================= */
.produtos-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 18px;
}

.produto-card {
    position: relative;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    min-height: 335px;
    background: #ffffff;
    border: 1px solid #e7ebf0;
    border-radius: 18px;
    padding: 14px;
    box-shadow: 0 3px 10px rgba(15, 23, 42, 0.05);
    transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
    overflow: hidden;
}

.produto-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 24px rgba(15, 23, 42, 0.12);
    border-color: #d7dee7;
}

.produto-card--destaque {
    border-color: #ffd38a;
    box-shadow: 0 10px 24px rgba(245, 158, 11, 0.14);
}

.produto-card--destaque::after {
    content: "Destaque";
    position: absolute;
    top: 12px;
    right: 12px;
    background: #fff4d6;
    color: #9a6700;
    font-size: 0.72rem;
    font-weight: 800;
    padding: 4px 8px;
    border-radius: 999px;
    z-index: 3;
}

.produto-link-imagem {
    text-decoration: none;
}

.produto-imagem-wrap {
    height: 138px;
    background: #f8fafc;
    border-radius: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 10px;
    overflow: hidden;
    margin-bottom: 12px;
}

.produto-imagem {
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
    transition: transform 0.22s ease;
}

.produto-card:hover .produto-imagem {
    transform: scale(1.05);
}

.produto-sem-imagem {
    color: #9aa4af;
    font-size: 0.82rem;
    text-align: center;
}

.produto-badge-desconto {
    position: absolute;
    top: 12px;
    left: 12px;
    z-index: 4;
    color: #fff;
    font-size: 0.76rem;
    font-weight: 800;
    padding: 5px 9px;
    border-radius: 999px;
    line-height: 1;
    box-shadow: 0 6px 14px rgba(0, 0, 0, 0.14);
}

.produto-badge-desconto.desconto-baixo {
    background: linear-gradient(135deg, #94a3b8, #64748b);
}

.produto-badge-desconto.desconto-medio {
    background: linear-gradient(135deg, #f59e0b, #ea580c);
}

.produto-badge-desconto.desconto-alto {
    background: linear-gradient(135deg, #ef4444, #dc2626);
}

.produto-conteudo {
    flex: 1;
    display: flex;
    flex-direction: column;
}

.produto-titulo-link {
    text-decoration: none;
}

.produto-titulo {
    color: #1f3448;
    font-size: 0.92rem;
    font-weight: 700;
    line-height: 1.28rem;
    min-height: 42px;
    margin-bottom: 6px;

    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

.produto-subinfo {
    color: #7b8794;
    font-size: 0.77rem;
    line-height: 1.15rem;
    min-height: 18px;
    margin-bottom: 8px;

    display: -webkit-box;
    -webkit-line-clamp: 1;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

.produto-precos {
    margin-top: 4px;
}

.produto-preco-antigo {
    min-height: 18px;
    color: #98a3af;
    font-size: 0.79rem;
    text-decoration: line-through;
    margin-bottom: 2px;
}

.produto-preco-antigo.vazio {
    visibility: hidden;
}

.produto-preco-atual {
    color: #16324f;
    line-height: 1.05;
    display: flex;
    align-items: flex-start;
    gap: 2px;
    flex-wrap: nowrap;
}

.produto-preco-moeda {
    font-size: 0.95rem;
    font-weight: 700;
    margin-top: 7px;
}

.produto-preco-valor {
    font-size: 1.72rem;
    font-weight: 800;
    letter-spacing: -0.03em;
}

.produto-preco-centavos {
    font-size: 0.95rem;
    font-weight: 800;
    margin-top: 4px;
}

.produto-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 10px;
    min-height: 28px;
}

.produto-tag {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 4px 8px;
    border-radius: 999px;
    font-size: 0.7rem;
    font-weight: 700;
    white-space: nowrap;
}

.produto-tag--estoque {
    background: #fff3df;
    color: #af6a00;
}

.produto-tag--vendido {
    background: #edf5ff;
    color: #1f5fa8;
}

.produto-tag--novo {
    background: #ecfdf3;
    color: #1d7a46;
}

.produto-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    margin-top: 14px;
}

.produto-btn-detalhes {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-height: 40px;
    padding: 0 14px;
    border-radius: 12px;
    background: #f5f8fb;
    color: #23415f;
    text-decoration: none;
    font-size: 0.82rem;
    font-weight: 700;
    transition: background 0.18s ease, color 0.18s ease, transform 0.18s ease;
}

.produto-btn-detalhes:hover {
    background: #eaf1f7;
    color: #173450;
    transform: translateY(-1px);
}

.btn-add-carrinho {
    width: 44px;
    height: 44px;
    border: none;
    border-radius: 50%;
    background: #fff;
    color: #16324f;
    box-shadow: 0 4px 12px rgba(15, 23, 42, 0.14);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.18s ease;
    flex-shrink: 0;
}

.btn-add-carrinho:hover {
    background: #16324f;
    color: #fff;
    transform: scale(1.06);
    box-shadow: 0 10px 20px rgba(22, 50, 79, 0.24);
}

/* =========================
   RESPONSIVO
========================= */
@media (max-width: 1200px) {
    .cards-destaque {
        grid-template-columns: 1fr;
    }
}

@media (max-width: 992px) {
    .vitrine-layout {
        grid-template-columns: 1fr;
    }

    .vitrine-sidebar {
        order: 2;
    }

    .vitrine-main {
        order: 1;
    }
}

@media (max-width: 768px) {
    .vitrine-page {
        padding: 12px;
    }

    .vitrine-hero {
        padding: 20px;
    }

    .vitrine-hero__titulo {
        font-size: 1.55rem;
    }

    .card-destaque {
        grid-template-columns: 1fr;
    }

    .card-destaque__imagem-wrap {
        height: 180px;
    }

    .produtos-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 14px;
    }

    .produto-card {
        min-height: 305px;
        padding: 12px;
        border-radius: 16px;
    }

    .produto-imagem-wrap {
        height: 118px;
    }

    .produto-preco-valor {
        font-size: 1.48rem;
    }

    .produto-btn-detalhes {
        padding: 0 10px;
        font-size: 0.76rem;
    }
}

@media (max-width: 480px) {
    .produtos-grid {
        grid-template-columns: 1fr 1fr;
    }

    .produto-titulo {
        font-size: 0.86rem;
    }

    .produto-preco-valor {
        font-size: 1.34rem;
    }

    .btn-add-carrinho {
        width: 40px;
        height: 40px;
    }

    .select-ordenacao {
        min-width: 130px;
    }
}
O que essa estrutura resolve

Ela melhora 5 pontos importantes:

1. Hierarquia

Agora existe:

hero
destaques
ofertas
catálogo
2. Curadoria

A lateral deixa de ser sobra e vira apoio comercial

3. Conversão

Preço, selo, ação e destaque ficam mais fortes

4. Escaneabilidade

O usuário entende rápido o que ver primeiro

5. Sensação de marketplace

Fica bem mais próximo de uma vitrine profissional

Ordem real de implantação

Eu faria assim:

etapa 1

Substituir apenas o card atual pelo novo produto-card

etapa 2

Adicionar a seção Destaques

etapa 3

Adicionar o hero superior

etapa 4

Reorganizar a lateral em blocos

Assim você evolui sem quebrar tudo de uma vez.

Observação importante

Para essa página funcionar bem no seu sistema, o ideal é o backend já entregar listas separadas:

promocoes
mais_vendidos
destaques
ofertas_semana
todos_produtos

Se ainda não tiver isso, dá para começar com recortes da mesma lista.