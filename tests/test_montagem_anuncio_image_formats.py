# Testes: formatos de criativo montagem (isolamento + dimensões).
from __future__ import annotations

import ast
import io
from pathlib import Path

import pytest
from PIL import Image

from app.services.montagem_anuncio_image import (
    FORMAT_SPECS,
    CreativeBuildError,
    CreativeData,
    filename_for,
    render_format,
)
from app.services.montagem_anuncio_image.formats import (
    fb_post_191,
    fb_stories,
    ig_post_4x5,
    ig_stories,
)

FORMATS_DIR = Path(__file__).resolve().parents[1] / "app" / "services" / "montagem_anuncio_image" / "formats"


def _synthetic_jpeg(w: int = 800, h: int = 800) -> bytes:
    img = Image.new("RGB", (w, h), (200, 180, 160))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def _sample_data() -> CreativeData:
    return CreativeData(
        titulo="Produto teste montagem isolamento",
        preco_original=100.0,
        preco_promocional=80.0,
        imagem_bytes=_synthetic_jpeg(),
        marca_nome="Marca Teste",
        dominio_site="https://www.exemplo.com.br",
        cidade_uf="Lençóis Paulista - SP",
        cor_primaria="#5C6E4A",
        cor_secundaria="#F6EDE4",
    )


@pytest.mark.parametrize(
    "formato,expected",
    [
        ("ig_stories", (1080, 1920)),
        ("ig_post_4x5", (1080, 1350)),
        ("fb_stories", (1080, 1920)),
        ("fb_post_191", (1200, 630)),
    ],
)
def test_render_format_exact_dimensions(formato, expected):
    jpeg = render_format(formato, _sample_data())
    assert jpeg[:2] == b"\xff\xd8"
    out = Image.open(io.BytesIO(jpeg))
    assert out.size == expected
    assert filename_for(formato) == FORMAT_SPECS[formato]["fname"]


def test_ig_post_1x1_rejected():
    with pytest.raises(CreativeBuildError) as exc:
        render_format("ig_post_1x1", _sample_data())
    assert "ig_post_1x1" in str(exc.value) or "Formato inválido" in str(exc.value)


def test_format_specs_has_exactly_four_keys():
    assert set(FORMAT_SPECS.keys()) == {
        "ig_stories",
        "ig_post_4x5",
        "fb_stories",
        "fb_post_191",
    }
    assert "ig_post_1x1" not in FORMAT_SPECS


def test_module_canvas_constants_match_specs():
    assert (ig_stories.CANVAS_W, ig_stories.CANVAS_H) == (1080, 1920)
    assert (ig_post_4x5.CANVAS_W, ig_post_4x5.CANVAS_H) == (1080, 1350)
    assert (fb_stories.CANVAS_W, fb_stories.CANVAS_H) == (1080, 1920)
    assert (fb_post_191.CANVAS_W, fb_post_191.CANVAS_H) == (1200, 630)


def test_formats_do_not_import_sibling_formats():
    """Guarda de isolamento: formats/A não importa formats/B."""
    siblings = {"ig_stories", "ig_post_4x5", "fb_stories", "fb_post_191"}
    for path in FORMATS_DIR.glob("*.py"):
        if path.name == "__init__.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                mod = node.module
                if "montagem_anuncio_image.formats" in mod:
                    for alias in node.names:
                        imported.add(alias.name)
                # from . import x / from .ig_stories import ...
                if node.level and node.module:
                    imported.add(node.module.split(".")[0])
                elif node.level and not node.module:
                    for alias in node.names:
                        imported.add(alias.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if "formats." in (alias.name or ""):
                        imported.add(alias.name.rsplit(".", 1)[-1])
        self_key = path.stem
        bad = (imported & siblings) - {self_key}
        assert not bad, f"{path.name} importa formatos irmãos: {bad}"


def test_forbidden_shared_layout_symbols_absent():
    pkg = Path(__file__).resolve().parents[1] / "app" / "services" / "montagem_anuncio_image"
    forbidden = (
        "_draw_vertical_creative",
        "render_vert_tall",
        "render_portrait",
        "render_square",
        "render_landscape",
    )
    for path in pkg.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for name in forbidden:
            assert f"def {name}" not in text, f"{path} ainda define {name}"
