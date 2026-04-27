---
name: Redis no Módulo Motor Tributário e Regras Fiscais ICMS
overview: Integrar Redis como cache para o motor tributário ICMS e a API de regras fiscais, reduzindo carga no banco e latência em emissões de NF-e com múltiplos itens e empresas.
todos: []
isProject: false
---

# Redis no Motor Tributário e Regras Fiscais ICMS

## Contexto

O sistema já utiliza Redis em `app/core/redis_cache.py` e `app/core/redis_client.py` para:

- Cache de subscription_blocked, permissões, loja categorias
- Blacklist de tokens (logout)
- Rate limiting

**Padrão vigente:** `_cache_get`, `_cache_set`, `_cache_delete`, TTL por use case, fallback para DB quando Redis indisponível. Chaves com prefixo `pdv:` via `prefix_key()`.

**Módulo alvo:** Motor tributário ICMS (`motor_tributario_icms.py`), API regras fiscais (`regras_fiscais_icms.py`), tabela `regras_fiscais_icms`, integração em `emissao_service.py`.

---

## Objetivo

Reduzir consultas ao PostgreSQL em cenários de:

1. Emissão de NF-e com vários itens (regras carregadas por empresa)
2. Múltiplas emissões simultâneas da mesma empresa
3. Listagem da tela de Regras Fiscais (opcional)

---

## 1. Cache de Regras Fiscais por Empresa (prioridade alta)

### Chave Redis

```
regras_fiscais_icms:empresa:{empresa_id}
```

### TTL

- **300 segundos (5 min)** — regras mudam com baixa frequência
- Variável: `REGRA_FISCAL_ICMS_TTL` no `.env` (opcional)

### Serialização

- Armazenar lista de dicts com os campos necessários para o motor (id, crt, tipo_operacao, tipo_destinatario, uf_destinatario, ncm_prefix, ncm_exato, cest, cfop_filtro, vigencia_inicio, vigencia_fim, cfop, origem_mercadoria, cst_icms, csosn, aliquota_icms, modalidade_bc_icms, percentual_reducao_bc, gera_icms_st, aliquota_icms_st, modalidade_bc_icms_st, percentual_mva_st, permite_credito_icms, ordem_prioridade)
- Usar `json.dumps(data, default=str)` para datas e Decimals

### Fluxo no motor

1. Em `resolver_regra_icms` (ou em `_aplicar_motor_tributario_itens` antes do loop):
  - Se `regras_precarregadas` é None, tentar obter do Redis
  - Se cache hit: deserializar e usar lista de objetos leve (dataclass ou dict) compatível com `_regra_compativel_contexto`
  - Se cache miss: query no DB, serializar e gravar no Redis

### Deserialização → objeto compatível

- O motor usa `RegraFiscalIcms` (ORM) em `_regra_compativel_contexto`, `_especificidade_regra`, `_validar_resultado_regra`
- Alternativa: criar `RegraFiscalIcmsCache` (dataclass ou NamedTuple) com os campos necessários e adaptar as funções a aceitar esse tipo (duck typing por atributos)
- Ou: deserializar para objetos "mock" com `__getattr`__ que lê do dict

**Recomendação:** Criar dataclass `RegraFiscalIcmsCache` e refatorar `_regra_compativel_contexto`, `_especificidade_regra`, `_validar_resultado_regra` para aceitar Union[RegraFiscalIcms, RegraFiscalIcmsCache] — ambos expõem os mesmos atributos.

---

## 2. Invalidação no CRUD

### Pontos de invalidação


| Ação                 | Chave a invalidar                          |
| -------------------- | ------------------------------------------ |
| POST criar regra     | `regras_fiscais_icms:empresa:{empresa_id}` |
| PUT atualizar regra  | `regras_fiscais_icms:empresa:{empresa_id}` |
| DELETE excluir regra | `regras_fiscais_icms:empresa:{empresa_id}` |


### Onde chamar

- Em `criar_regra_fiscal_icms`, após `db.commit()`: `invalidate_regras_fiscais_empresa(regra_data.empresa_id)`
- Em `atualizar_regra_fiscal_icms`, após `db.commit()`: `invalidate_regras_fiscais_empresa(regra.empresa_id)`
- Em `excluir_regra_fiscal_icms`, após `db.delete()` (antes do commit): guardar `empresa_id`, após commit: `invalidate_regras_fiscais_empresa(empresa_id)`

---

## 3. Funções em redis_cache.py

### Novas funções

```python
REGRA_FISCAL_ICMS_TTL = 300  # segundos

def get_regras_fiscais_empresa_cached(empresa_id: int, fetch_from_db: Callable[[], List]) -> List:
    """Retorna regras ativas da empresa. fetch_from_db retorna lista de RegraFiscalIcms."""
    key = f"regras_fiscais_icms:empresa:{empresa_id}"
    cached = _cache_get(key)
    if cached is not None:
        try:
            return _deserializar_regras(cached)  # List[RegraFiscalIcmsCache]
        except Exception:
            pass
    regras = fetch_from_db()
    _cache_set(key, _serializar_regras(regras), REGRA_FISCAL_ICMS_TTL)
    return regras

def invalidate_regras_fiscais_empresa(empresa_id: int) -> None:
    """Invalida cache de regras da empresa."""
    _cache_delete(f"regras_fiscais_icms:empresa:{empresa_id}")

def invalidate_regras_fiscais_all() -> None:
    """Invalida todos os caches de regras fiscais. Útil para manutenção."""
    client = get_redis_client()
    if client is None:
        return
    try:
        pattern = prefix_key("regras_fiscais_icms:empresa:*")
        for key in client.scan_iter(match=pattern):
            client.delete(key)
    except Exception:
        pass
```

---

## 4. Integração no emissao_service.py

Em `_aplicar_motor_tributario_itens`:

**Antes:**

```python
regras_empresa = (
    db.query(RegraFiscalIcms)
    .filter(...)
    .all()
)
```

**Depois:**

```python
from app.core.redis_cache import get_regras_fiscais_empresa_cached

def _fetch_regras(db, empresa_id):
    return db.query(RegraFiscalIcms).filter(
        RegraFiscalIcms.empresa_id == empresa_id,
        RegraFiscalIcms.ativo == True,
    ).order_by(RegraFiscalIcms.ordem_prioridade.asc()).all()

regras_empresa = get_regras_fiscais_empresa_cached(
    empresa.id,
    lambda: _fetch_regras(db, empresa.id)
)
```

**Importante:** O motor hoje recebe `List[RegraFiscalIcms]`. Se usarmos `RegraFiscalIcmsCache` no cache, o motor deve aceitar ambos. Ou manter serialização de atributos e recriar objetos ORM-like (compatíveis).

---

## 5. Cache da Listagem da API (prioridade baixa)

### Chave Redis

```
regras_fiscais_icms:list:{hash(params)}
```

Params: empresa_id, ativo, crt, tipo_operacao, limit, escopo (allowed_ids hash).

### TTL

- **60 segundos** — listagem muda ao criar/editar/excluir; invalidação seria mais complexa (multi-empresa)

### Consideração

- Filtros variam bastante; invalidação ao CRUD exigiria invalidar várias chaves (todas as combinações que incluam aquela empresa)
- **Recomendação:** Não implementar cache na listagem na Fase 1. Avaliar após métricas de uso.

---

## 6. Arquivos a alterar/criar


| Ação     | Arquivo                                                                                                                |
| -------- | ---------------------------------------------------------------------------------------------------------------------- |
| Alterar  | `app/core/redis_cache.py` — adicionar funções de cache/invalidação                                                     |
| Alterar  | `app/services/fiscal/motor_tributario_icms.py` — aceitar RegraFiscalIcmsCache (se aplicável)                           |
| Alterar  | `app/services/fiscal/emissao_service.py` — usar get_regras_fiscais_empresa_cached                                      |
| Alterar  | `app/api/v1/regras_fiscais_icms.py` — chamar invalidate após create/update/delete                                      |
| Criar    | `app/services/fiscal/regra_fiscal_cache.py` — RegraFiscalIcmsCache, serialização (opcional; pode ficar em redis_cache) |
| Opcional | Script `load_tests/scripts/limpar_cache_regras_fiscais.py` — limpa chaves do cache                                     |


---

## 7. Dataclass RegraFiscalIcmsCache

Criar em `app/services/fiscal/motor_tributario_icms.py` ou em arquivo separado:

```python
@dataclass
class RegraFiscalIcmsCache:
    """Versão leve para cache Redis. Atributos compatíveis com RegraFiscalIcms."""
    id: int
    empresa_id: int
    crt: Optional[int]
    tipo_operacao: Optional[str]
    tipo_destinatario: Optional[str]
    uf_destinatario: Optional[str]
    ncm_prefix: Optional[str]
    ncm_exato: Optional[str]
    cest: Optional[str]
    cfop_filtro: Optional[str]
    vigencia_inicio: Optional[date]
    vigencia_fim: Optional[date]
    cfop: str
    origem_mercadoria: int
    cst_icms: Optional[str]
    csosn: Optional[str]
    aliquota_icms: Decimal
    modalidade_bc_icms: Optional[str]
    percentual_reducao_bc: Optional[Decimal]
    gera_icms_st: bool
    aliquota_icms_st: Optional[Decimal]
    modalidade_bc_icms_st: Optional[str]
    percentual_mva_st: Optional[Decimal]
    permite_credito_icms: Optional[bool]
    ordem_prioridade: int
```

Funções `_regra_compativel_contexto`, `_especificidade_regra`, `_validar_resultado_regra` acessam atributos — funcionam com dataclass se os nomes forem iguais.

---

## 8. Fallback quando Redis indisponível

- Se `get_redis_client()` retorna None: `_cache_get` retorna None → cache miss → busca no DB
- Se `_cache_set` falha: ignora, próximo request busca do DB
- **Sem mudança de comportamento funcional** — apenas otimização

---

## 9. Configuração (.env)

```env
# Opcional - já existem
REDIS_URL=redis://localhost:6379/0
REDIS_KEY_PREFIX=pdv:
REDIS_TIMEOUT=2
REDIS_MAX_CONNECTIONS=20

# Novo (opcional)
REGRA_FISCAL_ICMS_TTL=300
```

---

## 10. Testes

- Teste unitário: cache hit retorna dados deserializados corretamente
- Teste unitário: cache miss chama fetch_from_db e grava no Redis
- Teste unitário: invalidate limpa a chave
- Teste de integração: emissão NF-e usa cache (mock Redis ou Redis real em teste)
- Teste: Redis indisponível → fluxo continua normal (fallback DB)

---

## 11. Ordem de implementação

1. Criar `RegraFiscalIcmsCache` e garantir que motor aceita ambos tipos
2. Adicionar funções em `redis_cache.py` (get_regras_fiscais_empresa_cached, invalidate_regras_fiscais_empresa)
3. Integrar cache em `emissao_service._aplicar_motor_tributario_itens`
4. Adicionar invalidação nos endpoints POST, PUT, DELETE da API regras
5. Testes
6. Documentar no MAPA_DO_SISTEMA (seção Redis/cache)
7. (Opcional) Script limpar_cache_regras_fiscais.py

---

## 12. Riscos e mitigações


| Risco                                    | Mitigação                                         |
| ---------------------------------------- | ------------------------------------------------- |
| Cache stale após alteração externa no DB | Invalidação em todos os pontos de escrita (CRUD)  |
| Serialização de Decimal/date falha       | Usar `default=str` e parser na deserialização     |
| Redis indisponível em produção           | Fallback já implementado em _cache_get/_cache_set |


---

## Referências

- `app/core/redis_cache.py` — padrão existente
- `app/core/redis_client.py` — prefix_key, get_redis_client
- `.cursor/plans/motor_tributário_icms_nf-e_81ae6d7c.plan.md` — plano do motor tributário

