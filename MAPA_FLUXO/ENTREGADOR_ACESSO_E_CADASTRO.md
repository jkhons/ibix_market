# Entregador — Como criar e como acessar

## Como o entregador acessa o sistema

O entregador usa uma **área separada** do PDV (não usa login de usuário/tenant). Acesso pela **URL da aplicação** + o path da área entregador.

### Endereços (URLs)

| Uso | URL (relativa) | Exemplo (app em produção) |
|-----|----------------|---------------------------|
| **Login** | `/entregador/login` | `https://www.seudominio.com.br/entregador/login` |
| Após login (padrão) | `/entregador/disponiveis` | — |
| Minhas entregas | `/entregador/minhas-entregas` | — |
| Detalhe de uma entrega | `/entregador/entrega/{id}` | — |
| Sair | `/entregador/logout` | — |

**Em desenvolvimento (localhost):**  
`http://localhost:8000/entregador/login`

O entregador abre o link de **login**, informa **e-mail** e **senha**, e após sucesso é redirecionado para **Entregas disponíveis**. O token fica no cookie `entregador_token` (ou pode ser enviado no header `Authorization: Bearer <token>` nas chamadas à API).

---

## Como criar um entregador

Hoje não existe tela de “cadastro de entregador” no sistema. Há duas formas de criar:

### 1. Entregador de teste (seed)

Se a tabela `entregadores` estiver vazia, a migração **lg02** insere um entregador de teste:

- **E-mail:** `carlos.moto@teste.com`
- **Senha:** `123456`
- **Nome:** Carlos Moto | **Tipo veículo:** moto | **Cidade:** Barra Bonita

Para usar esse usuário, basta rodar as migrações (`alembic upgrade head`) e acessar `/entregador/login` com esse e-mail e senha.

### 2. Novos entregadores: script

Use o script na raiz do projeto para criar entregadores (senha hasheada com bcrypt, igual ao login):

```bash
cd /caminho/para/pdv_solumatica
.venv/bin/python scripts/criar_entregador.py "Nome Completo" "email@exemplo.com" "senha123" "17999999999" "moto" "Barra Bonita"
```

Argumentos (na ordem):

1. **Nome** (obrigatório)
2. **E-mail** (obrigatório, único)
3. **Senha** (obrigatório)
4. **Telefone** (opcional; use `-` para pular)
5. **Tipo veículo:** `moto`, `carro` ou `utilitario` (opcional; use `-` para NULL)
6. **Cidade** (opcional; use `-` para NULL)

Exemplo só com obrigatórios (telefone e cidade vazios):

```bash
.venv/bin/python scripts/criar_entregador.py "Maria Entregadora" "maria@empresa.com" "minhasenha" "-" "-" "-"
```

Depois disso, o entregador acessa normalmente por **`/entregador/login`** (ou a URL completa do seu ambiente, como na tabela acima).

---

## Resumo rápido

| Pergunta | Resposta |
|----------|----------|
| **Onde o entregador faz login?** | Na URL do sistema + `/entregador/login` (ex.: `https://www.seudominio.com.br/entregador/login`). |
| **Como criar o primeiro entregador?** | Rodar migrações (seed cria `carlos.moto@teste.com` / `123456`) ou usar o script `scripts/criar_entregador.py`. |
| **Como criar mais entregadores?** | Usar o script `criar_entregador.py` com nome, e-mail, senha e, se quiser, telefone, tipo_veiculo e cidade. |
