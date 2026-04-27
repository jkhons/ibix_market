# Checklist Backend — Módulo Frete / Logística

Use este checklist para validar o backend do módulo de frete (entregador + logística) manualmente ou via testes automatizados.

---

## 1. Autenticação entregador

| # | Item | Como validar | Teste auto |
|---|------|----------------|------------|
| 1.1 | `create_entregador_token` retorna JWT com `sub`, `tipo=entregador` | Unit: decodificar token e checar payload | `test_create_entregador_token_payload` |
| 1.2 | Login com e-mail/senha inválidos retorna 401 ou 422 | POST /api/v1/entregador/login body inválido | `test_entregador_login_credenciais_invalidas_401_ou_422` |
| 1.3 | Login com credenciais válidas retorna 200, `access_token`, `entregador` | POST login (depende de seed entregador) | `test_entregador_login_ok_retorna_token_e_entregador` |
| 1.4 | Resposta de login contém `entregador.id`, `entregador.nome`, `entregador.tipo_veiculo` | Conferir JSON da resposta | (no test_login_ok) |
| 1.5 | Rotas protegidas sem token retornam 401 | GET entregas-disponiveis, minhas-entregas, etc. sem Authorization | `test_entregas_disponiveis_sem_token_401` |

---

## 2. API Entregador (com token)

| # | Item | Como validar | Teste auto |
|---|------|----------------|------------|
| 2.1 | GET entregas-disponiveis com token retorna 200 e lista (pode ser vazia) | Header Bearer token válido | `test_entregas_disponiveis_com_token_200` |
| 2.2 | Contrato: cada item disponível tem id, pedido_id, valor_frete, loja_nome (opcional) | Inspecionar JSON | (no test_entregas_disponiveis) |
| 2.3 | POST aceitar entrega inexistente retorna 404 | POST /entregas/99999/aceitar com token | `test_aceitar_entrega_inexistente_404` |
| 2.4 | POST aceitar entrega já aceita retorna 409 | Aceitar mesma entrega duas vezes (ou mock) | `test_aceitar_entrega_ja_aceita_409` (se dados) |
| 2.5 | GET minhas-entregas com token retorna 200 e lista | Header Bearer | `test_minhas_entregas_com_token_200` |
| 2.6 | GET detalhe entrega inexistente retorna 404 | GET /entregas/99999 com token | `test_detalhe_entrega_inexistente_404` |
| 2.7 | POST status com transição inválida retorna 400 | Ex.: status "entregue" quando entrega está "aceita" (pula em_retirada) | `test_atualizar_status_transicao_invalida_400` |
| 2.8 | Entregador não pode alterar status de entrega de outro | POST status em entrega cujo entregador_id != logado → 400/403 | (service test ou API) |

---

## 3. API Logística (tenant)

| # | Item | Como validar | Teste auto |
|---|------|----------------|------------|
| 3.1 | Sem token tenant: POST criar, GET listar, GET detalhe, POST publicar, POST cancelar retornam 401 | Todas as rotas sem Authorization | `test_logistica_sem_token_401` |
| 3.2 | GET /logistica/entregas com token tenant retorna 200 e lista | Token de usuário com permissão marketplace | (opcional, depende fixture) |
| 3.3 | POST criar entrega com pedido_id fora do escopo retorna 403 | Token de outro tenant | (opcional) |
| 3.4 | POST criar entrega com pedido inexistente retorna 404 | pedido_id=99999 | `test_logistica_criar_pedido_inexistente_404` (se auth mock) |
| 3.5 | GET detalhe entrega inexistente retorna 404 | GET /entregas/99999 com token | `test_logistica_detalhe_inexistente_404` |

---

## 4. Regras de negócio (services)

| # | Item | Como validar | Teste auto |
|---|------|----------------|------------|
| 4.1 | Criar entrega: pedido deve pertencer ao tenant | Service ou API com tenant_id diferente | (API test 3.3) |
| 4.2 | Não pode existir duas entregas para o mesmo pedido | Segundo criar_entrega mesmo pedido_id → ValueError | `test_criar_entrega_duplicada_erro` |
| 4.3 | Publicar só se status aguardando_publicacao | publicar_entrega com status disponivel → ValueError | (service unit) |
| 4.4 | Aceite: só se status disponivel e entregador_id NULL | Service aceitar_entrega | (API 2.4) |
| 4.5 | Máquina de estados: aceita→em_retirada→retirada→em_rota→entregue/falha | atualizar_status_entrega com transições inválidas | `test_status_transicoes_invalidas` |
| 4.6 | Cancelar: só em aguardando_publicacao, disponivel ou aceita | cancelar_entrega com status entregue → ValueError | (service unit) |
| 4.7 | marcar_entregas_expiradas: entregas disponivel com aceita_ate_em < now viram expirada | Chamar service e checar status + evento | (service unit com db) |

---

## 5. Contratos e constantes

| # | Item | Como validar | Teste auto |
|---|------|----------------|------------|
| 5.1 | Constantes de status existem e têm valores corretos (ex.: DISPONIVEL == "disponivel") | Import e assert | `test_constantes_status` |
| 5.2 | Schema EnderecoEntregaJson tem campos cep, logradouro, numero, bairro, cidade, uf, referencia | Import e model_validate | (opcional) |
| 5.3 | Resposta EntregaOut inclui eventos (lista) | GET detalhe entrega e checar campo eventos | (no test detalhe) |

---

## 6. Execução dos testes

```bash
# Todos os testes do módulo frete/logística
pytest tests/test_frete_logistica.py -v

# Com cobertura (opcional)
pytest tests/test_frete_logistica.py -v --tb=short
```

Testes que dependem de dados no banco (ex.: login entregador com seed) podem usar `pytest.skip` ou fixture com dados mínimos quando o banco estiver disponível.
