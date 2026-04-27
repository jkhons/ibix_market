# Códigos de erro padronizados (MODULO_FATURAMENT_V2.MD Parte VII.8)
from enum import Enum


class NfseErrorCode(str, Enum):
    MUN_IBGE_MISSING = "MUN_IBGE_MISSING"
    CERT_EXPIRED = "CERT_EXPIRED"
    CERT_MISSING = "CERT_MISSING"
    RPS_UNAVAILABLE = "RPS_UNAVAILABLE"
    NETWORK_ERROR = "NETWORK_ERROR"
    SCHEMA_INVALID = "SCHEMA_INVALID"
    # Rejeição do provedor: usar prefixo REJEICAO_ + código original
    REJEICAO_PREFIX = "REJEICAO_"

    @classmethod
    def rejeicao(cls, codigo_provedor: str) -> str:
        return f"{cls.REJEICAO_PREFIX.value}{codigo_provedor}"
