# PDV Ibix - Cliente Mercado Pago (preference, payment, webhook signature)
import hashlib
import hmac as hmac_lib
import os
from typing import Any, Dict, Optional, Tuple

import httpx

from app.core.logging import log_struct
from app.utils.mercadopago_errors import looks_like_mp_html_payload, mp_api_failure_message

# Motivos de falha na verificação do webhook (log granular no 401)
MP_WEBHOOK_FAIL_MISSING_SECRET = "missing_secret"
MP_WEBHOOK_FAIL_MISSING_X_SIGNATURE = "missing_x_signature"
MP_WEBHOOK_FAIL_MALFORMED_X_SIGNATURE = "malformed_x_signature"
MP_WEBHOOK_FAIL_MISSING_TS = "missing_ts"
MP_WEBHOOK_FAIL_MISSING_V1 = "missing_v1"
MP_WEBHOOK_FAIL_MISSING_DATA_ID = "missing_data_id"
MP_WEBHOOK_FAIL_DIGEST_MISMATCH = "digest_mismatch"

MP_BASE = "https://api.mercadopago.com"

# Validação do token: doc MP recomenda Authorization: Bearer no header e GET users/me
# https://www.mercadopago.com.br/developers/pt/docs/your-integrations/credentials
MP_VALIDATE_URL = "https://api.mercadolibre.com/users/me"


def parse_x_signature(header_value: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Extrai ts e v1 do header x-signature (formato: ts=1704908010,v1=618c8534...).
    Retorna (ts, v1) ou (None, None) se inválido.
    """
    if not header_value or not header_value.strip():
        return None, None
    ts, v1 = None, None
    for part in header_value.split(","):
        part = part.strip()
        if "=" in part:
            key, _, value = part.partition("=")
            key, value = key.strip(), value.strip()
            if key == "ts":
                ts = value
            elif key == "v1":
                v1 = value
    return ts, v1


def timing_safe_equal(a: str, b: str) -> bool:
    """Comparação em tempo constante para evitar timing attacks."""
    if len(a) != len(b):
        return False
    return hmac_lib.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def _request_id_to_uuid(value: str) -> str:
    """Se for 32 hex chars sem hífen, formata como UUID 8-4-4-4-12 (doc. MP usa esse formato no exemplo)."""
    s = value.strip().replace("-", "")
    if len(s) == 32 and all(c in "0123456789abcdefABCDEF" for c in s):
        return f"{s[:8]}-{s[8:12]}-{s[12:16]}-{s[16:20]}-{s[20:32]}".lower()
    return value.strip()


def build_manifest(data_id: str, x_request_id: Optional[str], ts: str) -> str:
    """
    Monta o manifest do MP: id:[data.id_url];request-id:[x-request-id_header];ts:[ts_header];
    Se x_request_id ausente, omitir request-id (doc: "remover do modelo se não estiver presente").
    Observação: NÃO normalizamos `data_id` aqui. Qualquer modificação (strip/lower) pode quebrar
    a assinatura do Mercado Pago para esse webhook específico.
    """
    id_val = data_id  # mantenha exatamente como recebido/decodificado
    if x_request_id:
        return f"id:{id_val};request-id:{x_request_id};ts:{ts};"
    return f"id:{id_val};ts:{ts};"


def compute_signature(
    secret: str,
    data_id: str,
    x_request_id: Optional[str],
    ts: str,
) -> str:
    """
    Gera HMAC-SHA256 em hex do manifest MP.
    """
    manifest = build_manifest(data_id, x_request_id, ts)
    sig = hmac_lib.new(
        secret.encode("utf-8"),
        manifest.encode("utf-8"),
        hashlib.sha256,
    )
    return sig.hexdigest()


def verify_webhook_signature(
    secret: str,
    body: Dict[str, Any],
    x_signature: Optional[str],
    x_request_id: Optional[str],
    data_id_from_query: Optional[str] = None,
) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """
    Verifica x-signature do webhook MP.
    Doc. MP: template id:[data.id_url];request-id:[x-request-id_header];ts:[ts_header];
    Retorna (sucesso, motivo_falha, debug_info). Em sucesso: (True, None, debug_info ou None).
    Em falha: (False, motivo, debug_info com manifest e received_v1_prefix para diagnóstico).

    Checklist digest_mismatch (qualquer diferença no manifest muda o HMAC):
    1. data.id: usar da URL/query (data.id_url); body só como fallback.
    2. x-request-id: usar exatamente o valor recebido no header (sem variações).
    3. ts: usar exatamente o valor extraído do x-signature.
    4. secret: deve ser exatamente o configurado no painel MP para a aplicação/URL.
    """
    debug: Optional[Dict[str, Any]] = None

    def make_debug(manifest: str, manifest_mode: str, data_id: str, ts: str, v1_prefix: Optional[str]) -> Dict[str, Any]:
        return {
            "data_id": data_id,
            "ts": ts,
            "manifest": manifest,
            "manifest_mode": manifest_mode,
            "received_v1_prefix": v1_prefix[:10] if v1_prefix and len(v1_prefix) >= 10 else v1_prefix,
        }

    secret = (secret or "").strip()
    if not secret:
        return False, MP_WEBHOOK_FAIL_MISSING_SECRET, None
    if not x_signature or not x_signature.strip():
        return False, MP_WEBHOOK_FAIL_MISSING_X_SIGNATURE, None
    ts, v1 = parse_x_signature(x_signature)
    if not ts:
        return False, MP_WEBHOOK_FAIL_MISSING_TS, None
    if not v1:
        return False, MP_WEBHOOK_FAIL_MISSING_V1, None
    # Malformado se não conseguiu extrair ts e v1 (já tratado acima); motivo genérico se parse retornou vazio
    # NÃO normalize v1 (não fazer .lower()), pois o cálculo/digest pode quebrar.
    v1 = v1.strip()
    if data_id_from_query is not None and str(data_id_from_query).strip():
        data_id = str(data_id_from_query)
    else:
        data = body.get("data") or {}
        raw_id = data.get("id")
        if raw_id is None:
            return False, MP_WEBHOOK_FAIL_MISSING_DATA_ID, None
        data_id = raw_id if isinstance(raw_id, str) else str(raw_id)

    manifest_mode = "with_request_id" if x_request_id else "without_request_id"
    manifest = build_manifest(data_id, x_request_id, ts)
    computed = compute_signature(secret, data_id, x_request_id, ts)

    # Log obrigatório para fechar diagnóstico (ativar via MP_WEBHOOK_DEBUG=true).
    if os.getenv("MP_WEBHOOK_DEBUG", "").lower() == "true":
        log_struct(
            "mp_webhook_debug_full",
            manifest=manifest,
            ts=ts,
            data_id=data_id,
            x_request_id=x_request_id,
            computed_signature=computed,
            received_signature=v1,
        )

    if timing_safe_equal(computed, v1):
        return True, None, make_debug(manifest, manifest_mode, data_id, ts, v1)

    debug = make_debug(manifest, manifest_mode, data_id, ts, v1)
    debug["computed_v1_prefix"] = computed[:10] if computed and len(computed) >= 10 else computed
    return False, MP_WEBHOOK_FAIL_DIGEST_MISMATCH, debug


class MercadoPagoClient:
    """Cliente HTTP para API Mercado Pago (preference e payment)."""

    def __init__(self, access_token: str, base_url: str = MP_BASE):
        self.access_token = access_token
        self.base_url = base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    async def create_preference(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        POST /checkout/preferences. Retorna dict com init_point, id, etc.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/checkout/preferences",
                json=payload,
                headers=self._headers,
            )
            if not response.is_success:
                try:
                    body = response.json()
                    msg = body.get("message") or body.get("error") or response.text[:200]
                except Exception:
                    msg = response.text[:200] if response.text else str(response.status_code)
                raise RuntimeError(f"Mercado Pago {response.status_code}: {msg}")
            return response.json()

    async def fetch_payment(self, payment_id: int) -> Dict[str, Any]:
        """
        GET /v1/payments/{id}. Retorna dados do pagamento.
        """
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{self.base_url}/v1/payments/{payment_id}",
                headers=self._headers,
            )
            response.raise_for_status()
            return response.json()

    async def search_payments(self, external_reference: str) -> Optional[Dict[str, Any]]:
        """
        GET /v1/payments/search?external_reference={ref}.
        Returns the most recent approved/paid payment, or the first result if none approved.
        """
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{self.base_url}/v1/payments/search",
                params={"external_reference": external_reference, "sort": "date_created", "criteria": "desc"},
                headers=self._headers,
            )
            response.raise_for_status()
            data = response.json()
            results = data.get("results") or []
            if not results:
                return None
            for r in results:
                if (r.get("status") or "").lower() in ("approved", "authorized"):
                    return r
            return results[0]

    async def validate_token(self) -> Tuple[bool, str]:
        """
        Valida o Access Token conforme doc MP: GET users/me com Authorization: Bearer no header.
        Retorna (True, "") se o token for aceito, (False, mensagem) em caso de 401/403 ou erro.
        """
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.get(
                    MP_VALIDATE_URL,
                    headers=self._headers,
                )
                if response.is_success:
                    return True, ""
                raw = (response.text or "").strip()
                ct = response.headers.get("content-type")
                if looks_like_mp_html_payload(raw) or "text/html" in (ct or "").lower():
                    msg = mp_api_failure_message(response.status_code, raw, ct)
                else:
                    try:
                        body = response.json()
                        msg = body.get("message") or body.get("error") or raw[:200]
                    except Exception:
                        msg = raw[:200] if raw else str(response.status_code)
                    if isinstance(msg, str) and looks_like_mp_html_payload(msg):
                        msg = mp_api_failure_message(response.status_code, raw, ct)
                    elif not msg or msg == str(response.status_code):
                        msg = f"HTTP {response.status_code}"
                    if response.status_code in (401, 403) and len(raw) < 5:
                        msg += (
                            " — token inválido/revogado, credencial de teste em produção, ou valor que não é o Access Token (APP_USR-…)."
                        )
                rid = response.headers.get("x-request-id")
                if rid:
                    msg += f" x-request-id={rid}"
                return False, msg[:500]
        except httpx.TimeoutException:
            return False, "Timeout ao validar token"
        except Exception as e:
            return False, str(e)[:200]
