# PDV Ibix - Cliente Service
import math
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from ..models.cliente import Cliente
from ..models.empresa import Empresa
from ..schemas.cliente import ClienteCreate, ClienteSearchParams, ClienteUpdate


class ClienteService:
    """Serviço para operações com clientes"""

    @staticmethod
    def criar_cliente(
        db: Session,
        cliente_data: ClienteCreate,
        ids_escopo_subcliente: Optional[List[int]] = None,
    ) -> Cliente:
        """
        Cria um novo cliente (PJ com CNPJ ou PF com CPF).
        ids_escopo_subcliente: quando informado (CA criando subcliente), valida CNPJ/CPF
        duplicado apenas entre os clientes desse escopo. Quando None (Admin/Super),
        não valida duplicata global (permite mesmo CNPJ em CAs diferentes).
        """
        try:
            if cliente_data.cnpj:
                q = db.query(Cliente).filter(Cliente.cnpj == cliente_data.cnpj)
                if ids_escopo_subcliente is not None:
                    q = q.filter(Cliente.id.in_(ids_escopo_subcliente))
                if q.first():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="CNPJ já cadastrado no sistema"
                    )
            if cliente_data.cpf:
                q = db.query(Cliente).filter(Cliente.cpf == cliente_data.cpf)
                if ids_escopo_subcliente is not None:
                    q = q.filter(Cliente.id.in_(ids_escopo_subcliente))
                if q.first():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="CPF já cadastrado no sistema"
                    )

            # Criar cliente (PJ = cnpj preenchido; PF = cpf preenchido)
            cliente = Cliente(**cliente_data.model_dump())
            db.add(cliente)
            db.commit()
            db.refresh(cliente)

            if cliente.cep:
                try:
                    from app.worker.geo_tasks import geocode_endereco
                    geocode_endereco.delay("clientes", cliente.id, cliente.cep)
                except Exception:
                    pass

            return cliente
            
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao criar cliente: {str(e)}"
            )
    
    @staticmethod
    def obter_cliente(db: Session, cliente_id: int) -> Optional[Cliente]:
        """Obtém um cliente por ID"""
        cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        if not cliente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente não encontrado"
            )
        return cliente
    
    @staticmethod
    def listar_clientes(db: Session, params: ClienteSearchParams) -> Dict[str, Any]:
        """Lista clientes com filtros e paginação"""
        try:
            # Query base
            query = db.query(Cliente)
            
            # Aplicar filtros
            filtros = []
            
            if params.nome:
                filtros.append(Cliente.nome.ilike(f"%{params.nome}%"))
            
            if params.cnpj:
                filtros.append(Cliente.cnpj.ilike(f"%{params.cnpj}%"))
            if params.cpf:
                filtros.append(Cliente.cpf.ilike(f"%{params.cpf}%"))
            
            if params.cidade:
                filtros.append(Cliente.cidade.ilike(f"%{params.cidade}%"))
            
            if params.uf:
                filtros.append(Cliente.uf == params.uf.upper())
            if params.cliente_ids is not None and len(params.cliente_ids) > 0:
                query = query.filter(Cliente.id.in_(params.cliente_ids))

            # Filtro Empresa Fiscal: "true"=só Clientes com Empresa vinculada, "false"=só Subclientes
            if params.empresa_fiscal == "true":
                subq = db.query(Empresa.cliente_id).filter(Empresa.cliente_id.isnot(None)).distinct()
                query = query.filter(Cliente.id.in_(subq))
            elif params.empresa_fiscal == "false":
                subq = db.query(Empresa.cliente_id).filter(Empresa.cliente_id.isnot(None)).distinct()
                query = query.filter(~Cliente.id.in_(subq))
            
            if filtros:
                query = query.filter(or_(*filtros))
            
            # Contar total
            total = query.count()
            
            # Aplicar paginação
            offset = (params.pagina - 1) * params.por_pagina
            clientes = query.offset(offset).limit(params.por_pagina).all()
            
            # Calcular total de páginas
            total_paginas = math.ceil(total / params.por_pagina)
            
            return {
                "clientes": clientes,
                "total": total,
                "pagina": params.pagina,
                "por_pagina": params.por_pagina,
                "total_paginas": total_paginas
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao listar clientes: {str(e)}"
            )
    
    @staticmethod
    def atualizar_cliente(
        db: Session,
        cliente_id: int,
        cliente_data: ClienteUpdate,
        ids_escopo_subcliente: Optional[List[int]] = None,
    ) -> Cliente:
        """Atualiza um cliente. ids_escopo_subcliente: quando informado, valida CNPJ/CPF duplicado só nesse escopo."""
        try:
            # Buscar cliente
            cliente = ClienteService.obter_cliente(db, cliente_id)
            
            if cliente_data.cnpj is not None and cliente_data.cnpj != cliente.cnpj:
                q = db.query(Cliente).filter(
                    and_(Cliente.cnpj == cliente_data.cnpj, Cliente.id != cliente_id)
                )
                if ids_escopo_subcliente is not None:
                    q = q.filter(Cliente.id.in_(ids_escopo_subcliente))
                if q.first():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="CNPJ já cadastrado no sistema"
                    )
            if cliente_data.cpf is not None and cliente_data.cpf != cliente.cpf:
                q = db.query(Cliente).filter(
                    and_(Cliente.cpf == cliente_data.cpf, Cliente.id != cliente_id)
                )
                if ids_escopo_subcliente is not None:
                    q = q.filter(Cliente.id.in_(ids_escopo_subcliente))
                if q.first():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="CPF já cadastrado no sistema"
                    )
            
            # Atualizar campos
            dados_atualizacao = cliente_data.model_dump(exclude_unset=True)
            for campo, valor in dados_atualizacao.items():
                setattr(cliente, campo, valor)
            
            db.commit()
            db.refresh(cliente)

            if (("cep" in dados_atualizacao) or ("endereco" in dados_atualizacao)) and cliente.cep:
                try:
                    from app.worker.geo_tasks import geocode_endereco
                    geocode_endereco.delay("clientes", cliente.id, cliente.cep)
                except Exception:
                    pass

            return cliente
            
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao atualizar cliente: {str(e)}"
            )
    
    @staticmethod
    def deletar_cliente(db: Session, cliente_id: int) -> bool:
        """Deleta um cliente"""
        try:
            # Buscar cliente
            cliente = ClienteService.obter_cliente(db, cliente_id)
            
            # Deletar cliente
            db.delete(cliente)
            db.commit()
            
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao deletar cliente: {str(e)}"
            )
    
    @staticmethod
    def buscar_por_cnpj(db: Session, cnpj: str) -> Optional[Cliente]:
        """Busca cliente por CNPJ"""
        return db.query(Cliente).filter(Cliente.cnpj == cnpj).first()
    
    @staticmethod
    def obter_estatisticas(db: Session) -> Dict[str, Any]:
        """Obtém estatísticas dos clientes"""
        try:
            total_clientes = db.query(Cliente).count()
            
            # Clientes por UF
            clientes_por_uf = db.query(Cliente.uf, db.func.count(Cliente.id)).group_by(Cliente.uf).all()
            
            # Top 5 cidades
            top_cidades = db.query(Cliente.cidade, db.func.count(Cliente.id)).group_by(Cliente.cidade).order_by(
                db.func.count(Cliente.id).desc()
            ).limit(5).all()
            
            return {
                "total_clientes": total_clientes,
                "clientes_por_uf": dict(clientes_por_uf),
                "top_cidades": dict(top_cidades)
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao obter estatísticas: {str(e)}"
            ) 