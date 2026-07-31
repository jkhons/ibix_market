# PDV Ibix — Pacote de criativos JPEG por formato (montagem de anúncio).
"""API pública estável. Implementação: primitives + formats/* + dispatch."""
from app.services.montagem_anuncio_image.dispatch import (
    FORMAT_SPECS,
    FormatKey,
    filename_for,
    render_format,
)
from app.services.montagem_anuncio_image.primitives import (
    CreativeBuildError,
    CreativeData,
    SourceImageTooSmallError,
    pick_best_image_url,
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
