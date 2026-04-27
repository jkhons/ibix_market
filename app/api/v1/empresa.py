# PDV Ibix - API de Empresa (Dados Fiscais)
import base64
import json
import os
import re
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ...core.middleware import forbid_cliente_access, get_cliente_scope_dep, get_current_user, require_permission
from ...core.scope import ClienteScope
from ...database.connection import get_db
from ...models.empresa import Empresa
from ...models.usuario import Usuario
from ...schemas.empresa import EmpresaCreate, EmpresaResponse, EmpresaUpdate

router = APIRouter(
    prefix="/fiscal/empresa",
    tags=["Fiscal - Empresa"],
    dependencies=[Depends(forbid_cliente_access)]
)


# Parâmetros fiscais (opções dinâmicas para o front — sistema real, não estático)
OPCOES_AMBIENTE = [
    {"value": "homologacao", "label": "Homologação (testes SEFAZ)"},
    {"value": "producao", "label": "Produção (emissão real)"},
]


@router.get("/parametros")
async def obter_parametros_fiscal(
    current_user: Usuario = Depends(get_current_user),
):
    """Retorna parâmetros/opções para o formulário de Empresa Fiscal. Front carrega dinamicamente."""
    return {"opcoes_ambiente": OPCOES_AMBIENTE}


# Diretório para logos de empresa (emissor). Servido em /static/uploads/empresa_logos/
UPLOAD_LOGO_DIR = "app/static/uploads/empresa_logos"
ALLOWED_LOGO_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
MIME_TO_EXT = {"image/png": ".png", "image/jpeg": ".jpg", "image/jpg": ".jpg", "image/gif": ".gif", "image/webp": ".webp"}


def _salvar_logo_emissor(logo_blob: str, empresa_id: int, cliente_id: Optional[int] = None) -> str:
    """
    Decodifica logo em base64 (aceita data URL ou base64 puro), salva em disco
    e retorna o caminho relativo para uso em logo_url.
    Novos arquivos em uploads/empresa_logos/cliente_{cliente_id}/; sem cliente_id (legado) na raiz (compatibilidade).
    """
    if not logo_blob or not logo_blob.strip():
        raise ValueError("logo_emissor_blob vazio")
    raw = logo_blob.strip()
    m = re.match(r"^data:([^;]+);base64,(.+)$", raw, re.DOTALL)
    if m:
        mime = m.group(1).strip().lower()
        b64 = m.group(2)
        ext = MIME_TO_EXT.get(mime, ".png")
    else:
        b64 = raw
        ext = ".png"
    if ext not in ALLOWED_LOGO_EXTENSIONS:
        ext = ".png"
    try:
        content = base64.b64decode(b64)
    except Exception as e:
        raise ValueError(f"Base64 inválido: {e}")
    if not content:
        raise ValueError("Conteúdo da imagem vazio")
    filename = f"empresa_{empresa_id}{ext}"
    if cliente_id is not None:
        subdir = f"cliente_{cliente_id}"
        save_dir = os.path.join(UPLOAD_LOGO_DIR, subdir)
        rel_path = f"/static/uploads/empresa_logos/{subdir}/{filename}"
    else:
        save_dir = UPLOAD_LOGO_DIR
        rel_path = f"/static/uploads/empresa_logos/{filename}"
    file_path = os.path.join(save_dir, filename)
    os.makedirs(save_dir, exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(content)
    return rel_path


def _scope_allows_empresa(scope: ClienteScope, empresa: Empresa) -> bool:
    """Verifica se o escopo do usuário permite acessar a empresa (por cliente_id)."""
    if scope.is_superadmin or scope.see_all:
        return True
    if empresa.cliente_id is None:
        return True  # empresas sem cliente_id (legado) só Superadmin/ver todos
    return empresa.cliente_id in scope.allowed_ids


def _scope_allows_cliente_id(scope: ClienteScope, cliente_id: int) -> bool:
    """Verifica se o escopo permite usar o cliente_id (criar empresa para esse cliente)."""
    if scope.is_superadmin or scope.see_all:
        return True
    return cliente_id in scope.allowed_ids


def _parse_aliquotas_uf(value):  # noqa: ANN001
    """Converte aliquotas_uf (string JSON no banco) para dict/list para a resposta da API."""
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return None
    return None


def converter_empresa_para_dict(empresa: Empresa) -> dict:
    """Converte objeto Empresa do SQLAlchemy para dicionário compatível com EmpresaResponse"""
    from ...models.empresa import AmbienteEnum as SQLAmbienteEnum
    from ...models.empresa import TipoEquipamentoEnum as SQLTipoEquipamentoEnum
    
    # Converter ambiente - retornar string normalizada, o validador do Pydantic fará a conversão
    ambiente_value = None
    if empresa.ambiente is not None:
        try:
            # Se for enum do SQLAlchemy, pegar o valor
            if isinstance(empresa.ambiente, SQLAmbienteEnum):
                str_value = empresa.ambiente.value
            elif hasattr(empresa.ambiente, 'value'):
                str_value = empresa.ambiente.value
            elif isinstance(empresa.ambiente, str):
                str_value = empresa.ambiente.lower().strip()
            else:
                # Tentar converter para string
                str_value = str(empresa.ambiente).lower().strip()
            
            # Normalizar o valor
            if str_value:
                if str_value in ['homologacao', 'HOMOLOGACAO']:
                    ambiente_value = 'homologacao'
                elif str_value in ['producao', 'PRODUCAO']:
                    ambiente_value = 'producao'
        except Exception as e:
            # Se falhar, deixar None e logar o erro
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Erro ao converter ambiente para empresa {empresa.id}: {str(e)}")
            ambiente_value = None
    
    # Converter tipo_equipamento_sat - retornar string normalizada
    tipo_equipamento_value = None
    if empresa.tipo_equipamento_sat is not None:
        try:
            # Se for enum do SQLAlchemy, pegar o valor
            if isinstance(empresa.tipo_equipamento_sat, SQLTipoEquipamentoEnum):
                str_value = empresa.tipo_equipamento_sat.value
            elif hasattr(empresa.tipo_equipamento_sat, 'value'):
                str_value = empresa.tipo_equipamento_sat.value
            elif isinstance(empresa.tipo_equipamento_sat, str):
                str_value = empresa.tipo_equipamento_sat.upper().strip()
            else:
                str_value = str(empresa.tipo_equipamento_sat).upper().strip()
            
            # Normalizar o valor
            if str_value:
                if str_value == 'SAT':
                    tipo_equipamento_value = 'SAT'
                elif str_value in ['MFE', 'MFe']:
                    tipo_equipamento_value = 'MFe'
        except Exception as e:
            # Se falhar, deixar None
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Erro ao converter tipo_equipamento_sat para empresa {empresa.id}: {str(e)}")
            tipo_equipamento_value = None
    
    # Converter crt
    crt_value = None
    if empresa.crt is not None:
        if hasattr(empresa.crt, 'value'):
            crt_value = empresa.crt.value
        elif isinstance(empresa.crt, int):
            crt_value = empresa.crt
        else:
            try:
                crt_value = int(empresa.crt)
            except (ValueError, TypeError):
                crt_value = None
    
    cliente_nome = None
    if empresa.cliente_id and hasattr(empresa, 'cliente') and empresa.cliente:
        cliente_nome = empresa.cliente.nome

    return {
        'id': empresa.id,
        'cliente_id': empresa.cliente_id,
        'cliente_nome': cliente_nome,
        'razao_social': empresa.razao_social,
        'nome_fantasia': empresa.nome_fantasia,
        'cnpj': empresa.cnpj,
        'ie': empresa.ie,
        'im': empresa.im,
        'cnae': empresa.cnae,
        'crt': crt_value,
        'cep': empresa.cep,
        'endereco': empresa.endereco,
        'numero': empresa.numero,
        'complemento': empresa.complemento,
        'bairro': empresa.bairro,
        'cidade': empresa.cidade,
        'uf': empresa.uf,
        'telefone': empresa.telefone,
        'email': empresa.email,
        'certificado_a1_path': empresa.certificado_a1_path,
        'senha_certificado': None,  # Nunca expor senha em resposta
        'certificado_validade': empresa.certificado_validade,
        'provedor_fiscal': getattr(empresa, 'provedor_fiscal', None),
        'ambiente': ambiente_value,
        'uf_emissao': empresa.uf_emissao,
        'municipio_ibge': getattr(empresa, 'municipio_ibge', None),
        'cnae_servicos': empresa.cnae_servicos,
        'codigo_servico_municipal': empresa.codigo_servico_municipal,
        'aliquota_iss': empresa.aliquota_iss,
        'codigo_ativacao_sat': empresa.codigo_ativacao_sat,
        'numero_serie_sat': empresa.numero_serie_sat,
        'tipo_equipamento_sat': tipo_equipamento_value,
        'logo_url': getattr(empresa, 'logo_url', None),
        'nfce_habilitado': getattr(empresa, 'nfce_habilitado', None),
        'nfce_csc_id': getattr(empresa, 'nfce_csc_id', None),
        'nfce_csc_token_configurado': bool((getattr(empresa, 'nfce_csc_token', None) or '').strip()),
        'ativo': empresa.ativo,
        'regime_tributario': getattr(empresa, 'regime_tributario', None),
        'aliquotas_uf': _parse_aliquotas_uf(getattr(empresa, 'aliquotas_uf', None)),
        'modo_recebimento': getattr(empresa, 'modo_recebimento', None),
        'gateway_plataforma': getattr(empresa, 'gateway_plataforma', None) or 'mercadopago',
        'taxa_plataforma_percentual': getattr(empresa, 'taxa_plataforma_percentual', None),
        'taxa_plataforma_valor_fixo': getattr(empresa, 'taxa_plataforma_valor_fixo', None),
        'created_at': empresa.created_at,
        'updated_at': empresa.updated_at
    }

@router.post("", response_model=EmpresaResponse, status_code=status.HTTP_201_CREATED)
async def criar_empresa(
    empresa_data: EmpresaCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("fiscal.empresa.criar")),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Cria uma nova empresa com dados fiscais. Empresa fiscal pertence obrigatoriamente ao cliente (cliente direto)."""
    try:
        if not _scope_allows_cliente_id(scope, empresa_data.cliente_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cliente não permitido para seu escopo. A empresa fiscal deve pertencer a um cliente que você gerencia."
            )
        # Verificar se já existe empresa com o mesmo CNPJ
        empresa_existente = db.query(Empresa).filter(Empresa.cnpj == empresa_data.cnpj).first()
        if empresa_existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe uma empresa cadastrada com este CNPJ"
            )
        
        # Processar certificado e logo; remover blobs do dict antes de criar o modelo
        empresa_dict = empresa_data.model_dump(exclude_unset=True)
        logo_blob = empresa_dict.pop("logo_emissor_blob", None)
        nfce_hab = empresa_dict.get("nfce_habilitado")
        if nfce_hab is True or (isinstance(nfce_hab, str) and str(nfce_hab).lower() in ("true", "1", "yes")):
            if not (empresa_dict.get("nfce_csc_id") or "").strip():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID CSC obrigatório para NFC-e habilitado.")
            if not (empresa_dict.get("nfce_csc_token") or "").strip():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token CSC obrigatório para NFC-e habilitado.")
        if 'certificado_a1_blob' in empresa_dict and empresa_dict['certificado_a1_blob']:
            try:
                # Converter base64 para bytes
                certificado_bytes = base64.b64decode(empresa_dict['certificado_a1_blob'])
                empresa_dict['certificado_a1_blob'] = certificado_bytes
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Erro ao processar certificado: {str(e)}"
                )
        if 'senha_certificado' in empresa_dict and empresa_dict.get('senha_certificado'):
            from app.services.payments.credentials import encrypt_cert_password
            empresa_dict['senha_certificado'] = encrypt_cert_password(empresa_dict['senha_certificado']) or empresa_dict['senha_certificado']
        if 'nfce_csc_token' in empresa_dict and empresa_dict.get('nfce_csc_token'):
            from app.services.payments.credentials import encrypt_cert_password
            empresa_dict['nfce_csc_token'] = encrypt_cert_password(empresa_dict['nfce_csc_token']) or empresa_dict['nfce_csc_token']
        if 'nfce_habilitado' in empresa_dict:
            v = empresa_dict['nfce_habilitado']
            empresa_dict['nfce_habilitado'] = v is True or (isinstance(v, str) and str(v).lower() in ("true", "1", "yes"))

        # Converter enums para valores primitivos
        from ...models.empresa import AmbienteEnum, TipoEquipamentoEnum
        
        if 'crt' in empresa_dict and empresa_dict['crt'] is not None:
            # Se for enum, pegar o valor inteiro
            if hasattr(empresa_dict['crt'], 'value'):
                empresa_dict['crt'] = empresa_dict['crt'].value
            elif isinstance(empresa_dict['crt'], int):
                empresa_dict['crt'] = empresa_dict['crt']
            else:
                empresa_dict['crt'] = int(empresa_dict['crt'])
        
        if 'ambiente' in empresa_dict and empresa_dict['ambiente'] is not None:
            # Converter string para enum do SQLAlchemy (objeto enum, não string)
            if isinstance(empresa_dict['ambiente'], str):
                ambiente_str = empresa_dict['ambiente'].lower()
                if ambiente_str == 'homologacao':
                    empresa_dict['ambiente'] = AmbienteEnum.HOMOLOGACAO
                elif ambiente_str == 'producao':
                    empresa_dict['ambiente'] = AmbienteEnum.PRODUCAO
            # Se já for enum do Pydantic, converter para enum do SQLAlchemy
            elif hasattr(empresa_dict['ambiente'], 'value'):
                ambiente_value = empresa_dict['ambiente'].value
                if ambiente_value == 'homologacao':
                    empresa_dict['ambiente'] = AmbienteEnum.HOMOLOGACAO
                elif ambiente_value == 'producao':
                    empresa_dict['ambiente'] = AmbienteEnum.PRODUCAO
        
        if 'tipo_equipamento_sat' in empresa_dict and empresa_dict['tipo_equipamento_sat'] is not None:
            # Converter string para enum do SQLAlchemy (objeto enum, não string)
            if isinstance(empresa_dict['tipo_equipamento_sat'], str):
                tipo_str = empresa_dict['tipo_equipamento_sat'].upper()
                if tipo_str == 'SAT':
                    empresa_dict['tipo_equipamento_sat'] = TipoEquipamentoEnum.SAT
                elif tipo_str == 'MFE':
                    empresa_dict['tipo_equipamento_sat'] = TipoEquipamentoEnum.MFE
            # Se já for enum do Pydantic, converter para enum do SQLAlchemy
            elif hasattr(empresa_dict['tipo_equipamento_sat'], 'value'):
                tipo_value = empresa_dict['tipo_equipamento_sat'].value
                if tipo_value == 'SAT':
                    empresa_dict['tipo_equipamento_sat'] = TipoEquipamentoEnum.SAT
                elif tipo_value == 'MFe':
                    empresa_dict['tipo_equipamento_sat'] = TipoEquipamentoEnum.MFE
        
        if 'aliquotas_uf' in empresa_dict and empresa_dict['aliquotas_uf'] is not None:
            v = empresa_dict['aliquotas_uf']
            empresa_dict['aliquotas_uf'] = json.dumps(v) if isinstance(v, (dict, list)) else v
        
        # Criar nova empresa
        empresa = Empresa(**empresa_dict)
        db.add(empresa)
        db.commit()
        db.refresh(empresa)
        # Se foi enviado logo em base64, salvar arquivo e vincular (subpasta por cliente para isolamento)
        if logo_blob:
            try:
                logo_url = _salvar_logo_emissor(logo_blob, empresa.id, empresa.cliente_id)
                empresa.logo_url = logo_url
                db.commit()
                db.refresh(empresa)
            except ValueError as e:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        
        return EmpresaResponse(**converter_empresa_para_dict(empresa))
        
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Erro ao criar empresa. Verifique se o CNPJ já está cadastrado."
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@router.get("", response_model=List[EmpresaResponse])
async def listar_empresas(
    ativo: Optional[bool] = Query(None, description="Filtrar por empresas ativas/inativas"),
    todas: bool = Query(False, description="Quando true, lista ativas e inativas (ignora ativo)"),
    cliente_id: Optional[int] = Query(None, description="Filtrar por cliente (cliente direto)"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Lista empresas cadastradas. Filtro por escopo: Superadmin vê todas; Administrador/Cliente Administrador só as dos seus clientes. Por padrão retorna apenas ativas (excluídas = soft delete não aparecem)."""
    try:
        from sqlalchemy.orm import joinedload
        query = db.query(Empresa).options(joinedload(Empresa.cliente))
        
        # Padrão: apenas ativas, para que "excluídas" (soft delete) sumam da lista; "todas" mostra ativas+inativas
        if not todas:
            if ativo is None:
                ativo = True
            query = query.filter(Empresa.ativo == ativo)
        if cliente_id is not None:
            query = query.filter(Empresa.cliente_id == cliente_id)
        # Escopo: apenas empresas dos clientes permitidos
        if scope.must_filter_by_cliente() and scope.allowed_ids:
            query = query.filter(Empresa.cliente_id.in_(scope.allowed_ids))
        elif scope.must_filter_by_cliente() and not scope.allowed_ids:
            query = query.filter(Empresa.id == -1)  # lista vazia
        
        empresas = query.order_by(Empresa.razao_social).all()
        
        # Converter enums do SQLAlchemy para valores antes de serializar
        empresas_response = []
        for emp in empresas:
            try:
                emp_dict = converter_empresa_para_dict(emp)
                empresas_response.append(EmpresaResponse(**emp_dict))
            except Exception as e:
                # Log detalhado do erro
                import logging
                import traceback
                logger = logging.getLogger(__name__)
                logger.error(f"Erro ao converter empresa {emp.id}: {str(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                logger.error(f"Tipo de ambiente: {type(emp.ambiente)}, Valor: {emp.ambiente}")
                logger.error(f"Tipo de tipo_equipamento_sat: {type(emp.tipo_equipamento_sat)}, Valor: {emp.tipo_equipamento_sat}")
                
                # Tentar criar resposta com tratamento especial
                try:
                    emp_dict = converter_empresa_para_dict(emp)
                    # Se ainda houver erro, criar dict manualmente
                    if 'ambiente' in emp_dict:
                        # Se ambiente não for enum válido, tentar converter
                        if not isinstance(emp_dict['ambiente'], (type(None), str)):
                            try:
                                from ...schemas.empresa import AmbienteEnum
                                if hasattr(emp_dict['ambiente'], 'value'):
                                    str_val = emp_dict['ambiente'].value
                                else:
                                    str_val = str(emp_dict['ambiente']).lower()
                                if str_val == 'homologacao':
                                    emp_dict['ambiente'] = AmbienteEnum.HOMOLOGACAO
                                elif str_val == 'producao':
                                    emp_dict['ambiente'] = AmbienteEnum.PRODUCAO
                                else:
                                    emp_dict['ambiente'] = None
                            except:
                                emp_dict['ambiente'] = None
                    
                    empresas_response.append(EmpresaResponse(**emp_dict))
                except Exception as e2:
                    logger.error(f"Erro ao serializar empresa {emp.id} (segunda tentativa): {str(e2)}")
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Erro ao serializar empresa {emp.id}: {str(e2)}"
                    )
        
        return empresas_response
        
    except HTTPException:
        raise
    except Exception as e:
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        logger.error(f"Erro ao listar empresas: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@router.get("/{empresa_id}", response_model=EmpresaResponse)
async def obter_empresa(
    empresa_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Obtém uma empresa específica por ID (respeitando escopo por cliente)."""
    try:
        from sqlalchemy.orm import joinedload
        empresa = db.query(Empresa).options(joinedload(Empresa.cliente)).filter(Empresa.id == empresa_id).first()
        
        if not empresa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Empresa não encontrada"
            )
        if not _scope_allows_empresa(scope, empresa):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Empresa fora do seu escopo.")
        
        return EmpresaResponse(**converter_empresa_para_dict(empresa))
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@router.put("/{empresa_id}", response_model=EmpresaResponse)
async def atualizar_empresa(
    empresa_id: int,
    empresa_data: EmpresaUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Atualiza uma empresa existente (respeitando escopo por cliente)."""
    try:
        from sqlalchemy.orm import joinedload
        empresa = db.query(Empresa).options(joinedload(Empresa.cliente)).filter(Empresa.id == empresa_id).first()
        
        if not empresa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Empresa não encontrada"
            )
        if not _scope_allows_empresa(scope, empresa):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Empresa fora do seu escopo.")
        
        # Atualizar apenas campos fornecidos
        update_data = empresa_data.model_dump(exclude_unset=True)

        _CAMPOS_SUPERADMIN = {"modo_recebimento", "taxa_plataforma_percentual", "taxa_plataforma_valor_fixo", "gateway_plataforma"}
        _has_superadmin_fields = any(k in update_data for k in _CAMPOS_SUPERADMIN)
        _is_superadmin = current_user.role and getattr(current_user.role, "nome", None) == "Superadministrador"
        if _has_superadmin_fields and not _is_superadmin:
            for campo in _CAMPOS_SUPERADMIN:
                update_data.pop(campo, None)
        if "modo_recebimento" in update_data:
            if update_data["modo_recebimento"] not in ("direto", "plataforma"):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="modo_recebimento deve ser 'direto' ou 'plataforma'.")
        if "gateway_plataforma" in update_data and update_data["gateway_plataforma"] is not None:
            gw = str(update_data["gateway_plataforma"]).strip().lower()
            if gw not in ("mercadopago", "pagbank", "pagarme"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="gateway_plataforma deve ser mercadopago, pagbank ou pagarme.",
                )
            update_data["gateway_plataforma"] = gw

        logo_blob = update_data.pop("logo_emissor_blob", None)
        if logo_blob:
            try:
                logo_url = _salvar_logo_emissor(logo_blob, empresa_id, empresa.cliente_id)
                update_data["logo_url"] = logo_url
            except ValueError as e:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        
        if 'cliente_id' in update_data and update_data['cliente_id'] is not None:
            if not _scope_allows_cliente_id(scope, update_data['cliente_id']):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cliente não permitido para seu escopo.")
        
        # Processar certificado se fornecido
        if 'certificado_a1_blob' in update_data and update_data['certificado_a1_blob']:
            try:
                # Converter base64 para bytes
                certificado_bytes = base64.b64decode(update_data['certificado_a1_blob'])
                update_data['certificado_a1_blob'] = certificado_bytes
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Erro ao processar certificado: {str(e)}"
                )
        
        # Converter enums para valores primitivos
        from ...models.empresa import AmbienteEnum, TipoEquipamentoEnum
        
        if 'crt' in update_data and update_data['crt'] is not None:
            # Se for enum, pegar o valor inteiro
            if hasattr(update_data['crt'], 'value'):
                update_data['crt'] = update_data['crt'].value
            elif isinstance(update_data['crt'], int):
                update_data['crt'] = update_data['crt']
            else:
                update_data['crt'] = int(update_data['crt'])
        
        if 'ambiente' in update_data and update_data['ambiente'] is not None:
            # Converter string para enum do SQLAlchemy (objeto enum, não string)
            if isinstance(update_data['ambiente'], str):
                ambiente_str = update_data['ambiente'].lower()
                if ambiente_str == 'homologacao':
                    update_data['ambiente'] = AmbienteEnum.HOMOLOGACAO
                elif ambiente_str == 'producao':
                    update_data['ambiente'] = AmbienteEnum.PRODUCAO
            # Se já for enum do Pydantic, converter para enum do SQLAlchemy
            elif hasattr(update_data['ambiente'], 'value'):
                ambiente_value = update_data['ambiente'].value
                if ambiente_value == 'homologacao':
                    update_data['ambiente'] = AmbienteEnum.HOMOLOGACAO
                elif ambiente_value == 'producao':
                    update_data['ambiente'] = AmbienteEnum.PRODUCAO
        
        if 'tipo_equipamento_sat' in update_data and update_data['tipo_equipamento_sat'] is not None:
            # Converter string para enum do SQLAlchemy (objeto enum, não string)
            if isinstance(update_data['tipo_equipamento_sat'], str):
                tipo_str = update_data['tipo_equipamento_sat'].upper()
                if tipo_str == 'SAT':
                    update_data['tipo_equipamento_sat'] = TipoEquipamentoEnum.SAT
                elif tipo_str == 'MFE':
                    update_data['tipo_equipamento_sat'] = TipoEquipamentoEnum.MFE
            # Se já for enum do Pydantic, converter para enum do SQLAlchemy
            elif hasattr(update_data['tipo_equipamento_sat'], 'value'):
                tipo_value = update_data['tipo_equipamento_sat'].value
                if tipo_value == 'SAT':
                    update_data['tipo_equipamento_sat'] = TipoEquipamentoEnum.SAT
                elif tipo_value == 'MFe':
                    update_data['tipo_equipamento_sat'] = TipoEquipamentoEnum.MFE
        
        if 'aliquotas_uf' in update_data and update_data['aliquotas_uf'] is not None:
            v = update_data['aliquotas_uf']
            update_data['aliquotas_uf'] = json.dumps(v) if isinstance(v, (dict, list)) else v

        nfce_hab_new = update_data.get("nfce_habilitado") if "nfce_habilitado" in update_data else getattr(empresa, "nfce_habilitado", None)
        nfce_csc_id_new = update_data.get("nfce_csc_id") if "nfce_csc_id" in update_data else getattr(empresa, "nfce_csc_id", None)
        nfce_csc_token_new = update_data.get("nfce_csc_token") if "nfce_csc_token" in update_data else getattr(empresa, "nfce_csc_token", None)
        nfce_hab_final = nfce_hab_new is True or (isinstance(nfce_hab_new, str) and str(nfce_hab_new).lower() in ("true", "1", "yes"))
        if nfce_hab_final:
            if not (nfce_csc_id_new or "").strip() if isinstance(nfce_csc_id_new, str) else not nfce_csc_id_new:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID CSC obrigatório para NFC-e habilitado.")
            if not (nfce_csc_token_new or "").strip() if isinstance(nfce_csc_token_new, str) else not nfce_csc_token_new:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token CSC obrigatório para NFC-e habilitado.")
        # Não sobrescrever token CSC com valor vazio na edição (token não é retornado na API por segurança)
        if "nfce_csc_token" in update_data and not (update_data.get("nfce_csc_token") or "").strip():
            update_data.pop("nfce_csc_token", None)
        if "nfce_csc_token" in update_data and update_data.get("nfce_csc_token"):
            from app.services.payments.credentials import encrypt_cert_password
            update_data["nfce_csc_token"] = encrypt_cert_password(update_data["nfce_csc_token"]) or update_data["nfce_csc_token"]
        if "nfce_habilitado" in update_data:
            v = update_data["nfce_habilitado"]
            update_data["nfce_habilitado"] = v is True or (isinstance(v, str) and str(v).lower() in ("true", "1", "yes"))

        # Garantir que municipio_ibge seja persistido como inteiro (obrigatório para NF-e)
        if 'municipio_ibge' in update_data:
            raw = update_data['municipio_ibge']
            if raw is None or raw == '' or (isinstance(raw, (int, float)) and int(raw) <= 0):
                update_data['municipio_ibge'] = None
            else:
                try:
                    update_data['municipio_ibge'] = int(raw)
                except (TypeError, ValueError):
                    update_data['municipio_ibge'] = None

        if 'senha_certificado' in update_data and update_data.get('senha_certificado'):
            from app.services.payments.credentials import encrypt_cert_password
            update_data['senha_certificado'] = encrypt_cert_password(update_data['senha_certificado']) or update_data['senha_certificado']

        for field, value in update_data.items():
            setattr(empresa, field, value)
        
        db.commit()
        db.refresh(empresa)
        
        return EmpresaResponse(**converter_empresa_para_dict(empresa))
        
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Erro ao atualizar empresa. Verifique se o CNPJ já está cadastrado."
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@router.post("/{empresa_id}/certificado", response_model=EmpresaResponse)
async def upload_certificado_empresa(
    empresa_id: int,
    arquivo: UploadFile = File(..., description="Arquivo .pfx ou .p12 do certificado A1"),
    senha: str = Form(..., min_length=1, description="Senha do certificado"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Envia certificado A1 (PFX/P12) e senha para a empresa. Escopo CA: apenas empresas do cliente. Atualiza certificado_validade."""
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada")
    if not _scope_allows_empresa(scope, empresa):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Empresa fora do seu escopo")
    if not arquivo.filename or not (arquivo.filename.lower().endswith(".pfx") or arquivo.filename.lower().endswith(".p12")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Envie um arquivo .pfx ou .p12")
    content = await arquivo.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivo vazio")
    try:
        from cryptography.hazmat.primitives.serialization.pkcs12 import load_key_and_certificates
    except ImportError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Módulo de certificado indisponível")
    try:
        key, cert, _ = load_key_and_certificates(content, senha.encode("utf-8"))
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Senha inválida ou arquivo corrompido")
    if not cert:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Certificado inválido")
    from datetime import date
    validade = getattr(cert, "not_valid_after_utc", None) or getattr(cert, "not_valid_after", None)
    if validade is None:
        validade_date = None
    elif hasattr(validade, "date"):
        validade_date = validade.date()
    else:
        validade_date = date(validade.year, validade.month, validade.day)
    from app.services.payments.credentials import encrypt_cert_password
    empresa.certificado_a1_blob = content
    empresa.senha_certificado = encrypt_cert_password(senha) or senha  # criptografado em repouso se FISCAL_CERT_* definido
    empresa.certificado_validade = validade_date
    empresa.certificado_a1_path = None  # prioridade ao blob
    db.commit()
    db.refresh(empresa)
    return converter_empresa_para_dict(empresa)


@router.delete("/{empresa_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_empresa(
    empresa_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("fiscal.empresa.excluir")),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Deleta uma empresa (soft delete - apenas desativa). Respeita escopo por cliente. Apenas Superadministrador e Administrador (Cliente Administrador e abaixo não têm permissão)."""
    try:
        empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
        
        if not empresa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Empresa não encontrada"
            )
        if not _scope_allows_empresa(scope, empresa):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Empresa fora do seu escopo.")
        
        # Verificar se há documentos fiscais vinculados
        if empresa.notas_fiscais or empresa.notas_servico or empresa.cupons_fiscais or empresa.mdfes:
            # Soft delete - apenas desativar
            empresa.ativo = False
            db.commit()
        else:
            # Hard delete - remover completamente
            db.delete(empresa)
            db.commit()
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@router.get("/cnpj/{cnpj}", response_model=EmpresaResponse)
async def buscar_empresa_por_cnpj(
    cnpj: str,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Busca empresa por CNPJ (respeitando escopo por cliente)."""
    try:
        from sqlalchemy.orm import joinedload
        empresa = db.query(Empresa).options(joinedload(Empresa.cliente)).filter(Empresa.cnpj == cnpj).first()
        
        if not empresa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Empresa não encontrada"
            )
        if not _scope_allows_empresa(scope, empresa):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Empresa fora do seu escopo.")
        
        return EmpresaResponse(**converter_empresa_para_dict(empresa))
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

