# PDV Ibix — Categorias da vitrine no cadastro do lojista (CA)
from typing import List, Optional, Sequence

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models import (
    Cliente,
    ClienteAdministradorCliente,
    ClienteMaterialCategoria,
    Empresa,
    LojaMarketplace,
    MaterialCategoria,
    Usuario,
)
def listar_categorias_vitrine_ativas(db: Session) -> List[MaterialCategoria]:
    """Mesma base da vitrine: material_categoria ativas, ordenadas por nome."""
    return (
        db.query(MaterialCategoria)
        .filter(MaterialCategoria.ativo.is_(True))
        .order_by(MaterialCategoria.nome)
        .all()
    )


def validar_ids_categorias_vitrine(db: Session, ids: Sequence[int]) -> List[int]:
    """Retorna IDs únicos válidos; falha se vazio ou ID inválido/inativo."""
    raw = [int(x) for x in ids if x is not None]
    unique = list(dict.fromkeys(raw))
    if not unique:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selecione ao menos uma categoria de produtos que sua loja comercializa.",
        )
    ativos = {
        r[0]
        for r in db.query(MaterialCategoria.id)
        .filter(MaterialCategoria.id.in_(unique), MaterialCategoria.ativo.is_(True))
        .all()
    }
    invalidos = [i for i in unique if i not in ativos]
    if invalidos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uma ou mais categorias selecionadas são inválidas ou estão inativas.",
        )
    return unique


def salvar_categorias_cliente(db: Session, cliente_id: int, categoria_ids: Sequence[int]) -> None:
    ids = validar_ids_categorias_vitrine(db, categoria_ids)
    for cid in ids:
        db.add(
            ClienteMaterialCategoria(
                cliente_id=cliente_id,
                material_categoria_id=cid,
            )
        )


def listar_categorias_do_cliente(db: Session, cliente_id: int) -> List[dict]:
    rows = (
        db.query(MaterialCategoria)
        .join(
            ClienteMaterialCategoria,
            ClienteMaterialCategoria.material_categoria_id == MaterialCategoria.id,
        )
        .filter(ClienteMaterialCategoria.cliente_id == cliente_id)
        .order_by(MaterialCategoria.nome)
        .all()
    )
    return [
        {
            "id": r.id,
            "nome": r.nome,
            "codigo": r.codigo,
            "icone": r.icone,
            "descricao": r.descricao,
        }
        for r in rows
    ]


def cliente_eh_empresa_fiscal(db: Session, cliente_id: int) -> bool:
    return (
        db.query(Empresa.id)
        .filter(Empresa.cliente_id == cliente_id)
        .first()
        is not None
    )


def build_perfil_lojista(db: Session, cliente_id: int) -> dict:
    """Dados completos do CA/lojista para Superadmin (empresa fiscal + responsável + categorias)."""
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado")

    empresa = db.query(Empresa).filter(Empresa.cliente_id == cliente_id).first()
    if not empresa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Este cliente não é uma empresa fiscal (cadastro de lojista).",
        )

    ca_link = (
        db.query(ClienteAdministradorCliente)
        .filter(ClienteAdministradorCliente.cliente_id == cliente_id)
        .order_by(ClienteAdministradorCliente.id.asc())
        .first()
    )
    usuario_ca: Optional[Usuario] = None
    if ca_link:
        usuario_ca = (
            db.query(Usuario)
            .options(joinedload(Usuario.role))
            .filter(Usuario.id == ca_link.usuario_id)
            .first()
        )

    loja = db.query(LojaMarketplace).filter(LojaMarketplace.cliente_id == cliente_id).first()
    categorias = listar_categorias_do_cliente(db, cliente_id)

    tenant_id = usuario_ca.tenant_id if usuario_ca else None
    tenant_nome = None
    tenant_slug = None
    if tenant_id:
        from app.models.tenant import Tenant

        t = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if t:
            tenant_nome = t.nome
            tenant_slug = t.slug

    return {
        "cliente_id": cliente.id,
        "empresa": {
            "nome": cliente.nome,
            "cnpj": cliente.cnpj,
            "cpf": cliente.cpf,
            "cep": cliente.cep,
            "endereco": cliente.endereco,
            "cidade": cliente.cidade,
            "uf": cliente.uf,
            "contato": cliente.contato,
            "telefone": cliente.telefone,
            "email": cliente.email,
            "banco_nome": cliente.banco_nome,
            "banco_codigo": cliente.banco_codigo,
            "agencia": cliente.agencia,
            "conta": cliente.conta,
            "tipo_conta": cliente.tipo_conta,
            "pix_chave": cliente.pix_chave,
            "created_at": cliente.created_at.isoformat() if cliente.created_at else None,
        },
        "empresa_fiscal": {
            "id": empresa.id,
            "razao_social": empresa.razao_social,
            "nome_fantasia": empresa.nome_fantasia,
            "cnpj": empresa.cnpj,
            "ambiente": empresa.ambiente.value if hasattr(empresa.ambiente, "value") else str(empresa.ambiente),
            "ativo": empresa.ativo,
        },
        "responsavel_ca": {
            "usuario_id": usuario_ca.id if usuario_ca else None,
            "nome": usuario_ca.nome if usuario_ca else None,
            "email": usuario_ca.email if usuario_ca else None,
            "ativo": usuario_ca.ativo if usuario_ca else None,
            "role": usuario_ca.role.nome if usuario_ca and usuario_ca.role else None,
            "tenant_id": tenant_id,
        },
        "tenant": {
            "id": tenant_id,
            "nome": tenant_nome,
            "slug": tenant_slug,
        },
        "loja_marketplace": {
            "id": loja.id if loja else None,
            "nome_loja": loja.nome_loja if loja else None,
            "nome_fantasia": loja.nome_fantasia if loja else None,
            "slug": loja.slug if loja else None,
            "status": loja.status if loja else None,
        }
        if loja
        else None,
        "categorias_vitrine": categorias,
    }
