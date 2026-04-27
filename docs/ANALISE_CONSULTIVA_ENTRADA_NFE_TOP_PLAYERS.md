# Análise consultiva: Entrada de NF-e e conciliação — referência aos top players do mercado

**Objetivo:** Posicionar o módulo de entrada de notas fiscais (importação XML, conciliação e custo) do PDV Solumática em relação às práticas dos principais ERPs e sistemas de gestão fiscal do mercado brasileiro.

---

## 1. Top players e práticas de referência

Com base em soluções destacadas no mercado (NexGen, Nevra, NeoPdv, Datacaixa, entre outros), as práticas comuns são:

| Prática | Descrição | Referência de mercado |
|--------|------------|------------------------|
| **Importação automática via XML** | Upload ou recebimento de XML da NF-e (compras) e quebra em cabeçalho + itens, sem “inventar” produto na hora. | NexGen, Nevra, NeoPdv, Datacaixa: todos oferecem “entrada automática de notas via XML” ou “importador XML para entrada de compras”. |
| **Conciliação antes do estoque** | Itens do XML ficam pendentes até o usuário vincular ao produto interno (ou criar novo). Evita duplicação de cadastro e erro de custo. | Alinhado ao fluxo “pré-cadastro com conciliação (matching) antes de lançar no estoque” recomendado em boas práticas de ERP. |
| **Mapa fornecedor → SKU** | Tabela de equivalência (fornecedor + código do fornecedor → produto interno). Na próxima NF do mesmo fornecedor, o sistema já reconhece pelo código. | Equivalente ao “produto_fornecedor_map” / “código do fornecedor” em ERPs de compras. |
| **Custo com rateio** | Custo do item = vProd + rateio (frete, seguro, outras despesas) − rateio desconto + IPI + ICMS-ST quando aplicável. Rateio proporcional ao valor do item. | Padrão em sistemas de custeio (médio ponderado, custo de aquisição). |
| **Rastreabilidade fiscal** | Movimento de estoque referenciando documento e item da NF-e (nfe_documento_id, nfe_item_id). Auditoria e SPED facilitados. | Exigência de rastreabilidade em operações tributárias e fiscais. |
| **Multi-estabelecimento (tenant)** | Escopo por estabelecimento (cliente_id): cada loja com suas notas, fornecedores e produtos. | Comum em retaguarda/PDV com múltiplas lojas. |

---

## 2. Posicionamento do PDV Solumática

O desenho do módulo de entrada de notas (conforme plano em `.cursor/plans/entrada_de_notas_nfe_views_e_sql.plan.md`) está alinhado a essas práticas:

- **Três camadas:** documento (nfe_documentos), itens do XML (nfe_itens), movimentos (movimentacoes_estoque com nfe_documento_id/nfe_item_id). Não mistura com notas de emissão (notas_fiscais).
- **Produto canônico:** uso de `produtos_cliente` como SKU interno por estabelecimento; mapa em `produtos_fornecedor` (estendido com fator_conversao, ativo, UNIQUE por fornecedor+código).
- **Conciliação:** itens pendentes; auto-vínculo por GTIN (codigos_barras_cliente) e por mapa (fornecedor + cProd); tela de conciliação com sugestão do mapa; “confirmar e lançar” só após vínculo.
- **Custo:** modelo SQL de rateio (proporcional a vProd) e geração de movimentos com custo_total/custo_unitário.
- **Escopo:** cliente_id em nfe_documentos e nas views; APIs filtram por scope (allowed_ids).

Isso coloca o Solumática no mesmo patamar funcional dos players que oferecem “entrada automática de notas via XML” e conciliação antes de baixa no estoque.

---

## 3. Recomendações (visão consultiva)

1. **MVP de recebimento:** Manter upload de XML pelo usuário como primeiro canal; depois evoluir para pasta monitorada ou distribuição DF-e (certificado + regras de ambiente), como fazem soluções mais robustas.
2. **Sugestão por similaridade:** Em fase 2, considerar heurística por similaridade de descrição (xProd) + NCM + unidade para sugerir vínculo, sem substituir o mapa fornecedor+código como fonte principal.
3. **Eventos fiscais:** Tabela nfe_eventos (cancelamento, CCe, inutilização) para alinhar à rastreabilidade e a relatórios fiscais, quando a operação exigir.
4. **Integração com emissão:** Quando houver baixa de estoque por venda/NF de saída, manter vínculo opcional ao item da nota emitida (nfe_item_id ou equivalente) para rastreabilidade de saída.

---

## 4. Conclusão

O módulo de entrada de notas do PDV Solumática, com importação XML em 3 camadas, mapa fornecedor→produto, conciliação antes do estoque e custo rateado, está **alinhado às práticas dos principais ERPs e sistemas de gestão fiscal do mercado brasileiro**. As migrations e o plano técnico implementam esse desenho sem duplicar estruturas existentes (uso de fornecedores_cliente, produtos_cliente, produtos_fornecedor e movimentacoes_estoque).
