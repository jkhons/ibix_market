# PDV Ibix - Provedores marketplace (contrato base.PaymentProviderBase)
"""Implementações do contrato base para checkout redirecionado: MP + stubs asaas, pagarme, stripe."""
import json
import uuid
from decimal import Decimal
from typing import Any, Dict, Optional

import httpx

from app.integrations.mercadopago import verify_webhook_signature

from .base import (
    CheckoutResult,
    NormalizedWebhookEvent,
    PaymentProviderBase,
)
from .mercadopago_api import (
    MP_PAYMENTS_URL,
    MP_PREFERENCES_URL,
    extract_pix_from_mp_payment_body,
    format_mercadopago_api_error,
    validate_mercadopago_access_token,
)
from .status_map import to_internal

PROVIDER_MP = "mercadopago"


class MercadoPagoMarketplaceProvider(PaymentProviderBase):
    """Provedor Mercado Pago para marketplace: preferência checkout → redirect_url."""

    def __init__(self, webhook_secret: Optional[str] = None):
        self._webhook_secret = webhook_secret

    @property
    def provider_code(self) -> str:
        return PROVIDER_MP

    def create_checkout(
        self,
        amount: Decimal,
        payment_method: str,
        external_reference: str,
        credentials: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> CheckoutResult:
        credentials = credentials or {}
        access_token = (
            credentials.get("access_token")
            or credentials.get("ACCESS_TOKEN")
            or credentials.get("token")
        )
        if not access_token:
            raise ValueError(
                "Credenciais Mercado Pago não configuradas (access_token). "
                "O dono da loja deve configurar em Meu Negócio > Recebíveis: adicione uma configuração Mercado Pago com o Access Token (APP_USR-...)."
            )
        bad_token = validate_mercadopago_access_token(access_token)
        if bad_token:
            raise RuntimeError(
                "Access Token do Mercado Pago rejeitado na validação oficial (GET users/me). "
                f"{bad_token} Atualize Admin Billing (billing_mp_access_token), variável MP_ACCESS_TOKEN "
                "ou a credencial em Meu Negócio > Recebíveis — use o Access Token de produção (APP_USR-...) em Suas integrações."
            )
        method = (payment_method or "pix").lower()
        if method not in ("pix", "credit_card", "credit", "debit", "boleto"):
            method = "pix"
        amount_f = float(amount or 0)
        if amount_f <= 0:
            raise ValueError("Valor de pagamento inválido.")

        if method == "pix":
            payer_info = kwargs.get("payer_info") or {}
            email = (payer_info.get("email") or "").strip()
            if not email:
                raise ValueError(
                    "E-mail do comprador é obrigatório para PIX no Mercado Pago (checkout transparente). "
                    "Verifique comprador_email no pedido."
                )
            items_detail_pix = kwargs.get("items_detail")
            if items_detail_pix and len(items_detail_pix) > 0:
                first_title = (items_detail_pix[0].get("title") or "Pedido Marketplace")[:255]
            else:
                first_title = "Pedido Marketplace"
            pay_body: Dict[str, Any] = {
                "transaction_amount": round(amount_f, 2),
                "description": first_title,
                "payment_method_id": "pix",
                "external_reference": (external_reference or "")[:256],
                "payer": {"email": email[:256]},
            }
            nu = kwargs.get("notification_url")
            if nu:
                pay_body["notification_url"] = str(nu).strip()[:500]
            idem = kwargs.get("mp_idempotency_key") or str(uuid.uuid4())
            pay_headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "X-Idempotency-Key": str(idem)[:128],
            }
            with httpx.Client(timeout=30.0) as client:
                pay_resp = client.post(MP_PAYMENTS_URL, json=pay_body, headers=pay_headers)
            if not pay_resp.is_success:
                raise RuntimeError(f"Mercado Pago recusou: {format_mercadopago_api_error(pay_resp)}")
            pdata = pay_resp.json()
            if not isinstance(pdata, dict):
                raise RuntimeError("Mercado Pago retornou corpo inválido ao criar PIX.")
            qr, qr_b64, ticket_url, exp_iso, pid, _mp_st = extract_pix_from_mp_payment_body(pdata)
            if not qr:
                raise RuntimeError(
                    "Mercado Pago não retornou QR Code PIX. Verifique chave Pix na conta e credenciais."
                )
            return CheckoutResult(
                provider=PROVIDER_MP,
                checkout_type="pix",
                payment_method="pix",
                provider_payment_id=str(pid) if pid is not None else None,
                provider_checkout_id=None,
                redirect_url=ticket_url,
                qr_code=qr,
                qr_code_base64=qr_b64,
                copy_paste_code=qr,
                expires_at=exp_iso,
                external_reference=external_reference,
                raw_payload=pdata,
            )

        items_detail = kwargs.get("items_detail")
        if items_detail:
            items_payload = [
                {
                    "id": str(it.get("id", "")),
                    "title": (it.get("title") or "Produto")[:256],
                    "description": (it.get("description") or "Produto Marketplace")[:256],
                    "category_id": (it.get("category_id") or "others")[:256],
                    "quantity": it.get("quantity", 1),
                    "currency_id": "BRL",
                    "unit_price": float(it.get("unit_price", 0)),
                }
                for it in items_detail
            ]
        else:
            items_payload = [
                {
                    "title": "Pedido Marketplace",
                    "quantity": 1,
                    "currency_id": "BRL",
                    "unit_price": amount_f,
                }
            ]

        payload: Dict[str, Any] = {
            "items": items_payload,
            "external_reference": external_reference,
            "metadata": {"payment_method": method, "external_reference": external_reference},
            "auto_return": "approved",
        }

        payer_info = kwargs.get("payer_info")
        if payer_info:
            payer: Dict[str, Any] = {}
            if payer_info.get("first_name"):
                payer["first_name"] = payer_info["first_name"][:256]
            if payer_info.get("last_name"):
                payer["last_name"] = payer_info["last_name"][:256]
            if payer_info.get("email"):
                payer["email"] = payer_info["email"][:256]
            if payer:
                payload["payer"] = payer

        if kwargs.get("back_urls"):
            bu = dict(kwargs["back_urls"])
            # MP exige back_urls.pending em vários fluxos (PIX/boleto em análise); reutiliza sucesso se omitido.
            if bu.get("success") and "pending" not in bu:
                bu["pending"] = bu["success"]
            payload["back_urls"] = bu
        if kwargs.get("notification_url"):
            payload["notification_url"] = kwargs["notification_url"]
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=30.0) as client:
            response = client.post(MP_PREFERENCES_URL, json=payload, headers=headers)
        if not response.is_success:
            raise RuntimeError(f"Mercado Pago recusou: {format_mercadopago_api_error(response)}")
        data = response.json()
        init_point = data.get("init_point") or data.get("sandbox_init_point") or ""
        pref_id = str(data.get("id") or "")
        return CheckoutResult(
            provider=PROVIDER_MP,
            checkout_type="redirect",
            payment_method=method,
            provider_checkout_id=pref_id,
            redirect_url=init_point or None,
            external_reference=external_reference,
            raw_payload=data,
        )

    def fetch_payment(
        self,
        provider_payment_id: str,
        credentials: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        credentials = credentials or {}
        access_token = (
            credentials.get("access_token")
            or credentials.get("ACCESS_TOKEN")
            or credentials.get("token")
        )
        if not access_token:
            return None
        url = f"{MP_PAYMENTS_URL}/{provider_payment_id}"
        headers = {"Authorization": f"Bearer {access_token}"}
        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.get(url, headers=headers)
            if not response.is_success:
                return None
            return response.json()
        except Exception:
            return None

    def search_payment_by_reference(
        self,
        external_reference: str,
        credentials: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Busca pagamento por external_reference na API do MP (sincrono)."""
        credentials = credentials or {}
        access_token = (
            credentials.get("access_token")
            or credentials.get("ACCESS_TOKEN")
            or credentials.get("token")
        )
        if not access_token:
            return None
        headers = {"Authorization": f"Bearer {access_token}"}
        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.get(
                    f"{MP_PAYMENTS_URL}/search",
                    params={
                        "external_reference": external_reference,
                        "sort": "date_created",
                        "criteria": "desc",
                    },
                    headers=headers,
                )
            if not response.is_success:
                return None
            results = (response.json() or {}).get("results") or []
            if not results:
                return None
            for r in results:
                if (r.get("status") or "").lower() in ("approved", "authorized"):
                    return r
            return results[0]
        except Exception:
            return None

    def refund(
        self,
        provider_payment_id: str,
        amount: Optional[Decimal] = None,
        credentials: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        credentials = credentials or {}
        access_token = (
            credentials.get("access_token")
            or credentials.get("ACCESS_TOKEN")
            or credentials.get("token")
        )
        if not access_token:
            return {"success": False, "message": "Credenciais não configuradas"}
        url = f"{MP_PAYMENTS_URL}/{provider_payment_id}/refunds"
        payload: Dict[str, Any] = {}
        if amount is not None and amount > 0:
            payload["amount"] = float(amount)
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, json=payload if payload else None, headers=headers)
            if not response.is_success:
                try:
                    body = response.json()
                    msg = body.get("message") or body.get("error") or response.text[:200]
                except Exception:
                    msg = response.text[:200] or str(response.status_code)
                return {"success": False, "message": msg, "provider_refund_id": None}
            data = response.json()
            ref_id = data.get("id") if isinstance(data, dict) else None
            return {
                "success": True,
                "provider_refund_id": str(ref_id) if ref_id else None,
                "message": "Estorno solicitado",
            }
        except Exception as e:
            return {"success": False, "message": str(e)[:200], "provider_refund_id": None}

    def parse_webhook(
        self,
        payload: bytes,
        headers: Optional[Dict[str, str]] = None,
        query_params: Optional[Dict[str, str]] = None,
    ) -> Optional[NormalizedWebhookEvent]:
        try:
            data = json.loads(payload) if payload else {}
        except json.JSONDecodeError:
            return None
        event_type = data.get("type") or "payment"
        data_obj = data.get("data") or {}
        provider_payment_id = data_obj.get("id")
        if provider_payment_id is not None and not isinstance(provider_payment_id, str):
            provider_payment_id = str(provider_payment_id)
        action = data.get("action")
        if action and not provider_payment_id:
            provider_payment_id = action
        event_key = f"{PROVIDER_MP}:{event_type}:{provider_payment_id or 'unknown'}"
        signature_valid = False
        if self._webhook_secret and headers and payload:
            x_sig = (headers or {}).get("x-signature") or (headers or {}).get("X-Signature")
            x_rid = (headers or {}).get("x-request-id") or (headers or {}).get("X-Request-Id")
            data_id = (query_params or {}).get("data.id") if query_params else None
            if not data_id and data_obj:
                data_id = data_obj.get("id")
                if data_id is not None:
                    data_id = str(data_id)
            ok, _, _ = verify_webhook_signature(
                self._webhook_secret, data, x_sig, x_rid, data_id_from_query=data_id
            )
            signature_valid = ok
        status_raw = None
        if data.get("action"):
            status_raw = data.get("action")
        return NormalizedWebhookEvent(
            provider=PROVIDER_MP,
            event_key=event_key,
            event_type=event_type,
            provider_event_id=data.get("id"),
            provider_payment_id=provider_payment_id,
            normalized_status=to_internal(PROVIDER_MP, status_raw or "pending") if status_raw else None,
            signature_valid=signature_valid,
            raw_payload=data,
            headers=dict(headers) if headers else None,
            query_params=dict(query_params) if query_params else None,
        )


class PagBankMarketplaceProvider(PaymentProviderBase):
    """Provedor PagBank para marketplace: checkout via POST /orders com redirect ou Pix QR."""

    SANDBOX_URL = "https://sandbox.api.pagseguro.com"
    PRODUCTION_URL = "https://api.pagseguro.com"

    def __init__(self, webhook_secret: Optional[str] = None):
        self._webhook_secret = webhook_secret

    @property
    def provider_code(self) -> str:
        return "pagbank"

    def _base_url(self, credentials: Optional[Dict[str, Any]]) -> str:
        import os

        if credentials and credentials.get("sandbox"):
            return self.SANDBOX_URL
        if os.environ.get("PAGBANK_CONNECT_SANDBOX", "true").strip().lower() in ("true", "1"):
            return self.SANDBOX_URL
        return self.PRODUCTION_URL

    def create_checkout(
        self,
        amount: Decimal,
        payment_method: str,
        external_reference: str,
        credentials: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> CheckoutResult:
        credentials = credentials or {}
        access_token = credentials.get("access_token")
        if not access_token:
            raise ValueError("Credenciais PagBank não configuradas (access_token). Conecte a conta em Recebíveis.")

        method = (payment_method or "pix").lower()
        amount_centavos = int(amount * 100)
        if amount_centavos <= 0:
            raise ValueError("Valor de pagamento inválido.")

        base_url = self._base_url(credentials)
        idem_key = external_reference or str(uuid.uuid4())
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "x-idempotency-key": idem_key,
        }

        payload: Dict[str, Any] = {
            "reference_id": external_reference,
            "items": [{"name": "Pedido Marketplace", "quantity": 1, "unit_amount": amount_centavos}],
        }

        if kwargs.get("notification_url"):
            payload["notification_urls"] = [kwargs["notification_url"]]

        if method == "pix":
            payload["qr_codes"] = [{"amount": {"value": amount_centavos}}]
        else:
            charge: Dict[str, Any] = {
                "amount": {"value": amount_centavos, "currency": "BRL"},
                "payment_method": {"type": "CREDIT_CARD" if method in ("credit", "credit_card") else "BOLETO"},
            }
            payload["charges"] = [charge]

        with httpx.Client(timeout=30.0) as client:
            response = client.post(f"{base_url}/orders", json=payload, headers=headers)

        if not response.is_success:
            try:
                body = response.json()
                msg = str(body.get("error_messages", body.get("message", ""))) or response.text[:200]
            except Exception:
                msg = response.text[:200]
            raise RuntimeError(f"PagBank recusou: {msg}")

        data = response.json()
        order_id = data.get("id", "")
        qr_code = None
        if data.get("qr_codes"):
            qr = data["qr_codes"][0]
            qr_code = qr.get("text")
            for link in qr.get("links", []):
                if link.get("media") == "image/png":
                    link.get("href")
                    break

        checkout_type = "qr_code" if method == "pix" else "redirect"
        return CheckoutResult(
            provider="pagbank",
            checkout_type=checkout_type,
            payment_method=method,
            provider_checkout_id=order_id,
            provider_payment_id=order_id,
            qr_code=qr_code,
            qr_code_base64=None,
            copy_paste_code=qr_code,
            external_reference=external_reference,
            raw_payload=data,
        )

    def fetch_payment(self, provider_payment_id: str, credentials: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        credentials = credentials or {}
        access_token = credentials.get("access_token")
        if not access_token:
            return None
        base_url = self._base_url(credentials)
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(f"{base_url}/orders/{provider_payment_id}", headers={"Authorization": f"Bearer {access_token}"})
            if resp.is_success:
                return resp.json()
        except Exception:
            pass
        return None

    def refund(self, provider_payment_id: str, amount: Optional[Decimal] = None, credentials: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        credentials = credentials or {}
        access_token = credentials.get("access_token")
        if not access_token:
            return {"success": False, "message": "Credenciais PagBank não configuradas.", "provider_refund_id": None}
        base_url = self._base_url(credentials)
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(f"{base_url}/orders/{provider_payment_id}", headers={"Authorization": f"Bearer {access_token}"})
            if not resp.is_success:
                return {"success": False, "message": "Pedido não encontrado.", "provider_refund_id": None}
            order = resp.json()
            charges = order.get("charges", [])
            if not charges:
                return {"success": False, "message": "Sem cobranças no pedido.", "provider_refund_id": None}
            charge_id = charges[0].get("id")
            amount_val = charges[0].get("amount", {}).get("value")
            refund_body = {"amount": {"value": int(amount * 100) if amount else amount_val}}
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(f"{base_url}/charges/{charge_id}/cancel", json=refund_body, headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"})
            if resp.is_success:
                return {"success": True, "message": "Estorno PagBank solicitado.", "provider_refund_id": charge_id}
            return {"success": False, "message": resp.text[:200], "provider_refund_id": None}
        except Exception as e:
            return {"success": False, "message": str(e)[:200], "provider_refund_id": None}

    def parse_webhook(self, payload: bytes, headers: Optional[Dict[str, str]] = None, query_params: Optional[Dict[str, str]] = None) -> Optional[NormalizedWebhookEvent]:
        try:
            data = json.loads(payload) if payload else {}
        except json.JSONDecodeError:
            return None
        charges = data.get("charges", [])
        charge_status = charges[0].get("status", "WAITING").upper() if charges else "WAITING"
        order_id = data.get("id", "")
        data.get("reference_id", "")
        status_map = {"PAID": "paid", "AUTHORIZED": "authorized", "DECLINED": "refused", "CANCELED": "cancelled", "WAITING": "pending", "IN_ANALYSIS": "pending"}
        return NormalizedWebhookEvent(
            provider="pagbank",
            event_key=f"pagbank:order:{order_id}",
            event_type="order",
            provider_payment_id=order_id,
            normalized_status=status_map.get(charge_status, "pending"),
            signature_valid=True,
            raw_payload=data,
            headers=dict(headers) if headers else None,
            query_params=dict(query_params) if query_params else None,
        )


class PagarMeMarketplaceProvider(PaymentProviderBase):
    """Provedor Pagar.me para marketplace: checkout via POST /orders API v5."""

    BASE_URL = "https://api.pagar.me/core/v5"

    def __init__(self, webhook_secret: Optional[str] = None):
        self._webhook_secret = webhook_secret

    @property
    def provider_code(self) -> str:
        return "pagarme"

    def _auth(self, credentials: Optional[Dict[str, Any]]) -> Optional[tuple]:
        credentials = credentials or {}
        sk = credentials.get("secret_key") or credentials.get("api_key") or credentials.get("sk")
        if not sk:
            return None
        return (sk, "")

    def create_checkout(
        self,
        amount: Decimal,
        payment_method: str,
        external_reference: str,
        credentials: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> CheckoutResult:
        auth = self._auth(credentials)
        if not auth:
            raise ValueError("Credenciais Pagar.me não configuradas (secret_key). Informe em Recebíveis.")

        method = (payment_method or "pix").lower()
        amount_centavos = int(amount * 100)
        if amount_centavos <= 0:
            raise ValueError("Valor de pagamento inválido.")

        payment_obj: Dict[str, Any] = {"amount": amount_centavos}
        if method == "pix":
            payment_obj["payment_method"] = "pix"
            payment_obj["pix"] = {"expires_in": 3600}
        elif method in ("credit_card", "credit"):
            payment_obj["payment_method"] = "credit_card"
            payment_obj["credit_card"] = {"installments": 1}
        elif method == "boleto":
            payment_obj["payment_method"] = "boleto"
            payment_obj["boleto"] = {"instructions": "Pagar até o vencimento"}
        else:
            payment_obj["payment_method"] = "pix"
            payment_obj["pix"] = {"expires_in": 3600}

        payload: Dict[str, Any] = {
            "code": external_reference,
            "customer": {"name": "Cliente Marketplace"},
            "items": [{"amount": amount_centavos, "description": "Pedido Marketplace", "quantity": 1}],
            "payments": [payment_obj],
        }

        with httpx.Client(timeout=30.0) as client:
            response = client.post(f"{self.BASE_URL}/orders", json=payload, headers={"Content-Type": "application/json"}, auth=auth)

        if not response.is_success:
            try:
                body = response.json()
                msg = str(body.get("message", body.get("errors", ""))) or response.text[:200]
            except Exception:
                msg = response.text[:200]
            raise RuntimeError(f"Pagar.me recusou: {msg}")

        data = response.json()
        order_id = data.get("id", "")
        qr_code = None
        charges = data.get("charges", [])
        if charges and method == "pix":
            last_tx = charges[0].get("last_transaction", {})
            qr_code = last_tx.get("qr_code")
            last_tx.get("qr_code_url")

        checkout_type = "qr_code" if method == "pix" else "redirect"
        return CheckoutResult(
            provider="pagarme",
            checkout_type=checkout_type,
            payment_method=method,
            provider_checkout_id=order_id,
            qr_code=qr_code,
            copy_paste_code=qr_code,
            external_reference=external_reference,
            raw_payload=data,
        )

    def fetch_payment(self, provider_payment_id: str, credentials: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        auth = self._auth(credentials)
        if not auth:
            return None
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(f"{self.BASE_URL}/orders/{provider_payment_id}", auth=auth)
            if resp.is_success:
                return resp.json()
        except Exception:
            pass
        return None

    def refund(self, provider_payment_id: str, amount: Optional[Decimal] = None, credentials: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        auth = self._auth(credentials)
        if not auth:
            return {"success": False, "message": "Credenciais Pagar.me não configuradas.", "provider_refund_id": None}
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(f"{self.BASE_URL}/orders/{provider_payment_id}", auth=auth)
            if not resp.is_success:
                return {"success": False, "message": "Pedido não encontrado.", "provider_refund_id": None}
            order = resp.json()
            charges = order.get("charges", [])
            if not charges:
                return {"success": False, "message": "Sem cobranças.", "provider_refund_id": None}
            charge_id = charges[0].get("id")
            with httpx.Client(timeout=30.0) as client:
                resp = client.delete(f"{self.BASE_URL}/charges/{charge_id}", auth=auth)
            if resp.is_success:
                return {"success": True, "message": "Estorno solicitado.", "provider_refund_id": charge_id}
            return {"success": False, "message": resp.text[:200], "provider_refund_id": None}
        except Exception as e:
            return {"success": False, "message": str(e)[:200], "provider_refund_id": None}

    def parse_webhook(self, payload: bytes, headers: Optional[Dict[str, str]] = None, query_params: Optional[Dict[str, str]] = None) -> Optional[NormalizedWebhookEvent]:
        try:
            data = json.loads(payload) if payload else {}
        except json.JSONDecodeError:
            return None
        event_type = data.get("type", "order.paid")
        order_data = data.get("data", {})
        order_id = order_data.get("id", "")
        order_status = (order_data.get("status") or "pending").lower()
        status_map = {"paid": "paid", "pending": "pending", "failed": "refused", "canceled": "cancelled", "closed": "paid"}
        return NormalizedWebhookEvent(
            provider="pagarme",
            event_key=f"pagarme:{event_type}:{order_id}",
            event_type=event_type,
            provider_payment_id=order_id,
            normalized_status=status_map.get(order_status, "pending"),
            signature_valid=True,
            raw_payload=data,
            headers=dict(headers) if headers else None,
            query_params=dict(query_params) if query_params else None,
        )


class StubMarketplaceProvider(PaymentProviderBase):
    """Stub para outro gateway (asaas, pagarme, stripe): não implementado na V1."""

    def __init__(self, code: str = "stub"):
        self._code = code

    @property
    def provider_code(self) -> str:
        return self._code

    def create_checkout(
        self,
        amount: Decimal,
        payment_method: str,
        external_reference: str,
        credentials: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> CheckoutResult:
        raise NotImplementedError(f"Provedor {self._code} não implementado para checkout marketplace.")

    def fetch_payment(
        self,
        provider_payment_id: str,
        credentials: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        return None

    def refund(
        self,
        provider_payment_id: str,
        amount: Optional[Decimal] = None,
        credentials: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return {"success": False, "message": f"Provedor {self._code} não implementado.", "provider_refund_id": None}

    def parse_webhook(
        self,
        payload: bytes,
        headers: Optional[Dict[str, str]] = None,
        query_params: Optional[Dict[str, str]] = None,
    ) -> Optional[NormalizedWebhookEvent]:
        return None


def get_marketplace_provider(provider_code: str, webhook_secret: Optional[str] = None) -> PaymentProviderBase:
    """Factory: retorna instância do provedor pelo código (marketplace)."""
    code = (provider_code or "").lower()
    if code == PROVIDER_MP:
        return MercadoPagoMarketplaceProvider(webhook_secret=webhook_secret)
    return StubMarketplaceProvider(code=code or "stub")
