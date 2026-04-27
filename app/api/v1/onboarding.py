# PDV Ibix - Onboarding e importação em lote (Fase 1.4)
"""Templates para importação e importação em lote de estabelecimentos/clientes."""
import csv
import io
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ...core.middleware import forbid_cliente_access, get_cliente_scope_dep, get_current_user
from ...core.scope import ClienteScope
from ...database.connection import get_db
from ...models import Cliente, ClienteAdministradorCliente, Usuario
from ...schemas.cliente import ClienteCreate

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])


def _allowed_cliente_ids(scope: ClienteScope) -> list | None:
    if not scope.must_filter_by_cliente():
        return None
    return scope.allowed_ids or []


@router.get("/template/clientes")
async def download_template_clientes(
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
):
    """Retorna CSV modelo para importação de clientes/estabelecimentos (nome, cnpj, endereço, etc.)."""
    headers = [
        "nome", "cnpj", "cep", "endereco", "cidade", "uf", "contato", "telefone", "email"
    ]
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    # Linha de exemplo vazia: apenas cabeçalhos; sem dados mockados
    writer.writerow([""] * len(headers))
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=template_clientes.csv"},
    )


class ClienteImportItem(ClienteCreate):
    """Item para importação em lote (mesmo schema de ClienteCreate)."""
    pass


class ClienteImportResponse(BaseModel):
    criados: int
    erros: List[dict]


@router.post("/import/clientes", response_model=ClienteImportResponse)
async def importar_clientes_lote(
    body: List[ClienteImportItem],
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Importa clientes em lote (JSON). Respeita escopo: CA vincula novos clientes ao seu escopo."""
    allowed = _allowed_cliente_ids(scope)
    criados = 0
    erros: List[dict] = []
    if current_user.role and current_user.role.nome == "Cliente Administrador" and allowed is not None and not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cliente Administrador sem escopo para vincular estabelecimentos",
        )
    for idx, item in enumerate(body):
        try:
            data = item.model_dump()
            if db.query(Cliente).filter(Cliente.cnpj == data["cnpj"]).first():
                erros.append({"linha": idx + 1, "cnpj": data["cnpj"], "erro": "CNPJ já cadastrado"})
                continue
            cliente = Cliente(**data)
            db.add(cliente)
            db.flush()
            if current_user.role and current_user.role.nome == "Cliente Administrador":
                db.add(ClienteAdministradorCliente(usuario_id=current_user.id, cliente_id=cliente.id))
            criados += 1
        except HTTPException:
            raise
        except IntegrityError:
            erros.append({"linha": idx + 1, "cnpj": data.get("cnpj", ""), "erro": "CNPJ ou registro duplicado"})
        except Exception as e:
            erros.append({"linha": idx + 1, "cnpj": data.get("cnpj", ""), "erro": str(e)})
    db.commit()
    return ClienteImportResponse(criados=criados, erros=erros)
