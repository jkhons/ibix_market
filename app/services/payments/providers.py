# PDV Ibix - Interface de provedores de pagamento (Fase 3.3)
"""Interface única que todos os provedores implementam (charge, refund, getStatus, supportsMethod)."""
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, Optional

import httpx

from .mercadopago_api import (
    MP_PAYMENTS_URL,
    extract_pix_from_mp_payment_body,
    format_mercadopago_api_error,
    minutes_until_mp_expiration,
)

# Métodos suportados pelo plano: credit, debit, pix, boleto, cash, transfer
SUPPORTED_METHODS = {"credit", "debit", "pix", "boleto", "cash", "transfer"}


@dataclass
class ChargeRequest:
    """Request para cobrança."""
    amount: Decimal
    payment_method: str
    payment_submethod: Optional[str] = None
    installments: int = 1
    idempotency_key: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ChargeResult:
    """Resultado da cobrança."""
    success: bool
    provider_transaction_id: Optional[str] = None
    status: str = "pending"  # pending, authorized, paid, failed
    payment_details: Optional[Dict[str, Any]] = None
    message: Optional[str] = None


@dataclass
class RefundResult:
    """Resultado do estorno."""
    success: bool
    status: str = "refunded"
    message: Optional[str] = None


@dataclass
class StatusResult:
    """Status da transação no provedor."""
    status: str
    provider_transaction_id: Optional[str] = None
    paid_at: Optional[Any] = None
    message: Optional[str] = None


class PaymentProvider(ABC):
    """Interface que todos os provedores (PagBank, Cielo, Stone, Efí, etc.) implementam."""

    @property
    @abstractmethod
    def provider_code(self) -> str:
        """Código do provedor (pagbank, cielo, stone, efi, mercadopago)."""
        pass

    @abstractmethod
    def charge(self, request: ChargeRequest, credentials: Optional[Dict[str, Any]]) -> ChargeResult:
        """Processa cobrança. credentials = dict deserializado (já descriptografado)."""
        pass

    @abstractmethod
    def refund(self, transaction_id: str, credentials: Optional[Dict[str, Any]]) -> RefundResult:
        """Estorna transação pelo ID no provedor."""
        pass

    @abstractmethod
    def get_status(self, transaction_id: str, credentials: Optional[Dict[str, Any]]) -> StatusResult:
        """Consulta status da transação no provedor."""
        pass

    def supports_method(self, method: str) -> bool:
        """Retorna True se o provedor suporta o método (credit, debit, pix, etc.)."""
        return method.lower() in SUPPORTED_METHODS


class StubProvider(PaymentProvider):
    """Provedor stub para desenvolvimento e testes. Não chama gateway real."""

    @property
    def provider_code(self) -> str:
        return "stub"

    def charge(self, request: ChargeRequest, credentials: Optional[Dict[str, Any]]) -> ChargeResult:
        return ChargeResult(
            success=True,
            provider_transaction_id=f"stub-{id(request)}",
            status="authorized",
            payment_details={"message": "StubProvider: cobrança simulada (3.3.1)"},
        )

    def refund(self, transaction_id: str, credentials: Optional[Dict[str, Any]]) -> RefundResult:
        return RefundResult(success=True, status="refunded", message="StubProvider: estorno simulado")

    def get_status(self, transaction_id: str, credentials: Optional[Dict[str, Any]]) -> StatusResult:
        return StatusResult(status="paid", provider_transaction_id=transaction_id)


class MercadoPagoProvider(PaymentProvider):
    """Provedor Mercado Pago (fase 1): gera cobrança real via preferência checkout."""

    @property
    def provider_code(self) -> str:
        return "mercadopago"

    def supports_method(self, method: str) -> bool:
        return method.lower() in {"credit", "debit", "pix", "boleto"}

    def charge(self, request: ChargeRequest, credentials: Optional[Dict[str, Any]]) -> ChargeResult:
        credentials = credentials or {}
        access_token = (
            credentials.get("access_token")
            or credentials.get("ACCESS_TOKEN")
            or credentials.get("token")
        )
        if not access_token:
            return ChargeResult(
                success=False,
                status="failed",
                message="Credenciais do Mercado Pago não configuradas (access_token).",
            )

        method = (request.payment_method or "").lower()
        if not self.supports_method(method):
            return ChargeResult(
                success=False,
                status="failed",
                message=f"Método '{method}' não suportado no gateway Mercado Pago nesta fase.",
            )

        idem_key = request.idempotency_key or str(uuid.uuid4())
        amount = float(request.amount or 0)
        if amount <= 0:
            return ChargeResult(success=False, status="failed", message="Valor de pagamento inválido.")

        if method == "pix":
            meta = request.metadata or {}
            email = (meta.get("payer_email") or "").strip()
            if not email:
                return ChargeResult(
                    success=False,
                    status="failed",
                    message="Para PIX Mercado Pago informe method_details.payer_email (e-mail do pagador).",
                )
            notification_url = (meta.get("notification_url") or "").strip()
            pay_body: Dict[str, Any] = {
                "transaction_amount": round(amount, 2),
                "description": "Venda PDV Ibix",
                "payment_method_id": "pix",
                "external_reference": idem_key,
                "payer": {"email": email[:256]},
            }
            if notification_url:
                pay_body["notification_url"] = notification_url[:500]
            pay_headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "X-Idempotency-Key": str(idem_key)[:128],
            }
            try:
                with httpx.Client(timeout=30.0) as client:
                    pay_resp = client.post(MP_PAYMENTS_URL, json=pay_body, headers=pay_headers)
                if not pay_resp.is_success:
                    body = {}
                    try:
                        body = pay_resp.json()
                    except Exception:
                        body = {"raw": pay_resp.text[:500]}
                    msg = format_mercadopago_api_error(pay_resp)
                    return ChargeResult(
                        success=False,
                        status="failed",
                        payment_details={"provider_error": body},
                        message=f"Mercado Pago recusou a solicitação PIX: {msg}",
                    )
                pdata = pay_resp.json()
                if not isinstance(pdata, dict):
                    return ChargeResult(
                        success=False,
                        status="failed",
                        message="Resposta inválida do Mercado Pago ao criar PIX.",
                    )
                qr, qr_b64, ticket_url, exp_iso, pay_id, _st = extract_pix_from_mp_payment_body(pdata)
                if not qr:
                    return ChargeResult(
                        success=False,
                        status="failed",
                        message="Mercado Pago não retornou QR Code PIX. Verifique chave Pix na conta.",
                    )
                exp_min = minutes_until_mp_expiration(exp_iso)
                return ChargeResult(
                    success=True,
                    status="pending",
                    provider_transaction_id=str(pay_id) if pay_id is not None else idem_key,
                    payment_details={
                        "checkout_type": "pix",
                        "pix": {
                            "copia_cola": qr,
                            "qr_code": qr,
                            "qr_code_base64": qr_b64,
                            "expiracao_minutos": exp_min,
                        },
                        "ticket_url": ticket_url,
                        "idempotency_key": idem_key,
                    },
                    message="PIX gerado. Aguardando confirmação do pagamento.",
                )
            except Exception as exc:
                return ChargeResult(
                    success=False,
                    status="failed",
                    message=f"Falha ao conectar com Mercado Pago (PIX): {str(exc)}",
                )

        payload = {
            "items": [
                {
                    "title": "Venda PDV Ibix",
                    "quantity": 1,
                    "currency_id": "BRL",
                    "unit_price": amount,
                }
            ],
            "external_reference": idem_key,
            "metadata": {
                "idempotency_key": idem_key,
                "payment_method": method,
            },
            "auto_return": "approved",
        }
        if request.installments and request.installments > 0:
            payload["payment_methods"] = {"installments": int(request.installments)}

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Idempotency-Key": idem_key,
        }
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    "https://api.mercadopago.com/checkout/preferences",
                    json=payload,
                    headers=headers,
                )
            if not response.is_success:
                body = {}
                try:
                    body = response.json()
                except Exception:
                    body = {"raw": response.text[:500]}
                msg = body.get("message") or body.get("error") or f"HTTP {response.status_code}"
                return ChargeResult(
                    success=False,
                    status="failed",
                    payment_details={"provider_error": body},
                    message=f"Mercado Pago recusou a solicitação: {msg}",
                )

            data = response.json()
            return ChargeResult(
                success=True,
                status="pending",
                provider_transaction_id=str(data.get("id") or idem_key),
                payment_details={
                    "checkout_preference_id": data.get("id"),
                    "checkout_url": data.get("init_point"),
                    "checkout_sandbox_url": data.get("sandbox_init_point"),
                    "idempotency_key": idem_key,
                },
                message="Cobrança criada no Mercado Pago. Aguardando confirmação do pagamento.",
            )
        except Exception as exc:
            return ChargeResult(
                success=False,
                status="failed",
                message=f"Falha ao conectar com Mercado Pago: {str(exc)}",
            )

    def refund(self, transaction_id: str, credentials: Optional[Dict[str, Any]]) -> RefundResult:
        return RefundResult(
            success=False,
            status="failed",
            message="Estorno via gateway não implementado nesta fase.",
        )

    def get_status(self, transaction_id: str, credentials: Optional[Dict[str, Any]]) -> StatusResult:
        return StatusResult(
            status="pending",
            provider_transaction_id=transaction_id,
            message="Consulta online de status no provedor será concluída em próxima fase.",
        )


class PagBankProvider(PaymentProvider):
    """Provedor PagBank: cobrança real via API de Pedidos (POST /orders)."""

    SANDBOX_URL = "https://sandbox.api.pagseguro.com"
    PRODUCTION_URL = "https://api.pagseguro.com"

    @property
    def provider_code(self) -> str:
        return "pagbank"

    def supports_method(self, method: str) -> bool:
        return method.lower() in {"credit", "debit", "pix", "boleto"}

    def _base_url(self, credentials: Optional[Dict[str, Any]]) -> str:
        if credentials and credentials.get("sandbox"):
            return self.SANDBOX_URL
        import os
        if os.environ.get("PAGBANK_CONNECT_SANDBOX", "true").strip().lower() in ("true", "1"):
            return self.SANDBOX_URL
        return self.PRODUCTION_URL

    def charge(self, request: ChargeRequest, credentials: Optional[Dict[str, Any]]) -> ChargeResult:
        credentials = credentials or {}
        access_token = credentials.get("access_token")
        if not access_token:
            return ChargeResult(
                success=False,
                status="failed",
                message="Credenciais PagBank não configuradas (access_token). Conecte sua conta em Recebíveis.",
            )

        method = (request.payment_method or "").lower()
        if not self.supports_method(method):
            return ChargeResult(
                success=False,
                status="failed",
                message=f"Método '{method}' não suportado no PagBank.",
            )

        idem_key = request.idempotency_key or str(uuid.uuid4())
        amount_centavos = int(request.amount * 100)
        if amount_centavos <= 0:
            return ChargeResult(success=False, status="failed", message="Valor de pagamento inválido.")

        base_url = self._base_url(credentials)
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "x-idempotency-key": idem_key,
        }

        payload: Dict[str, Any] = {
            "reference_id": idem_key,
            "customer": {
                "name": request.metadata.get("customer_name", "Cliente") if request.metadata else "Cliente",
                "tax_id": request.metadata.get("customer_tax_id", "") if request.metadata else "",
            },
            "items": [
                {
                    "name": "Venda PDV Ibix",
                    "quantity": 1,
                    "unit_amount": amount_centavos,
                }
            ],
        }

        app_url = (credentials.get("app_url") or "").rstrip("/")
        if app_url:
            payload["notification_urls"] = [f"{app_url}/api/v1/payments/webhook/pagbank"]

        if method == "pix":
            payload["qr_codes"] = [{"amount": {"value": amount_centavos}}]
        elif method in ("credit", "debit"):
            charge_obj: Dict[str, Any] = {
                "amount": {"value": amount_centavos, "currency": "BRL"},
                "payment_method": {
                    "type": "CREDIT_CARD" if method == "credit" else "DEBIT_CARD",
                    "installments": int(request.installments) if request.installments else 1,
                },
            }
            card_token = (request.metadata or {}).get("card_token")
            if card_token:
                charge_obj["payment_method"]["card"] = {"id": card_token}
            payload["charges"] = [charge_obj]
        elif method == "boleto":
            charge_obj = {
                "amount": {"value": amount_centavos, "currency": "BRL"},
                "payment_method": {
                    "type": "BOLETO",
                    "boleto": {
                        "due_date": (request.metadata or {}).get("due_date", ""),
                    },
                },
            }
            payload["charges"] = [charge_obj]

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(f"{base_url}/orders", json=payload, headers=headers)

            if not response.is_success:
                body = {}
                try:
                    body = response.json()
                except Exception:
                    body = {"raw": response.text[:500]}
                msg = str(body.get("error_messages", body.get("message", ""))) or f"HTTP {response.status_code}"
                return ChargeResult(
                    success=False,
                    status="failed",
                    payment_details={"provider_error": body},
                    message=f"PagBank recusou a solicitação: {msg}",
                )

            data = response.json()
            order_id = data.get("id", "")

            details: Dict[str, Any] = {
                "order_id": order_id,
                "idempotency_key": idem_key,
            }

            if method == "pix" and data.get("qr_codes"):
                qr = data["qr_codes"][0]
                details["qr_code"] = qr.get("text")
                details["qr_code_url"] = None
                for link in qr.get("links", []):
                    if link.get("media") == "image/png":
                        details["qr_code_url"] = link.get("href")
                        break

            charges = data.get("charges", [])
            order_status = "pending"
            if charges:
                charge_status = (charges[0].get("status") or "").upper()
                if charge_status == "PAID":
                    order_status = "paid"
                elif charge_status in ("AUTHORIZED",):
                    order_status = "authorized"
                elif charge_status in ("DECLINED", "CANCELED"):
                    order_status = "failed"

            return ChargeResult(
                success=True,
                status=order_status,
                provider_transaction_id=order_id,
                payment_details=details,
                message="Cobrança criada no PagBank.",
            )
        except Exception as exc:
            return ChargeResult(
                success=False,
                status="failed",
                message=f"Falha ao conectar com PagBank: {str(exc)}",
            )

    def refund(self, transaction_id: str, credentials: Optional[Dict[str, Any]]) -> RefundResult:
        credentials = credentials or {}
        access_token = credentials.get("access_token")
        if not access_token:
            return RefundResult(success=False, status="failed", message="Credenciais PagBank não configuradas.")
        base_url = self._base_url(credentials)

        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(f"{base_url}/orders/{transaction_id}", headers={
                    "Authorization": f"Bearer {access_token}",
                })
            if not resp.is_success:
                return RefundResult(success=False, status="failed", message=f"Pedido não encontrado: {transaction_id}")

            order = resp.json()
            charges = order.get("charges", [])
            if not charges:
                return RefundResult(success=False, status="failed", message="Pedido sem cobranças para estornar.")

            charge_id = charges[0].get("id")
            amount_val = charges[0].get("amount", {}).get("value")
            refund_payload = {"amount": {"value": amount_val}}

            with httpx.Client(timeout=30.0) as client:
                resp = client.post(
                    f"{base_url}/charges/{charge_id}/cancel",
                    json=refund_payload,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                    },
                )
            if resp.is_success:
                return RefundResult(success=True, status="refunded", message="Estorno solicitado no PagBank.")
            return RefundResult(success=False, status="failed", message=f"PagBank recusou estorno: {resp.text[:300]}")
        except Exception as exc:
            return RefundResult(success=False, status="failed", message=f"Erro ao estornar no PagBank: {str(exc)}")

    def get_status(self, transaction_id: str, credentials: Optional[Dict[str, Any]]) -> StatusResult:
        credentials = credentials or {}
        access_token = credentials.get("access_token")
        if not access_token:
            return StatusResult(status="pending", message="Credenciais PagBank não configuradas.")
        base_url = self._base_url(credentials)

        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(f"{base_url}/orders/{transaction_id}", headers={
                    "Authorization": f"Bearer {access_token}",
                })
            if not resp.is_success:
                return StatusResult(status="pending", message=f"Erro ao consultar PagBank: HTTP {resp.status_code}")
            data = resp.json()
            charges = data.get("charges", [])
            if charges:
                raw_status = (charges[0].get("status") or "WAITING").upper()
                status_map = {
                    "PAID": "paid",
                    "AUTHORIZED": "authorized",
                    "DECLINED": "refused",
                    "CANCELED": "cancelled",
                    "IN_ANALYSIS": "pending",
                    "WAITING": "pending",
                }
                internal_status = status_map.get(raw_status, "pending")
                return StatusResult(status=internal_status, provider_transaction_id=transaction_id)
            return StatusResult(status="pending", provider_transaction_id=transaction_id)
        except Exception as exc:
            return StatusResult(status="pending", message=f"Erro: {str(exc)}")


class PagarMeProvider(PaymentProvider):
    """Provedor Pagar.me: cobrança real via API v5 (POST /orders). Auth: HTTP Basic com Secret Key."""

    BASE_URL = "https://api.pagar.me/core/v5"

    @property
    def provider_code(self) -> str:
        return "pagarme"

    def supports_method(self, method: str) -> bool:
        return method.lower() in {"credit", "debit", "pix", "boleto"}

    def _auth(self, credentials: Optional[Dict[str, Any]]) -> Optional[tuple]:
        """Retorna tupla (user, pass) para HTTP Basic Auth."""
        credentials = credentials or {}
        secret_key = (
            credentials.get("secret_key")
            or credentials.get("api_key")
            or credentials.get("sk")
        )
        if not secret_key:
            return None
        return (secret_key, "")

    def charge(self, request: ChargeRequest, credentials: Optional[Dict[str, Any]]) -> ChargeResult:
        auth = self._auth(credentials)
        if not auth:
            return ChargeResult(
                success=False,
                status="failed",
                message="Credenciais Pagar.me não configuradas (secret_key). Informe sua Secret Key em Recebíveis.",
            )

        method = (request.payment_method or "").lower()
        if not self.supports_method(method):
            return ChargeResult(
                success=False,
                status="failed",
                message=f"Método '{method}' não suportado no Pagar.me.",
            )

        idem_key = request.idempotency_key or str(uuid.uuid4())
        amount_centavos = int(request.amount * 100)
        if amount_centavos <= 0:
            return ChargeResult(success=False, status="failed", message="Valor de pagamento inválido.")

        metadata = request.metadata or {}
        customer_name = metadata.get("customer_name", "Cliente PDV")
        customer_email = metadata.get("customer_email", "")
        customer_document = metadata.get("customer_document", "")

        payment_obj: Dict[str, Any] = {"amount": amount_centavos}

        if method == "pix":
            payment_obj["payment_method"] = "pix"
            payment_obj["pix"] = {"expires_in": 3600}
        elif method in ("credit", "debit"):
            pm = "credit_card" if method == "credit" else "debit_card"
            payment_obj["payment_method"] = pm
            card_data: Dict[str, Any] = {
                "installments": int(request.installments) if request.installments else 1,
            }
            card_id = metadata.get("card_id")
            card_token = metadata.get("card_token")
            if card_id:
                card_data["card_id"] = card_id
            elif card_token:
                card_data["card_token"] = card_token
            payment_obj[pm] = card_data
        elif method == "boleto":
            payment_obj["payment_method"] = "boleto"
            payment_obj["boleto"] = {
                "due_at": metadata.get("due_date", ""),
                "instructions": "Pagar até o vencimento",
            }

        payload: Dict[str, Any] = {
            "code": idem_key,
            "customer": {
                "name": customer_name,
            },
            "items": [
                {
                    "amount": amount_centavos,
                    "description": "Venda PDV Ibix",
                    "quantity": 1,
                }
            ],
            "payments": [payment_obj],
        }

        if customer_email:
            payload["customer"]["email"] = customer_email
        if customer_document:
            payload["customer"]["document"] = customer_document
            payload["customer"]["type"] = "individual" if len(customer_document) <= 11 else "company"

        headers = {"Content-Type": "application/json"}

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self.BASE_URL}/orders",
                    json=payload,
                    headers=headers,
                    auth=auth,
                )

            if not response.is_success:
                body = {}
                try:
                    body = response.json()
                except Exception:
                    body = {"raw": response.text[:500]}
                msg = str(body.get("message", body.get("errors", ""))) or f"HTTP {response.status_code}"
                return ChargeResult(
                    success=False,
                    status="failed",
                    payment_details={"provider_error": body},
                    message=f"Pagar.me recusou a solicitação: {msg}",
                )

            data = response.json()
            order_id = data.get("id", "")
            order_status_raw = (data.get("status") or "pending").lower()

            details: Dict[str, Any] = {
                "order_id": order_id,
                "idempotency_key": idem_key,
            }

            charges = data.get("charges", [])
            if charges and method == "pix":
                last_tx = charges[0].get("last_transaction", {})
                if last_tx.get("qr_code"):
                    details["qr_code"] = last_tx["qr_code"]
                if last_tx.get("qr_code_url"):
                    details["qr_code_url"] = last_tx["qr_code_url"]

            if charges and method == "boleto":
                last_tx = charges[0].get("last_transaction", {})
                if last_tx.get("url"):
                    details["boleto_url"] = last_tx["url"]
                if last_tx.get("barcode"):
                    details["boleto_barcode"] = last_tx["barcode"]

            status_map = {
                "paid": "paid",
                "pending": "pending",
                "failed": "failed",
                "canceled": "cancelled",
                "closed": "paid",
            }
            internal_status = status_map.get(order_status_raw, "pending")

            return ChargeResult(
                success=True,
                status=internal_status,
                provider_transaction_id=order_id,
                payment_details=details,
                message="Cobrança criada no Pagar.me.",
            )
        except Exception as exc:
            return ChargeResult(
                success=False,
                status="failed",
                message=f"Falha ao conectar com Pagar.me: {str(exc)}",
            )

    def refund(self, transaction_id: str, credentials: Optional[Dict[str, Any]]) -> RefundResult:
        auth = self._auth(credentials)
        if not auth:
            return RefundResult(success=False, status="failed", message="Credenciais Pagar.me não configuradas.")
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(f"{self.BASE_URL}/orders/{transaction_id}", auth=auth)
            if not resp.is_success:
                return RefundResult(success=False, status="failed", message=f"Pedido não encontrado: {transaction_id}")

            order = resp.json()
            charges = order.get("charges", [])
            if not charges:
                return RefundResult(success=False, status="failed", message="Pedido sem cobranças.")

            charge_id = charges[0].get("id")
            with httpx.Client(timeout=30.0) as client:
                resp = client.delete(
                    f"{self.BASE_URL}/charges/{charge_id}",
                    auth=auth,
                )
            if resp.is_success:
                return RefundResult(success=True, status="refunded", message="Estorno solicitado no Pagar.me.")
            return RefundResult(
                success=False, status="failed",
                message=f"Pagar.me recusou estorno: {resp.text[:300]}",
            )
        except Exception as exc:
            return RefundResult(success=False, status="failed", message=f"Erro ao estornar no Pagar.me: {str(exc)}")

    def get_status(self, transaction_id: str, credentials: Optional[Dict[str, Any]]) -> StatusResult:
        auth = self._auth(credentials)
        if not auth:
            return StatusResult(status="pending", message="Credenciais Pagar.me não configuradas.")
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(f"{self.BASE_URL}/orders/{transaction_id}", auth=auth)
            if not resp.is_success:
                return StatusResult(status="pending", message=f"Erro ao consultar Pagar.me: HTTP {resp.status_code}")
            data = resp.json()
            raw = (data.get("status") or "pending").lower()
            status_map = {"paid": "paid", "pending": "pending", "failed": "refused", "canceled": "cancelled", "closed": "paid"}
            return StatusResult(
                status=status_map.get(raw, "pending"),
                provider_transaction_id=transaction_id,
            )
        except Exception as exc:
            return StatusResult(status="pending", message=f"Erro: {str(exc)}")


_PROVIDERS: Dict[str, type] = {
    "stub": StubProvider,
    "mercadopago": MercadoPagoProvider,
    "pagbank": PagBankProvider,
    "pagarme": PagarMeProvider,
}


def register_provider(code: str, provider_class: type) -> None:
    """Registra implementação de provedor."""
    _PROVIDERS[code.lower()] = provider_class


def get_provider(code: str) -> PaymentProvider:
    """Factory: retorna instância do provedor pelo código."""
    code = code.lower()
    if code not in _PROVIDERS:
        raise ValueError(f"Provedor de pagamento '{code}' não registrado no sistema.")
    return _PROVIDERS[code]()
