# PDV Ibix — Marketing vitrine: config singleton + payload público
import logging
import random
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session, joinedload

from app.models import AnuncioPlataforma, LojaMarketplace, MarketingVitrineCard, MarketingVitrineConfig
from app.schemas.marketplace import AnuncioVitrineResponse

logger = logging.getLogger(__name__)

MAX_DESTAQUES = 8
MAX_OFERTAS_SEMANA = 8

CONFIG_ID = 1


def marketing_vitrine_template_fallback() -> Dict[str, Any]:
    """Fallback SSR (BD indisponível): só flags; títulos vêm do admin via API — aqui None até salvar no front."""
    return {
        "mostrar_hero_carrossel": True,
        "mostrar_secao_em_alta": True,
        "mostrar_secao_lojas_destaque": True,
        "ativo": True,
        "mostrar_todos_produtos": True,
        "limite_ofertas_semana": 8,
        "ofertas_cliente_ids": None,
        "ofertas_embaralhar": False,
        "ofertas_somente_desconto": True,
        "ofertas_semana": [],
        "titulo_ofertas_semana": None,
        "subtitulo_ofertas_semana": None,
        "titulo_faixa_destaques": None,
        "destaque_layout": "carrossel",
        "destaque_mostrar_setas": True,
        "destaque_scroll_snap": True,
        "destaque_embaralhar": False,
        "titulo_em_alta": None,
        "subtitulo_em_alta": None,
    }


def _marketing_schema_missing(exc: Exception) -> bool:
    msg = str(getattr(exc, "orig", None) or exc)
    return "marketing_vitrine" in msg and "does not exist" in msg


def vitrine_index_template_context(db: Session) -> Dict[str, Any]:
    """Flags, títulos e cards «Ofertas da semana» na home /loja (SSR) — mesmo payload de GET vitrine-home."""
    try:
        payload = build_public_payload(db)
    except ProgrammingError as e:
        if _marketing_schema_missing(e):
            logger.warning(
                "Marketing vitrine: schema ausente (rode alembic upgrade head). Home com defaults."
            )
            return marketing_vitrine_template_fallback()
        raise
    c = payload.get("config") or {}
    return {
        "mostrar_hero_carrossel": bool(c.get("mostrar_hero_carrossel", True)),
        "mostrar_secao_em_alta": bool(c.get("mostrar_secao_em_alta", True)),
        "mostrar_secao_lojas_destaque": bool(c.get("mostrar_secao_lojas_destaque", True)),
        "titulo_ofertas_semana": c.get("titulo_ofertas_semana"),
        "subtitulo_ofertas_semana": c.get("subtitulo_ofertas_semana"),
        "titulo_faixa_destaques": c.get("titulo_faixa_destaques"),
        "destaque_layout": c.get("destaque_layout") or "carrossel",
        "destaque_mostrar_setas": bool(c.get("destaque_mostrar_setas", True)),
        "destaque_scroll_snap": bool(c.get("destaque_scroll_snap", True)),
        "destaque_embaralhar": bool(c.get("destaque_embaralhar", False)),
        "titulo_em_alta": c.get("titulo_em_alta"),
        "subtitulo_em_alta": c.get("subtitulo_em_alta"),
        "ativo": bool(c.get("ativo", True)),
        "mostrar_todos_produtos": bool(c.get("mostrar_todos_produtos", True)),
        "limite_ofertas_semana": int(c.get("limite_ofertas_semana", MAX_OFERTAS_SEMANA)),
        "ofertas_cliente_ids": c.get("ofertas_cliente_ids"),
        "ofertas_embaralhar": bool(c.get("ofertas_embaralhar", False)),
        "ofertas_somente_desconto": bool(c.get("ofertas_somente_desconto", True)),
        "ofertas_semana": payload.get("ofertas_semana") or [],
    }


def _cliente_ids_from_cabecalho(card: MarketingVitrineCard) -> Optional[List[int]]:
    raw = getattr(card, "cliente_ids", None)
    if not raw or not isinstance(raw, list):
        return None
    out: List[int] = []
    seen = set()
    for x in raw:
        try:
            i = int(x)
        except (TypeError, ValueError):
            continue
        if i < 1 or i in seen:
            continue
        seen.add(i)
        out.append(i)
    return out or None


def config_para_payload_publico(
    cfg: MarketingVitrineConfig,
    cabecalho_visivel: Optional[MarketingVitrineCard] = None,
    filtros_ofertas: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Campos de config expostos na API pública.

    - Textos (título/subtítulo): só do cabeçalho «visível» (ativo + janela de datas); senão legado na config singleton.
    - Filtros (CAs, embaralhar, só desconto, limite): vêm de ``filtros_ofertas`` (merge de todos os cabeçalhos
      no bloco oferta_semana — ver ``_merge_filtros_cabecalhos_oferta_semana``).
    """
    limite_ofertas = getattr(cfg, "limite_ofertas_semana", MAX_OFERTAS_SEMANA) or MAX_OFERTAS_SEMANA
    titulo_os = cfg.titulo_ofertas_semana
    subtitulo_os = cfg.subtitulo_ofertas_semana
    cli_ids: Optional[List[int]] = None
    embaralhar = False
    somente_desc = True

    if cabecalho_visivel is not None:
        titulo_os = cabecalho_visivel.titulo
        subtitulo_os = cabecalho_visivel.descricao

    if filtros_ofertas is not None:
        cli_ids = filtros_ofertas.get("cliente_ids")
        le = filtros_ofertas.get("limite_exibicao")
        if le is not None and 1 <= int(le) <= 8:
            limite_ofertas = int(le)
        ev = filtros_ofertas.get("embaralhar_produtos")
        embaralhar = bool(ev) if ev is not None else False
        sv = filtros_ofertas.get("somente_com_desconto")
        somente_desc = bool(sv) if sv is not None else True
    return {
        "mostrar_todos_produtos": bool(cfg.mostrar_todos_produtos),
        "titulo_ofertas_semana": titulo_os,
        "subtitulo_ofertas_semana": subtitulo_os,
        "ativo": bool(cfg.ativo),
        "limite_ofertas_semana": int(limite_ofertas),
        "ofertas_cliente_ids": cli_ids,
        "ofertas_embaralhar": embaralhar,
        "ofertas_somente_desconto": somente_desc,
        "mostrar_hero_carrossel": bool(cfg.mostrar_hero_carrossel),
        "mostrar_secao_em_alta": bool(cfg.mostrar_secao_em_alta),
        "mostrar_secao_lojas_destaque": bool(cfg.mostrar_secao_lojas_destaque),
        "titulo_faixa_destaques": cfg.titulo_faixa_destaques,
        "destaque_layout": (getattr(cfg, "destaque_layout", None) or "carrossel"),
        "destaque_mostrar_setas": bool(getattr(cfg, "destaque_mostrar_setas", True)),
        "destaque_scroll_snap": bool(getattr(cfg, "destaque_scroll_snap", True)),
        "destaque_embaralhar": bool(getattr(cfg, "destaque_embaralhar", False)),
        "titulo_em_alta": cfg.titulo_em_alta,
        "subtitulo_em_alta": cfg.subtitulo_em_alta,
    }


def get_or_create_config_row(db: Session) -> MarketingVitrineConfig:
    row = db.query(MarketingVitrineConfig).filter(MarketingVitrineConfig.id == CONFIG_ID).first()
    if row:
        return row
    # Textos de título/subtítulo: preenchidos pelo Superadmin em /admin/marketing-vitrine (PATCH), não no backend.
    row = MarketingVitrineConfig(
        id=CONFIG_ID,
        mostrar_todos_produtos=True,
        ativo=True,
        mostrar_hero_carrossel=True,
        mostrar_secao_em_alta=True,
        mostrar_secao_lojas_destaque=True,
        limite_ofertas_semana=MAX_OFERTAS_SEMANA,
        destaque_layout="carrossel",
        destaque_mostrar_setas=True,
        destaque_scroll_snap=True,
        destaque_embaralhar=False,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def anuncio_e_publicavel(anuncio: Optional[AnuncioPlataforma]) -> bool:
    if not anuncio:
        return False
    if anuncio.status != "publicado":
        return False
    loja = anuncio.loja
    if not loja or loja.status != "ativo":
        return False
    return True


def anuncio_para_vitrine_response(anuncio: AnuncioPlataforma, db: Session) -> AnuncioVitrineResponse:
    from app.api.v1.loja import _imagens_anuncio_ou_fallback

    imgs = _imagens_anuncio_ou_fallback(anuncio, db)
    if not imgs:
        raise ValueError("Anúncio sem imagem válida para exibição na vitrine")
    loja = anuncio.loja
    frete_fmt = (
        (anuncio.formato_frete_produto if anuncio.frete_sobrescrever_loja else (loja.formato_frete if loja else None))
        or "sem_frete"
    )
    return AnuncioVitrineResponse(
        id=anuncio.id,
        titulo=anuncio.titulo,
        loja_id=anuncio.loja_id,
        preco_original=anuncio.preco_original,
        preco_promocional=anuncio.preco_promocional,
        imagens=imgs,
        og_image_url=(getattr(anuncio, "og_image_url", None) or "").strip() or None,
        slug_loja=loja.slug if loja else None,
        nome_loja=loja.nome_loja if loja else None,
        estoque_atual=anuncio.estoque_atual,
        status=anuncio.status,
        frete_formato_efetivo=frete_fmt,
        frete_origem_regra="produto" if anuncio.frete_sobrescrever_loja else "loja",
        frete_gratis=(frete_fmt == "gratis"),
    )


def validar_anuncio_vinculo(db: Session, anuncio_id: int) -> AnuncioPlataforma:
    anuncio = (
        db.query(AnuncioPlataforma)
        .options(joinedload(AnuncioPlataforma.loja))
        .filter(AnuncioPlataforma.id == anuncio_id)
        .first()
    )
    if not anuncio:
        raise ValueError("Anúncio não encontrado")
    if not anuncio_e_publicavel(anuncio):
        raise ValueError("Anúncio deve estar publicado e a loja ativa na vitrine")
    from app.api.v1.loja import _imagens_anuncio_ou_fallback

    imgs = _imagens_anuncio_ou_fallback(anuncio, db)
    if not imgs:
        raise ValueError("Anúncio sem imagem válida para a vitrine")
    return anuncio


def listar_anuncios_picklist_vitrine(
    db: Session,
    q: Optional[str],
    limit: int,
    cliente_ids: Optional[List[int]] = None,
    anuncio_ids: Optional[List[int]] = None,
    embaralhar: bool = False,
) -> List[Dict[str, Any]]:
    """Lista anúncios elegíveis para card «Anúncio» (publicado, loja ativa, com imagem). Usado pelo admin."""
    from app.api.v1.loja import _imagens_anuncio_ou_fallback

    query = (
        db.query(AnuncioPlataforma)
        .options(joinedload(AnuncioPlataforma.loja))
        .join(LojaMarketplace, AnuncioPlataforma.loja_id == LojaMarketplace.id)
        .filter(AnuncioPlataforma.status == "publicado")
        .filter(LojaMarketplace.status == "ativo")
    )
    cid_list: List[int] = []
    if cliente_ids:
        for cid in cliente_ids:
            try:
                i = int(cid)
            except (TypeError, ValueError):
                continue
            if i > 0 and i not in cid_list:
                cid_list.append(i)
    if cid_list:
        query = query.filter(LojaMarketplace.cliente_id.in_(cid_list))
    aid_list: List[int] = []
    if anuncio_ids:
        for aid in anuncio_ids:
            try:
                i = int(aid)
            except (TypeError, ValueError):
                continue
            if i > 0 and i not in aid_list:
                aid_list.append(i)
    if aid_list:
        query = query.filter(AnuncioPlataforma.id.in_(aid_list))
    if q and q.strip():
        for tok in [t for t in q.strip().split() if t][:12]:
            query = query.filter(AnuncioPlataforma.titulo.ilike(f"%{tok}%"))
    over = max(limit * 3, min(300, limit * 5))
    if embaralhar:
        rows = query.order_by(func.random()).limit(over).all()
    else:
        rows = query.order_by(AnuncioPlataforma.updated_at.desc()).limit(over).all()
    out: List[Dict[str, Any]] = []
    for anuncio in rows:
        if not anuncio_e_publicavel(anuncio):
            continue
        imgs = _imagens_anuncio_ou_fallback(anuncio, db)
        if not imgs:
            continue
        loja = anuncio.loja
        out.append(
            {
                "id": anuncio.id,
                "titulo": (anuncio.titulo or "").strip(),
                "nome_loja": (loja.nome_loja if loja else None) or "",
                "cliente_id": int(loja.cliente_id) if (loja and loja.cliente_id is not None) else None,
            }
        )
        if len(out) >= limit:
            break
    return out


def _agora_utc() -> datetime:
    return datetime.now(timezone.utc)


def _card_visivel_agora(card: MarketingVitrineCard, now: datetime) -> bool:
    if not card.ativo:
        return False
    if card.inicio_em and card.inicio_em > now:
        return False
    if card.fim_em and card.fim_em < now:
        return False
    return True


def _merge_filtros_cabecalhos_oferta_semana(db: Session) -> Optional[Dict[str, Any]]:
    """Une `cliente_ids` dos cards cabecalho_ofertas **ativos** do bloco oferta_semana.

    Só entram cards com ``ativo=True``; desativar o card no admin remove tenants/limite/flags
    da config pública (antes o merge ignorava ``ativo`` e a vitrine continuava com os parâmetros).

    Vários cabeçalhos ativos: união de tenants; limite/flags do cabeçalho de **maior ordem** com
    pelo menos um cliente (senão o de maior ordem entre os ativos).
    """
    cards = (
        db.query(MarketingVitrineCard)
        .filter(
            MarketingVitrineCard.tipo_bloco == "oferta_semana",
            MarketingVitrineCard.tipo_card == "cabecalho_ofertas",
            MarketingVitrineCard.ativo.is_(True),
        )
        .order_by(MarketingVitrineCard.ordem.asc(), MarketingVitrineCard.id.asc())
        .all()
    )
    if not cards:
        return None

    merged_ids: List[int] = []
    seen: set = set()
    for c in cards:
        part = _cliente_ids_from_cabecalho(c)
        if part:
            for i in part:
                if i not in seen:
                    seen.add(i)
                    merged_ids.append(i)

    ref: Optional[MarketingVitrineCard] = None
    for c in reversed(cards):
        if _cliente_ids_from_cabecalho(c):
            ref = c
            break
    if ref is None:
        ref = cards[-1]

    limite_raw = getattr(ref, "limite_exibicao", None)
    limite_i: Optional[int] = None
    if limite_raw is not None:
        try:
            li = int(limite_raw)
            if 1 <= li <= 8:
                limite_i = li
        except (TypeError, ValueError):
            pass

    ev = getattr(ref, "embaralhar_produtos", None)
    embaralhar = bool(ev) if ev is not None else False
    sv = getattr(ref, "somente_com_desconto", None)
    somente_desc = bool(sv) if sv is not None else True

    return {
        "cliente_ids": merged_ids if merged_ids else None,
        "limite_exibicao": limite_i,
        "embaralhar_produtos": embaralhar,
        "somente_com_desconto": somente_desc,
    }


def _primeiro_cabecalho_ofertas_visivel(db: Session, now: datetime) -> Optional[MarketingVitrineCard]:
    """Primeiro card «cabeçalho» do bloco oferta_semana (ordem crescente) visível agora. Textos da seção."""
    q = (
        db.query(MarketingVitrineCard)
        .filter(
            MarketingVitrineCard.tipo_bloco == "oferta_semana",
            MarketingVitrineCard.tipo_card == "cabecalho_ofertas",
        )
        .order_by(MarketingVitrineCard.ordem.asc(), MarketingVitrineCard.id.asc())
    )
    for card in q.all():
        if _card_visivel_agora(card, now):
            return card
    return None


def _anuncio_tem_preco_promocional_valido(anuncio: AnuncioPlataforma) -> bool:
    """Mesmo critério de GET /loja/anuncios?somente_promocao=true (preço promocional preenchido e > 0)."""
    pp = anuncio.preco_promocional
    if pp is None:
        return False
    try:
        return float(pp) > 0
    except (TypeError, ValueError):
        return False


def _card_para_item_publico(
    card: MarketingVitrineCard,
    db: Session,
    *,
    aplicar_somente_promocao: bool = False,
) -> Optional[Dict[str, Any]]:
    if card.tipo_card == "cabecalho_ofertas":
        return None
    if card.tipo_card == "livre":
        out: Dict[str, Any] = {
            "tipo_card": "livre",
            "card_id": card.id,
            "titulo": (card.titulo or "").strip(),
            "imagem_url": (card.imagem_url or "").strip(),
            "link_url": (card.link_url or "").strip(),
        }
        sub = (getattr(card, "descricao", None) or "").strip()
        if sub:
            out["descricao"] = sub
        return out
    if card.tipo_card == "anuncio" and card.anuncio_id:
        anuncio = (
            db.query(AnuncioPlataforma)
            .options(joinedload(AnuncioPlataforma.loja))
            .filter(AnuncioPlataforma.id == card.anuncio_id)
            .first()
        )
        if not anuncio_e_publicavel(anuncio):
            return None
        if aplicar_somente_promocao and not _anuncio_tem_preco_promocional_valido(anuncio):
            return None
        try:
            av = anuncio_para_vitrine_response(anuncio, db)
        except ValueError:
            return None
        return {
            "tipo_card": "anuncio",
            "card_id": card.id,
            "anuncio": av.model_dump(mode="json"),
        }
    return None


def _anuncio_ids_do_card(card: MarketingVitrineCard) -> List[int]:
    raw = getattr(card, "anuncio_ids", None)
    out: List[int] = []
    if isinstance(raw, list):
        for x in raw:
            try:
                i = int(x)
            except (TypeError, ValueError):
                continue
            if i > 0 and i not in out:
                out.append(i)
    if not out and getattr(card, "anuncio_id", None):
        try:
            i2 = int(card.anuncio_id)
            if i2 > 0:
                out.append(i2)
        except (TypeError, ValueError):
            pass
    return out


def _empty_public_payload(now: datetime) -> Dict[str, Any]:
    """Payload válido quando tabelas marketing ainda não existem (migração pendente)."""
    fb = marketing_vitrine_template_fallback()
    c = {
        "mostrar_todos_produtos": True,
        "titulo_ofertas_semana": fb["titulo_ofertas_semana"],
        "subtitulo_ofertas_semana": fb["subtitulo_ofertas_semana"],
        "ativo": True,
        "limite_ofertas_semana": fb["limite_ofertas_semana"],
        "ofertas_cliente_ids": fb["ofertas_cliente_ids"],
        "ofertas_embaralhar": fb["ofertas_embaralhar"],
        "ofertas_somente_desconto": fb["ofertas_somente_desconto"],
        "mostrar_hero_carrossel": fb["mostrar_hero_carrossel"],
        "mostrar_secao_em_alta": fb["mostrar_secao_em_alta"],
        "mostrar_secao_lojas_destaque": fb["mostrar_secao_lojas_destaque"],
        "titulo_faixa_destaques": fb["titulo_faixa_destaques"],
        "destaque_layout": fb.get("destaque_layout", "carrossel"),
        "destaque_mostrar_setas": fb.get("destaque_mostrar_setas", True),
        "destaque_scroll_snap": fb.get("destaque_scroll_snap", True),
        "destaque_embaralhar": fb.get("destaque_embaralhar", False),
        "titulo_em_alta": fb["titulo_em_alta"],
        "subtitulo_em_alta": fb["subtitulo_em_alta"],
    }
    return {
        "config": c,
        "destaques": [],
        "ofertas_semana": [],
        "generated_at": now.isoformat(),
    }


def build_public_payload(db: Session) -> Dict[str, Any]:
    now = _agora_utc()
    try:
        cfg = get_or_create_config_row(db)
        cab_visivel = _primeiro_cabecalho_ofertas_visivel(db, now)
        filtros_ofertas = _merge_filtros_cabecalhos_oferta_semana(db)
        if not cfg.ativo:
            c = config_para_payload_publico(cfg, cabecalho_visivel=cab_visivel, filtros_ofertas=filtros_ofertas)
            c["ativo"] = False
            return {
                "config": c,
                "destaques": [],
                "ofertas_semana": [],
                "generated_at": now.isoformat(),
            }

        q = (
            db.query(MarketingVitrineCard)
            .filter(MarketingVitrineCard.tipo_bloco == "destaque")
            .order_by(MarketingVitrineCard.ordem.asc(), MarketingVitrineCard.id.desc())
        )
        destaques: List[Dict[str, Any]] = []
        for card in q.all():
            if not _card_visivel_agora(card, now):
                continue
            if card.tipo_card == "anuncio":
                ids = _anuncio_ids_do_card(card)
                if ids:
                    for aid in ids:
                        shadow = MarketingVitrineCard(
                            tipo_bloco=card.tipo_bloco,
                            tipo_card="anuncio",
                            anuncio_id=aid,
                            ativo=card.ativo,
                            inicio_em=card.inicio_em,
                            fim_em=card.fim_em,
                        )
                        item = _card_para_item_publico(shadow, db)
                        if item:
                            destaques.append(item)
                        if len(destaques) >= MAX_DESTAQUES:
                            break
                else:
                    item = _card_para_item_publico(card, db)
                    if item:
                        destaques.append(item)
                if len(destaques) >= MAX_DESTAQUES:
                    break
            else:
                item = _card_para_item_publico(card, db)
                if item:
                    destaques.append(item)
                if len(destaques) >= MAX_DESTAQUES:
                    break

        if bool(getattr(cfg, "destaque_embaralhar", False)) and len(destaques) > 1:
            random.shuffle(destaques)

        q2 = (
            db.query(MarketingVitrineCard)
            .filter(MarketingVitrineCard.tipo_bloco == "oferta_semana")
            .order_by(MarketingVitrineCard.ordem.asc(), MarketingVitrineCard.id.desc())
        )
        ofertas: List[Dict[str, Any]] = []
        merged_cfg = config_para_payload_publico(cfg, cabecalho_visivel=cab_visivel, filtros_ofertas=filtros_ofertas)
        limite_ofertas = int(merged_cfg.get("limite_ofertas_semana", MAX_OFERTAS_SEMANA))
        somente_promo_ofertas = bool(merged_cfg.get("ofertas_somente_desconto", True))
        for card in q2.all():
            if card.tipo_card == "cabecalho_ofertas":
                continue
            if not _card_visivel_agora(card, now):
                continue
            if card.tipo_card == "anuncio":
                ids = _anuncio_ids_do_card(card)
                if ids:
                    for aid in ids:
                        shadow = MarketingVitrineCard(
                            tipo_bloco=card.tipo_bloco,
                            tipo_card="anuncio",
                            anuncio_id=aid,
                            ativo=card.ativo,
                            inicio_em=card.inicio_em,
                            fim_em=card.fim_em,
                        )
                        item = _card_para_item_publico(
                            shadow,
                            db,
                            aplicar_somente_promocao=somente_promo_ofertas,
                        )
                        if item:
                            ofertas.append(item)
                        if len(ofertas) >= limite_ofertas:
                            break
                else:
                    item = _card_para_item_publico(
                        card,
                        db,
                        aplicar_somente_promocao=somente_promo_ofertas,
                    )
                    if item:
                        ofertas.append(item)
                if len(ofertas) >= limite_ofertas:
                    break
            else:
                item = _card_para_item_publico(
                    card,
                    db,
                    aplicar_somente_promocao=somente_promo_ofertas,
                )
                if item:
                    ofertas.append(item)
                if len(ofertas) >= limite_ofertas:
                    break

        return {
            "config": merged_cfg,
            "destaques": destaques,
            "ofertas_semana": ofertas,
            "generated_at": now.isoformat(),
        }
    except ProgrammingError as e:
        if _marketing_schema_missing(e):
            logger.warning(
                "Marketing vitrine: schema ausente (rode alembic upgrade head). API vitrine-home degradada."
            )
            return _empty_public_payload(now)
        raise
