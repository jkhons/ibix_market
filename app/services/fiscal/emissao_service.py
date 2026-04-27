# PDV Ibix - Serviço de emissão fiscal (validação, envio, evento)
import json
import re
from datetime import datetime, timezone
from pathlib import Path as PathLib
from typing import Any, Dict, Optional

# Any usado em _destinatario_from_pedido_marketplace (PedidoMarketplace ou objeto com atributos)
from sqlalchemy.orm import Session, joinedload

from app.core.config import FISCAL_UPLOADS_DIR, PROJECT_ROOT
from app.core.redis_cache import get_regras_fiscais_empresa_cached
from app.models.cliente import Cliente
from app.models.configuracao import Configuracao
from app.models.empresa import Empresa
from app.models.fiscal_evento import DocumentoTipoFiscalEnum, EventoFiscalEnum, FiscalEvento
from app.models.nfe_tentativa_envio import NFeTentativaEnvio
from app.models.nota_fiscal import NotaFiscal, NotaFiscalItem, StatusNotaEnum
from app.models.nota_servico import NotaServico, StatusNotaServicoEnum
from app.models.produto_cliente import ProdutoCliente
from app.models.regra_fiscal_icms import RegraFiscalIcms, TipoOperacaoFiscalEnum
from app.services.pedido_service import _proximo_numero_nf

from .cfop_resolver import (
    ContextoCFOP,
    DestinoGeograficoCFOP,
    ErroCFOPResolver,
    NaturezaOperacaoCFOP,
    OrigemMercadoriaComercial,
    TipoMovimentoCFOP,
    resolver_cfop,
)
from .motor_tributario_icms import (
    MOTOR_VERSAO,
    ContextoFiscalItem,
    ErroMotorTributario,
    resolver_regra_icms,
)
from .provedor_base import IProvedorFiscal, ResultadoEnvioFiscal
from .provedor_local import ProvedorFiscalLocal
from .provedor_stub import ProvedorFiscalStub
from .sefaz_client import get_url_autorizacao

CHAVE_FISCAL_PROVEDOR = "fiscal.provedor"


def _validar_cpf(cpf: Optional[str]) -> Optional[str]:
    """Valida CPF (11 dígitos e dígitos verificadores). Retorna None se OK, mensagem de erro se inválido."""
    num = re.sub(r"\D", "", cpf or "")
    if len(num) != 11 or not num.isdigit():
        return "CPF deve ter 11 dígitos"
    if num == num[0] * 11:
        return "CPF inválido"
    # Primeiro dígito verificador
    pesos1 = list(range(10, 1, -1))
    soma = sum(int(num[i]) * pesos1[i] for i in range(9))
    d1 = (soma * 10 % 11) % 10
    if d1 != int(num[9]):
        return "CPF inválido (dígito verificador)"
    # Segundo dígito verificador
    pesos2 = list(range(11, 1, -1))
    soma2 = sum(int(num[i]) * pesos2[i] for i in range(10))
    d2 = (soma2 * 10 % 11) % 10
    if d2 != int(num[10]):
        return "CPF inválido (dígito verificador)"
    return None


def _validar_cnpj(cnpj: Optional[str]) -> Optional[str]:
    """Valida CNPJ (14 dígitos e dígitos verificadores). Retorna None se OK, mensagem de erro se inválido."""
    num = re.sub(r"\D", "", cnpj or "")
    if len(num) != 14 or not num.isdigit():
        return "CNPJ deve ter 14 dígitos"
    if num == num[0] * 14:
        return "CNPJ inválido"
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(num[i]) * pesos1[i] for i in range(12))
    d1 = (soma * 10 % 11) % 10
    if d1 != int(num[12]):
        return "CNPJ inválido (dígito verificador)"
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma2 = sum(int(num[i]) * pesos2[i] for i in range(13))
    d2 = (soma2 * 10 % 11) % 10
    if d2 != int(num[13]):
        return "CNPJ inválido (dígito verificador)"
    return None


def _get_config_val(db: Session, chave: str) -> Optional[str]:
    """Lê valor de configuração global por chave."""
    c = db.query(Configuracao).filter(Configuracao.chave == chave).first()
    return (c.valor or "").strip() or None if c else None


def get_provedor_fiscal(db: Session, empresa: Optional[Empresa] = None) -> IProvedorFiscal:
    """Retorna o provedor fiscal: ProvedorFiscalLocal (envio real SEFAZ) por padrão quando há empresa;
    use stub apenas se empresa.provedor_fiscal == 'stub' (testes)."""
    if empresa:
        pf = (getattr(empresa, "provedor_fiscal", None) or "").strip().lower()
        if pf == "stub":
            return ProvedorFiscalStub()
        # local, vazio ou qualquer outro valor: usar provedor real (Local)
        return ProvedorFiscalLocal(db)
    return ProvedorFiscalStub()


def validar_nota_servico(db: Session, nota: NotaServico) -> list:
    """Valida NFS-e antes do envio. Retorna lista de erros (vazia se OK)."""
    erros = []
    if not nota.cliente_id:
        erros.append("Cliente é obrigatório")
    if not nota.empresa_id:
        erros.append("Empresa é obrigatória")
    if not nota.discriminacao_servicos or not nota.discriminacao_servicos.strip():
        erros.append("Discriminação dos serviços é obrigatória")
    if not nota.itens or len(nota.itens) == 0:
        erros.append("Pelo menos um item é obrigatório")
    if (nota.valor_total is None) or float(nota.valor_total) <= 0:
        erros.append("Valor total deve ser maior que zero")
    return erros


def _empresa_crt_simples(crt: Any) -> bool:
    """CRT 1 ou 2 = Simples Nacional."""
    if crt is None:
        return False
    try:
        return int(crt) in (1, 2)
    except (TypeError, ValueError):
        return False


def _municipio_ibge_preenchido(empresa: Any) -> bool:
    """Retorna True se a empresa tem código IBGE do município válido (int ou string numérica > 0)."""
    val = getattr(empresa, "municipio_ibge", None)
    if val is None:
        return False
    try:
        n = int(val)
        return n > 0
    except (TypeError, ValueError):
        return bool(val and str(val).strip())


def _apenas_digitos_valido(val: Any, campo_nome: str) -> Optional[str]:
    """Valida que o valor contém apenas dígitos (bloqueio: não sanitizar silenciosamente). Retorna None se OK, mensagem de erro se inválido."""
    if val is None or (isinstance(val, str) and not val.strip()):
        return None  # vazio tratado por obrigatoriedade em outro lugar
    s = str(val).strip()
    if not s:
        return None
    if not s.isdigit():
        return f"{campo_nome} deve conter apenas dígitos."
    return None


def _validar_totais_nota(nota: NotaFiscal) -> Optional[str]:
    """Valida consistência dos totais da nota (soma dos itens vs total). Retorna mensagem de erro ou None."""
    itens = nota.itens or []
    if not itens:
        return None
    try:
        soma_itens = sum(float(getattr(i, "valor_total", 0) or 0) for i in itens)
    except (TypeError, ValueError):
        return "Valores dos itens inválidos para conferência de totais."
    total_nota = float(nota.valor_total or 0)
    valor_frete = float(getattr(nota, "valor_frete", 0) or 0)
    valor_seguro = float(getattr(nota, "valor_seguro", 0) or 0)
    valor_desconto = float(getattr(nota, "valor_desconto", 0) or 0)
    valor_outros = float(getattr(nota, "valor_outros", 0) or 0)
    # Total esperado: soma itens - desconto + frete + seguro + outros
    total_esperado = soma_itens - valor_desconto + valor_frete + valor_seguro + valor_outros
    tolerancia = 0.02  # centavos
    if abs(total_nota - total_esperado) > tolerancia:
        return (
            f"Totais inconsistentes: soma dos itens ({soma_itens:.2f}) com frete/seguro/desconto/outros "
            f"não confere com o valor total da nota ({total_nota:.2f}). Corrija os valores."
        )
    return None


def preparar_nota_para_validacao(db: Session, nota: NotaFiscal) -> Optional[str]:
    """
    Pré-processa a nota antes da validação: atribui número/série numéricos se forem
    placeholder (ex.: RASCUNHO-VENDA-X), preenche itens do produto e aplica motor tributário.
    Retorna None se OK, ou mensagem de erro se o motor falhar.
    As alterações são feitas na sessão (db.flush); o caller deve fazer commit se quiser persistir.
    """
    if not nota.empresa_id:
        return "Empresa é obrigatória"
    empresa = db.query(Empresa).filter(Empresa.id == nota.empresa_id).first()
    if not empresa:
        return "Empresa não encontrada"
    # Atribuir número/série numéricos se forem placeholder (ex.: RASCUNHO-VENDA-123)
    if _apenas_digitos_valido(nota.numero, "Número") is not None or _apenas_digitos_valido(nota.serie, "Série") is not None:
        serie_uso = (re.sub(r"\D", "", str(nota.serie or "1")) or "1")[:10] or "1"
        nota.numero = _proximo_numero_nf(db, nota.empresa_id, serie_uso)
        nota.serie = serie_uso
        db.flush()
    _preencher_fiscal_itens_desde_produto_cliente(db, nota)
    err_motor = _aplicar_motor_tributario_itens(db, nota, empresa)
    if err_motor:
        return err_motor
    db.flush()
    return None


def validar_nota_fiscal(db: Session, nota: NotaFiscal) -> list:
    """Valida NF-e/NFC-e antes do envio. Retorna lista de erros (vazia se OK)."""
    erros = []
    empresa = None
    if not nota.empresa_id:
        erros.append("Empresa é obrigatória")
    else:
        empresa = db.query(Empresa).filter(Empresa.id == nota.empresa_id).first()
        if empresa:
            db.refresh(empresa)  # garantir dados atualizados
            if not _municipio_ibge_preenchido(empresa):
                nome = getattr(empresa, "razao_social", None) or getattr(empresa, "nome_fantasia", None) or f"ID {empresa.id}"
                erros.append(
                    f"Empresa \"{nome}\" (ID {empresa.id}) deve ter o código IBGE do município cadastrado. "
                    "Acesse Fiscal > Empresa, edite esta empresa, preencha o campo \"Código IBGE do município (NF-e)\" (7 dígitos) e clique em Salvar."
                )
    if not nota.itens or len(nota.itens) == 0:
        erros.append("Pelo menos um item é obrigatório")
    if (nota.valor_total is None) or float(nota.valor_total) <= 0:
        erros.append("Valor total deve ser maior que zero")
    if not nota.numero or not nota.serie:
        erros.append("Número e série são obrigatórios")
    else:
        msg_serie = _apenas_digitos_valido(nota.serie, "Série")
        if msg_serie:
            erros.append(msg_serie)
        msg_numero = _apenas_digitos_valido(nota.numero, "Número da nota")
        if msg_numero:
            erros.append(msg_numero)
    # Modelo: 55 = NF-e, 65 = NFC-e (conforme tipo da nota)
    modelo = str(getattr(nota, "modelo", "") or "").strip()
    tipo_val = getattr(nota.tipo, "value", None) or str(getattr(nota, "tipo", ""))
    if tipo_val and str(tipo_val) in ("NFe", "NF-e"):
        if modelo != "55":
            erros.append("Modelo da nota deve ser 55 para NF-e.")
    elif tipo_val and str(tipo_val) in ("NFCe", "NFC-e"):
        if modelo != "65":
            erros.append("Modelo da nota deve ser 65 para NFC-e.")
        # Para modelo 65, exige CSC configurado na empresa
        if modelo == "65" and empresa is not None:
            nfce_hab = _nfce_habilitado(empresa)
            nfce_csc_id = getattr(empresa, "nfce_csc_id", None) or ""
            nfce_csc_token = getattr(empresa, "nfce_csc_token", None) or ""
            emp_id = getattr(empresa, "id", None)
            emp_msg = f" (Empresa ID {emp_id})" if emp_id else ""
            if not nfce_hab:
                erros.append(
                    f"Modelo 65 (NFC-e) requer NFC-e habilitado{emp_msg}. "
                    "Marque em Fiscal > Empresa > Configuração NFC-e e salve."
                )
            elif not (nfce_csc_id and str(nfce_csc_id).strip()):
                erros.append("Modelo 65 requer CSC configurado em Fiscal > Empresa (ID CSC obrigatório).")
            elif not nfce_csc_token or not str(nfce_csc_token).strip():
                erros.append("Modelo 65 requer CSC configurado em Fiscal > Empresa (Token CSC obrigatório).")
    # Ambiente: homologacao ou producao (nota.ambiente pode ser Enum)
    amb_val = getattr(nota, "ambiente", None)
    amb = (getattr(amb_val, "value", None) or str(amb_val or "")).strip().lower()
    if amb and amb not in ("homologacao", "producao"):
        erros.append("Ambiente deve ser homologação ou produção.")
    # CRT do emitente: obrigatório, 1, 2 ou 3 (bloqueio; não sanitizar)
    if empresa is not None:
        crt_val = getattr(empresa, "crt", None)
        if crt_val is None:
            erros.append("CRT do emitente é obrigatório. Preencha em Fiscal > Empresa (1=Simples, 2=Simples excedente, 3=Regime Normal).")
        else:
            try:
                c = int(crt_val)
                if c not in (1, 2, 3):
                    erros.append("CRT do emitente deve ser 1 (Simples Nacional), 2 (Simples excedente) ou 3 (Regime Normal). Preencha em Fiscal > Empresa.")
            except (TypeError, ValueError):
                erros.append("CRT do emitente deve ser 1, 2 ou 3. Preencha em Fiscal > Empresa.")
        # IE do emitente: obrigatória para emissão NF-e
        ie = getattr(empresa, "ie", None)
        if not ie or not str(ie).strip():
            erros.append("IE (Inscrição Estadual) do emitente é obrigatória para emissão NF-e. Preencha em Fiscal > Empresa.")
        # cUF: UF do emitente deve possuir webservice SEFAZ. Ambiente obrigatoriamente da Empresa Fiscal
        uf_emitente = (getattr(empresa, "uf", None) or getattr(empresa, "uf_emissao", None) or "").strip().upper()[:2]
        _e_amb = getattr(empresa, "ambiente", None)
        amb_env = str(getattr(_e_amb, "value", _e_amb) or amb or "homologacao").strip().lower()
        mod_val = str(getattr(nota, "modelo", None) or "55")
        url_aut = get_url_autorizacao(uf_emitente, amb_env, mod_val, logar=False) if uf_emitente else None
        if uf_emitente and url_aut is None:
            erros.append(f"UF do emitente ({uf_emitente}) não possui webservice SEFAZ cadastrado para o ambiente informado.")
        elif url_aut and modelo == "65":
            from .sefaz_client import validar_endpoint
            mod_int = int("".join(c for c in mod_val if c.isdigit()) or "65")
            ok_endpoint, motivo = validar_endpoint(mod_int, url_aut)
            if not ok_endpoint:
                erros.append(f"Endpoint NFC-e inconsistente: {motivo}. Modelo 65 exige webservice nfce (não nfe).")
    # Totais consistentes (bloqueio obrigatório antes da assinatura)
    err_totais = _validar_totais_nota(nota)
    if err_totais:
        erros.append(err_totais)
    usar_simples = _empresa_crt_simples(getattr(empresa, "crt", None) if empresa else None)
    _msg_produto = " O motor tributário deve preencher CFOP, origem e CSOSN/CST; verifique se há regras fiscais cadastradas para esta empresa."
    for i, item in enumerate(nota.itens or []):
        ncm = getattr(item, "ncm", None)
        if not ncm or not str(ncm).strip():
            erros.append(f"Item {i + 1} ({getattr(item, 'descricao', '') or 'sem descrição'}): NCM é obrigatório para envio à SEFAZ.{_msg_produto}")
        cfop = getattr(item, "cfop", None)
        if not cfop or not str(cfop).strip():
            erros.append(f"Item {i + 1} ({getattr(item, 'descricao', '') or 'sem descrição'}): CFOP é obrigatório.{_msg_produto}")
        origem = getattr(item, "origem", None)
        if origem is None:
            erros.append(f"Item {i + 1} ({getattr(item, 'descricao', '') or 'sem descrição'}): origem da mercadoria (0 a 8) é obrigatória.{_msg_produto}")
        else:
            try:
                o = int(origem)
                if o < 0 or o > 8:
                    erros.append(f"Item {i + 1}: origem da mercadoria deve estar entre 0 e 8.{_msg_produto}")
            except (TypeError, ValueError):
                erros.append(f"Item {i + 1}: origem da mercadoria inválida (use 0 a 8).{_msg_produto}")
        if usar_simples:
            csosn = getattr(item, "csosn", None)
            if not csosn or not str(csosn).strip():
                erros.append(f"Item {i + 1} ({getattr(item, 'descricao', '') or 'sem descrição'}): CSOSN é obrigatório para empresa no Simples Nacional.{_msg_produto}")
        else:
            cst = getattr(item, "cst_icms", None)
            if not cst or not str(cst).strip():
                erros.append(f"Item {i + 1} ({getattr(item, 'descricao', '') or 'sem descrição'}): CST ICMS é obrigatório para empresa em Regime Normal.{_msg_produto}")
    if nota.cliente_id:
        cliente = db.query(Cliente).filter(Cliente.id == nota.cliente_id).first()
        if cliente:
            if cliente.cnpj and str(cliente.cnpj).strip():
                msg_cnpj = _validar_cnpj(cliente.cnpj)
                if msg_cnpj:
                    erros.append(f"Destinatário (CNPJ): {msg_cnpj}")
            elif cliente.cpf and str(cliente.cpf).strip():
                msg_cpf = _validar_cpf(cliente.cpf)
                if msg_cpf:
                    erros.append(f"Destinatário (CPF): {msg_cpf}")
    return erros


def _preencher_fiscal_itens_desde_produto_cliente(db: Session, nota: NotaFiscal) -> None:
    """Preenche itens da nota com NCM, CEST, unidade, descrição do ProdutoCliente.
    CFOP, origem, CSOSN e CST são definidos exclusivamente pelo motor tributário."""
    for item in nota.itens or []:
        pc_id = getattr(item, "produto_cliente_id", None)
        pc = db.query(ProdutoCliente).filter(ProdutoCliente.id == pc_id).first() if pc_id else None
        if not pc:
            continue
        if (not getattr(item, "ncm", None) or not str(item.ncm).strip()) and getattr(pc, "ncm", None) and str(pc.ncm).strip():
            item.ncm = str(pc.ncm).strip()[:10]
        if (not getattr(item, "unidade", None) or not str(item.unidade).strip()) and getattr(pc, "unidade_medida", None) and str(pc.unidade_medida).strip():
            item.unidade = str(pc.unidade_medida).strip()[:10]
        if (not getattr(item, "cest", None) or not str(item.cest).strip()) and getattr(pc, "cest", None) and str(pc.cest).strip():
            item.cest = str(pc.cest).strip()[:10]
        if (not getattr(item, "descricao", None) or not str(item.descricao).strip()) and getattr(pc, "nome", None) and str(pc.nome).strip():
            item.descricao = str(pc.nome).strip()[:255]
    db.flush()


def _aplicar_motor_tributario_itens(db: Session, nota: NotaFiscal, empresa: Empresa) -> Optional[str]:
    """Aplica o motor tributário em cada item da nota. Retorna mensagem de erro ou None se OK."""
    uf_emitente = (getattr(empresa, "uf", None) or getattr(empresa, "uf_emissao", None) or "").strip().upper()[:2]
    crt_val = getattr(empresa, "crt", None)
    if crt_val is None:
        return "CRT do emitente é obrigatório para aplicar motor tributário."
    try:
        crt = int(crt_val)
    except (TypeError, ValueError):
        return "CRT do emitente inválido."
    if crt not in (1, 2, 3):
        return "CRT do emitente deve ser 1, 2 ou 3."

    uf_dest = None
    tipo_dest = "pf"
    if nota.cliente_id and nota.cliente:
        cli = nota.cliente
        uf_dest = (getattr(cli, "uf", None) or "").strip().upper()[:2] or None
        tipo_dest = "pj" if (getattr(cli, "cnpj", None) and str(cli.cnpj or "").strip()) else "pf"
    elif getattr(nota, "pedido_marketplace_id", None) and getattr(nota, "pedido_marketplace", None):
        pm = nota.pedido_marketplace
        dest_dict = _destinatario_from_pedido_marketplace(pm)
        uf_dest = (dest_dict.get("uf") or "").strip().upper()[:2] or None
        tipo_dest = dest_dict.get("tipo_pessoa", "pf")

    if uf_emitente and uf_dest:
        tipo_operacao = (
            TipoOperacaoFiscalEnum.VENDA_INTERNA.value
            if uf_emitente == uf_dest
            else TipoOperacaoFiscalEnum.VENDA_INTERESTADUAL.value
        )
        destino_geo = (
            DestinoGeograficoCFOP.INTERNA.value
            if uf_emitente == uf_dest
            else DestinoGeograficoCFOP.INTERESTADUAL.value
        )
    else:
        tipo_operacao = TipoOperacaoFiscalEnum.QUALQUER.value
        destino_geo = DestinoGeograficoCFOP.INTERNA.value

    # Carrega regras uma vez por empresa (cache Redis quando disponível)
    def _fetch_regras():
        return (
            db.query(RegraFiscalIcms)
            .filter(
                RegraFiscalIcms.empresa_id == empresa.id,
                RegraFiscalIcms.ativo == True,
            )
            .order_by(RegraFiscalIcms.ordem_prioridade.asc())
            .all()
        )

    regras_empresa = get_regras_fiscais_empresa_cached(empresa.id, _fetch_regras)

    for idx, item in enumerate(nota.itens or []):
        ncm = (getattr(item, "ncm", None) or "").strip()
        if not ncm:
            return f"Item {idx + 1} ({getattr(item, 'descricao', '') or 'sem descrição'}): NCM é obrigatório. Cadastre no produto."
        cest = (getattr(item, "cest", None) or "").strip() or None
        pc = getattr(item, "produto_cliente", None)

        origem_comercial = OrigemMercadoriaComercial.MERCADORIA_TERCEIROS.value
        if pc and getattr(pc, "producao_propria", None) is True:
            origem_comercial = OrigemMercadoriaComercial.PRODUCAO_PROPRIA.value

        contexto_cfop = ContextoCFOP(
            tipo_documento=TipoMovimentoCFOP.SAIDA.value,
            uf_emitente=uf_emitente or "",
            uf_destinatario=uf_dest,
            destino_geografico=destino_geo,
            natureza_operacao=NaturezaOperacaoCFOP.VENDA.value,
            origem_mercadoria_comercial=origem_comercial,
            destinatario_contribuinte_icms=None,
            consumidor_final=None,
            gera_icms_st=False,
            finalidade_emissao=None,
        )
        try:
            cfop_sugerido = resolver_cfop(contexto_cfop)
        except ErroCFOPResolver as e:
            return f"Item {idx + 1} (NCM {ncm}): {str(e)}"

        ctx = ContextoFiscalItem(
            empresa_id=empresa.id,
            crt=crt,
            uf_emitente=uf_emitente or "",
            uf_destinatario=uf_dest,
            tipo_destinatario=tipo_dest,
            tipo_operacao=tipo_operacao,
            ncm=ncm,
            cest=cest,
            cfop_sugerido=cfop_sugerido,
        )
        try:
            decisao = resolver_regra_icms(db, ctx, regras_precarregadas=regras_empresa)
        except ErroMotorTributario as e:
            return f"Item {idx + 1} (NCM {ncm}): {str(e)}"

        item.cfop = decisao.cfop
        item.origem = decisao.origem_mercadoria
        item.cst_icms = decisao.cst_icms
        item.csosn = decisao.csosn
        item.aliquota_icms = decisao.aliquota_icms
        item.regra_fiscal_icms_id = decisao.regra_fiscal_id
        item.motor_versao = MOTOR_VERSAO
        item.motor_contexto_json = {
            "empresa_id": ctx.empresa_id,
            "crt": ctx.crt,
            "uf_emitente": ctx.uf_emitente,
            "uf_destinatario": ctx.uf_destinatario,
            "tipo_destinatario": ctx.tipo_destinatario,
            "tipo_operacao": ctx.tipo_operacao,
            "ncm": ctx.ncm,
            "cest": ctx.cest,
            "cfop_sugerido": cfop_sugerido,
        }
        item.motor_resultado_json = {
            "cfop": decisao.cfop,
            "origem_mercadoria": decisao.origem_mercadoria,
            "cst_icms": decisao.cst_icms,
            "csosn": decisao.csosn,
            "aliquota_icms": str(decisao.aliquota_icms),
            "regra_fiscal_id": decisao.regra_fiscal_id,
        }
        if decisao.aliquota_icms_st is not None:
            item.aliquota_icms_st = decisao.aliquota_icms_st
        if decisao.modalidade_bc_icms_st is not None:
            try:
                item.modalidade_bc_icms_st = int(str(decisao.modalidade_bc_icms_st).strip())
            except (TypeError, ValueError):
                pass
    db.flush()
    return None


def _nfce_habilitado(empresa: Any) -> bool:
    """Retorna True se NFC-e está habilitado na empresa (aceita bool, str, int)."""
    v = getattr(empresa, "nfce_habilitado", None) if hasattr(empresa, "nfce_habilitado") else (empresa.get("nfce_habilitado") if isinstance(empresa, dict) else None)
    return v is True or (isinstance(v, str) and str(v).lower() in ("true", "1", "yes")) or v == 1


def _descriptografar_token_csc(empresa: Empresa) -> Optional[str]:
    """Retorna o token CSC em texto plano para uso no payload. Se não houver token ou não habilitado, retorna None.
    Se a descriptografia falhar, levanta ValueError."""
    if not _nfce_habilitado(empresa):
        return None
    raw = getattr(empresa, "nfce_csc_token", None)
    if not raw or not str(raw).strip():
        return None
    s = raw if isinstance(raw, str) else (raw.decode("utf-8") if isinstance(raw, bytes) else str(raw))
    from app.services.payments.credentials import decrypt_cert_password
    return decrypt_cert_password(s, raise_on_failure=True)


def _empresa_para_payload(empresa: Empresa) -> Dict[str, Any]:
    """Monta dict com dados da empresa para o provedor (DANFE/PDF: logo, nome, endereço)."""
    cidade_uf = None
    if getattr(empresa, "cidade", None) and getattr(empresa, "uf", None):
        cidade_uf = f"{empresa.cidade}/{empresa.uf}"
    elif getattr(empresa, "cidade", None):
        cidade_uf = empresa.cidade
    elif getattr(empresa, "uf", None):
        cidade_uf = empresa.uf
    partes = [p for p in [
        empresa.endereco,
        f"nº {empresa.numero}" if getattr(empresa, "numero", None) else None,
        getattr(empresa, "complemento", None),
        getattr(empresa, "bairro", None),
        cidade_uf,
    ] if p]
    endereco_completo = ", ".join(partes) if partes else None
    return {
        "id": empresa.id,
        "razao_social": empresa.razao_social,
        "nome_fantasia": getattr(empresa, "nome_fantasia", None),
        "cnpj": empresa.cnpj,
        "ie": getattr(empresa, "ie", None),
        "im": getattr(empresa, "im", None),
        "crt": getattr(empresa, "crt", None),
        "municipio_ibge": getattr(empresa, "municipio_ibge", None),
        "endereco": empresa.endereco,
        "numero": getattr(empresa, "numero", None),
        "complemento": getattr(empresa, "complemento", None),
        "bairro": getattr(empresa, "bairro", None),
        "cidade": getattr(empresa, "cidade", None),
        "uf": getattr(empresa, "uf", None),
        "cep": getattr(empresa, "cep", None),
        "endereco_completo": endereco_completo,
        "telefone": getattr(empresa, "telefone", None),
        "email": getattr(empresa, "email", None),
        "logo_url": getattr(empresa, "logo_url", None) or None,
        "nfce_habilitado": getattr(empresa, "nfce_habilitado", None),
        "nfce_csc_id": getattr(empresa, "nfce_csc_id", None),
        "nfce_csc_token": _descriptografar_token_csc(empresa),
    }


def _cliente_destinatario_para_payload(cliente: Cliente) -> Dict[str, Any]:
    """Monta dict do destinatário (CF) para o provedor/SEFAZ. Inclui cnpj ou cpf conforme PJ/PF."""
    tipo_pessoa = "pj" if (cliente.cnpj and cliente.cnpj.strip()) else "pf"
    return {
        "id": cliente.id,
        "nome": cliente.nome,
        "razao_social": getattr(cliente, "razao_social", None) or cliente.nome,
        "cnpj": cliente.cnpj if tipo_pessoa == "pj" else None,
        "cpf": cliente.cpf if tipo_pessoa == "pf" else None,
        "tipo_pessoa": tipo_pessoa,
        "ie": getattr(cliente, "ie", None),
        "municipio_ibge": getattr(cliente, "municipio_ibge", None),
        "endereco": getattr(cliente, "endereco", None),
        "numero": getattr(cliente, "numero", None),
        "bairro": getattr(cliente, "bairro", None),
        "cidade": getattr(cliente, "cidade", None),
        "uf": getattr(cliente, "uf", None),
        "cep": getattr(cliente, "cep", None),
        "contato": getattr(cliente, "contato", None),
        "telefone": getattr(cliente, "telefone", None),
        "email": getattr(cliente, "email", None),
    }


def _destinatario_from_pedido_marketplace(pedido: Any) -> Dict[str, Any]:
    """Monta dict do destinatário para NF-e quando a nota vem de pedido marketplace (comprador não é cliente)."""
    doc = (getattr(pedido, "comprador_documento", None) or "").strip().replace(".", "").replace("-", "").replace("/", "")
    tipo_pessoa = "pj" if (len(doc) == 14 and doc.isdigit()) else "pf"
    return {
        "id": getattr(pedido, "id", None),
        "nome": (getattr(pedido, "comprador_nome", None) or "").strip() or "Consumidor",
        "cnpj": doc if tipo_pessoa == "pj" else None,
        "cpf": doc if tipo_pessoa == "pf" else None,
        "tipo_pessoa": tipo_pessoa,
        "endereco": (getattr(pedido, "endereco_entrega", None) or "").strip() or None,
        "cidade": None,
        "uf": None,
        "cep": None,
        "contato": getattr(pedido, "comprador_nome", None),
        "telefone": (getattr(pedido, "comprador_telefone", None) or "").strip() or None,
        "email": (getattr(pedido, "comprador_email", None) or "").strip() or None,
    }


def _payload_nota_servico(nota: NotaServico) -> Dict[str, Any]:
    """Monta payload mínimo da NFS-e para o provedor."""
    return {
        "id": nota.id,
        "numero": nota.numero,
        "valor_total": str(nota.valor_total),
        "discriminacao_servicos": nota.discriminacao_servicos,
        "cliente_id": nota.cliente_id,
        "itens": [
            {
                "item_numero": i.item_numero,
                "discriminacao": i.discriminacao,
                "valor_total": str(i.valor_total),
            }
            for i in (nota.itens or [])
        ],
    }


def _decimal_str(val: Any) -> str:
    """Converte valor decimal/número para string no payload (compatível com XML/SEFAZ)."""
    if val is None:
        return "0"
    return str(val)


def _origem_int(val: Any) -> int:
    """Origem da mercadoria 0-8 para o payload; inválido (ex.: 'R') vira 0."""
    if val is None:
        return 0
    try:
        o = int(val)
        return max(0, min(8, o))
    except (TypeError, ValueError):
        return 0


def _payload_nota_fiscal(nota: NotaFiscal) -> Dict[str, Any]:
    """Monta payload completo da NF-e/NFC-e para o provedor (layout compatível com NF-e 4.0).
    Inclui todos os campos do modelo que mapeiam para o XML padronizado pelo governo (infNFe, det, etc.).
    O provedor é responsável por gerar o XML no formato SEFAZ e enviar à autorizadora."""
    payload = {
        "id": nota.id,
        "numero": nota.numero,
        "serie": nota.serie or "1",
        "tipo": nota.tipo.value if nota.tipo else None,
        "modelo": nota.modelo,
        "data_emissao": nota.data_emissao,
        "data_saida": nota.data_saida,
        "natureza_operacao": nota.natureza_operacao,
        "ambiente": nota.ambiente.value if getattr(nota.ambiente, "value", None) else str(nota.ambiente) if nota.ambiente else "homologacao",
        "valor_total": _decimal_str(nota.valor_total),
        "valor_produtos": _decimal_str(nota.valor_produtos),
        "valor_frete": _decimal_str(nota.valor_frete),
        "valor_seguro": _decimal_str(nota.valor_seguro),
        "valor_desconto": _decimal_str(nota.valor_desconto),
        "valor_outros": _decimal_str(nota.valor_outros),
        "valor_icms": _decimal_str(nota.valor_icms),
        "valor_icms_desonerado": _decimal_str(nota.valor_icms_desonerado),
        "valor_icms_st": _decimal_str(nota.valor_icms_st),
        "valor_ipi": _decimal_str(nota.valor_ipi),
        "valor_pis": _decimal_str(nota.valor_pis),
        "valor_cofins": _decimal_str(nota.valor_cofins),
        "cliente_id": nota.cliente_id,
        "forma_pagamento": nota.forma_pagamento,
        "tipo_pagamento": nota.tipo_pagamento,
        "observacoes": nota.observacoes,
        "informacoes_complementares": nota.informacoes_complementares,
        "itens": [],
    }
    for i in nota.itens or []:
        item = {
            "item_numero": i.item_numero,
            "descricao": i.descricao,
            "codigo_produto": i.codigo_produto,
            "ncm": i.ncm,
            "cest": i.cest,
            "cfop": i.cfop,
            "unidade": i.unidade or "UN",
            "extipi": i.extipi,
            "quantidade": _decimal_str(i.quantidade),
            "valor_unitario": _decimal_str(i.valor_unitario),
            "valor_total": _decimal_str(i.valor_total),
            "valor_desconto": _decimal_str(i.valor_desconto),
            "origem": _origem_int(i.origem),
            "cst_icms": i.cst_icms,
            "csosn": i.csosn,
            "aliquota_icms": _decimal_str(i.aliquota_icms) if i.aliquota_icms is not None else None,
            "valor_icms": _decimal_str(i.valor_icms),
            "valor_base_icms": _decimal_str(i.valor_base_icms),
            "modalidade_bc_icms_st": i.modalidade_bc_icms_st,
            "aliquota_icms_st": _decimal_str(i.aliquota_icms_st) if i.aliquota_icms_st is not None else None,
            "valor_base_icms_st": _decimal_str(i.valor_base_icms_st),
            "valor_icms_st": _decimal_str(i.valor_icms_st),
            "ipi_cst": i.ipi_cst,
            "ipi_codigo_enquadramento": i.ipi_codigo_enquadramento,
            "ipi_aliquota": _decimal_str(i.ipi_aliquota) if i.ipi_aliquota is not None else None,
            "valor_ipi": _decimal_str(i.valor_ipi),
            "valor_base_ipi": _decimal_str(i.valor_base_ipi),
            "pis_cst": i.pis_cst,
            "pis_aliquota": _decimal_str(i.pis_aliquota) if i.pis_aliquota is not None else None,
            "pis_valor": _decimal_str(i.pis_valor),
            "pis_base_calculo": _decimal_str(i.pis_base_calculo),
            "cofins_cst": i.cofins_cst,
            "cofins_aliquota": _decimal_str(i.cofins_aliquota) if i.cofins_aliquota is not None else None,
            "cofins_valor": _decimal_str(i.cofins_valor),
            "cofins_base_calculo": _decimal_str(i.cofins_base_calculo),
            "informacoes_adicionais": i.informacoes_adicionais,
            "produto_cliente_id": getattr(i, "produto_cliente_id", None),
        }
        payload["itens"].append(item)
    return payload


def _registrar_evento(
    db: Session,
    documento_tipo: str,
    documento_id: int,
    empresa_id: int,
    evento: str,
    payload_raw: Optional[str] = None,
    usuario_id: Optional[int] = None,
    resposta_bruta: Optional[str] = None,
    http_content_type: Optional[str] = None,
    status_http: Optional[int] = None,
) -> None:
    doc_enum = DocumentoTipoFiscalEnum(documento_tipo)
    ev_enum = EventoFiscalEnum(evento)
    fe = FiscalEvento(
        documento_tipo=doc_enum,
        documento_id=documento_id,
        empresa_id=empresa_id,
        evento=ev_enum,
        payload_raw=payload_raw,
        usuario_id=usuario_id,
        resposta_bruta=resposta_bruta,
        http_content_type=http_content_type,
        status_http=status_http,
    )
    db.add(fe)
    db.flush()


def _gerar_danfe_se_autorizado(db: Session, nota: NotaFiscal, empresa: Empresa) -> None:
    """Se o provedor não retornou pdf_path, gera e salva o DANFE agora para a nota já autorizada.
    Evita geração sob demanda no primeiro clique (que causa 'Client closed request' por timeout)."""
    if getattr(nota, "danfe_path", None):
        return
    try:
        from app.services.pdf_orcamento_pedido import gerar_pdf_danfe
    except Exception:
        return
    empresa_nome = (empresa.razao_social or empresa.nome_fantasia or "-") if empresa else "-"
    cliente_nome = (
        (nota.cliente.nome or getattr(nota.cliente, "razao_social", None) or "Consumidor final")
        if nota.cliente
        else "Consumidor final"
    )
    itens = [
        {
            "item_numero": getattr(i, "item_numero", idx + 1),
            "descricao": getattr(i, "descricao", ""),
            "quantidade": getattr(i, "quantidade", 0),
            "valor_unitario": getattr(i, "valor_unitario", 0),
            "valor_total": getattr(i, "valor_total", 0),
        }
        for idx, i in enumerate(nota.itens or [])
    ]
    dados = {
        "numero": nota.numero,
        "serie": getattr(nota, "serie", None) or "1",
        "data_emissao": nota.data_emissao,
        "chave_acesso": getattr(nota, "chave_acesso", None),
        "empresa_nome": empresa_nome,
        "cliente_nome": cliente_nome,
        "valor_total": nota.valor_total,
        "itens": itens,
    }
    try:
        pdf_bytes = gerar_pdf_danfe(dados)
    except Exception:
        return
    dir_pdf = FISCAL_UPLOADS_DIR / f"empresa_{nota.empresa_id}"
    dir_pdf.mkdir(parents=True, exist_ok=True)
    path = str(dir_pdf / f"danfe_{nota.id}.pdf")
    PathLib(path).write_bytes(pdf_bytes)
    nota.danfe_path = path
    db.flush()


class FiscalEmissaoService:
    """Orquestra validação, envio ao provedor e atualização de status/evento."""

    def __init__(self, db: Session):
        self.db = db

    def enviar_nfse(
        self, nota_id: int, usuario_id: Optional[int] = None
    ) -> tuple[bool, Optional[str], Optional[ResultadoEnvioFiscal]]:
        """Valida, envia NFS-e e atualiza status/evento. Retorna (sucesso, mensagem_erro, resultado)."""
        nota = (
            self.db.query(NotaServico)
            .options(joinedload(NotaServico.cliente))
            .filter(NotaServico.id == nota_id)
            .first()
        )
        if not nota:
            return False, "Nota de serviço não encontrada", None
        erros = validar_nota_servico(self.db, nota)
        if erros:
            return False, "; ".join(erros), None
        empresa = self.db.query(Empresa).filter(Empresa.id == nota.empresa_id).first()
        if not empresa:
            return False, "Empresa não encontrada", None
        provedor = get_provedor_fiscal(self.db, empresa)
        payload = _payload_nota_servico(nota)
        payload["empresa"] = _empresa_para_payload(empresa)
        if nota.cliente:
            payload["destinatario"] = _cliente_destinatario_para_payload(nota.cliente)
        else:
            payload["destinatario"] = None
        _registrar_evento(
            self.db, "nfse", nota.id, nota.empresa_id, "envio",
            payload_raw=json.dumps(payload, default=str), usuario_id=usuario_id,
        )
        resultado = provedor.enviar_nfse(nota.empresa_id, nota.id, payload)
        pr = resultado.payload_retorno or {}
        _registrar_evento(
            self.db, "nfse", nota.id, nota.empresa_id,
            "autorizacao" if resultado.sucesso else "rejeicao",
            payload_raw=json.dumps(pr, default=str),
            usuario_id=usuario_id,
            resposta_bruta=pr.get("raw_response"),
            http_content_type=pr.get("http_content_type"),
            status_http=pr.get("status_http"),
        )
        if resultado.sucesso:
            nota.status = StatusNotaServicoEnum.AUTORIZADO
            nota.protocolo_autorizacao = resultado.protocolo
            if resultado.pdf_path:
                nota.pdf_path = resultado.pdf_path
        else:
            nota.status = StatusNotaServicoEnum.REJEITADO
            nota.mensagem_retorno = resultado.mensagem
        self.db.flush()
        return resultado.sucesso, None if resultado.sucesso else resultado.mensagem, resultado

    def enviar_nfe(
        self, nota_id: int, usuario_id: Optional[int] = None
    ) -> tuple[bool, Optional[str], Optional[ResultadoEnvioFiscal]]:
        """Valida, envia NF-e e atualiza status/evento."""
        nota = (
            self.db.query(NotaFiscal)
            .options(
                joinedload(NotaFiscal.cliente),
                joinedload(NotaFiscal.itens).joinedload(NotaFiscalItem.produto_cliente),
                joinedload(NotaFiscal.pedido_marketplace),
            )
            .filter(NotaFiscal.id == nota_id)
            .first()
        )
        if not nota:
            return False, "Nota fiscal não encontrada", None
        if nota.status == StatusNotaEnum.AUTORIZADO:
            return False, "Nota já autorizada. Reenvio não permitido.", None
        # Regra CA/CF: nota vinculada a venda deve usar Empresa FISCAL do estabelecimento da venda (nunca de outro CA)
        venda_id = getattr(nota, "venda_id", None)
        if venda_id:
            from app.core.scope import get_empresa_fiscal_para_estabelecimento, get_estabelecimento_cliente_id_da_venda
            estab_id = get_estabelecimento_cliente_id_da_venda(self.db, venda_id)
            empresa_estab = get_empresa_fiscal_para_estabelecimento(self.db, estab_id) if estab_id else None
            if empresa_estab and empresa_estab.id != nota.empresa_id:
                return False, "A nota está vinculada a uma venda; a empresa fiscal da nota deve ser a do estabelecimento da venda (CA). Emita pela tela da venda ou corrija a nota.", None
        # Rascunhos de venda/pedido podem vir com numero placeholder (ex.: RASCUNHO-VENDA-123); atribuir próximo número numérico
        if _apenas_digitos_valido(nota.numero, "Número") is not None or _apenas_digitos_valido(nota.serie, "Série") is not None:
            serie_uso = (re.sub(r"\D", "", str(nota.serie or "1")) or "1")[:10]
            if not serie_uso:
                serie_uso = "1"
            nota.numero = _proximo_numero_nf(self.db, nota.empresa_id, serie_uso)
            nota.serie = serie_uso
            self.db.flush()
        _preencher_fiscal_itens_desde_produto_cliente(self.db, nota)
        empresa = self.db.query(Empresa).filter(Empresa.id == nota.empresa_id).first()
        if not empresa:
            return False, "Empresa não encontrada", None
        err_motor = _aplicar_motor_tributario_itens(self.db, nota, empresa)
        if err_motor:
            return False, err_motor, None
        erros = validar_nota_fiscal(self.db, nota)
        if erros:
            return False, "; ".join(erros), None
        empresa = self.db.query(Empresa).filter(Empresa.id == nota.empresa_id).first()
        if not empresa:
            return False, "Empresa não encontrada", None
        provedor = get_provedor_fiscal(self.db, empresa)
        payload = _payload_nota_fiscal(nota)
        if str(nota.modelo or "").strip() == "65":
            now_utc = datetime.now(timezone.utc)
            payload["data_emissao"] = now_utc
            payload["data_saida"] = now_utc
        payload["empresa"] = _empresa_para_payload(empresa)
        if nota.cliente:
            payload["destinatario"] = _cliente_destinatario_para_payload(nota.cliente)
        elif getattr(nota, "pedido_marketplace_id", None) and getattr(nota, "pedido_marketplace", None):
            payload["destinatario"] = _destinatario_from_pedido_marketplace(nota.pedido_marketplace)
        else:
            payload["destinatario"] = None
        _registrar_evento(
            self.db, "nfe", nota.id, nota.empresa_id, "envio",
            payload_raw=json.dumps(payload, default=str), usuario_id=usuario_id,
        )
        resultado = provedor.enviar_nfe(nota.empresa_id, nota.id, payload)
        pr = resultado.payload_retorno or {}
        _registrar_evento(
            self.db, "nfe", nota.id, nota.empresa_id,
            "autorizacao" if resultado.sucesso else "rejeicao",
            payload_raw=json.dumps(pr, default=str),
            usuario_id=usuario_id,
            resposta_bruta=pr.get("raw_response"),
            http_content_type=pr.get("http_content_type"),
            status_http=pr.get("status_http"),
        )
        tentativa_numero = (self.db.query(NFeTentativaEnvio).filter(NFeTentativaEnvio.nota_fiscal_id == nota.id).count()) + 1
        if pr.get("tipo_erro"):
            tipo_erro = pr.get("tipo_erro")
        elif pr.get("tipo_resultado") == "erro_tecnico":
            tipo_erro = "conexao"
        elif resultado.sucesso:
            tipo_erro = None
        elif pr.get("status_http") == 200:
            tipo_erro = "rejeicao_fiscal"
        elif "Falha técnica" in (resultado.mensagem or "") or "Erro de conexão" in (resultado.mensagem or ""):
            tipo_erro = "conexao"
        elif "assinar" in (resultado.mensagem or "").lower() or "assinatura" in (resultado.mensagem or "").lower():
            tipo_erro = "assinatura"
        else:
            tipo_erro = "http_html"
        raw_full = pr.get("raw_response") or ""
        resposta_bruta_path_val: Optional[str] = None
        LIMITE_RESPOSTA_BRUTA = 50000
        if raw_full:
            if len(raw_full) > LIMITE_RESPOSTA_BRUTA:
                dir_empresa = FISCAL_UPLOADS_DIR / f"empresa_{nota.empresa_id}"
                dir_empresa.mkdir(parents=True, exist_ok=True)
                nome_arquivo = f"resposta_bruta_{nota.id}_{tentativa_numero}.txt"
                arquivo_path = dir_empresa / nome_arquivo
                try:
                    arquivo_path.write_text(raw_full, encoding="utf-8")
                    resposta_bruta_path_val = str(arquivo_path.relative_to(PROJECT_ROOT))
                except Exception:
                    resposta_bruta_path_val = None
                resposta_bruta_val = raw_full[:1000] + "\n...[truncado, ver resposta_bruta_path]"
            else:
                resposta_bruta_val = raw_full
        else:
            resposta_bruta_val = None
        self.db.add(NFeTentativaEnvio(
            nota_fiscal_id=nota.id,
            empresa_id=nota.empresa_id,
            sucesso=resultado.sucesso,
            status_http=pr.get("status_http"),
            http_content_type=pr.get("http_content_type"),
            tipo_erro=tipo_erro,
            servico=pr.get("servico") or "autorizacao",
            ambiente_sefaz=pr.get("ambiente_sefaz"),
            mensagem=resultado.mensagem,
            cert_serial=pr.get("cert_serial"),
            cert_subject=pr.get("cert_subject"),
            xml_hash_sha256=pr.get("xml_hash_sha256"),
            duracao_ms=pr.get("duracao_ms"),
            resposta_bruta=resposta_bruta_val,
            resposta_bruta_path=resposta_bruta_path_val,
            payload_retorno=json.dumps(pr, default=str) if pr else None,
            tentativa_numero=tentativa_numero,
            cstat=pr.get("cstat"),
            xmotivo=pr.get("xmotivo"),
            nrec=pr.get("nrec"),
            protocolo=pr.get("protocolo"),
            url=pr.get("url"),
            erro_tecnico=pr.get("erro_tecnico"),
            tipo_resultado=pr.get("tipo_resultado"),
        ))
        if resultado.sucesso:
            nota.status = StatusNotaEnum.AUTORIZADO
            nota.protocolo_autorizacao = resultado.protocolo
            nota.codigo_status = (pr.get("cstat") or "").strip()[:10] or None
            if resultado.chave:
                nota.chave_acesso = resultado.chave
            if str(nota.modelo or "").strip() == "65" and "data_emissao" in payload:
                nota.data_emissao = payload["data_emissao"]
                if payload.get("data_saida"):
                    nota.data_saida = payload["data_saida"]
            if resultado.pdf_path:
                nota.danfe_path = resultado.pdf_path
            else:
                # Pré-gerar DANFE para evitar "Client closed request" ao abrir/baixar PDF depois
                _gerar_danfe_se_autorizado(self.db, nota, empresa)
            if getattr(resultado, "xml_path", None):
                nota.xml_path = resultado.xml_path
            if getattr(resultado, "xml_retorno_path", None):
                nota.xml_retorno_path = resultado.xml_retorno_path
        else:
            nota.status = StatusNotaEnum.REJEITADO
            msg_retorno = resultado.mensagem or ""
            if pr.get("tipo_resultado") in ("resposta_invalida", "resposta_vazia") and "nfe_tentativa_envio" in msg_retorno:
                msg_retorno = f"{msg_retorno.rstrip('.')} (nota_id={nota.id})."
            nota.mensagem_retorno = msg_retorno or None
            nota.codigo_status = (pr.get("cstat") or "").strip()[:10] or None
            if getattr(resultado, "chave", None) and str(resultado.chave).strip():
                nota.chave_acesso = (resultado.chave or "").strip()[:44]
            if getattr(resultado, "xml_retorno_path", None):
                nota.xml_retorno_path = resultado.xml_retorno_path
        self.db.flush()
        return resultado.sucesso, None if resultado.sucesso else resultado.mensagem, resultado

    def cancelar_nfse(
        self, nota_id: int, motivo: str, usuario_id: Optional[int] = None
    ) -> tuple[bool, Optional[str]]:
        """Cancela NFS-e no provedor e atualiza status/evento."""
        nota = self.db.query(NotaServico).filter(NotaServico.id == nota_id).first()
        if not nota:
            return False, "Nota de serviço não encontrada"
        empresa = self.db.query(Empresa).filter(Empresa.id == nota.empresa_id).first()
        if not empresa:
            return False, "Empresa não encontrada"
        provedor = get_provedor_fiscal(self.db, empresa)
        resultado = provedor.cancelar_nfse(nota.empresa_id, nota.id, motivo)
        pr = resultado.payload_retorno or {}
        _registrar_evento(
            self.db, "nfse", nota.id, nota.empresa_id, "cancelamento",
            payload_raw=json.dumps(pr, default=str),
            usuario_id=usuario_id,
            resposta_bruta=pr.get("raw_response"),
            http_content_type=pr.get("http_content_type"),
            status_http=pr.get("status_http"),
        )
        if resultado.sucesso:
            nota.status = StatusNotaServicoEnum.CANCELADO
            nota.mensagem_retorno = motivo
        self.db.flush()
        return resultado.sucesso, None if resultado.sucesso else resultado.mensagem

    def cancelar_nfe(
        self, nota_id: int, motivo: str, usuario_id: Optional[int] = None
    ) -> tuple[bool, Optional[str]]:
        """Cancela NF-e no provedor e atualiza status/evento."""
        nota = self.db.query(NotaFiscal).filter(NotaFiscal.id == nota_id).first()
        if not nota:
            return False, "Nota fiscal não encontrada"
        empresa = self.db.query(Empresa).filter(Empresa.id == nota.empresa_id).first()
        if not empresa:
            return False, "Empresa não encontrada"
        provedor = get_provedor_fiscal(self.db, empresa)
        resultado = provedor.cancelar_nfe(nota.empresa_id, nota.id, motivo)
        pr = resultado.payload_retorno or {}
        _registrar_evento(
            self.db, "nfe", nota.id, nota.empresa_id, "cancelamento",
            payload_raw=json.dumps(pr, default=str),
            usuario_id=usuario_id,
            resposta_bruta=pr.get("raw_response"),
            http_content_type=pr.get("http_content_type"),
            status_http=pr.get("status_http"),
        )
        if resultado.sucesso:
            nota.status = StatusNotaEnum.CANCELADO
            nota.mensagem_retorno = motivo
        self.db.flush()
        return resultado.sucesso, None if resultado.sucesso else resultado.mensagem
