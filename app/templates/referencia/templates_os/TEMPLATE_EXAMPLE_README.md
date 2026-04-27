# Template Example - Guia de Referência

Este arquivo (`template_example.json`) é um exemplo completo e documentado de um template de Ordem de Serviço (OS) que demonstra todos os recursos disponíveis no editor de templates do sistema CertiLog.

## Estrutura do Template

Um template é um objeto JSON com três propriedades principais:

```json
{
  "layout": "column",
  "secoes": [...],
  "campos": [...]
}
```

### Layout

Define o tipo de layout do formulário:
- `"column"`: Layout em coluna (padrão)

### Seções

Array de objetos que organizam os campos em grupos lógicos. Cada seção possui:

- `id`: Identificador único da seção
- `titulo`: Título exibido na interface
- `ordem`: Ordem de exibição (número inteiro)
- `campos`: Array de IDs dos campos que pertencem a esta seção

### Campos

Array de objetos que definem os campos do formulário. Cada campo possui uma estrutura completa com várias propriedades.

## Estrutura de um Campo

### Propriedades Obrigatórias

- `id`: Identificador único do campo
- `tipo`: Tipo do campo (ver tipos disponíveis abaixo)
- `label`: Rótulo exibido na interface

### Propriedades de Layout

```json
"layout": {
  "width": "full" | "half" | "third",
  "columns": 1,
  "align": "left" | "center" | "right"
}
```

- `width`: Largura do campo
  - `"full"`: 100% da largura
  - `"half"`: 50% da largura
  - `"third"`: 33% da largura
- `columns`: Número de colunas (para campos especiais como tabelas)
- `align`: Alinhamento do conteúdo

### Propriedades de Dados

```json
"data": {
  "mode": "input" | "computed" | "readonly",
  "binding": "caminho.da.propriedade" | null,
  "default": valor_padrao | null
}
```

- `mode`: Modo de operação do campo
  - `"input"`: Campo editável pelo usuário
  - `"computed"`: Valor calculado automaticamente
  - `"readonly"`: Valor somente leitura
- `binding`: Caminho para propriedade da OS (ex: `"os.numero_os"`)
- `default`: Valor padrão quando o campo está vazio

### Propriedades de Renderização

```json
"render": {
  "showWhen": [{"if": "always"}],
  "format": {
    "date": "DD/MM/YYYY",
    "datetime": "DD/MM/YYYY HH:mm",
    "numberDecimals": 2,
    "mask": "###.###.###-##"
  },
  "placeholder": "Texto de exemplo",
  "emptyState": "—"
}
```

- `showWhen`: Condições de visibilidade (ex: `[{"if": "always"}]`)
- `format`: Formatação específica por tipo de campo
- `placeholder`: Texto exibido quando o campo está vazio
- `emptyState`: Texto exibido quando não há valor

### Propriedades de Validação

```json
"validation": {
  "required": true | false,
  "requiredWhen": [
    {
      "field": "campo_id",
      "operator": "equals" | "notEquals" | "contains",
      "value": "valor_esperado"
    }
  ],
  "rules": [
    {
      "type": "minLength" | "maxLength" | "min" | "max" | "pattern",
      "value": valor,
      "message": "Mensagem de erro"
    }
  ]
}
```

- `required`: Campo obrigatório
- `requiredWhen`: Campo obrigatório quando outra condição é verdadeira
- `rules`: Regras de validação adicionais

### Propriedades de Permissões

```json
"permissions": {
  "visibility": ["ADMIN", "PCM", "SUPERVISOR", "TECNICO", "SOLICITANTE"],
  "editable": ["ADMIN", "PCM", "SUPERVISOR"],
  "editableWhen": []
}
```

- `visibility`: Perfis que podem ver o campo
- `editable`: Perfis que podem editar o campo
- `editableWhen`: Condições para edição

### Propriedades de Auditoria

```json
"audit": {
  "trackChanges": true | false,
  "immutableAfter": ["status1", "status2"]
}
```

- `trackChanges`: Rastrear alterações do campo
- `immutableAfter`: Campos que não podem ser alterados após certos status

## Tipos de Campos Disponíveis

### Campos Básicos

#### `text`
Campo de texto simples.

```json
{
  "id": "campo_texto",
  "tipo": "text",
  "label": "Descrição",
  "render": {
    "format": {
      "mask": null
    },
    "placeholder": "Digite o texto..."
  }
}
```

#### `number`
Campo numérico.

```json
{
  "id": "campo_numero",
  "tipo": "number",
  "label": "Quantidade",
  "render": {
    "format": {
      "numberDecimals": 2
    }
  },
  "validation": {
    "rules": [
      {"type": "min", "value": 0},
      {"type": "max", "value": 100}
    ]
  }
}
```

#### `date`
Campo de data.

```json
{
  "id": "campo_data",
  "tipo": "date",
  "label": "Data",
  "render": {
    "format": {
      "date": "DD/MM/YYYY"
    }
  }
}
```

#### `hora`
Campo de hora.

```json
{
  "id": "campo_hora",
  "tipo": "hora",
  "label": "Hora",
  "render": {
    "format": {
      "mask": "HH:mm"
    }
  }
}
```

#### `datetime`
Campo de data e hora.

```json
{
  "id": "campo_datetime",
  "tipo": "datetime",
  "label": "Data e Hora",
  "render": {
    "format": {
      "datetime": "DD/MM/YYYY HH:mm"
    }
  }
}
```

#### `select`
Campo de seleção (dropdown).

```json
{
  "id": "campo_select",
  "tipo": "select",
  "label": "Selecione",
  "config": {
    "options": [
      {"value": "opcao1", "label": "Opção 1"},
      {"value": "opcao2", "label": "Opção 2"}
    ]
  }
}
```

#### `boolean`
Campo booleano (Sim/Não).

```json
{
  "id": "campo_boolean",
  "tipo": "boolean",
  "label": "Ativo?",
  "data": {
    "default": false
  }
}
```

#### `checkbox`
Campo de múltipla seleção.

```json
{
  "id": "campo_checkbox",
  "tipo": "checkbox",
  "label": "Opções",
  "config": {
    "options": [
      {"value": "op1", "label": "Opção 1"},
      {"value": "op2", "label": "Opção 2"}
    ]
  },
  "data": {
    "default": []
  }
}
```

#### `texto_informativo`
Campo somente leitura para exibir informações.

```json
{
  "id": "campo_info",
  "tipo": "texto_informativo",
  "label": "Informação",
  "data": {
    "mode": "readonly",
    "binding": "os.numero_os"
  }
}
```

### Blocos CMMS

#### `cabecalho_os`
Bloco institucional com logo, códigos, revisão, etc.

```json
{
  "id": "campo_cabecalho",
  "tipo": "cabecalho_os",
  "label": "Cabeçalho da OS",
  "config": {
    "showLogo": true,
    "showProgramName": true,
    "showUnit": true,
    "showDocumentCode": true,
    "showRegulatory": true,
    "showRevision": true,
    "showPageCounter": true,
    "showOsNumber": true,
    "showOsType": true,
    "showIssueDate": true
  },
  "layout": {
    "variant": "print_like" | "compact",
    "columns": 3,
    "showBorders": true
  }
}
```

#### `equipamentos`
Seleção de equipamentos relacionados.

```json
{
  "id": "campo_equipamentos",
  "tipo": "equipamentos",
  "label": "Equipamentos"
}
```

#### `apontamento_horas`
Tabela de apontamento de horas por técnico.

```json
{
  "id": "campo_apontamento",
  "tipo": "apontamento_horas",
  "label": "Apontamento de Horas"
}
```

#### `materiais_pecas`
Registro de materiais e peças utilizadas.

```json
{
  "id": "campo_materiais",
  "tipo": "materiais_pecas",
  "label": "Materiais e Peças"
}
```

#### `status_final`
Status final do serviço (Concluído/Andamento/Paliativo).

```json
{
  "id": "campo_status_final",
  "tipo": "status_final",
  "label": "Status Final"
}
```

#### `seguranca_operacional`
Avaliação de segurança operacional (Sim/Não).

```json
{
  "id": "campo_seguranca",
  "tipo": "seguranca_operacional",
  "label": "Segurança Operacional"
}
```

#### `qsa`
Avaliação QSA - Qualidade e Segurança de Alimentos (C/NC).

```json
{
  "id": "campo_qsa",
  "tipo": "qsa",
  "label": "QSA"
}
```

### Blocos Especiais

#### `checklist`
Checklist com itens C/NC/NA e observações.

```json
{
  "id": "campo_checklist",
  "tipo": "checklist",
  "label": "Checklist",
  "config": {
    "items": [
      {
        "id": "item_1",
        "label": "Item 1",
        "tipo": "c_nc_na",
        "obrigatorio": true
      }
    ]
  }
}
```

#### `tabela`
Tabela repetível com múltiplas colunas.

```json
{
  "id": "campo_tabela",
  "tipo": "tabela",
  "label": "Tabela",
  "config": {
    "columns": [
      {
        "id": "col_1",
        "label": "Coluna 1",
        "tipo": "text",
        "obrigatorio": true,
        "width": "50%"
      }
    ]
  }
}
```

#### `upload`
Upload de arquivos (fotos, PDFs, etc.).

```json
{
  "id": "campo_upload",
  "tipo": "upload",
  "label": "Documentos",
  "config": {
    "maxFiles": 10,
    "maxFileSize": 5242880,
    "allowedTypes": ["image/jpeg", "image/png", "application/pdf"],
    "accept": ".jpg,.jpeg,.png,.pdf"
  }
}
```

## Como Usar o Template Example

### 1. Visualizar no Editor

1. Acesse o editor de templates: `/manutencao/templates/editor`
2. Crie um novo template ou edite um existente
3. Use a função de importação (se disponível) ou copie o conteúdo do JSON

### 2. Usar como Referência

O template example serve como referência completa para:
- Estrutura correta do schema JSON
- Exemplos de todos os tipos de campos
- Configurações avançadas (validações, permissões, auditoria)
- Boas práticas de organização em seções

### 3. Adaptar para Suas Necessidades

1. Copie o template example
2. Remova campos não necessários
3. Adicione campos específicos do seu caso
4. Ajuste validações e permissões conforme necessário
5. Organize as seções de acordo com seu fluxo de trabalho

## Validação do Template

O template deve seguir a estrutura validada pelo sistema:

1. **Estrutura básica**: Deve ter `layout`, `secoes` e `campos`
2. **Seções**: Cada seção deve ter `id`, `titulo`, `ordem` e `campos` (array de IDs)
3. **Campos**: Cada campo deve ter `id`, `tipo` e `label`
4. **Referências**: Os IDs em `secoes[].campos` devem existir em `campos[]`

## Exemplos de Uso Avançado

### Campo Condicional

```json
{
  "id": "campo_condicional",
  "tipo": "text",
  "label": "Campo Condicional",
  "render": {
    "showWhen": [
      {
        "field": "campo_boolean",
        "operator": "equals",
        "value": true
      }
    ]
  }
}
```

### Campo Obrigatório Condicional

```json
{
  "id": "campo_obrigatorio_condicional",
  "tipo": "text",
  "label": "Campo Obrigatório Condicional",
  "validation": {
    "required": false,
    "requiredWhen": [
      {
        "field": "campo_status_final",
        "operator": "equals",
        "value": "concluido"
      }
    ]
  }
}
```

### Campo com Binding

```json
{
  "id": "campo_com_binding",
  "tipo": "texto_informativo",
  "label": "Número da OS",
  "data": {
    "mode": "computed",
    "binding": "os.numero_os"
  }
}
```

## Notas Importantes

1. **IDs Únicos**: Todos os IDs de campos e seções devem ser únicos
2. **Referências**: Campos referenciados em seções devem existir no array `campos`
3. **Validação**: O sistema valida a estrutura antes de salvar/publicar
4. **Versionamento**: Templates publicados são versionados automaticamente
5. **Permissões**: Configure permissões adequadas para cada campo conforme necessário

## Suporte

Para dúvidas ou problemas:
- Consulte a documentação do sistema em `MAPA_SISTEMA/`
- Verifique os exemplos no código em `app/static/js/form_builder_editor.js`
- Entre em contato com a equipe de desenvolvimento
