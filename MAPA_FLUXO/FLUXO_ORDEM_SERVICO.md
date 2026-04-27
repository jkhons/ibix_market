# FLUXO DE ORDENS DE SERVIÇO

## Visão Geral

Este documento detalha o fluxo completo de criação, execução e fechamento de ordens de serviço no PDV Ibix. Ordens de serviço podem estar vinculadas a agendamentos, processos e clientes, e podem gerar vendas e notas fiscais.

**Modelo:** `app/models/ordem_servico.py`  
**API:** `app/api/v1/ordens_servico.py`  
**Tabela:** `ordem_servico`

---

## Pré-requisitos

- Cliente cadastrado no sistema (obrigatório)
- Equipamento(s) cadastrado(s) (opcional, mas recomendado)
- Agendamento ou Processo (opcional)
- Usuário autenticado com permissão para criar/editar ordens de serviço

---

## Fluxo Principal de Criação

```mermaid
flowchart TD
    Start([Usuário acessa criação de OS]) --> ValidarPermissao{Usuário tem permissão?}
    ValidarPermissao -->|Não| ErroPermissao[Erro: Sem permissão]
    ValidarPermissao -->|Sim| SelecionarCliente[Selecionar cliente]
    
    SelecionarCliente --> ClienteExiste{Cliente existe?}
    ClienteExiste -->|Não| ErroCliente[Erro: Cliente não encontrado]
    ClienteExiste -->|Sim| DefinirOrigem[Definir origem da OS]
    
    DefinirOrigem --> TemAgendamento{Tem agendamento?}
    TemAgendamento -->|Sim| VincularAgendamento[Vincular agendamento]
    TemAgendamento -->|Não| TemProcesso{Tem processo?}
    
    VincularAgendamento --> ValidarAgendamento{Agendamento válido?}
    ValidarAgendamento -->|Não| ErroAgendamento[Erro: Agendamento inválido]
    ValidarAgendamento -->|Sim| PreencherDados
    TemProcesso -->|Sim| VincularProcesso[Vincular processo]
    TemProcesso -->|Não| PreencherDados[Preencher dados da OS]
    
    VincularProcesso --> ValidarProcesso{Processo válido?}
    ValidarProcesso -->|Não| ErroProcesso[Erro: Processo inválido]
    ValidarProcesso -->|Sim| PreencherDados
    
    PreencherDados --> SelecionarEquipamentos[Selecionar equipamentos]
    SelecionarEquipamentos --> AdicionarItens[Adicionar itens/serviços]
    AdicionarItens --> GerarCodigo[Gerar código único]
    GerarCodigo --> CriarRegistro[Criar registro no banco]
    
    CriarRegistro --> StatusAberta[Status: aberta]
    StatusAberta --> Sucesso[Ordem de serviço criada]
    Sucesso --> RetornarDados[Retornar dados da OS]
    
    ErroPermissao --> End([Fim])
    ErroCliente --> End
    ErroAgendamento --> End
    ErroProcesso --> End
    RetornarDados --> End
    
    style Start fill:#e1f5ff
    style Sucesso fill:#e1ffe1
    style ErroPermissao fill:#ffe1e1
    style ErroCliente fill:#ffe1e1
    style ErroAgendamento fill:#ffe1e1
    style ErroProcesso fill:#ffe1e1
```

---

## Campos Obrigatórios

| Campo | Tipo | Descrição | Validação |
|-------|------|-----------|-----------|
| `cliente_id` | Integer | ID do cliente | Obrigatório, FK para `clientes.id` |
| `codigo` | String(30) | Código único da OS | Obrigatório, único |
| `tipo` | Enum | Tipo de OS | Obrigatório: instalacao, manutencao, calibracao, afericao, reparo, visita, outro |
| `prioridade` | Enum | Prioridade | Obrigatório: baixa, media, alta, critica (default: media) |
| `status` | Enum | Status | Obrigatório: aberta, em_andamento, aguardando_material, aguardando_cliente, concluida, cancelada (default: aberta) |

### Campos Opcionais

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `agendamento_id` | Integer | FK para `agendamentos.id` |
| `processo_relacionado_id` | Integer | FK para `processos.id` |
| `responsavel_id` | Integer | FK para `usuarios.id` |
| `lacre_utilizado_id` | Integer | FK para `lacres_selos.id` |
| `data_prevista` | DateTime | Data prevista de conclusão |
| `observacoes` | Text | Observações da OS |

---

## Status e Transições

```mermaid
stateDiagram-v2
    [*] --> aberta: Criar OS
    aberta --> em_andamento: Iniciar execução
    aberta --> cancelada: Cancelar
    em_andamento --> aguardando_material: Aguardar material
    em_andamento --> aguardando_cliente: Aguardar cliente
    aguardando_material --> em_andamento: Material recebido
    aguardando_cliente --> em_andamento: Cliente disponível
    em_andamento --> concluida: Finalizar
    aguardando_material --> concluida: Finalizar
    aguardando_cliente --> concluida: Finalizar
    concluida --> [*]
    cancelada --> [*]
```

---

## Fluxo de Execução

```mermaid
flowchart TD
    Start([OS aberta]) --> IniciarExecucao[Iniciar execução]
    IniciarExecucao --> StatusEmAndamento[Status: em_andamento]
    StatusEmAndamento --> ExecutarServico[Executar serviço]
    
    ExecutarServico --> NecessitaMaterial{Necessita material?}
    NecessitaMaterial -->|Sim| StatusAguardandoMaterial[Status: aguardando_material]
    NecessitaMaterial -->|Não| NecessitaCliente{Necessita cliente?}
    
    StatusAguardandoMaterial --> MaterialRecebido{Material recebido?}
    MaterialRecebido -->|Sim| StatusEmAndamento
    MaterialRecebido -->|Não| StatusAguardandoMaterial
    
    NecessitaCliente -->|Sim| StatusAguardandoCliente[Status: aguardando_cliente]
    NecessitaCliente -->|Não| ServicoConcluido{Serviço concluído?}
    
    StatusAguardandoCliente --> ClienteDisponivel{Cliente disponível?}
    ClienteDisponivel -->|Sim| StatusEmAndamento
    ClienteDisponivel -->|Não| StatusAguardandoCliente
    
    ServicoConcluido -->|Não| ExecutarServico
    ServicoConcluido -->|Sim| FinalizarOS[Finalizar OS]
    FinalizarOS --> StatusConcluida[Status: concluida]
    StatusConcluida --> GerarVenda{Gerar venda?}
    
    GerarVenda -->|Sim| CriarVenda[Criar venda]
    GerarVenda -->|Não| End
    CriarVenda --> End([Fim])
    
    style Start fill:#e1f5ff
    style StatusConcluida fill:#e1ffe1
```

---

## Relacionamentos

### Relacionamentos da Ordem de Serviço

```mermaid
erDiagram
    ORDEM_SERVICO }o--|| CLIENTE : pertence_a
    ORDEM_SERVICO }o--o| AGENDAMENTO : vinculada_a
    ORDEM_SERVICO }o--o| PROCESSO : relacionada_a
    ORDEM_SERVICO }o--o| LACRE_SELO : utiliza_lacre
    ORDEM_SERVICO }o--o| USUARIO : responsavel
    ORDEM_SERVICO ||--o{ ORDEM_SERVICO_EQUIPAMENTO : tem_equipamentos
    ORDEM_SERVICO ||--o{ ORDEM_SERVICO_ITEM : tem_itens
    ORDEM_SERVICO ||--o| VENDA : gera
    
    ORDEM_SERVICO {
        int id PK
        string codigo UK
        int cliente_id FK
        int agendamento_id FK
        int processo_relacionado_id FK
        enum tipo
        enum prioridade
        enum status
    }
```

---

## APIs Envolvidas

### Criar Ordem de Serviço
```
POST /api/v1/ordens-servico
Content-Type: application/json

{
  "cliente_id": 1,
  "agendamento_id": 1,
  "tipo": "calibracao",
  "prioridade": "alta",
  "observacoes": "Calibração de balança"
}

Response: 201 Created
{
  "id": 1,
  "codigo": "OS-2026-0001",
  "status": "aberta",
  ...
}
```

### Atualizar Status
```
PUT /api/v1/ordens-servico/{id}
Content-Type: application/json

{
  "status": "em_andamento"
}

Response: 200 OK
```

---

## Regras de Negócio

1. **Cliente Obrigatório:** OS deve estar sempre vinculada a um cliente
2. **Código Único:** Código da OS deve ser único no sistema
3. **Status Inicial:** OS é criada com status "aberta"
4. **Equipamentos:** OS pode ter múltiplos equipamentos (N:N)
5. **Itens:** OS pode ter múltiplos itens (materiais, serviços, lacres)
6. **Geração de Venda:** OS concluída pode gerar venda automaticamente

---

## Referências

- [INDICE.md](INDICE.md) - Índice dos fluxos
- [FLUXO_CONTRATOS_AGENDAMENTO.md](FLUXO_CONTRATOS_AGENDAMENTO.md) - Agendamentos
- [FLUXO_CERTIFICACAO_CALIBRACAO.md](FLUXO_CERTIFICACAO_CALIBRACAO.md) - Calibração
- [FLUXO_FINANCEIRO.md](FLUXO_FINANCEIRO.md) - Fluxo financeiro
- MAPA_SISTEMA/MAPA_DO_SISTEMA.md - Estrutura do banco (Parte 2)

---

**Última Atualização:** 2026-01-23
