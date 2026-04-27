Landing Certipeso - arquivos para outro servidor

Estrutura:
  templates/landing.html   -> servir como página inicial (ex.: index.html ou via app)
  static/css/              -> servir em /static/css/
  static/img/              -> servir em /static/img/

No outro servidor:
  - Monte "static" na URL /static (ou ajuste os caminhos no HTML de /static/ para o seu prefixo).
  - A landing usa apenas CSS (dashboard.css, certipeso.css); não há JS externo.
  - Se faltar icon-48x48.png ou logo/logo.png, coloque em static/img/icons/ e static/img/logo/.
