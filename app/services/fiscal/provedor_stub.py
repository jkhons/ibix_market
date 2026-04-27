# PDV Ibix - Provedor fiscal stub (desenvolvimento / testes)
from typing import Any, Dict

from .provedor_base import IProvedorFiscal, ResultadoCancelamentoFiscal, ResultadoEnvioFiscal


class ProvedorFiscalStub(IProvedorFiscal):
    """Implementação stub do provedor fiscal. Não chama SEFAZ/provedor real; simula sucesso para desenvolvimento."""

    def enviar_nfse(
        self, empresa_id: int, nota_servico_id: int, payload: Dict[str, Any]
    ) -> ResultadoEnvioFiscal:
        return ResultadoEnvioFiscal(
            sucesso=True,
            status="autorizado",
            protocolo=f"STUB-NFSE-{nota_servico_id}",
            chave=None,
            mensagem="Envio simulado (stub)",
            payload_retorno={"stub": True, "nota_servico_id": nota_servico_id},
        )

    def enviar_nfe(
        self, empresa_id: int, nota_fiscal_id: int, payload: Dict[str, Any]
    ) -> ResultadoEnvioFiscal:
        # Chave 44 dígitos única por nota para não violar UNIQUE no banco
        chave_stub = (str(nota_fiscal_id).zfill(44))[-44:]
        return ResultadoEnvioFiscal(
            sucesso=True,
            status="autorizado",
            protocolo=f"STUB-NFE-{nota_fiscal_id}",
            chave=chave_stub,
            mensagem="Envio simulado (stub)",
            payload_retorno={"stub": True, "nota_fiscal_id": nota_fiscal_id},
        )

    def enviar_nfce(
        self, empresa_id: int, nota_fiscal_id: int, payload: Dict[str, Any]
    ) -> ResultadoEnvioFiscal:
        # Chave 44 dígitos única por nota para não violar UNIQUE no banco
        chave_stub = (str(nota_fiscal_id).zfill(44))[-44:]
        return ResultadoEnvioFiscal(
            sucesso=True,
            status="autorizado",
            protocolo=f"STUB-NFCE-{nota_fiscal_id}",
            chave=chave_stub,
            mensagem="Envio simulado (stub)",
            payload_retorno={"stub": True, "nota_fiscal_id": nota_fiscal_id},
        )

    def cancelar_nfse(
        self, empresa_id: int, nota_servico_id: int, motivo: str
    ) -> ResultadoCancelamentoFiscal:
        return ResultadoCancelamentoFiscal(
            sucesso=True,
            mensagem="Cancelamento simulado (stub)",
            payload_retorno={"stub": True, "nota_servico_id": nota_servico_id},
        )

    def cancelar_nfe(
        self, empresa_id: int, nota_fiscal_id: int, motivo: str
    ) -> ResultadoCancelamentoFiscal:
        return ResultadoCancelamentoFiscal(
            sucesso=True,
            mensagem="Cancelamento simulado (stub)",
            payload_retorno={"stub": True, "nota_fiscal_id": nota_fiscal_id},
        )

    def cancelar_nfce(
        self, empresa_id: int, nota_fiscal_id: int, motivo: str
    ) -> ResultadoCancelamentoFiscal:
        return ResultadoCancelamentoFiscal(
            sucesso=True,
            mensagem="Cancelamento simulado (stub)",
            payload_retorno={"stub": True, "nota_fiscal_id": nota_fiscal_id},
        )
