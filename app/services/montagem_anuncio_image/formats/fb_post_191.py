# PDV Ibix — Criativo fb_post_191 (1200×630).
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

FORMAT_KEY = "fb_post_191"
CANVAS_W = 1200
CANVAS_H = 630
FILENAME = "fb-post-1200x630.jpg"

JPEG_QUALITY = 95
JPEG_SUBSAMPLING = 0
PHOTO_FIT = "contain"
MIN_SOURCE_COVERAGE = 0.45
MIN_SOURCE_SIDE_PX = 280
BG = (246, 237, 228)


def _draw_canvas(data: CreativeData) -> Image.Image:
    w, h = CANVAS_W, CANVAS_H
    action = hex_to_rgb(data.cor_primaria, DEFAULT_ACTION)
    canvas = Image.new("RGB", (w, h), BG)

    outer_pad = 24
    outer_w, outer_h = w - outer_pad * 2, h - outer_pad * 2
    outer = Image.new("RGB", (outer_w, outer_h), BG)
    inner_pad = 18
    gap = 14
    stack_h = outer_h - inner_pad * 2
    photo_w = int((outer_w - inner_pad * 2 - gap) * 0.46)
    right_w = outer_w - inner_pad * 2 - gap - photo_w

    photo_card = new_white_card(photo_w, stack_h)
    src = open_product_image(data)
    assert_source_resolution(
        src,
        photo_w - 4,
        stack_h - 4,
        min_source_coverage=MIN_SOURCE_COVERAGE,
        min_source_side_px=MIN_SOURCE_SIDE_PX,
    )
    photo = fit_photo(src, photo_w, stack_h, mode=PHOTO_FIT)
    photo_card.paste(photo, (0, 0))

    info = new_white_card(right_w, stack_h)
    idraw = ImageDraw.Draw(info)
    pad = 22
    cw = right_w - pad * 2 - 100
    cy = pad

    lines, font_t, line_h = fit_text(idraw, data.titulo, "bold", cw, 2, 28, size_min=16)
    for ln in lines:
        idraw.text((pad, cy), ln, font=font_t, fill=DEFAULT_TEXT)
        cy += line_h
    cy += 8

    font_badge = load_font("semibold", 15)
    _, ph = draw_pill(
        idraw,
        pad,
        cy,
        data.badge_estoque,
        font_badge,
        DEFAULT_STOCK_FG,
        DEFAULT_STOCK_BG,
        (220, 170, 120),
        pad_x=10,
        pad_y=5,
    )
    cy += ph + 10

    old_price, eff = effective_price(data)
    if old_price is not None:
        font_old = load_font("regular", 18)
        old_txt = fmt_preco(old_price)
        idraw.text((pad, cy), old_txt, font=font_old, fill=DEFAULT_MUTED)
        ow = text_width(idraw, old_txt, font_old)
        oh = text_height(idraw, old_txt, font_old)
        idraw.line((pad, cy + oh // 2 + 2, pad + ow, cy + oh // 2 + 2), fill=DEFAULT_MUTED, width=2)
        cy += oh + 4
    font_price = load_font("bold", 40)
    idraw.text((pad, cy), fmt_preco(eff), font=font_price, fill=action)
    cy += text_height(idraw, fmt_preco(eff), font_price) + 14

    site = domain_display(data.dominio_site)
    font_site = load_font("bold", 22)
    idraw.text((pad, cy), site, font=font_site, fill=action)
    cy += text_height(idraw, site, font_site) + 10

    if not (data.cidade_uf or "").strip():
        raise CreativeBuildError("Cidade/UF da loja ausente para o criativo.")
    geo_txt = f"Apenas em {data.cidade_uf.strip()}"
    _, gh = draw_pill(
        idraw, pad, cy, geo_txt, font_badge, action, DEFAULT_GEO_BG, (160, 180, 140), pad_x=10, pad_y=5
    )
    cy += gh + 8
    draw_pill(
        idraw,
        pad,
        cy,
        data.badge_frete,
        font_badge,
        DEFAULT_FRETE_FG,
        DEFAULT_FRETE_BG,
        (220, 170, 120),
        pad_x=10,
        pad_y=5,
    )
    paste_mascote(info, (right_w - 130, stack_h - 120, 110, 90))

    paste_rounded(outer, (inner_pad, inner_pad), photo_card, radius=22)
    paste_rounded(outer, (inner_pad + photo_w + gap, inner_pad), info, radius=22)
    paste_rounded(canvas, (outer_pad, outer_pad), outer, radius=28, border_w=3)
    return canvas


def render_jpeg(data: CreativeData) -> bytes:
    img = _draw_canvas(data)
    if img.size != (CANVAS_W, CANVAS_H):
        raise CreativeBuildError(
            f"Dimensão gerada {img.size} difere do esperado ({CANVAS_W}, {CANVAS_H})."
        )
    return encode_jpeg(img, quality=JPEG_QUALITY, subsampling=JPEG_SUBSAMPLING)
