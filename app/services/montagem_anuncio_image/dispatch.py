# PDV Ibix — Dispatch de criativos por formato (sem lógica de desenho).
"""Roteia para formats/*.py. Catálogo sem layout genérico compartilhado."""
from __future__ import annotations

from typing import Callable, Literal

from app.services.montagem_anuncio_image.formats import (
    fb_post_191,
    fb_stories,
    ig_post_4x5,
    ig_stories,
)
from app.services.montagem_anuncio_image.primitives import CreativeBuildError, CreativeData

FormatKey = Literal[
    "ig_stories",
    "ig_post_4x5",
    "fb_stories",
    "fb_post_191",
]

_RENDERERS: dict[str, Callable[[CreativeData], bytes]] = {
    ig_stories.FORMAT_KEY: ig_stories.render_jpeg,
    ig_post_4x5.FORMAT_KEY: ig_post_4x5.render_jpeg,
    fb_stories.FORMAT_KEY: fb_stories.render_jpeg,
    fb_post_191.FORMAT_KEY: fb_post_191.render_jpeg,
}

FORMAT_SPECS: dict[str, dict] = {
    ig_stories.FORMAT_KEY: {
        "w": ig_stories.CANVAS_W,
        "h": ig_stories.CANVAS_H,
        "fname": ig_stories.FILENAME,
    },
    ig_post_4x5.FORMAT_KEY: {
        "w": ig_post_4x5.CANVAS_W,
        "h": ig_post_4x5.CANVAS_H,
        "fname": ig_post_4x5.FILENAME,
    },
    fb_stories.FORMAT_KEY: {
        "w": fb_stories.CANVAS_W,
        "h": fb_stories.CANVAS_H,
        "fname": fb_stories.FILENAME,
    },
    fb_post_191.FORMAT_KEY: {
        "w": fb_post_191.CANVAS_W,
        "h": fb_post_191.CANVAS_H,
        "fname": fb_post_191.FILENAME,
    },
}


def render_format(formato: FormatKey | str, data: CreativeData) -> bytes:
    """Renderiza o formato via módulo dedicado. Sem fallback para outro modelo."""
    renderer = _RENDERERS.get(formato)
    if renderer is None:
        raise CreativeBuildError(
            f"Formato inválido: {formato}. Use um de: {', '.join(FORMAT_SPECS)}."
        )
    return renderer(data)


def filename_for(formato: str) -> str:
    spec = FORMAT_SPECS.get(formato)
    if not spec:
        raise CreativeBuildError(f"Formato inválido: {formato}")
    return spec["fname"]
