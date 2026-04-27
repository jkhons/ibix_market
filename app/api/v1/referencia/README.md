# API Referência (Certilog)

Estes arquivos são **cópia de referência** do sistema Certilog e **não devem ser usados diretamente** no PDV Ibix.

- **Não montar** estes routers em `main.py` (ROUTER_SPECS) sem antes adaptar imports e modelos ao PDV Ibix.
- Imports atuais referem-se a módulos do Certilog (ex.: `app.models.comum`, `app.models.manutencao`, `app.database.base`, `app.core.rbac`). No PDV Ibix:
  - `app.core.rbac` existe e re-exporta `require_permission` e `is_super_admin` a partir de `app.core.middleware`.
  - `get_db` está em `app.database.connection` (não em `app.database.base`).
  - Usuário é `app.models.usuario.Usuario` (não `ComumUsuario`).
- Modelos e serviços de manutenção/OS do Certilog não existem no PDV Ibix; seria necessário implementar ou remover rotas que os usam.

**Se for reutilizar algum endpoint:** copiar a lógica para um router dentro de `app.api.v1` e usar apenas dependências e modelos do PDV Ibix (`app.core.middleware`, `app.models`, `app.database.connection`).
