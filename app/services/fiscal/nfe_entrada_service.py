# PDV Ibix - Serviço de importação e conciliação NF-e (entrada)
"""
Importa XML → NfeDocumento + NfeItens; resolve emitente (FornecedorCliente);
aplica auto-vínculo por GTIN e por mapa produto_fornecedor; confirma e lança no estoque.
"""
from __future__ import annotations

import hashlib
import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from ...models.codigo_barras_cliente import CodigoBarrasCliente
from ...models.fornecedor_cliente import FornecedorCliente
from ...models.movimentacao_estoque import MovimentacaoEstoque
from ...models.nfe_entrada import NfeDocumento, NfeItem
from ...models.produto_cliente import ProdutoCliente
from ...models.produto_fornecedor import ProdutoFornecedor
from .nfe_entrada_parser import parse_nfe_xml

logger = logging.getLogger(__name__)

# Máximo de arquivos por requisição em importar-lote (evita corpo HTTP excessivo).
NFE_ENTRADA_IMPORTAR_LOTE_MAX = 500


def _decode_xml_bytes(raw: bytes) -> str:
    """Decodifica bytes do XML para armazenar em texto (NF-e costuma vir em UTF-8 ou ISO-8859-1)."""
    if not raw:
        return ""
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _cnpj_limpo(cnpj: Optional[str]) -> str:
    if not cnpj:
        return ""
    return "".join(c for c in str(cnpj) if c.isdigit())


def _telefone_emitente_xml(fone: Optional[str]) -> Optional[str]:
    """
    Normaliza fone do XML (enderEmit) para gravar em fornecedores_cliente.telefone (até 50 chars).
    Preferência: só dígitos; se não houver dígitos, usa texto trimado.
    """
    if not fone or not str(fone).strip():
        return None
    raw = str(fone).strip()
    digits = "".join(c for c in raw if c.isdigit())
    if digits:
        return digits[:50]
    return raw[:50] if raw else None


def _buscar_ou_criar_emitente(
    db: Session,
    cliente_id: int,
    cnpj: str,
    razao: str,
    telefone_xml: Optional[str] = None,
) -> Optional[int]:
    """Retorna fornecedor_cliente.id do emitente; cria se não existir (por cliente_id + CNPJ).
    Preenche/atualiza telefone a partir de emit/enderEmit/fone quando informado no XML."""
    cnpj_limpo = _cnpj_limpo(cnpj)
    if not cnpj_limpo:
        return None
    tel = _telefone_emitente_xml(telefone_xml)
    f = db.query(FornecedorCliente).filter(
        FornecedorCliente.cliente_id == cliente_id,
        FornecedorCliente.cnpj == cnpj_limpo,
    ).first()
    if f:
        if tel and not (f.telefone and str(f.telefone).strip()):
            f.telefone = tel
            db.flush()
        return f.id
    # Criar novo fornecedor
    novo = FornecedorCliente(
        cliente_id=cliente_id,
        cnpj=cnpj_limpo,
        nome=razao or f"Fornecedor {cnpj_limpo[:8]}...",
        telefone=tel,
        ativo=True,
    )
    db.add(novo)
    db.flush()
    return novo.id


def backfill_fornecedor_telefone_desde_nfe_xml(
    db: Session,
    *,
    force: bool = False,
    yield_per: int = 150,
) -> Dict[str, int]:
    """
    Preenche ``fornecedores_cliente.telefone`` a partir de ``nfe_documentos.xml_original``
    (emit/enderEmit/fone).

    Por padrão só grava quando o telefone do fornecedor está vazio (mesmo critério da importação).
    Com ``force=True``, sobrescreve na ordem de ``nfe_documentos.id`` (última nota processada vence).

    O chamador deve fazer ``commit`` na sessão quando aplicável.
    """
    stmt = (
        select(NfeDocumento)
        .where(
            and_(
                NfeDocumento.xml_original.isnot(None),
                NfeDocumento.emitente_fornecedor_id.isnot(None),
            )
        )
        .order_by(NfeDocumento.id)
        .execution_options(yield_per=yield_per)
    )
    atualizados = 0
    parse_erros = 0
    xml_sem_fone = 0
    for doc in db.scalars(stmt):
        xml = (doc.xml_original or "").strip()
        if not xml:
            continue
        try:
            parsed = parse_nfe_xml(xml)
        except Exception:
            parse_erros += 1
            continue
        tel = _telefone_emitente_xml(parsed.get("emitente_fone"))
        if not tel:
            xml_sem_fone += 1
            continue
        fid = doc.emitente_fornecedor_id
        if not fid:
            continue
        f = db.get(FornecedorCliente, fid)
        if not f:
            continue
        if not force and (f.telefone and str(f.telefone).strip()):
            continue
        if (f.telefone or "").strip() == tel:
            continue
        f.telefone = tel
        atualizados += 1
        if atualizados % 200 == 0:
            db.flush()
    db.flush()
    return {
        "fornecedores_atualizados": atualizados,
        "xml_parse_erros": parse_erros,
        "xml_sem_fone_emitente": xml_sem_fone,
    }


def importar_xml(
    db: Session,
    cliente_id: int,
    xml_content: str | bytes,
    *,
    guardar_xml: bool = True,
) -> Tuple[NfeDocumento, List[Dict[str, Any]]]:
    """
    Parseia o XML, cria NfeDocumento e NfeItens, associa emitente, aplica auto-vínculo.
    Retorna (documento, lista de erros/avisos).
    """
    parsed = parse_nfe_xml(xml_content)
    chave = parsed["chave_acesso_44"]

    # Evitar duplicata por chave (constraint global: uq_nfe_documentos_chave_acesso_44)
    existente = db.query(NfeDocumento).filter(
        NfeDocumento.chave_acesso_44 == chave,
    ).first()
    if existente:
        if existente.cliente_id == cliente_id:
            return existente, [{"msg": "Nota já importada com esta chave.", "chave": chave}]
        raise ValueError(
            f"Chave de acesso {chave} já importada por outro estabelecimento (cliente_id={existente.cliente_id})."
        )

    emitente_id = _buscar_ou_criar_emitente(
        db,
        cliente_id,
        parsed.get("emitente_cnpj") or "",
        parsed.get("emitente_razao") or "",
        telefone_xml=parsed.get("emitente_fone"),
    )

    if guardar_xml:
        xml_original = _decode_xml_bytes(xml_content) if isinstance(xml_content, bytes) else (xml_content or "")
    else:
        xml_original = None
    xml_sha256 = hashlib.sha256((xml_original or "").encode("utf-8")).hexdigest() if xml_original else None

    doc = NfeDocumento(
        cliente_id=cliente_id,
        chave_acesso_44=chave,
        modelo=parsed.get("modelo"),
        serie=parsed.get("serie"),
        numero=parsed.get("numero"),
        emissao_em=parsed.get("emissao_em"),
        # Módulo "Entrada de Notas": comprador importa XML do fornecedor → sempre ENTRADA para o estabelecimento (tpNF no XML é saída do emissor)
        entrada_saida="ENTRADA",
        ambiente=parsed.get("ambiente"),
        emitente_fornecedor_id=emitente_id,
        emitente_razao_social=(parsed.get("emitente_razao") or "").strip() or None,
        total_produtos=parsed.get("total_produtos"),
        total_nota=parsed.get("total_nota"),
        xml_original=xml_original,
        xml_sha256=xml_sha256,
        status="IMPORTADO",
    )
    db.add(doc)
    db.flush()

    itens_data = parsed.get("itens") or []
    for row in itens_data:
        item = NfeItem(
            nfe_id=doc.id,
            fornecedor_id=emitente_id,
            numero_item=row.get("numero_item"),
            cprod_xml=row.get("cprod_xml"),
            xprod_xml=row.get("xprod_xml"),
            ean_xml=row.get("ean_xml"),
            ncm_xml=row.get("ncm_xml"),
            cfop_xml=row.get("cfop_xml"),
            ucom_xml=row.get("ucom_xml"),
            qcom_xml=row.get("qcom_xml") if row.get("qcom_xml") is not None else row.get("qcom"),
            vuncom_xml=row.get("vuncom_xml"),
            vprod_xml=row.get("vprod_xml"),
            vdesc_xml=row.get("vdesc_xml"),
            vfrete_xml=row.get("vfrete_xml"),
            vseg_xml=row.get("vseg_xml"),
            voutro_xml=row.get("voutro_xml"),
            vipi_xml=row.get("vipi_xml"),
            vicmsst_xml=row.get("vicmsst_xml"),
            cest_xml=row.get("cest_xml"),
            extipi_xml=row.get("extipi_xml"),
            infadprod_xml=row.get("infadprod_xml"),
            orig_xml=row.get("orig_xml"),
            conciliar_status="PENDENTE",
        )
        db.add(item)
    db.flush()

    avisos: List[Dict[str, Any]] = []
    aplicados = aplicar_auto_vinculo(db, doc.id, avisos)
    if aplicados:
        avisos.append({"msg": f"Auto-vínculo aplicado em {aplicados} item(ns)."})
    db.commit()
    db.refresh(doc)
    return doc, avisos


def importar_xml_lote(
    db: Session,
    cliente_id: int,
    arquivos: List[Tuple[str, bytes]],
) -> List[Dict[str, Any]]:
    """
    Importa vários XMLs sequencialmente (cada um com commit próprio).
    Retorna lista de dicts: arquivo, sucesso, erro (opcional), documento (NfeDocumento ou None), avisos.
    """
    resultados: List[Dict[str, Any]] = []
    for nome, raw in arquivos:
        nome = (nome or "sem_nome.xml").strip() or "sem_nome.xml"
        item: Dict[str, Any] = {
            "arquivo": nome,
            "sucesso": False,
            "erro": None,
            "documento": None,
            "avisos": [],
        }
        try:
            if not raw or not raw.strip():
                item["erro"] = "Arquivo vazio"
                resultados.append(item)
                continue
            doc, avisos = importar_xml(db, cliente_id, raw, guardar_xml=True)
            item["sucesso"] = True
            item["documento"] = doc
            item["avisos"] = avisos or []
        except ValueError as e:
            db.rollback()
            item["erro"] = str(e)
        except Exception:
            db.rollback()
            logger.exception("importar_xml_lote falhou arquivo=%s", nome)
            item["erro"] = "Erro ao processar o XML. Verifique se é uma NF-e válida (modelo 55/65)."
        resultados.append(item)
    return resultados


def aplicar_auto_vinculo(db: Session, nfe_id: int, avisos: Optional[List[Dict[str, Any]]] = None) -> int:
    """
    Para itens PENDENTES da nota: vincula por GTIN (CodigoBarrasCliente) e por mapa (produtos_fornecedor).
    Retorna quantidade de itens atualizados.
    """
    if avisos is None:
        avisos = []

    doc = db.query(NfeDocumento).filter(NfeDocumento.id == nfe_id).first()
    if not doc or doc.entrada_saida != "ENTRADA":
        return 0

    emitente_id = doc.emitente_fornecedor_id
    cliente_id = doc.cliente_id
    itens = db.query(NfeItem).filter(NfeItem.nfe_id == nfe_id, NfeItem.conciliar_status == "PENDENTE").all()
    count = 0

    for ni in itens:
        produto_id = None
        # 1) Por GTIN/EAN
        if ni.ean_xml and ni.ean_xml.strip():
            ean_limpo = _cnpj_limpo(ni.ean_xml)
            if len(ean_limpo) >= 8:
                cb = (
                    db.query(CodigoBarrasCliente)
                    .join(ProdutoCliente, CodigoBarrasCliente.produto_cliente_id == ProdutoCliente.id)
                    .filter(
                        CodigoBarrasCliente.codigo_barras == ean_limpo,
                        ProdutoCliente.cliente_id == cliente_id,
                    )
                    .first()
                )
                if cb:
                    produto_id = cb.produto_cliente_id

        # 2) Por mapa fornecedor + cProd
        if produto_id is None and emitente_id and ni.cprod_xml:
            pf = db.query(ProdutoFornecedor).filter(
                ProdutoFornecedor.fornecedor_cliente_id == emitente_id,
                ProdutoFornecedor.codigo_fornecedor == ni.cprod_xml.strip(),
                ProdutoFornecedor.ativo == True,
            ).first()
            if pf:
                produto_id = pf.produto_cliente_id

        if produto_id is not None:
            ni.produto_cliente_id = produto_id
            ni.conciliar_status = "VINCULADO"
            ni.fornecedor_id = emitente_id
            # Gravar unidade do XML no produto (estoque)
            if ni.ucom_xml and (ni.ucom_xml or "").strip():
                prod = db.query(ProdutoCliente).filter(ProdutoCliente.id == produto_id).first()
                if prod:
                    prod.unidade_medida = (ni.ucom_xml or "").strip()[:20] or prod.unidade_medida
            count += 1

    if count:
        db.flush()
    return count


def calcular_custos_rateados(db: Session, nfe_id: int) -> List[Dict[str, Any]]:
    """
    Calcula custo total e unitário por item (vProd + rateio frete/seg/outro + IPI + ICMS-ST - rateio desconto).
    Retorna lista de dicts com nfe_item_id, produto_cliente_id, quantidade, custo_total, custo_unitario.
    """
    # Itens vinculados da nota
    itens = db.query(NfeItem).filter(
        NfeItem.nfe_id == nfe_id,
        NfeItem.conciliar_status == "VINCULADO",
        NfeItem.produto_cliente_id.isnot(None),
    ).all()
    if not itens:
        return []

    totais = {"vprod": sum((i.vprod_xml or Decimal("0")) for i in itens),
              "vfrete": sum((i.vfrete_xml or Decimal("0")) for i in itens),
              "vseg": sum((i.vseg_xml or Decimal("0")) for i in itens),
              "voutro": sum((i.voutro_xml or Decimal("0")) for i in itens),
              "vdesc": sum((i.vdesc_xml or Decimal("0")) for i in itens)}
    soma_vprod = totais["vprod"]
    if soma_vprod <= 0:
        soma_vprod = Decimal("1")

    resultado = []
    for i in itens:
        vprod = i.vprod_xml or Decimal("0")
        p_rateio = vprod / soma_vprod
        rateio_frete = totais["vfrete"] * p_rateio
        rateio_seg = totais["vseg"] * p_rateio
        rateio_outro = totais["voutro"] * p_rateio
        rateio_desc = totais["vdesc"] * p_rateio
        custo_total = (
            vprod + rateio_frete + rateio_seg + rateio_outro
            + (i.vipi_xml or Decimal("0")) + (i.vicmsst_xml or Decimal("0"))
            - rateio_desc
        )
        raw = i.qcom_xml
        if raw is not None:
            try:
                q = Decimal(str(raw))
            except Exception:
                q = Decimal("0")
        else:
            q = Decimal("0")
        # Fallback: se quantidade veio zerada do XML, derivar de vProd/vUnCom quando possível
        if q <= 0 and (i.vprod_xml or 0) > 0 and (i.vuncom_xml or 0) > 0:
            q = (i.vprod_xml or Decimal("0")) / (i.vuncom_xml or Decimal("1"))
        custo_unit = (custo_total / q) if q > 0 else None
        logger.debug(
            "calcular_custos_rateados nfe_id=%s nfe_item_id=%s qcom_xml=%s quantidade_final=%s",
            nfe_id,
            i.id,
            raw,
            q,
        )
        resultado.append({
            "nfe_item_id": i.id,
            "produto_cliente_id": i.produto_cliente_id,
            "quantidade": float(q),
            "custo_total": float(custo_total),
            "custo_unitario": float(custo_unit) if custo_unit is not None else None,
        })
    return resultado


def confirmar_e_lancar_estoque(db: Session, nfe_id: int, usuario_id: Optional[int] = None) -> Tuple[int, List[str]]:
    """
    Gera movimentações de estoque (ENTRADA) para todos os itens vinculados da nota,
    atualiza quantidade_atual e valor_custo do ProdutoCliente, marca documento e itens como conciliados.
    Retorna (número de movimentações criadas, lista de erros).
    """
    doc = db.query(NfeDocumento).filter(NfeDocumento.id == nfe_id).first()
    if not doc:
        return 0, ["Nota não encontrada."]
    if doc.entrada_saida != "ENTRADA":
        return 0, ["Apenas notas de ENTRADA podem ser lançadas no estoque."]
    if doc.status == "CONCILIADO":
        return 0, ["Nota já foi conciliada e lançada no estoque."]

    custos = calcular_custos_rateados(db, nfe_id)
    if not custos:
        return 0, ["Nenhum item vinculado para lançar. Concilie todos os itens primeiro."]

    logger.debug(
        "confirmar_e_lancar_estoque nfe_id=%s custos_count=%s itens=%s",
        nfe_id,
        len(custos),
        [(c.get("nfe_item_id"), c.get("produto_cliente_id"), c.get("quantidade")) for c in custos],
    )

    # E.1: Exigir todos os itens vinculados (evitar lançamento parcial)
    if any(not c.get("produto_cliente_id") for c in custos):
        return 0, ["Existem itens não vinculados. Vincule todos os itens antes de confirmar e lançar."]

    # E.2: Evitar duplo lançamento do documento
    mov_existente = db.query(MovimentacaoEstoque).filter(
        MovimentacaoEstoque.nfe_documento_id == nfe_id,
    ).first()
    if mov_existente:
        return 0, ["Documento já lançado no estoque."]

    # Evitar duplicatas: constraint única por nfe_item_id em movimentacoes_estoque
    nfe_item_ids = [c["nfe_item_id"] for c in custos]
    rows = db.query(MovimentacaoEstoque.nfe_item_id).filter(
        MovimentacaoEstoque.nfe_item_id.in_(nfe_item_ids),
    ).all()
    ja_lancados = {r[0] for r in rows if r[0] is not None}
    if ja_lancados:
        return 0, [f"Itens já lançados no estoque (nfe_item_id: {sorted(ja_lancados)}). Não é permitido gerar movimentos duplicados por item de NF-e."]

    erros: List[str] = []
    count = 0
    for c in custos:
        try:
            qty = Decimal(str(c["quantidade"]))
            if qty <= 0:
                erros.append(f"Item {c.get('nfe_item_id')}: quantidade inválida ou zerada (qCom/qTrib no XML).")
                continue

            # Busca produto com escopo do estabelecimento (doc.cliente_id)
            prod = db.query(ProdutoCliente).filter(
                ProdutoCliente.id == c["produto_cliente_id"],
                ProdutoCliente.cliente_id == doc.cliente_id,
            ).first()
            if not prod:
                logger.warning(
                    "Produto %s não encontrado para estabelecimento (nfe_item_id=%s, doc=%s)",
                    c["produto_cliente_id"],
                    c.get("nfe_item_id"),
                    nfe_id,
                )
                erros.append(
                    f"Produto {c['produto_cliente_id']} não encontrado para o estabelecimento da nota (item nfe_item_id={c.get('nfe_item_id')})."
                )
                continue

            # Bloco principal: movimento + saldo (ordem: add(mov) → quantidade_atual += → flush)
            mov = MovimentacaoEstoque(
                produto_cliente_id=c["produto_cliente_id"],
                tipo="entrada",
                quantidade=qty,
                valor_unitario=Decimal(str(c["custo_unitario"])) if c.get("custo_unitario") else None,
                custo_total=Decimal(str(c["custo_total"])),
                nfe_documento_id=nfe_id,
                nfe_item_id=c["nfe_item_id"],
                observacao="Entrada via importação XML NF-e",
                usuario_id=usuario_id,
            )
            db.add(mov)
            qty_atual = prod.quantidade_atual
            if qty_atual is None:
                qty_atual = Decimal("0")
            elif not isinstance(qty_atual, Decimal):
                qty_atual = Decimal(str(qty_atual))
            prod.quantidade_atual = qty_atual + qty
            prod.valor_custo = Decimal(str(c["custo_unitario"])) if c.get("custo_unitario") else prod.valor_custo
            db.flush()
            count += 1

            # E.3: Log explícito da quantidade aplicada
            logger.info(
                "NFe %s | Produto %s | +%s | Novo saldo %s",
                doc.id,
                prod.id,
                qty,
                prod.quantidade_atual,
            )

            # Bloco fiscal (opcional): preencher NCM, CFOP etc. Falha aqui não reverte estoque.
            try:
                nfe_item = db.query(NfeItem).filter(NfeItem.id == c["nfe_item_id"]).first()
                if nfe_item:
                    if (not prod.ncm or not str(prod.ncm).strip()) and nfe_item.ncm_xml and str(nfe_item.ncm_xml).strip():
                        prod.ncm = str(nfe_item.ncm_xml).strip()[:10]
                    if (not prod.cfop_padrao or not str(prod.cfop_padrao).strip()) and nfe_item.cfop_xml and str(nfe_item.cfop_xml).strip():
                        prod.cfop_padrao = str(nfe_item.cfop_xml).strip()[:10]
                    if getattr(nfe_item, "cest_xml", None) and str(getattr(nfe_item, "cest_xml", "") or "").strip() and (not getattr(prod, "cest", None) or not str(getattr(prod, "cest", "") or "").strip()):
                        prod.cest = str(nfe_item.cest_xml).strip()[:10]
                    if getattr(nfe_item, "extipi_xml", None) and str(getattr(nfe_item, "extipi_xml", "") or "").strip() and (not getattr(prod, "extipi", None) or not str(getattr(prod, "extipi", "") or "").strip()):
                        prod.extipi = str(nfe_item.extipi_xml).strip()[:5]
                    if getattr(nfe_item, "orig_xml", None) is not None and getattr(prod, "origem_mercadoria", None) is None and 0 <= getattr(nfe_item, "orig_xml", -1) <= 8:
                        prod.origem_mercadoria = nfe_item.orig_xml
                db.flush()
            except Exception as e_fiscal:
                logger.warning(
                    "Bloco fiscal: erro ao preencher dados do produto (nfe_item_id=%s, produto_id=%s): %s",
                    c.get("nfe_item_id"),
                    prod.id,
                    e_fiscal,
                    exc_info=True,
                )
        except Exception as e:
            erros.append(f"Item {c.get('nfe_item_id')}: {e}")

    if erros:
        logger.error(
            "confirmar_e_lancar rollback nfe_id=%s: %s",
            nfe_id,
            erros,
        )
        db.rollback()
        return 0, erros

    doc.status = "CONCILIADO"
    db.commit()
    return count, []


def vincular_item(
    db: Session,
    nfe_item_id: int,
    produto_cliente_id: int,
    *,
    nfe_documento_id: Optional[int] = None,
    atualizar_mapa: bool = True,
) -> Optional[NfeItem]:
    """
    Vincula um item da NF-e a um produto interno e opcionalmente atualiza o mapa produto_fornecedor.
    """
    item = db.query(NfeItem).filter(NfeItem.id == nfe_item_id).first()
    if not item:
        return None
    doc = item.nfe_documento if hasattr(item, "nfe_documento") else None
    if not doc:
        doc = db.query(NfeDocumento).filter(NfeDocumento.id == item.nfe_id).first()
    if nfe_documento_id is not None and doc and doc.id != nfe_documento_id:
        return None
    item.produto_cliente_id = produto_cliente_id
    item.conciliar_status = "VINCULADO"
    if not item.fornecedor_id and doc:
        item.fornecedor_id = doc.emitente_fornecedor_id
    prod = db.query(ProdutoCliente).filter(ProdutoCliente.id == produto_cliente_id).first()
    if prod:
        # Unidade do XML no produto (estoque)
        if item.ucom_xml and (item.ucom_xml or "").strip():
            prod.unidade_medida = (item.ucom_xml or "").strip()[:20] or prod.unidade_medida
        # Dados fiscais do XML no produto quando ainda vazios (rastreio e emissão NF)
        if (not prod.ncm or not str(prod.ncm).strip()) and item.ncm_xml and str(item.ncm_xml).strip():
            prod.ncm = str(item.ncm_xml).strip()[:10]
        if (not prod.cfop_padrao or not str(prod.cfop_padrao).strip()) and item.cfop_xml and str(item.cfop_xml).strip():
            prod.cfop_padrao = str(item.cfop_xml).strip()[:10]
        if getattr(item, "cest_xml", None) and str(item.cest_xml).strip() and (not getattr(prod, "cest", None) or not str(prod.cest).strip()):
            prod.cest = str(item.cest_xml).strip()[:10]
        if getattr(item, "extipi_xml", None) and str(item.extipi_xml).strip() and (not getattr(prod, "extipi", None) or not str(prod.extipi).strip()):
            prod.extipi = str(item.extipi_xml).strip()[:5]
        if getattr(item, "orig_xml", None) is not None and getattr(prod, "origem_mercadoria", None) is None:
            o = item.orig_xml
            if 0 <= o <= 8:
                prod.origem_mercadoria = o
        # EAN do XML como código de barras do produto (se válido e ainda não existir)
        ean = (item.ean_xml or "").strip()
        if ean and ean not in ("0000000000000", "SEM GTIN") and len(ean) <= 50:
            existente_global = db.query(CodigoBarrasCliente).filter(CodigoBarrasCliente.codigo_barras == ean).first()
            if not existente_global:
                existente_prod = db.query(CodigoBarrasCliente).filter(
                    CodigoBarrasCliente.produto_cliente_id == produto_cliente_id,
                    CodigoBarrasCliente.codigo_barras == ean,
                ).first()
                if not existente_prod:
                    ja_tem = db.query(CodigoBarrasCliente).filter(CodigoBarrasCliente.produto_cliente_id == produto_cliente_id).first()
                    db.add(CodigoBarrasCliente(produto_cliente_id=produto_cliente_id, codigo_barras=ean[:50], principal=ja_tem is None))
    if atualizar_mapa and doc and item.fornecedor_id and item.cprod_xml:
        # Criar ou atualizar produtos_fornecedor
        pf = db.query(ProdutoFornecedor).filter(
            ProdutoFornecedor.fornecedor_cliente_id == item.fornecedor_id,
            ProdutoFornecedor.codigo_fornecedor == item.cprod_xml.strip(),
        ).first()
        if pf:
            pf.produto_cliente_id = produto_cliente_id
            pf.xprod_amostra = (item.xprod_xml or "")[:500]
            pf.ean_amostra = (item.ean_xml or "")[:14]
            pf.ucom_amostra = (item.ucom_xml or "")[:10]
            pf.ativo = True
        else:
            pf = ProdutoFornecedor(
                fornecedor_cliente_id=item.fornecedor_id,
                produto_cliente_id=produto_cliente_id,
                codigo_fornecedor=item.cprod_xml.strip(),
                xprod_amostra=(item.xprod_xml or "")[:500],
                ean_amostra=(item.ean_xml or "")[:14],
                ucom_amostra=(item.ucom_xml or "")[:10],
                fator_conversao=Decimal("1"),
                ativo=True,
            )
            db.add(pf)
    db.flush()
    return item
