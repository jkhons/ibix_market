# Provider NFS-e Nacional (padrão 2026). Stub até integração real com portal.
from datetime import datetime, timezone
from typing import Any, Optional

from .base import CancelResult, IssueResult, NfseProviderBase, PollResult


def _redact_payload(data: Any) -> str:
    """Redige dados sensíveis para log (senhas, certificados, tokens)."""
    if data is None:
        return "[null]"
    if isinstance(data, dict):
        out = {}
        for k, v in data.items():
            key_lower = (k or "").lower()
            if any(x in key_lower for x in ("password", "senha", "certificado", "pfx", "token", "secret")):
                out[k] = "[REDACTED]"
            else:
                out[k] = _redact_payload(v)
        return str(out)
    if isinstance(data, (list, tuple)):
        return str([_redact_payload(x) for x in data])
    return str(data)[:2000]


class ProviderNacional(NfseProviderBase):
    """
    Provider padrão nacional. Atualmente stub: retorna AUTHORIZED e preenche numero/codigo.
    Quando houver integração real: chamar API do portal, tratar retorno e preencher IssueResult/PollResult/CancelResult.
    """

    def issue(
        self,
        invoice: Any,
        empresa: Any,
        credential: Any,
        rps_numero: int,
        rps_serie: str = "1",
    ) -> IssueResult:
        payload = {
            "invoice_id": getattr(invoice, "id", None),
            "empresa_id": getattr(empresa, "id", None),
            "rps_numero": rps_numero,
            "rps_serie": rps_serie,
        }
        # Stub: simula sucesso. Integração real: POST ao portal, parse resposta.
        return IssueResult(
            success=True,
            status="AUTHORIZED",
            numero_nfse=f"NFSE-{getattr(invoice, 'id', 0)}-{rps_numero}",
            codigo_verificacao=f"CV{getattr(invoice, 'id', 0)}",
            url_consulta=None,
            data_emissao=datetime.now(timezone.utc),
            payload_out_redacted=_redact_payload(payload),
            response_in_redacted='{"status":"AUTHORIZED","numero":"NFSE-..."}',
            http_status=200,
        )

    def poll(self, invoice: Any, empresa: Any, credential: Any) -> PollResult:
        status = getattr(invoice, "status", "SENT")
        if status == "AUTHORIZED":
            return PollResult(
                success=True,
                status="AUTHORIZED",
                numero_nfse=getattr(invoice, "numero_nfse", None),
                codigo_verificacao=getattr(invoice, "codigo_verificacao", None),
                url_consulta=getattr(invoice, "url_consulta", None),
                data_emissao=getattr(invoice, "data_emissao", None),
                response_redacted='{"status":"AUTHORIZED"}',
                http_status=200,
            )
        if status == "REJECTED":
            return PollResult(
                success=False,
                status="REJECTED",
                error_code=getattr(invoice, "last_error_code", None),
                error_msg=getattr(invoice, "last_error_msg", None),
                response_redacted="[redacted]",
                http_status=200,
            )
        return PollResult(
            success=True,
            status=status or "SENT",
            response_redacted='{"status":"pending"}',
            http_status=200,
        )

    def cancel(
        self,
        invoice: Any,
        empresa: Any,
        credential: Any,
        reason: str,
        codigo_cancelamento: Optional[str] = None,
    ) -> CancelResult:
        payload = {"invoice_id": getattr(invoice, "id", None), "reason": reason[:200]}
        # Stub: sucesso. Integração real: chamar endpoint de cancelamento.
        return CancelResult(
            success=True,
            payload_out_redacted=_redact_payload(payload),
            response_in_redacted='{"cancelado":true}',
            http_status=200,
        )
