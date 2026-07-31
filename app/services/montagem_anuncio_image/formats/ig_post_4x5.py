# PDV Ibix — Criativo ig_post_4x5 (1080×1350).
"""Módulo isolado: correções deste formato NÃO devem alterar outros formats/*.

Layout: a imagem 1080×1350 É o card geral (full-bleed). Os dois cards brancos
dentro são responsivos — sem margem externa / letterbox para “completar”.
Foto em contain (inteira, sem corte).
"""
from __future__ import annotations

from PIL import Image, ImageDraw

from app.services.montagem_anuncio_image.primitives import (
    DEFAULT_ACTION,
    DEFAULT_FRETE_BG,
    DEFAULT_FRETE_FG,
    DEFAULT_GEO_BG,
    DEFAULT_MUTED,
    DEFAULT_STOCK_BG,
    DEFAULT_STOCK_FG,
    DEFAULT_TEXT,
    CreativeBuildError,
    CreativeData,
    assert_source_resolution,
    domain_display,
    draw_pill,
    effective_price,
    encode_jpeg,
    fit_photo,
    fit_text,
    fmt_preco,
    hex_to_rgb,
    load_font,
    new_white_card,
    open_product_image,
    paste_mascote,
    paste_rounded,
    text_height,
    text_width,
)

FORMAT_KEY = "ig_post_4x5"
CANVAS_W = 1080
CANVAS_H = 1350
FILENAME = "ig-post-1080x1350.jpg"

# --- Quality / layout deste modelo (locais) ---
JPEG_QUALITY = 95
JPEG_SUBSAMPLING = 0
PHOTO_FIT = "contain"  # foto inteira no slot, sem corte
MIN_SOURCE_COVERAGE = 0.32
MIN_SOURCE_SIDE_PX = 280
PHOTO_MAX_H_RATIO = 1.0
INNER_PAD = 28
CARD_GAP = 14
CARD_RADIUS = 26
TITLE_MAX_LINES = 3
TITLE_SIZE = 38
BG = (246, 237, 228)


def _measure_product_body_h(
    data: CreativeData,
    width: int,
    *,
    title_max_lines: int,
    title_size: int,
    pad: int,
) -> int:
    probe = new_white_card(width, 400)
    draw = ImageDraw.Draw(probe)
    inner = pad
    cw = width - inner * 2
    cy = 22
    lines, font_t, line_h = fit_text(
        draw, data.titulo, "bold", cw, title_max_lines, title_size, size_min=20
    )
    cy += line_h * max(1, len(lines)) + 12
    font_badge = load_font("semibold", max(18, title_size // 2))
    _, ph = draw_pill(
        draw,
        inner,
        cy,
        data.badge_estoque,
        font_badge,
        DEFAULT_STOCK_FG,
        DEFAULT_STOCK_BG,
        (220, 170, 120),
    )
    cy += ph + 14
    old_price, eff = effective_price(data)
    if old_price is not None:
        font_old = load_font("regular", max(22, title_size - 12))
        oh = text_height(draw, fmt_preco(old_price), font_old)
        cy += oh + 4
    font_price = load_font("bold", max(40, title_size + 12))
    cy += text_height(draw, fmt_preco(eff), font_price) + pad
    return cy


def _draw_product_card(
    data: CreativeData,
    width: int,
    *,
    target_h: int,
    title_max_lines: int,
    title_size: int,
    pad: int = 24,
) -> Image.Image:
    action = hex_to_rgb(data.cor_primaria, DEFAULT_ACTION)
    body_h = _measure_product_body_h(
        data, width, title_max_lines=title_max_lines, title_size=title_size, pad=pad
    )
    photo_cap = max(260, int(width * PHOTO_MAX_H_RATIO))
    photo_h = min(photo_cap, max(260, target_h - body_h))
    if photo_h < 260 and title_size > 26:
        title_size = max(26, title_size - 6)
        body_h = _measure_product_body_h(
            data, width, title_max_lines=title_max_lines, title_size=title_size, pad=pad
        )
        photo_h = min(photo_cap, max(200, target_h - body_h))

    card = new_white_card(width, target_h)
    draw = ImageDraw.Draw(card)

    src = open_product_image(data)
    assert_source_resolution(
        src,
        width,
        photo_h,
        min_source_coverage=MIN_SOURCE_COVERAGE,
        min_source_side_px=MIN_SOURCE_SIDE_PX,
    )
    photo = fit_photo(src, width, photo_h, mode=PHOTO_FIT)
    card.paste(photo, (0, 0))

    inner = pad
    cw = width - inner * 2
    cy = photo_h + 18

    lines, font_t, line_h = fit_text(
        draw, data.titulo, "bold", cw, title_max_lines, title_size, size_min=18
    )
    for ln in lines:
        draw.text((inner, cy), ln, font=font_t, fill=DEFAULT_TEXT)
        cy += line_h
    cy += 10

    font_badge = load_font("semibold", max(16, title_size // 2))
    _, ph = draw_pill(
        draw,
        inner,
        cy,
        data.badge_estoque,
        font_badge,
        DEFAULT_STOCK_FG,
        DEFAULT_STOCK_BG,
        (220, 170, 120),
    )
    cy += ph + 12

    old_price, eff = effective_price(data)
    if old_price is not None:
        font_old = load_font("regular", max(20, title_size - 12))
        old_txt = fmt_preco(old_price)
        draw.text((inner, cy), old_txt, font=font_old, fill=DEFAULT_MUTED)
        ow = text_width(draw, old_txt, font_old)
        oh = text_height(draw, old_txt, font_old)
        mid = cy + oh // 2 + 2
        draw.line((inner, mid, inner + ow, mid), fill=DEFAULT_MUTED, width=2)
        cy += oh + 4
    font_price = load_font("bold", max(36, title_size + 10))
    price_txt = fmt_preco(eff)
    draw.text((inner, cy), price_txt, font=font_price, fill=action)
    return card


def _draw_footer_card(
    data: CreativeData,
    width: int,
    *,
    pad: int = 24,
    badge_size: int = 18,
    site_size: int = 28,
    mascote_box: tuple[int, int] = (140, 96),
) -> Image.Image:
    action = hex_to_rgb(data.cor_primaria, DEFAULT_ACTION)
    if not (data.cidade_uf or "").strip():
        raise CreativeBuildError("Cidade/UF da loja ausente para o criativo.")

    mw, mh = mascote_box
    probe = new_white_card(width, 400)
    pdraw = ImageDraw.Draw(probe)
    inner = pad
    cy = pad

    font_site = load_font("bold", site_size)
    site = domain_display(data.dominio_site)
    cy += text_height(pdraw, site, font_site) + 12

    font_badge = load_font("semibold", badge_size)
    geo_txt = f"Apenas em {data.cidade_uf.strip()}"
    _, gh = draw_pill(
        pdraw, inner, cy, geo_txt, font_badge, action, DEFAULT_GEO_BG, (160, 180, 140)
    )
    cy += gh + 8

    fw, fh = draw_pill(
        pdraw,
        inner,
        cy,
        data.badge_frete,
        font_badge,
        DEFAULT_FRETE_FG,
        DEFAULT_FRETE_BG,
        (220, 170, 120),
    )
    cy += fh + 8
    _, eh = draw_pill(
        pdraw,
        inner,
        cy,
        data.badge_escolha,
        font_badge,
        DEFAULT_TEXT,
        (250, 250, 250),
        (210, 210, 210),
    )
    cy += eh + pad
    final_h = max(cy, pad + mh + pad)

    card = new_white_card(width, final_h)
    draw = ImageDraw.Draw(card)
    cy = pad
    draw.text((inner, cy), site, font=font_site, fill=action)
    cy += text_height(draw, site, font_site) + 12
    _, gh = draw_pill(
        draw, inner, cy, geo_txt, font_badge, action, DEFAULT_GEO_BG, (160, 180, 140)
    )
    cy += gh + 8
    fw, fh = draw_pill(
        draw,
        inner,
        cy,
        data.badge_frete,
        font_badge,
        DEFAULT_FRETE_FG,
        DEFAULT_FRETE_BG,
        (220, 170, 120),
    )
    font_ou = load_font("semibold", max(14, badge_size - 2))
    ou = "ou"
    ou_h = text_height(draw, ou, font_ou)
    draw.text(
        (inner + fw + 10, cy + (fh - ou_h) // 2),
        ou,
        font=font_ou,
        fill=DEFAULT_MUTED,
    )
    cy += fh + 8
    draw_pill(
        draw,
        inner,
        cy,
        data.badge_escolha,
        font_badge,
        DEFAULT_TEXT,
        (250, 250, 250),
        (210, 210, 210),
    )
    paste_mascote(card, (width - pad - mw, final_h - pad - mh, mw, mh))
    return card


def _draw_canvas(data: CreativeData) -> Image.Image:
    """Canvas 1080×1350 = card geral full-bleed; dois cards internos responsivos."""
    canvas = Image.new("RGB", (CANVAS_W, CANVAS_H), BG)
    stack_w = CANVAS_W - INNER_PAD * 2
    avail_h = CANVAS_H - INNER_PAD * 2

    footer = _draw_footer_card(
        data,
        stack_w,
        pad=24,
        badge_size=max(15, TITLE_SIZE // 2 - 1),
        site_size=max(26, TITLE_SIZE - 8),
        mascote_box=(140, 96),
    )

    product_target_h = avail_h - CARD_GAP - footer.size[1]
    if product_target_h < 360:
        raise CreativeBuildError(
            f"Espaço do card de produto insuficiente ({product_target_h}px) no Post 4:5."
        )

    product = _draw_product_card(
        data,
        stack_w,
        target_h=product_target_h,
        title_max_lines=TITLE_MAX_LINES,
        title_size=TITLE_SIZE,
        pad=24,
    )

    paste_rounded(canvas, (INNER_PAD, INNER_PAD), product, radius=CARD_RADIUS)
    paste_rounded(
        canvas,
        (INNER_PAD, INNER_PAD + product.size[1] + CARD_GAP),
        footer,
        radius=CARD_RADIUS,
    )
    return canvas


def render_jpeg(data: CreativeData) -> bytes:
    img = _draw_canvas(data)
    if img.size != (CANVAS_W, CANVAS_H):
        raise CreativeBuildError(
            f"Dimensão gerada {img.size} difere do esperado ({CANVAS_W}, {CANVAS_H})."
        )
    return encode_jpeg(img, quality=JPEG_QUALITY, subsampling=JPEG_SUBSAMPLING)
