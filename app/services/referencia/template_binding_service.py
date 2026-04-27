# -*- coding: utf-8 -*-
"""
REFERÊNCIA DO CERTILOG - Serviço de Resolução de Bindings para Templates
Este arquivo é uma cópia de referência do sistema Certilog.
Não deve ser usado diretamente no PDV Ibix.
Adaptar conforme necessário para implementação futura.

Serviço de Resolução de Bindings para Templates
Resolve bindings complexos como os.number, user.name, company.logo_url, etc.
"""

import logging
from typing import Any, Dict, Optional

from app.models.comum import ComumUsuario
from app.models.manutencao import ManutencaoOrdemServico
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class TemplateBindingResolver:
    """Resolver de bindings para templates de OS"""
    
    @staticmethod
    def obter_contexto_completo(os_id: Optional[int], db: Session, current_user: Optional[ComumUsuario] = None) -> Dict[str, Any]:
        """
        Obter contexto completo para resolução de bindings
        
        Args:
            os_id: ID da OS (opcional)
            db: Sessão do banco de dados
            current_user: Usuário atual (opcional)
        
        Returns:
            Dicionário com contexto completo (os, user, status, refs)
        """
        contexto = {
            "os": None,
            "user": None,
            "status": None,
            "refs": {
                "company": None,
                "unit": None,
                "program": None,
                "asset": None
            }
        }
        
        # Carregar OS se fornecido (com relacionamentos)
        os_obj = None
        if os_id:
            try:
                from sqlalchemy.orm import joinedload
                os_obj = db.query(ManutencaoOrdemServico).options(
                    joinedload(ManutencaoOrdemServico.template),
                    joinedload(ManutencaoOrdemServico.template_versao),
                    joinedload(ManutencaoOrdemServico.solicitante),
                    joinedload(ManutencaoOrdemServico.ativo_rel),
                    joinedload(ManutencaoOrdemServico.setor),
                    joinedload(ManutencaoOrdemServico.unidade),
                    joinedload(ManutencaoOrdemServico.tenant)
                ).filter(
                    ManutencaoOrdemServico.id == os_id
                ).first()
                
                if os_obj:
                    # Dados da OS
                    contexto["os"] = {
                        "id": os_obj.id,
                        "number": os_obj.numero_os,
                        "status": os_obj.status,
                        "type": os_obj.tipo_manutencao,
                        "created_at": os_obj.data_solicitacao.isoformat() if os_obj.data_solicitacao else None,
                        "tipo_manutencao": os_obj.tipo_manutencao,
                        "prioridade": os_obj.prioridade,
                        "data_solicitacao": os_obj.data_solicitacao.isoformat() if os_obj.data_solicitacao else None,
                        "data_inicio": os_obj.data_inicio.isoformat() if os_obj.data_inicio else None,
                        "data_fim": os_obj.data_fim.isoformat() if os_obj.data_fim else None,
                        "descricao_problema": os_obj.descricao_problema,
                    }
                    
                    # Status atual
                    contexto["status"] = os_obj.status
                    
                    # Carregar tenant (company)
                    if os_obj.tenant:
                        contexto["refs"]["company"] = {
                            "id": os_obj.tenant.id,
                            "name": os_obj.tenant.nome,
                            "razao_social": os_obj.tenant.razao_social,
                            "cnpj": os_obj.tenant.cnpj,
                            "email": os_obj.tenant.email,
                            "telefone": os_obj.tenant.telefone,
                            "endereco": os_obj.tenant.endereco,
                            "cidade": os_obj.tenant.cidade,
                            "estado": os_obj.tenant.estado,
                            "cep": os_obj.tenant.cep,
                            "logo_url": None,  # TODO: Adicionar campo logo_url no tenant se necessário
                        }
                    
                    # Carregar unidade (unit)
                    if os_obj.unidade:
                        # Montar endereço completo
                        endereco_parts = []
                        if os_obj.unidade.endereco:
                            endereco_parts.append(os_obj.unidade.endereco)
                        if os_obj.unidade.cidade:
                            endereco_parts.append(os_obj.unidade.cidade)
                        if os_obj.unidade.estado:
                            endereco_parts.append(os_obj.unidade.estado)
                        if os_obj.unidade.cep:
                            endereco_parts.append(f"CEP {os_obj.unidade.cep}")
                        
                        address_full = " - ".join(endereco_parts) if endereco_parts else None
                        
                        contexto["refs"]["unit"] = {
                            "id": os_obj.unidade.id,
                            "name": os_obj.unidade.nome,
                            "codigo": os_obj.unidade.codigo,
                            "address_full": address_full,
                            "endereco": os_obj.unidade.endereco,
                            "cidade": os_obj.unidade.cidade,
                            "estado": os_obj.unidade.estado,
                            "cep": os_obj.unidade.cep,
                            "telefone": os_obj.unidade.telefone,
                            "email": os_obj.unidade.email,
                        }
                        
                        # Se não houver address_full, construir a partir dos campos disponíveis
                        if not address_full and os_obj.unidade.nome:
                            parts = [os_obj.unidade.nome]
                            if os_obj.unidade.cidade:
                                parts.append(os_obj.unidade.cidade)
                            if os_obj.unidade.estado:
                                parts.append(os_obj.unidade.estado)
                            contexto["refs"]["unit"]["address_full"] = " - ".join(parts) if len(parts) > 1 else os_obj.unidade.nome
                    
                    # Carregar ativo (asset)
                    if os_obj.ativo_rel:
                        contexto["refs"]["asset"] = {
                            "id": os_obj.ativo_rel.id,
                            "tag": os_obj.ativo_rel.codigo or f"ATIVO-{os_obj.ativo_rel.id}",
                            "name": os_obj.ativo_rel.nome,
                            "descricao": os_obj.ativo_rel.descricao,
                        }
                    
                    # Carregar setor
                    if os_obj.setor:
                        contexto["refs"]["setor"] = {
                            "id": os_obj.setor.id,
                            "codigo": os_obj.setor.codigo,
                            "name": os_obj.setor.nome,
                            "descricao": os_obj.setor.descricao,
                        }
                    
                    # Carregar programa/plano do template (se existir)
                    # Base documental PCM (preferencial): usar snapshot do documento/formulário
                    # Fallback (legado): usar template/versionamento do Form Builder.
                    if getattr(os_obj, "documento", None):
                        doc = os_obj.documento
                        ver = getattr(os_obj, "documento_versao", None)
                        contexto["refs"]["program"] = {
                            "id": doc.id,
                            "name": doc.titulo or doc.chave,
                            "code": doc.codigo_documento,
                            "regulatory_org": None,
                            "revision_number": ver.numero_revisao if ver else None,
                            "revision_date": (
                                ver.data_revisao_documento.isoformat()
                                if ver and ver.data_revisao_documento
                                else (ver.vigencia_inicio.isoformat() if ver and ver.vigencia_inicio else None)
                            ),
                            "version": ver.versao_documento if ver else None,
                        }
                    elif os_obj.template:
                        contexto["refs"]["program"] = {
                            "id": os_obj.template.id,
                            "name": os_obj.template.nome,
                            "code": None,
                            "regulatory_org": None,
                            "revision_number": None,
                            "revision_date": None,
                        }
                        if os_obj.template_versao:
                            contexto["refs"]["program"]["revision_number"] = os_obj.template_versao.versao
                            contexto["refs"]["program"]["revision_date"] = (
                                os_obj.template_versao.data_inicio_vigencia.isoformat()
                                if os_obj.template_versao.data_inicio_vigencia
                                else None
                            )
                        
                        # Adicionar informações do template no contexto
                        contexto["template"] = {
                            "nome": os_obj.template.nome,
                            "criado_em": os_obj.template.criado_em.isoformat() if os_obj.template.criado_em else None,
                            "atualizado_em": os_obj.template.atualizado_em.isoformat() if os_obj.template.atualizado_em else None,
                            "versao": os_obj.template_versao.versao if os_obj.template_versao else None
                        }
                        contexto["templateNome"] = os_obj.template.nome
            except Exception as e:
                logger.error(f"Erro ao carregar contexto da OS {os_id}: {e}", exc_info=True)
        
        # Carregar usuário atual
        os_obj = None
        if os_id:
            try:
                os_obj = db.query(ManutencaoOrdemServico).filter(
                    ManutencaoOrdemServico.id == os_id
                ).first()
            except Exception as e:
                logger.error(f"Erro ao carregar OS {os_id}: {e}", exc_info=True)
        
        # Carregar solicitante da OS (prioridade sobre current_user para contexto da OS)
        if os_obj and os_obj.solicitante:
            # Obter role do solicitante
            role = None
            try:
                if hasattr(os_obj.solicitante, 'niveis') and os_obj.solicitante.niveis:
                    niveis_ativos = [n for n in os_obj.solicitante.niveis if hasattr(n, 'ativo') and n.ativo]
                    if niveis_ativos:
                        role = niveis_ativos[0].nivel.nome if niveis_ativos[0].nivel else None
            except Exception as e:
                logger.warning(f"Erro ao obter role do solicitante: {e}")
            
            contexto["user"] = {
                "id": os_obj.solicitante.id,
                "name": os_obj.solicitante.nome,
                "email": os_obj.solicitante.email,
                "username": os_obj.solicitante.username,
                "role": role,
                "papel_organizacional": os_obj.solicitante.papel_organizacional,
                "unidade_id": os_obj.solicitante.unidade_id,
                "telefone": getattr(os_obj.solicitante, 'telefone', None),
            }
        elif current_user:
            # Usar current_user como fallback
            # Obter role do usuário (primeiro nível ativo)
            role = None
            try:
                if hasattr(current_user, 'niveis') and current_user.niveis:
                    niveis_ativos = [n for n in current_user.niveis if hasattr(n, 'ativo') and n.ativo]
                    if niveis_ativos:
                        role = niveis_ativos[0].nivel.nome if niveis_ativos[0].nivel else None
            except Exception as e:
                logger.warning(f"Erro ao obter role do usuário: {e}")
            
            contexto["user"] = {
                "id": current_user.id,
                "name": current_user.nome,
                "email": current_user.email,
                "username": current_user.username,
                "role": role,
                "papel_organizacional": current_user.papel_organizacional,
                "unidade_id": current_user.unidade_id,
                "telefone": getattr(current_user, 'telefone', None),
            }
        
        return contexto
    
    @staticmethod
    def resolver_binding(binding_source: str, contexto: Dict[str, Any]) -> Any:
        """
        Resolver um binding específico
        
        Args:
            binding_source: Fonte do binding (ex: "os.number", "user.name")
            contexto: Contexto completo
        
        Returns:
            Valor resolvido ou None
        """
        if not binding_source:
            return None
        
        try:
            parts = binding_source.split('.')
            
            if len(parts) < 2:
                return None
            
            objeto = parts[0]
            propriedade = '.'.join(parts[1:])
            
            # Resolver bindings especiais
            if objeto == 'render':
                if propriedade == 'page_counter':
                    # TODO: Implementar contador de páginas quando necessário
                    return '1 de 1'
                return None
            
            # Resolver bindings de objetos principais
            if objeto == 'os':
                if not contexto.get('os'):
                    return None
                return TemplateBindingResolver._obter_valor_aninhado(contexto['os'], propriedade)
            
            elif objeto == 'user':
                if not contexto.get('user'):
                    return None
                return TemplateBindingResolver._obter_valor_aninhado(contexto['user'], propriedade)
            
            elif objeto == 'company':
                if not contexto.get('refs', {}).get('company'):
                    return None
                return TemplateBindingResolver._obter_valor_aninhado(contexto['refs']['company'], propriedade)
            
            elif objeto == 'unit':
                if not contexto.get('refs', {}).get('unit'):
                    return None
                return TemplateBindingResolver._obter_valor_aninhado(contexto['refs']['unit'], propriedade)
            
            elif objeto == 'program':
                if not contexto.get('refs', {}).get('program'):
                    return None
                return TemplateBindingResolver._obter_valor_aninhado(contexto['refs']['program'], propriedade)
            
            elif objeto == 'asset':
                if not contexto.get('refs', {}).get('asset'):
                    return None
                return TemplateBindingResolver._obter_valor_aninhado(contexto['refs']['asset'], propriedade)
            
            elif objeto == 'status':
                return contexto.get('status')
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao resolver binding {binding_source}: {e}", exc_info=True)
            return None
    
    @staticmethod
    def _obter_valor_aninhado(obj: Dict[str, Any], path: str) -> Any:
        """Obter valor aninhado de um dicionário usando path (ex: 'address_full' ou 'revision.number')"""
        if not obj or not path:
            return None
        
        try:
            # Se path é simples (sem pontos), retornar diretamente
            if '.' not in path:
                return obj.get(path)
            
            # Se path tem pontos, navegar recursivamente
            parts = path.split('.')
            valor = obj
            for part in parts:
                if isinstance(valor, dict):
                    valor = valor.get(part)
                    if valor is None:
                        return None
                else:
                    return None
            
            return valor
        except Exception as e:
            logger.error(f"Erro ao obter valor aninhado {path}: {e}", exc_info=True)
            return None
    
    @staticmethod
    def resolver_bindings_campo(campo: Dict[str, Any], contexto: Dict[str, Any]) -> Any:
        """
        Resolver binding de um campo específico
        
        Args:
            campo: Dicionário do campo do schema
            contexto: Contexto completo
        
        Returns:
            Valor resolvido ou None
        """
        if not campo.get('data') or not campo['data'].get('binding'):
            return None
        
        binding = campo['data']['binding']
        if isinstance(binding, dict) and 'source' in binding:
            return TemplateBindingResolver.resolver_binding(binding['source'], contexto)
        elif isinstance(binding, str):
            return TemplateBindingResolver.resolver_binding(binding, contexto)
        
        return None
    
    @staticmethod
    def resolver_bindings_schema(schema: Dict[str, Any], contexto: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processar todos os campos do schema e resolver bindings
        
        Args:
            schema: Schema do template
            contexto: Contexto completo
        
        Returns:
            Schema com valores resolvidos (não modifica o original)
        """
        if not schema:
            return schema
        
        schema_resolvido = schema.copy()
        
        # Processar campos
        if 'campos' in schema_resolvido:
            campos_resolvidos = []
            for campo in schema_resolvido['campos']:
                campo_resolvido = campo.copy()
                
                # Resolver binding se campo for computed ou readonly
                data = campo_resolvido.get('data', {})
                mode = data.get('mode', 'input')
                
                if mode in ['computed', 'readonly']:
                    valor_resolvido = TemplateBindingResolver.resolver_bindings_campo(campo, contexto)
                    if valor_resolvido is not None:
                        # Adicionar valor resolvido ao campo (para uso no frontend)
                        if 'valor_resolvido' not in campo_resolvido:
                            campo_resolvido['valor_resolvido'] = valor_resolvido
                
                campos_resolvidos.append(campo_resolvido)
            
            schema_resolvido['campos'] = campos_resolvidos
        
        return schema_resolvido
