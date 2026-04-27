# Deploy em produção — Alterações de pagamento e PDV

Checklist para colocar em produção as alterações que garantem o fluxo de pagamento na compra (PDV + gateway Mercado Pago) e a consistência de `venda_pagamentos`.

---

## Alterações incluídas

1. **Front PDV (`app/static/js/pdv.js`)**  
   - Payload da venda passa a enviar `produto_cliente_id` nos itens (em vez de `estoque_id`), conforme esperado pela API `POST /vendas`. Sem isso, a criação da venda falhava em validação.

2. **Webhook Mercado Pago (`app/api/webhooks_mercadopago.py`)**  
   - Ao reconciliar pagamento de venda, se não existir `VendaPagamento` para a venda/forma, o webhook **cria** um registro. Assim, vendas fechadas só pelo gateway passam a ter linha em `venda_pagamentos` (relatórios e dashboard corretos).  
   - Reconsulta antes de criar, para evitar duplicata em retentativas do webhook.  
   - Uso explícito de `Decimal` e import no topo do arquivo.

---

## Pré-requisitos (já devem estar em produção)

- **Variáveis de ambiente:** `REDIS_URL` (ou `CELERY_BROKER_URL`), `MP_WEBHOOK_SECRET` (ou secret nas configs por estabelecimento).  
- **Webhook MP:** URL configurada no Mercado Pago, ex.: `https://www.ibix.com.br/api/webhooks/mercadopago`.  
- **Configs de pagamento:** Estabelecimentos que usam gateway no PDV precisam de pelo menos uma config ativa em **Pagamentos** (Mercado Pago com `access_token`).

---

## Checklist de deploy

- [ ] **Backup:** Fazer backup do banco (ex.: `scripts/backup_pdv-solumatica.sh` ou procedimento usual).
- [ ] **Código:** Atualizar o código no servidor (git pull ou deploy do branch que contém estas alterações).
- [ ] **Migrações:** Não há migração de banco para estas alterações; não é necessário rodar `alembic upgrade`.
- [ ] **Reiniciar aplicação:**  
  `sudo systemctl restart pdv_solumatica`  
  (e, se quiser, `sudo systemctl restart pdv_solumatica-celery`).
- [ ] **Verificar saúde:**  
  `curl -s https://www.ibix.com.br/api/health` deve retornar `{"status":"ok", ...}`.
- [ ] **Teste rápido PDV:** Em homologação ou produção, abrir o PDV, adicionar produto, finalizar venda com **dinheiro** e confirmar que a venda é criada e aparece na listagem.
- [ ] **Teste gateway (opcional):** Com estabelecimento que tenha config Mercado Pago, finalizar uma venda com cartão/PIX; deve abrir a URL do checkout MP e, após pagamento, o webhook deve atualizar/criar o `VendaPagamento`.

---

## Rollback (se necessário)

1. Reverter o commit ou branch para a versão anterior.  
2. Reiniciar: `sudo systemctl restart pdv_solumatica`.  
3. Nenhuma migração a reverter; os registros de `venda_pagamentos` criados pelo webhook permanecem no banco (não quebram nada).

---

## Observações

- **Redis:** As melhorias de Redis (prefixo de chaves, pool, timeout) são compatíveis com produção; variáveis opcionais em `.env.example` (`REDIS_KEY_PREFIX`, `REDIS_TIMEOUT`, `REDIS_MAX_CONNECTIONS`).  
- **Logs:** Em caso de problema, verificar `logs/errors.log` e `journalctl -u pdv_solumatica -n 100`.
