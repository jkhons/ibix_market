# PDV Ibix — Criativo fb_stories (1080×1920).
"""Módulo isolado: correções deste formato NÃO devem alterar outros formats/*."""
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

FORMAT_KEY = "fb_stories"
CANVAS_W = 1080
CANVAS_H = 1920
FILENAME = "fb-stories-1080x1920.jpg"

# --- Quality / layout deste modelo (locais; não compartilhar com outros formatos) ---
JPEG_QUALITY = 95
JPEG_SUBSAMPLING = 0
PHOTO_FIT = "contain"  # contain | cover
MIN_SOURCE_COVERAGE = 0.45
MIN_SOURCE_SIDE_PX = 280
SAFE_TOP = 250
SAFE_BOTTOM = 250
PHOTO_RATIO = 0.38
TITLE_MAX_LINES = 3
TITLE_SIZE = 40
BG = (246, 237, 228)  # #F6EDE4 — fundo deste modelo


def _draw_product_card(
    data: CreativeData,
    width: int,
    *,
    photo_h: int,
    title_max_lines: int,
    title_size: int,
    pad: int = 28,
) -> Image.Image:
    action = hex_to_rgb(data.cor_primaria, DEFAULT_ACTION)
    body_estimate = 220 + title_max_lines * (title_size + 8)
    card_h = photo_h + pad + body_estimate
    card = new_white_card(width, card_h)
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
    cy = photo_h + 22

    lines, font_t, line_h = fit_text(
        draw, data.titulo, "bold", cw, title_max_lines, title_size, size_min=20
    )
    for ln in lines:
        draw.text((inner, cy), ln, font=font_t, fill=DEFAULT_TEXT)
        cy += line_h
    cy += 12

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
        old_txt = fmt_preco(old_price)
        draw.text((inner, cy), old_txt, font=font_old, fill=DEFAULT_MUTED)
        ow = text_width(draw, old_txt, font_old)
        oh = text_height(draw, old_txt, font_old)
        mid = cy + oh // 2 + 2
        draw.line((inner, mid, inner + ow, mid), fill=DEFAULT_MUTED, width=2)
        cy += oh + 4
    font_price = load_font("bold", max(40, title_size + 12))
    price_txt = fmt_preco(eff)
    draw.text((inner, cy), price_txt, font=font_price, fill=action)
    cy += text_height(draw, price_txt, font_price) + pad

    final_h = max(photo_h + 120, cy)
    if final_h < card_h:
        card = card.crop((0, 0, width, final_h))
    return card


def _draw_footer_card(
    data: CreativeData,
    width: int,
    *,
    pad: int = 28,
    badge_size: int = 20,
    site_size: int = 30,
    mascote_box: tuple[int, int] = (160, 110),
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
    cy += text_height(pdraw, site, font_site) + 14

    font_badge = load_font("semibold", badge_size)
    geo_txt = f"Apenas em {data.cidade_uf.strip()}"
    _, gh = draw_pill(
        pdraw, inner, cy, geo_txt, font_badge, action, DEFAULT_GEO_BG, (160, 180, 140)
    )
    cy += gh + 10

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
    cy += fh + 10
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
    cy += text_height(draw, site, font_site) + 14
    _, gh = draw_pill(
        draw, inner, cy, geo_txt, font_badge, action, DEFAULT_GEO_BG, (160, 180, 140)
    )
    cy += gh + 10
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
    font_ou = load_font("semibold", max(16, badge_size - 2))
    ou = "ou"
    ou_h = text_height(draw, ou, font_ou)
    draw.text(
        (inner + fw + 10, cy + (fh - ou_h) // 2),
        ou,
        font=font_ou,
        fill=DEFAULT_MUTED,
    )
    cy += fh + 10
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
    canvas_w, canvas_h = CANVAS_W, CANVAS_H
    canvas = Image.new("RGB", (canvas_w, canvas_h), BG)

    outer_pad = 40
    y0 = SAFE_TOP + outer_pad
    y1 = canvas_h - SAFE_BOTTOM - outer_pad
    avail_h = y1 - y0
    outer_w = canvas_w - outer_pad * 2

    outer = Image.new("RGB", (outer_w, avail_h), BG)
    outer_radius = 36
    inner_pad = 28
    gap = 14
    stack_w = outer_w - inner_pad * 2

    photo_h = min(stack_w, int(avail_h * PHOTO_RATIO))
    photo_h = max(260, min(photo_h, stack_w))

    product = _draw_product_card(
        data,
        stack_w,
        photo_h=photo_h,
        title_max_lines=TITLE_MAX_LINES,
        title_size=TITLE_SIZE,
        pad=28,
    )
    footer = _draw_footer_card(
        data,
        stack_w,
        pad=26,
        badge_size=max(16, TITLE_SIZE // 2 - 2),
        site_size=max(26, TITLE_SIZE - 8),
        mascote_box=(150, 100),
    )

    stack_h = product.size[1] + gap + footer.size[1]
    if stack_h + inner_pad * 2 > avail_h:
        overflow = stack_h + inner_pad * 2 - avail_h
        new_photo_h = max(220, photo_h - overflow - 20)
        if new_photo_h < photo_h:
            product = _draw_product_card(
                data,
                stack_w,
                photo_h=new_photo_h,
                title_max_lines=TITLE_MAX_LINES,
                title_size=max(26, TITLE_SIZE - 4),
                pad=22,
            )
            stack_h = product.size[1] + gap + footer.size[1]

    stack_top = max(inner_pad, (avail_h - stack_h) // 2)
    paste_rounded(outer, (inner_pad, stack_top), product, radius=28)
    paste_rounded(
        outer,
        (inner_pad, stack_top + product.size[1] + gap),
        footer,
        radius=28,
    )
    paste_rounded(canvas, (outer_pad, y0), outer, radius=outer_radius, border_w=3)
    return canvas


def render_jpeg(data: CreativeData) -> bytes:
    img = _draw_canvas(data)
    if img.size != (CANVAS_W, CANVAS_H):
        raise CreativeBuildError(
            f"Dimensão gerada {img.size} difere do esperado ({CANVAS_W}, {CANVAS_H})."
        )
    return encode_jpeg(img, quality=JPEG_QUALITY, subsampling=JPEG_SUBSAMPLING)
