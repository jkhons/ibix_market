# PDV Ibix — Primitivos Pillow para criativos (sem composição de layout).
"""Utilitários puros: dados, fontes, fit de imagem, texto, pills.

Layout de cada formato vive em formats/*.py — não colocar composição aqui.
"""
from __future__ import annotations

import io
import logging
import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional
from urllib.parse import urlparse

import httpx
from PIL import Image, ImageDraw, ImageFont, ImageOps

logger = logging.getLogger(__name__)

_STATIC_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "static")
)
_FONTS_DIR = os.path.join(_STATIC_ROOT, "fonts")
_MASCOTE_PATH = os.path.join(_STATIC_ROOT, "img", "montagem_carrinho.png")

# Fallback de cor só quando a marca não informa (não é layout de formato).
DEFAULT_ACTION = (92, 110, 74)
DEFAULT_SURFACE = (255, 255, 255)
DEFAULT_TEXT = (45, 45, 45)
DEFAULT_MUTED = (110, 110, 110)
DEFAULT_STOCK_FG = (139, 77, 31)
DEFAULT_STOCK_BG = (252, 236, 220)
DEFAULT_GEO_BG = (232, 238, 226)
DEFAULT_FRETE_FG = (168, 93, 40)
DEFAULT_FRETE_BG = (252, 236, 220)
DEFAULT_BORDER = (214, 198, 178)


@dataclass(frozen=True)
class CreativeData:
    titulo: str
    preco_original: float
    preco_promocional: Optional[float]
    imagem_bytes: bytes
    marca_nome: str
    dominio_site: str
    cidade_uf: str
    cor_primaria: str
    cor_secundaria: str
    badge_estoque: str = "Enquanto durarem os estoques"
    badge_frete: str = "Receba em instantes"
    badge_escolha: str = "Escolha como receber"


class SourceImageTooSmallError(ValueError):
    """Foto de origem insuficiente para o slot do formato."""


class CreativeBuildError(ValueError):
    """Falha ao montar o criativo (dados ou assets)."""


def hex_to_rgb(hex_color: str, fallback: tuple[int, int, int]) -> tuple[int, int, int]:
    raw = (hex_color or "").strip().lstrip("#")
    if len(raw) == 3:
        raw = "".join(c * 2 for c in raw)
    if len(raw) != 6:
        return fallback
    try:
        return (int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16))
    except ValueError:
        return fallback


@lru_cache(maxsize=16)
def _load_font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    names = {
        "regular": "Poppins-Regular.ttf",
        "semibold": "Poppins-SemiBold.ttf",
        "bold": "Poppins-Bold.ttf",
    }
    path = os.path.join(_FONTS_DIR, names.get(weight, names["regular"]))
    if not os.path.isfile(path):
        raise CreativeBuildError(
            f"Fonte ausente: {path}. Inclua Poppins TTF em app/static/fonts/."
        )
    return ImageFont.truetype(path, size)


def load_font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    return _load_font(weight, int(size))


def cover_crop(img: Image.Image, box_w: int, box_h: int) -> Image.Image:
    if box_w < 1 or box_h < 1:
        raise CreativeBuildError("Dimensões de crop inválidas.")
    src = img.convert("RGB")
    return ImageOps.fit(src, (box_w, box_h), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))


def contain_fit(
    img: Image.Image,
    box_w: int,
    box_h: int,
    *,
    bg: tuple[int, int, int] = (236, 236, 236),
) -> Image.Image:
    if box_w < 1 or box_h < 1:
        raise CreativeBuildError("Dimensões de encaixe inválidas.")
    src = img.convert("RGB")
    iw, ih = src.size
    if iw < 1 or ih < 1:
        raise CreativeBuildError("Imagem de produto sem dimensões válidas.")
    scale = min(box_w / iw, box_h / ih)
    nw = max(1, int(round(iw * scale)))
    nh = max(1, int(round(ih * scale)))
    resized = src.resize((nw, nh), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (box_w, box_h), bg)
    canvas.paste(resized, ((box_w - nw) // 2, (box_h - nh) // 2))
    return canvas


def text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    return max(0, bbox[2] - bbox[0])


def text_height(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    return max(0, bbox[3] - bbox[1])


def wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    max_w: int,
) -> list[str]:
    words = (text or "").strip().split()
    if not words:
        return []
    lines: list[str] = []
    cur = words[0]
    for w in words[1:]:
        trial = f"{cur} {w}"
        if text_width(draw, trial, font) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def fit_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    weight: str,
    max_w: int,
    max_lines: int,
    size_max: int,
    size_min: int = 18,
) -> tuple[list[str], ImageFont.FreeTypeFont, int]:
    size = size_max
    while size >= size_min:
        font = load_font(weight, size)
        lines = wrap_text(draw, text, font, max_w)
        if len(lines) <= max_lines:
            if all(text_width(draw, ln, font) <= max_w for ln in lines):
                line_h = text_height(draw, "Áy", font) + max(4, size // 6)
                return lines, font, line_h
        size -= 2
    font = load_font(weight, size_min)
    lines = wrap_text(draw, text, font, max_w)[:max_lines]
    if len(wrap_text(draw, text, font, max_w)) > max_lines and lines:
        last = lines[-1]
        while last and text_width(draw, last + "…", font) > max_w:
            last = last[:-1]
        lines[-1] = (last.rstrip() + "…") if last else "…"
    line_h = text_height(draw, "Áy", font) + max(4, size_min // 6)
    return lines, font, line_h


def draw_rounded_rect(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int, int, int],
    radius: int,
    fill: tuple[int, int, int],
    outline: Optional[tuple[int, int, int]] = None,
    width: int = 1,
) -> None:
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def draw_pill(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    text: str,
    font: ImageFont.ImageFont,
    fg: tuple[int, int, int],
    bg: tuple[int, int, int],
    border: tuple[int, int, int],
    pad_x: int = 14,
    pad_y: int = 8,
) -> tuple[int, int]:
    tw = text_width(draw, text, font)
    th = text_height(draw, text, font)
    w = tw + pad_x * 2
    h = th + pad_y * 2
    draw_rounded_rect(draw, (x, y, x + w, y + h), radius=h // 2, fill=bg, outline=border, width=2)
    ty = y + (h - th) // 2 - 1
    draw.text((x + pad_x, ty), text, font=font, fill=fg)
    return w, h


def paste_mascote(canvas: Image.Image, box: tuple[int, int, int, int]) -> None:
    if not os.path.isfile(_MASCOTE_PATH):
        raise CreativeBuildError(f"Mascote ausente: {_MASCOTE_PATH}")
    x, y, max_w, max_h = box
    mascote = Image.open(_MASCOTE_PATH).convert("RGBA")
    mw, mh = mascote.size
    scale = min(max_w / mw, max_h / mh, 1.0)
    nw, nh = max(1, int(mw * scale)), max(1, int(mh * scale))
    mascote = mascote.resize((nw, nh), Image.Resampling.LANCZOS)
    px = x + max_w - nw
    py = y + max_h - nh
    canvas.paste(mascote, (px, py), mascote)


def resolve_source_bytes(url_or_path: str, *, public_base: str = "") -> bytes:
    raw = (url_or_path or "").strip()
    if not raw:
        raise CreativeBuildError("Anúncio sem URL de imagem.")

    if raw.startswith("http://") or raw.startswith("https://"):
        try:
            with httpx.Client(timeout=20.0, follow_redirects=True) as client:
                resp = client.get(raw)
                resp.raise_for_status()
                data = resp.content
        except Exception as exc:
            raise CreativeBuildError(f"Não foi possível baixar a imagem: {exc}") from exc
        if len(data) < 64:
            raise CreativeBuildError("Imagem baixada inválida ou vazia.")
        return data

    path = raw
    if path.startswith("/static/"):
        path = os.path.join(_STATIC_ROOT, path[len("/static/") :])
    elif path.startswith("static/"):
        path = os.path.join(_STATIC_ROOT, path[len("static/") :])
    elif public_base and path.startswith("/"):
        joined = public_base.rstrip("/") + path
        return resolve_source_bytes(joined)

    if os.path.isfile(path):
        with open(path, "rb") as f:
            data = f.read()
        if len(data) < 64:
            raise CreativeBuildError("Arquivo de imagem local inválido ou vazio.")
        return data

    if public_base and raw.startswith("/"):
        return resolve_source_bytes(public_base.rstrip("/") + raw)

    raise CreativeBuildError(f"Imagem não encontrada: {raw}")


def pick_best_image_url(urls: list[str]) -> str:
    for u in urls:
        u = (u or "").strip()
        if u:
            return u
    raise CreativeBuildError("Anúncio sem imagem para montagem.")


def assert_source_resolution(
    img: Image.Image,
    slot_w: int,
    slot_h: int,
    *,
    min_source_coverage: float,
    min_source_side_px: int,
) -> None:
    """Limiares vêm do Quality do módulo de formato (não há constantes globais)."""
    iw, ih = img.size
    if min(iw, ih) < min_source_side_px:
        raise SourceImageTooSmallError(
            f"Foto do produto muito pequena (origem {iw}×{ih}px). "
            f"Use uma foto com o menor lado de pelo menos {min_source_side_px}px."
        )
    scale = max(slot_w / max(iw, 1), slot_h / max(ih, 1))
    if scale > (1.0 / min_source_coverage) + 1e-6:
        min_side = int(min(slot_w, slot_h) * min_source_coverage)
        raise SourceImageTooSmallError(
            f"Foto do produto insuficiente para este formato "
            f"(origem {iw}×{ih}px; slot {slot_w}×{slot_h}px). "
            f"Use uma foto com o menor lado de pelo menos ~{min_side}px."
        )


def fmt_preco(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def effective_price(data: CreativeData) -> tuple[Optional[float], float]:
    po = float(data.preco_original or 0)
    pp = float(data.preco_promocional) if data.preco_promocional is not None else 0.0
    if pp > 0 and po > 0 and pp < po:
        return po, pp
    return None, po if po > 0 else pp


def open_product_image(data: CreativeData) -> Image.Image:
    try:
        img = Image.open(io.BytesIO(data.imagem_bytes))
        img.load()
    except Exception as exc:
        raise CreativeBuildError(f"Imagem do produto inválida: {exc}") from exc
    return img.convert("RGB")


def domain_display(dominio: str) -> str:
    d = (dominio or "").strip()
    if not d:
        raise CreativeBuildError("Domínio público da marca ausente (seo_base_url).")
    parsed = urlparse(d if "://" in d else f"https://{d}")
    host = (parsed.netloc or parsed.path or "").strip().lower()
    if host.startswith("www."):
        return host
    if host:
        return f"www.{host}" if not host.startswith("www.") else host
    raise CreativeBuildError("Domínio público da marca inválido.")


def paste_rounded(
    base: Image.Image,
    xy: tuple[int, int],
    card: Image.Image,
    radius: int,
    border: tuple[int, int, int] = DEFAULT_BORDER,
    border_w: int = 2,
) -> None:
    w, h = card.size
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), radius=radius, fill=255)
    base.paste(card, xy, mask)
    if border_w > 0:
        draw = ImageDraw.Draw(base)
        x0, y0 = xy
        draw.rounded_rectangle(
            (x0, y0, x0 + w - 1, y0 + h - 1),
            radius=radius,
            outline=border,
            width=border_w,
        )


def new_white_card(w: int, h: int) -> Image.Image:
    return Image.new("RGB", (w, h), DEFAULT_SURFACE)


def encode_jpeg(
    img: Image.Image,
    *,
    quality: int,
    subsampling: int = 0,
) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True, subsampling=subsampling)
    return buf.getvalue()


def fit_photo(
    img: Image.Image,
    box_w: int,
    box_h: int,
    *,
    mode: str,
    contain_bg: tuple[int, int, int] = (236, 236, 236),
) -> Image.Image:
    """mode: 'contain' | 'cover' — política definida pelo módulo de formato."""
    src = img.convert("RGB")
    iw, ih = src.size
    if iw < 1 or ih < 1 or box_w < 1 or box_h < 1:
        raise CreativeBuildError("Dimensões inválidas para encaixe da foto.")
    if mode == "cover":
        return cover_crop(src, box_w, box_h)
    if mode == "contain":
        return contain_fit(src, box_w, box_h, bg=contain_bg)
    raise CreativeBuildError(f"Modo de encaixe de foto inválido: {mode}")
