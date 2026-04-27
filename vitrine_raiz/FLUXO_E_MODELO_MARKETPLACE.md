# 3. Fluxo atual do comprador

Como o comprador navega hoje (mesmo que incompleto):

1. **Entra na home**  
   Acessa `/loja`. Vê a faixa “Destaques” (carrossel com até 8 produtos, carregados via API e embaralhados) e o bloco “Produtos” com grid de cards (GET `/api/v1/loja/anuncios`). Ordenação: Mais recentes, Menor preço, Maior preço, Nome.

2. **Clica em categoria**  
   A rota existe: `/loja/categoria/{slug}` (ex.: `/loja/categoria/eletronicos`). O mesmo template da home é usado, com `categoria_id` e `categoria_nome` no contexto. **Hoje não há menu de categorias na home** — para chegar na listagem por categoria o usuário precisa do link direto ou de um link futuro (menu, footer, etc.).

3. **Abre a listagem**  
   É a mesma página da home (index), mas com filtro por categoria ou por busca:
   - **Categoria:** `categoria_id` enviado na chamada à API; o título do bloco mostra o nome da categoria.
   - **Busca:** formulário no header (action `/loja/busca`, query `q`). A mesma listagem é exibida com `q` na API.

4. **Filtra**  
   Na listagem há apenas o **select “Ordenar”** (recent, preco_asc, preco_desc, nome). Não há filtros por faixa de preço, condição, loja etc. A busca é só pelo campo do header.

5. **Entra no produto**  
   Clica em um card e vai para `/loja/produto/{id}`. A página carrega o anúncio via GET `/api/v1/loja/anuncios/{id}` e exibe: galeria de imagens, título, “Vendido por [nome_loja]”, preço (original e promocional), quantidade, botões “Adicionar ao carrinho” e “Comprar agora”, selos “Compra segura” e “Entrega para todo o Brasil”, e (se houver) descrição e tabela de características (atributos).

6. **Adiciona ao carrinho / chama vendedor / solicita serviço**  
   - **Adicionar ao carrinho:** sim. O item vai para o carrinho (localStorage). Badge no header atualiza.  
   - **Comprar agora:** adiciona ao carrinho e redireciona para `/loja/carrinho`.  
   - **Chamar vendedor / solicitar serviço:** não existe hoje. Não há botão “Fale com o vendedor”, WhatsApp ou fluxo de orçamento/serviço na vitrine.  
   - Do carrinho o usuário pode ir para **Checkout** (formulário: nome, e-mail, telefone, documento, tipo de entrega, endereço). POST `/api/v1/loja/checkout` cria o pedido; em sucesso, redireciona para `/loja/obrigado?pedido_id=...`.

**Resumo do fluxo:** Home → (opcional) categoria/busca → listagem (ordenar) → produto → carrinho → checkout → obrigado. Sem contato com vendedor e sem fluxo de serviço na vitrine.

---

# 4. Modelo do marketplace

## É catálogo com preço fixo?

**Sim, na prática.** Cada anúncio tem `preco_original` e opcionalmente `preco_promocional`. O comprador vê o preço e finaliza pelo checkout (pedido com valor fixo). Não há leilão nem “proposta de preço”.

## É marketplace de vários vendedores?

**Sim.** Existem várias **lojas** (`LojaMarketplace`), cada uma ligada a um estabelecimento (cliente). Cada anúncio pertence a uma loja. Na listagem e no produto aparecem `nome_loja` e `slug_loja`. O carrinho e o checkout tratam **um pedido por loja** (se houver itens de várias lojas, o usuário é avisado e finaliza um pedido por vez).

## Existe serviço e produto no mesmo ambiente?

**Não hoje.** A vitrine e a API de anúncios são só para **produtos** (anúncios atrelados a `ProdutoCliente`). Não há tipo “serviço” no anúncio nem fluxo de orçamento/serviço na loja pública. Serviços/orçamentos existem em outros módulos do sistema (negócios), não na vitrine.

## O usuário compra direto ou entra em contato?

**Compra direto.** Fluxo: ver produto → carrinho → checkout (dados do comprador + tipo de entrega + endereço) → POST checkout → pedido criado. Não há “Fale com o vendedor”, WhatsApp ou “Solicitar orçamento” na vitrine.

## Existe entrega, retirada ou ambos?

**Ambos.** No checkout o comprador escolhe:
- **Retirada** (`tipo_entrega: "retirada"`)
- **Entrega** (`tipo_entrega: "entrega"`), com campo `endereco_entrega` e `taxa_entrega` no pedido.

A loja (vendedor) tem configuração: `tipo_entrega`, `raio_entrega_km`, `taxa_entrega_fixa`, `entrega_gratis_apos`. Hoje o front não calcula frete por CEP; o checkout envia `taxa_entrega` (valor informado no fluxo).

## Haverá publicação de anúncios como no Mercado Livre?

**Já existe um modelo de “publicação”.** O anúncio tem `status` (ex.: rascunho, publicado). Só anúncios com `status == "publicado"` e loja ativa aparecem na vitrine. O vendedor (pelo painel/marketplace) cria anúncios a partir de produtos do cadastro e publica. Não é um marketplace aberto a qualquer pessoa criar conta e anunciar por conta própria sem vínculo com o sistema — as lojas estão atreladas a clientes/estabelecimentos do PDV.

---

# 5. Estrutura do card de produto (dados do item)

O que a API e o modelo expõem hoje para um item (anúncio) na vitrine:

| Dado | Existe hoje? | Onde / observação |
|------|----------------|-------------------|
| **Título** | Sim | `titulo` (listagem e detalhe) |
| **Imagem** | Sim | `imagens` — lista de URLs (uma ou várias); na listagem usa a primeira |
| **Preço** | Sim | `preco_original`; na vitrine usa preço efetivo (promocional se houver) |
| **Desconto** | Implícito | `preco_promocional`; quando preenchido e > 0, o front mostra preço riscado e badge “Oferta” |
| **Parcelamento** | Não | Não há campo nem exibição de parcelas na API/vitrine |
| **Frete** | Parcial | No **pedido**: `tipo_entrega`, `endereco_entrega`, `taxa_entrega`. No **card/listagem** não há cálculo nem exibição de frete (ex.: “Frete grátis”). A **loja** tem `taxa_entrega_fixa`, `entrega_gratis_apos`, `raio_entrega_km` — não expostos no card |
| **Localização** | Não | Não há campo de cidade/região do vendedor ou do produto no anúncio/card |
| **Avaliação** | Back-end sim, card não | Existe modelo `AvaliacaoMarketplace` e endpoint GET `/anuncios/{id}/avaliacoes`. **Não** entra em `AnuncioVitrineResponse` nem é exibido no card ou na listagem |
| **Vendedor** | Sim | `nome_loja`, `slug_loja` (e no detalhe objeto `loja` com id, slug, nome_loja, descricao). No card da listagem aparece `nome_loja` (opcional no layout) |
| **Condição (novo/usado)** | Não | Não há campo no modelo `AnuncioPlataforma` nem no schema da vitrine |
| **Estoque** | Sim (dado) | `estoque_atual` na API. Na vitrine atual **não** é exibido no card; no detalhe do produto poderia ser usado para “indisponível” ou limite de quantidade |
| **Tempo de envio** | Não | Não há campo “prazo de entrega” ou “envio em X dias” no anúncio |
| **Badge/promoção** | Sim | Badge “Oferta” quando há `preco_promocional`; não há outros badges (ex.: “Novo”, “Últimas unidades”) |

## Resumo para desenho da vitrine

- **Já existem:** título, imagem, preço, desconto (via preço promocional), vendedor (nome da loja), estoque (dado na API), badge de oferta.
- **Existem no sistema mas não no card/listagem:** avaliações (endpoint separado), configuração de frete da loja.
- **Não existem (nem no modelo):** parcelamento, localização, condição novo/usado, tempo de envio; e no card não há exibição de frete nem de avaliação.

Se quiser evoluir o card (ex.: avaliação, condição, frete, parcelamento), será preciso definir novos campos no modelo/schema e/ou passar a consumir endpoints já existentes (avaliações) no front da vitrine.
