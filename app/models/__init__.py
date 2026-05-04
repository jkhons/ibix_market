"""
PDV Ibix - Models Module

Requisitos:
- `from app.models import X` deve funcionar para qualquer Model usado nas rotas/serviços.
- Alembic importa `app.models` para registrar os modelos no metadata.

Implementação:
- Importa todos os módulos em `app/models/*.py`
- Exporta automaticamente todas as classes mapeadas no `Base.registry`
"""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path
from typing import Dict, List, Type

from app.database.base import Base

_pkg_dir = Path(__file__).resolve().parent

# 1) Importar todos os módulos de models para registrar mappers no Base.registry
for m in pkgutil.iter_modules([str(_pkg_dir)]):
    if m.name.startswith("_"):
        continue
    importlib.import_module(f"{__name__}.{m.name}")

# 2) Exportar classes mapeadas no namespace do pacote (permite `from app.models import X`)
_exported: Dict[str, Type] = {}
for mapper in list(Base.registry.mappers):
    cls = mapper.class_
    name = getattr(cls, "__name__", None)
    if not name:
        continue
    _exported[name] = cls
    globals()[name] = cls

__all__: List[str] = sorted(_exported.keys())

