# PDV Ibix - Registro centralizado de rotas API
"""RouterRegistry centraliza a importação e o registro de routers para reduzir
repetição de try/except e facilitar manutenção. Não altera latência por request."""
import importlib
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter


class RouterRegistry:
    """Registro de routers por nome. Usado para importação centralizada em main.py."""
    _routers: Dict[str, Optional[APIRouter]] = {}

    @classmethod
    def register(cls, name: str, router: APIRouter) -> None:
        cls._routers[name] = router

    @classmethod
    def get(cls, name: str) -> Optional[APIRouter]:
        return cls._routers.get(name)

    @classmethod
    def get_all(cls) -> Dict[str, Optional[APIRouter]]:
        return dict(cls._routers)


def load_and_register_routers(
    specs: List[Tuple[str, str, str]],
    log_error_fn: Any,
) -> None:
    """Importa cada módulo e registra o router. specs = (module_path, attr_name, log_name)."""
    for mod_path, attr, log_name in specs:
        try:
            mod = importlib.import_module(mod_path)
            router = getattr(mod, attr)
            RouterRegistry.register(log_name, router)
        except Exception as e:
            log_error_fn(f"Erro ao importar rotas {log_name}", exc_info=e)
