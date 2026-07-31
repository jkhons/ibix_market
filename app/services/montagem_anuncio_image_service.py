# PDV Ibix — Shim de compatibilidade.
"""Reexporta o pacote montagem_anuncio_image. Sem lógica de desenho neste arquivo."""
from app.services.montagem_anuncio_image import (
    FORMAT_SPECS,
    CreativeBuildError,
    CreativeData,
    FormatKey,
    SourceImageTooSmallError,
    filename_for,
    pick_best_image_url,
    render_format,
    resolve_source_bytes,
)

__all__ = [
    "FORMAT_SPECS",
    "FormatKey",
    "CreativeBuildError",
    "CreativeData",
    "SourceImageTooSmallError",
    "filename_for",
    "pick_best_image_url",
    "render_format",
    "resolve_source_bytes",
]
