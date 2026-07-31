# PDV Ibix — Montagem de anúncio: vídeo MP4 + imagem JPEG por formato (Superadmin).
import os
import shutil
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload
from starlette.background import BackgroundTask

from app.core.hardening import public_origin_from_request
from app.core.middleware import require_superadmin
from app.database.connection import get_db
from app.models import AnuncioPlataforma, Cliente, LojaMarketplace, Usuario
from app.services.brand_service import BrandContext
from app.services.montagem_anuncio_image_service import (
    FORMAT_SPECS,
    CreativeBuildError,
    CreativeData,
    SourceImageTooSmallError,
    filename_for,
    pick_best_image_url,
    render_format,
    resolve_source_bytes,
)
from app.services.montagem_anuncio_video_service import (
    ALLOWED_DURATION,
    MAX_SLIDES,
    build_montagem_video,
    build_montagem_video_multi,
    build_montagem_video_overlay,
    montagem_multi_temp_dir,
    montagem_video_temp_paths,
    validate_jpeg_upload,
)

router = APIRouter(prefix="/admin/montagem-anuncio", tags=["Admin Montagem Anúncio"])

FormatLiteral = Literal[
    "ig_stories",
    "ig_post_4x5",
    "fb_stories",
    "fb_post_191",
]


class MontagemImageRequest(BaseModel):
    anuncio_id: int = Field(..., ge=1)
    formato: FormatLiteral


def _cleanup_paths(*paths: str) -> None:
    for p in paths:
        if p and os.path.isfile(p):
            try:
                os.unlink(p)
            except OSError:
                pass


def _brand_from_request(request: Request) -> BrandContext:
    brand = getattr(request.state, "brand", None)
    if brand is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Contexto de marca ausente na requisição.",
        )
    return brand


def _cidade_uf(cli: Optional[Cliente]) -> str:
    if not cli:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Loja sem cadastro de Cliente (cidade/UF) para o criativo.",
        )
    cidade = (cli.cidade or "").strip()
    uf = (cli.uf or "").strip().upper()
    if not cidade:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cidade da loja ausente. Atualize o cadastro do estabelecimento.",
        )
    if uf:
        return f"{cidade} - {uf}" if " - " not in cidade else cidade
    return cidade


def _image_urls_for_anuncio(anuncio: AnuncioPlataforma, db: Session) -> list[str]:
    """Galeria completa (anúncio + produto) para montagem."""
    from app.api.v1.loja import _imagens_anuncio_completas

    return _imagens_anuncio_completas(anuncio, db)


@router.post("/image")
async def post_montagem_anuncio_image(
    body: MontagemImageRequest,
    request: Request,
    db: Session = Depends(get_db),
    _current_user: Usuario = Depends(require_superadmin()),
):
    """
    Gera JPEG do criativo no formato escolhido (Stories/Post IG/FB).
    Dimensões exatas; foto em cover sem distorção; erro 422 se a origem for pequena.
    """
    if body.formato not in FORMAT_SPECS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Formato inválido. Use: {', '.join(FORMAT_SPECS)}.",
        )

    anuncio = (
        db.query(AnuncioPlataforma)
        .options(
            joinedload(AnuncioPlataforma.loja).joinedload(LojaMarketplace.cliente),
            joinedload(AnuncioPlataforma.produto_cliente),
        )
        .filter(AnuncioPlataforma.id == body.anuncio_id)
        .first()
    )
    if not anuncio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Anúncio não encontrado.")
    if (anuncio.status or "").strip().lower() != "publicado":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Só é possível exportar anúncios com status publicado.",
        )

    brand = _brand_from_request(request)
    seo = (brand.seo_base_url or "").strip()
    if not seo:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Marca sem seo_base_url. Configure o domínio público da marca.",
        )

    loja = anuncio.loja
    cli = loja.cliente if loja else None
    if cli is None and loja is not None:
        cli = db.query(Cliente).filter(Cliente.id == loja.cliente_id).first()

    urls = _image_urls_for_anuncio(anuncio, db)
    try:
        best = pick_best_image_url(urls)
    except CreativeBuildError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    public_base = public_origin_from_request(request) or seo
    try:
        img_bytes = resolve_source_bytes(best, public_base=public_base)
    except CreativeBuildError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    po = float(anuncio.preco_original or 0)
    pp = float(anuncio.preco_promocional) if anuncio.preco_promocional is not None else None

    data = CreativeData(
        titulo=(anuncio.titulo or "").strip() or f"Anúncio #{anuncio.id}",
        preco_original=po,
        preco_promocional=pp,
        imagem_bytes=img_bytes,
        marca_nome=(brand.nome_exibicao or brand.nome_curto or "").strip(),
        dominio_site=seo,
        cidade_uf=_cidade_uf(cli),
        cor_primaria=(brand.cor_primaria or "").strip(),
        cor_secundaria=(brand.cor_secundaria or "").strip(),
    )
    if not data.marca_nome:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Marca sem nome de exibição.",
        )

    try:
        jpeg = render_format(body.formato, data)
    except SourceImageTooSmallError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except CreativeBuildError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha ao gerar criativo: {exc}",
        ) from exc

    fname = filename_for(body.formato)
    return Response(
        content=jpeg,
        media_type="image/jpeg",
        headers={
            "Content-Disposition": f'attachment; filename="{fname}"',
            "Cache-Control": "no-store",
        },
    )


@router.post("/video")
async def post_montagem_anuncio_video(
    imagens: List[UploadFile] = File(
        ...,
        description="JPEGs na ordem do carrossel. Modo card: criativo completo por slide. Modo overlay: só a foto pura do carrossel.",
    ),
    aspect: Literal["reels", "feed"] = Form(
        "reels",
        description="reels=1080×1920 (Stories/Reels); feed=1080×1080",
    ),
    duration_sec: int = Form(10, description="Duração em segundos (6, 10 ou 15)"),
    background: Optional[UploadFile] = File(
        None,
        description="Modo overlay: JPEG do card completo. Quando enviado junto com slot_x/y/w/h, só a foto troca; o card fica fixo.",
    ),
    slot_x: Optional[int] = Form(None, description="Modo overlay: X do slot da foto no background, em px."),
    slot_y: Optional[int] = Form(None, description="Modo overlay: Y do slot da foto no background, em px."),
    slot_w: Optional[int] = Form(None, description="Modo overlay: largura do slot da foto, em px."),
    slot_h: Optional[int] = Form(None, description="Modo overlay: altura do slot da foto, em px."),
    _current_user: Usuario = Depends(require_superadmin()),
):
    """
    - 1 imagem em `imagens`, sem background: modo zoom (Ken Burns + fade).
    - N imagens em `imagens`, sem background: modo card (todo o criativo desliza por slide).
    - N imagens em `imagens` + background + slot_*: modo overlay — só a foto do carrossel desliza,
      o resto do card (título, preço, badges, footer) fica fixo, como num clique no carrossel.
    """
    if duration_sec not in ALLOWED_DURATION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Duração inválida. Use uma de: {list(ALLOWED_DURATION)}.",
        )
    if not imagens:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Envie ao menos uma imagem (campo imagens).",
        )
    if len(imagens) > MAX_SLIDES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No máximo {MAX_SLIDES} imagens por vídeo.",
        )

    overlay_fields = (background, slot_x, slot_y, slot_w, slot_h)
    overlay_mode = all(v is not None for v in overlay_fields)
    if any(v is not None for v in overlay_fields) and not overlay_mode:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Modo overlay requer background, slot_x, slot_y, slot_w e slot_h juntos.",
        )
    if overlay_mode and len(imagens) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Modo overlay precisa de pelo menos 2 fotos do carrossel.",
        )

    raw_list: list[bytes] = []
    for uf in imagens:
        raw = await uf.read()
        validate_jpeg_upload(raw)
        raw_list.append(raw)

    bg_raw: bytes | None = None
    if overlay_mode and background is not None:
        bg_raw = await background.read()
        validate_jpeg_upload(bg_raw)

    path_in, path_out = montagem_video_temp_paths(".jpg")
    tmp_multi: str | None = None
    bg_path: str | None = None

    try:
        if overlay_mode and bg_raw is not None:
            _cleanup_paths(path_in)
            path_in = ""
            tmp_multi = montagem_multi_temp_dir()
            bg_path = os.path.join(tmp_multi, "background.jpg")
            with open(bg_path, "wb") as f:
                f.write(bg_raw)
            paths_jpg: list[str] = []
            for i, raw in enumerate(raw_list):
                p = os.path.join(tmp_multi, f"photo_{i}.jpg")
                with open(p, "wb") as f:
                    f.write(raw)
                paths_jpg.append(p)
            build_montagem_video_overlay(
                bg_path,
                paths_jpg,
                path_out,
                aspect=aspect,
                duration_sec=duration_sec,
                slot_x=int(slot_x or 0),
                slot_y=int(slot_y or 0),
                slot_w=int(slot_w or 0),
                slot_h=int(slot_h or 0),
            )
        elif len(raw_list) == 1:
            with open(path_in, "wb") as f:
                f.write(raw_list[0])
            build_montagem_video(path_in, path_out, aspect=aspect, duration_sec=duration_sec)
        else:
            _cleanup_paths(path_in)
            path_in = ""
            tmp_multi = montagem_multi_temp_dir()
            paths_jpg = []
            for i, raw in enumerate(raw_list):
                p = os.path.join(tmp_multi, f"slide_{i}.jpg")
                with open(p, "wb") as f:
                    f.write(raw)
                paths_jpg.append(p)
            build_montagem_video_multi(paths_jpg, path_out, aspect=aspect, duration_sec=duration_sec)
    except HTTPException:
        _cleanup_paths(path_in, path_out)
        if tmp_multi:
            shutil.rmtree(tmp_multi, ignore_errors=True)
        raise
    except Exception:
        _cleanup_paths(path_in, path_out)
        if tmp_multi:
            shutil.rmtree(tmp_multi, ignore_errors=True)
        raise
    finally:
        if tmp_multi:
            shutil.rmtree(tmp_multi, ignore_errors=True)

    return FileResponse(
        path_out,
        media_type="video/mp4",
        filename="montagem-anuncio.mp4",
        background=BackgroundTask(_cleanup_paths, path_in, path_out),
    )
