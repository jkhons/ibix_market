# ProviderRouter: escolha do provider por município (NACIONAL por padrão; SP capital = exceção)
from typing import Literal

from sqlalchemy.orm import Session

# Código IBGE São Paulo capital (exceção futura: SP_CAPITAL)
MUNICIPIO_IBGE_SP_CAPITAL = 3550308


def get_provider_for_municipio(
    empresa_id: int,
    municipio_prestacao_ibge: int,
    db: Session,
) -> Literal["NACIONAL", "SP_CAPITAL"] | None:
    """
    Retorna o provider a usar para o município.
    NACIONAL = padrão (padrão nacional 2026).
    SP_CAPITAL = São Paulo capital (3550308); pode retornar None até existir adapter.
    """
    if municipio_prestacao_ibge == MUNICIPIO_IBGE_SP_CAPITAL:
        # Por enquanto retornamos NACIONAL; quando houver ProviderSPCapital, retornar "SP_CAPITAL"
        return "NACIONAL"
    return "NACIONAL"
