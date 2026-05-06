from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.logging import log_error
from app.core.scope import resolve_tenant_id_from_cliente_id
from app.models import (
    Cliente,
    Configuracao,
    OrdemServico,
    OrdemServicoItem,
    OrdemServicoTipo,
    TipoMaterial,
    Usuario,
)
from app.schemas.ordem_servico import (
    OrdemServicoCreate,
    OrdemServicoResumoResponse,
    OrdemServicoStatusEnum,
    OrdemServicoUpdate,
)


class OrdemServicoService:
    """Serviço responsável pelas regras de negócio de Ordens de Serviço"""

    CODIGO_CONFIG_KEY = "ordem_servico.proximo_numero"
    CODIGO_PREFIX = "OS"

    # ------------------------------------------------------------------ #
    # Utilidades internas
    # ------------------------------------------------------------------ #
    @staticmethod
    def _gerar_codigo(db: Session) -> str:
        """Gera código sequencial no formato OS-ANO-#####"""
        ano_atual = datetime.now().year

        config = (
            db.query(Configuracao)
            .filter(Configuracao.chave == OrdemServicoService.CODIGO_CONFIG_KEY)
            .with_for_update(nowait=False)
            .first()
        )

        if not config:
            numero = 1
            config = Configuracao(
                chave=OrdemServicoService.CODIGO_CONFIG_KEY,
                valor="2",
                descricao="Sequência para geração de códigos de Ordem de Serviço",
            )
            db.add(config)
        else:
            numero = int(config.valor)
            config.valor = str(numero + 1)

        codigo = f"{OrdemServicoService.CODIGO_PREFIX}-{ano_atual}-{numero:05d}"
        return codigo

    @staticmethod
    def _sanitizar_decimal(valor: Any, default: Decimal = Decimal("0")) -> Decimal:
        if valor is None:
            return default
        if isinstance(valor, Decimal):
            return valor
        try:
            return Decimal(str(valor))
        except Exception:
            return default

    @staticmethod
    def garantir_tipo_servico_do_catalogo_estoque(db: Session, tenant_id: int) -> None:
        """
        Se o tenant ainda não tem nenhum tipo de ordem de serviço, cria um registro em
        `ordem_servico_tipo` espelhando o tipo de material global SERVICO (catálogo de estoque).

        Tipos de OS e tipos de material são tabelas distintas; esta rotina só faz o bootstrap
        para o dropdown não ficar vazio quando o CA nunca usou «Gerenciar tipos de ordem».
        Idempotente: se já existir qualquer tipo para o tenant, não altera nada.
        """
        existe = (
            db.query(OrdemServicoTipo.id)
            .filter(OrdemServicoTipo.tenant_id == tenant_id)
            .limit(1)
            .first()
        )
        if existe:
            return
        tm = (
            db.query(TipoMaterial)
            .filter(TipoMaterial.codigo == "SERVICO", TipoMaterial.ativo.is_(True))
            .first()
        )
        if tm:
            db.add(
                OrdemServicoTipo(
                    tenant_id=tenant_id,
                    nome=tm.nome,
                    codigo=tm.codigo,
                    ativo=True,
                )
            )
        else:
            db.add(
                OrdemServicoTipo(
                    tenant_id=tenant_id,
                    nome="Serviço",
                    codigo="SERVICO",
                    ativo=True,
                )
            )
        try:
            db.commit()
        except IntegrityError:
            db.rollback()

    @staticmethod
    def _preparar_itens(itens_payload: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        itens_sanitizados: List[Dict[str, Any]] = []
        for raw in itens_payload:
            nome = raw.get("nome")
            if not nome:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Item da OS sem descrição (nome).",
                )

            quantidade = OrdemServicoService._sanitizar_decimal(raw.get("quantidade"))
            valor_unitario = OrdemServicoService._sanitizar_decimal(raw.get("valor_unitario"))
            desconto = OrdemServicoService._sanitizar_decimal(raw.get("desconto"))
            if quantidade <= Decimal("0"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Quantidade do item deve ser maior que zero.",
                )
            if valor_unitario < Decimal("0"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Valor unitário do item não pode ser negativo.",
                )
            if desconto < Decimal("0"):
                desconto = Decimal("0")
            valor_total = raw.get("valor_total")
            valor_total_decimal = (
                OrdemServicoService._sanitizar_decimal(valor_total)
                if valor_total is not None
                else quantidade * valor_unitario - desconto
            )
            if valor_total_decimal < Decimal("0"):
                valor_total_decimal = Decimal("0")

            itens_sanitizados.append(
                {
                    "produto_cliente_id": raw.get("produto_cliente_id"),
                    "codigo": raw.get("codigo"),
                    "nome": nome,
                    "unidade": raw.get("unidade"),
                    "quantidade": quantidade.quantize(Decimal("0.01")),
                    "valor_unitario": valor_unitario.quantize(Decimal("0.01")),
                    "desconto": desconto.quantize(Decimal("0.01")),
                    "valor_total": valor_total_decimal.quantize(Decimal("0.01")),
                    "observacao": raw.get("observacao"),
                }
            )
        return itens_sanitizados

    @staticmethod
    def _validar_cliente(db: Session, cliente_id: int) -> Cliente:
        cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        if not cliente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente informado não foi encontrado",
            )
        return cliente

    @staticmethod
    def _validar_responsavel(db: Session, responsavel_id: Optional[int]) -> Optional[Usuario]:
        if responsavel_id is None:
            return None

        usuario = db.query(Usuario).filter(Usuario.id == responsavel_id).first()
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Responsável informado não foi encontrado",
            )
        return usuario

    @staticmethod
    def _validar_tipo_para_cliente(db: Session, tipo_id: int, cliente_id: int) -> OrdemServicoTipo:
        """Valida que o tipo existe e pertence ao tenant do cliente da OS."""
        tipo = db.query(OrdemServicoTipo).filter(
            OrdemServicoTipo.id == tipo_id,
            OrdemServicoTipo.ativo == True,
        ).first()
        if not tipo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tipo de ordem de serviço não encontrado ou inativo",
            )
        tenant_do_cliente = resolve_tenant_id_from_cliente_id(db, cliente_id)
        if tenant_do_cliente is not None and tipo.tenant_id != tenant_do_cliente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tipo de ordem de serviço não pertence ao tenant do cliente",
            )
        return tipo

    # ------------------------------------------------------------------ #
    # Operações públicas
    # ------------------------------------------------------------------ #
    @staticmethod
    def listar_ordens(
        db: Session,
        busca: Optional[str] = None,
        cliente_id: Optional[int] = None,
        cliente_ids: Optional[List[int]] = None,
        status: Optional[OrdemServicoStatusEnum] = None,
        responsavel_id: Optional[int] = None,
        tipo_id: Optional[int] = None,
        prioridade: Optional[str] = None,
    ) -> List[OrdemServico]:
        query = (
            db.query(OrdemServico)
            .options(
                selectinload(OrdemServico.itens),
                selectinload(OrdemServico.vendas),
                selectinload(OrdemServico.tipo_rel),
            )
            .order_by(OrdemServico.data_abertura.desc())
        )

        if cliente_ids is not None:
            if not cliente_ids:
                return []
            query = query.filter(OrdemServico.cliente_id.in_(cliente_ids))
        elif cliente_id is not None:
            query = query.filter(OrdemServico.cliente_id == cliente_id)

        if status:
            query = query.filter(OrdemServico.status == status.value)

        if responsavel_id:
            query = query.filter(OrdemServico.responsavel_id == responsavel_id)

        if tipo_id is not None:
            query = query.filter(OrdemServico.tipo_id == tipo_id)

        if prioridade:
            query = query.filter(OrdemServico.prioridade == prioridade)

        if busca:
            ilike = f"%{busca}%"
            query = query.filter(
                or_(
                    OrdemServico.codigo.ilike(ilike),
                    OrdemServico.observacoes.ilike(ilike),
                )
            )

        return query.all()

    @staticmethod
    def listar_ordens_paginado(
        db: Session,
        busca: Optional[str] = None,
        cliente_id: Optional[int] = None,
        cliente_ids: Optional[List[int]] = None,
        status: Optional[OrdemServicoStatusEnum] = None,
        responsavel_id: Optional[int] = None,
        tipo_id: Optional[int] = None,
        prioridade: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple:
        """Retorna (ordens, total) com paginação."""
        query = (
            db.query(OrdemServico)
            .options(
                selectinload(OrdemServico.itens),
                selectinload(OrdemServico.vendas),
                selectinload(OrdemServico.tipo_rel),
            )
            .order_by(OrdemServico.data_abertura.desc())
        )
        if cliente_ids is not None:
            if not cliente_ids:
                return [], 0
            query = query.filter(OrdemServico.cliente_id.in_(cliente_ids))
        elif cliente_id is not None:
            query = query.filter(OrdemServico.cliente_id == cliente_id)
        if status:
            query = query.filter(OrdemServico.status == status.value)
        if responsavel_id:
            query = query.filter(OrdemServico.responsavel_id == responsavel_id)
        if tipo_id is not None:
            query = query.filter(OrdemServico.tipo_id == tipo_id)
        if prioridade:
            query = query.filter(OrdemServico.prioridade == prioridade)
        if busca:
            ilike = f"%{busca}%"
            query = query.filter(
                or_(
                    OrdemServico.codigo.ilike(ilike),
                    OrdemServico.observacoes.ilike(ilike),
                )
            )
        total = query.count()
        ordens = query.offset(skip).limit(limit).all()
        return ordens, total

    @staticmethod
    def obter_ordem(db: Session, ordem_id: int) -> OrdemServico:
        ordem = (
            db.query(OrdemServico)
            .options(
                selectinload(OrdemServico.itens),
                selectinload(OrdemServico.vendas),
                selectinload(OrdemServico.tipo_rel),
            )
            .filter(OrdemServico.id == ordem_id)
            .first()
        )
        if not ordem:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ordem de serviço não encontrada",
            )
        return ordem

    @staticmethod
    def criar_ordem(db: Session, dados: OrdemServicoCreate, usuario_id: int, aplicado_por: Optional[str] = None) -> OrdemServico:
        try:
            cliente = OrdemServicoService._validar_cliente(db, dados.cliente_id)
            responsavel = OrdemServicoService._validar_responsavel(db, dados.responsavel_id)
            OrdemServicoService._validar_tipo_para_cliente(db, dados.tipo_id, dados.cliente_id)

            itens_sanitizados = OrdemServicoService._preparar_itens(
                [item.dict() for item in dados.itens] if dados.itens else []
            )

            codigo = dados.codigo or OrdemServicoService._gerar_codigo(db)

            # Obter nome do usuário para aplicado_por
            if not aplicado_por:
                usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
                aplicado_por = usuario.email if usuario and usuario.email else f"usuario_{usuario_id}"

            os_obj = OrdemServico(
                codigo=codigo,
                cliente_id=cliente.id,
                tipo_id=dados.tipo_id,
                prioridade=dados.prioridade.value,
                status=dados.status.value,
                responsavel_id=responsavel.id if responsavel else None,
                data_abertura=datetime.now(),
                data_prevista=dados.data_prevista,
                data_conclusao=dados.data_conclusao,
                observacoes=dados.observacoes,
            )

            db.add(os_obj)
            db.flush()

            # Criar itens
            for item_payload in itens_sanitizados:
                item_obj = OrdemServicoItem(
                    ordem_servico_id=os_obj.id,
                    **{k: v for k, v in item_payload.items() if k not in ["lacre_lote_id", "lacre_serial", "historico_selo_id"]},
                )
                db.add(item_obj)

            db.commit()
            db.refresh(os_obj)
            return os_obj

        except HTTPException:
            raise
        except Exception as exc:
            db.rollback()
            log_error(f"❌ Erro ao criar ordem de serviço: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao criar ordem de serviço: {exc}",
            )

    @staticmethod
    def atualizar_ordem(db: Session, ordem_id: int, dados: OrdemServicoUpdate) -> OrdemServico:
        try:
            ordem = OrdemServicoService.obter_ordem(db, ordem_id)

            if dados.responsavel_id is not None:
                OrdemServicoService._validar_responsavel(db, dados.responsavel_id)

            if dados.tipo_id is not None:
                OrdemServicoService._validar_tipo_para_cliente(db, dados.tipo_id, ordem.cliente_id)
            campos_atualizar = dados.dict(exclude_unset=True, exclude={"itens"})
            for campo, valor in campos_atualizar.items():
                if campo in {"prioridade", "status"} and valor is not None:
                    setattr(ordem, campo, valor.value if isinstance(valor, Enum) else valor)
                else:
                    setattr(ordem, campo, valor)

            if dados.itens is not None:
                itens_sanitizados = OrdemServicoService._preparar_itens(
                    [item.dict(exclude_unset=True) for item in dados.itens]
                )
                # Remover itens antigos
                db.query(OrdemServicoItem).filter(
                    OrdemServicoItem.ordem_servico_id == ordem.id
                ).delete()
                db.flush()
                # Criar novos itens
                for item_payload in itens_sanitizados:
                    item_obj = OrdemServicoItem(
                        ordem_servico_id=ordem.id,
                        **{k: v for k, v in item_payload.items() if k not in ["lacre_lote_id", "lacre_serial", "historico_selo_id", "id"]},
                    )
                    db.add(item_obj)

            db.commit()
            db.refresh(ordem)
            return ordem

        except HTTPException:
            raise
        except Exception as exc:
            db.rollback()
            log_error(f"❌ Erro ao atualizar ordem de serviço {ordem_id}: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao atualizar ordem de serviço: {exc}",
            )

    @staticmethod
    def atualizar_status(
        db: Session,
        ordem_id: int,
        novo_status: OrdemServicoStatusEnum,
        observacoes: Optional[str] = None,
        data_conclusao: Optional[datetime] = None,
    ) -> OrdemServico:
        try:
            ordem = OrdemServicoService.obter_ordem(db, ordem_id)
            ordem.status = novo_status.value

            if observacoes:
                ordem.observacoes = (ordem.observacoes or "") + f"\n{observacoes}"

            if novo_status == OrdemServicoStatusEnum.concluida:
                ordem.data_conclusao = data_conclusao or datetime.now()

            db.commit()
            db.refresh(ordem)
            return ordem
        except HTTPException:
            raise
        except Exception as exc:
            db.rollback()
            log_error(f"❌ Erro ao atualizar status da OS {ordem_id}: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao atualizar status da ordem de serviço: {exc}",
            )

    @staticmethod
    def remover_ordem(db: Session, ordem_id: int) -> None:
        try:
            ordem = OrdemServicoService.obter_ordem(db, ordem_id)
            db.delete(ordem)
            db.commit()
        except HTTPException:
            raise
        except Exception as exc:
            db.rollback()
            log_error(f"❌ Erro ao remover OS {ordem_id}: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao remover ordem de serviço: {exc}",
            )

    @staticmethod
    def listar_resumo(db: Session) -> List[OrdemServicoResumoResponse]:
        ordens = OrdemServicoService.listar_ordens(db)
        resposta: List[OrdemServicoResumoResponse] = []

        for ordem in ordens:
            tipo_rel = getattr(ordem, "tipo_rel", None)
            resposta.append(
                OrdemServicoResumoResponse(
                    id=ordem.id,
                    codigo=ordem.codigo,
                    cliente_id=ordem.cliente_id,
                    cliente_nome=ordem.cliente.nome if ordem.cliente else None,
                    status=OrdemServicoStatusEnum(ordem.status),
                    tipo_id=ordem.tipo_id,
                    tipo_nome=tipo_rel.nome if tipo_rel else None,
                    prioridade=ordem.prioridade,
                    data_abertura=ordem.data_abertura,
                    data_prevista=ordem.data_prevista,
                    data_conclusao=ordem.data_conclusao,
                )
            )

        return resposta


