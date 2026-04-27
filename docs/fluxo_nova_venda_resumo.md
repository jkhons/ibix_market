# Fluxo de Nova Venda (resumo)

Rota: **GET /negocio/venda** → template `meu_negocio/vendas/index.html`.  
API: **POST /api/v1/vendas/** (criar venda), **POST /api/v1/venda-pagamentos/** (pagamentos fracionados).

1. **Abrir modal** — Usuário clica em "Nova Venda"; modal de venda abre.
2. **Cliente (opcional)** — Busca por nome/CNPJ ou deixa em branco (venda avulsa).
3. **Buscar produto** — Digita código, nome ou descrição; lista de produtos disponíveis é exibida.
4. **Adicionar itens** — Da lista, adiciona produtos ao carrinho (Itens da venda) com quantidade e valor.
5. **Resumo** — Subtotal, desconto, acréscimo e total são calculados; botão "Finalizar Venda" é habilitado se houver itens.
6. **Finalizar** — Clica em "Finalizar Venda"; abre popup de finalização.
7. **Popup** — Define pagamentos (fracionamento: dinheiro, PIX, cartão etc.), desconto/acréscimo em R$, PDV/caixa (opcional) e observações.
8. **Confirmar** — Clica em "Confirmar Venda"; front envia POST para criar venda e depois POST em venda-pagamentos para cada forma de pagamento.
9. **Conclusão** — Modal fecha; lista de vendas é atualizada; venda concluída.

**Impressão de cupom de venda:** Não está integrada. O botão "Imprimir" no modal de detalhes da venda usa apenas `window.print()` (impressão da página). Nem o fluxo Nova Venda nem o PDV disparam impressão em impressora térmica/cupom após finalizar a venda. A configuração de impressora do PDV (tipo, porta, cortar papel) e o endpoint `POST /api/v1/pdvs/{id}/testar-impressao` existem, mas não há envio de conteúdo de cupom para a impressora.

Diagrama: `docs/fluxo_nova_venda.svg`.
