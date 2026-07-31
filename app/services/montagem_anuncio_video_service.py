# PDV Ibix — Vídeo curto (Ken Burns + fade) a partir de JPEG(s) da montagem (FFmpeg no servidor).
import os
import shutil
import subprocess
import tempfile
from typing import Literal

JPEG_MAGIC = b"\xff\xd8\xff"
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_SLIDES = 12
ALLOWED_DURATION = (6, 10, 15)
AspectKey = Literal["reels", "feed"]


def ffmpeg_binary() -> str | None:
    return shutil.which("ffmpeg")


def validate_jpeg_upload(raw: bytes) -> None:
    from fastapi import HTTPException, status

    if not raw or len(raw) < 256:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo de imagem inválido ou muito pequeno.",
        )
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Imagem excede o limite de {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.",
        )
    if not raw.startswith(JPEG_MAGIC):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Envie apenas JPEG (exportação da montagem).",
        )


def dimensions_for_aspect(aspect: AspectKey) -> tuple[int, int]:
    if aspect == "reels":
        return 1080, 1920
    return 1080, 1080


def _zoompan_vf(
    w: int,
    h: int,
    segment_duration: float,
    fps: int = 30,
    *,
    fade_in: bool = True,
    fade_out: bool = True,
) -> str:
    """
    Filtro com overscan (pad ~6% extra) ANTES do zoompan, garantindo que o zoom
    máximo (~1.06) mostre 100% do conteúdo do criativo sem cortar topo/rodapé.
    A borda extra usa o mesmo bege do tema (#F6EDE4), imperceptível no início.
    """
    total_frames = max(int(round(segment_duration * fps)), max(15, fps // 2))
    den = max(1, total_frames - 1)

    overscan = 0.06
    zoom_max = 0.06
    canvas_w = int(round(w * 3 * (1 + overscan)))
    canvas_h = int(round(h * 3 * (1 + overscan)))
    canvas_w += canvas_w % 2
    canvas_h += canvas_h % 2

    chain = [
        f"scale={canvas_w}:{canvas_h}:force_original_aspect_ratio=decrease:flags=lanczos",
        f"pad={canvas_w}:{canvas_h}:(ow-iw)/2:(oh-ih)/2:color=0xF6EDE4",
        (
            f"zoompan=z='min(1+{zoom_max}*on/{den},{1 + zoom_max})':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d={total_frames}:s={w}x{h}:fps={fps}"
        ),
    ]
    if fade_in:
        fade_d = min(0.28, max(0.12, segment_duration * 0.08))
        chain.append(f"fade=t=in:st=0:d={fade_d}")
    if fade_out:
        fade_d = min(0.28, max(0.12, segment_duration * 0.08))
        fade_out_st = max(0.01, segment_duration - fade_d)
        chain.append(f"fade=t=out:st={fade_out_st}:d={fade_d}")
    chain.append("setsar=1")
    chain.append("format=yuv420p")
    return ",".join(chain)


def _run_ffmpeg(cmd: list[str], timeout_sec: float) -> None:
    from fastapi import HTTPException, status

    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=timeout_sec)
    except subprocess.TimeoutExpired as e:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Tempo esgotado ao gerar o vídeo. Tente novamente.",
        ) from e
    except subprocess.CalledProcessError as e:
        err = (e.stderr or b"").decode("utf-8", errors="replace")[-800:]
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha ao codificar vídeo (FFmpeg). {err}" if err else "Falha ao codificar vídeo (FFmpeg).",
        ) from e


def build_one_zoom_segment(
    input_jpeg_path: str,
    output_mp4_path: str,
    *,
    aspect: AspectKey,
    segment_duration: float,
    exe: str,
    fade_in: bool = True,
    fade_out: bool = True,
) -> None:
    from fastapi import HTTPException, status

    if segment_duration < 0.25:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duração por slide insuficiente para o número de imagens.",
        )
    w, h = dimensions_for_aspect(aspect)
    vf = _zoompan_vf(w, h, segment_duration, fade_in=fade_in, fade_out=fade_out)
    cmd = [
        exe,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-loop",
        "1",
        "-i",
        input_jpeg_path,
        "-vf",
        vf,
        "-t",
        f"{segment_duration:.6f}",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-an",
        output_mp4_path,
    ]
    _run_ffmpeg(cmd, float(segment_duration) + 90.0)
    if not os.path.isfile(output_mp4_path) or os.path.getsize(output_mp4_path) < 256:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="FFmpeg não gerou um segmento de vídeo válido.",
        )


def _xfade_filter_complex(
    n: int,
    segment_duration: float,
    xfade_duration: float,
    transition: str = "slideleft",
) -> str:
    """Encadeia (n-1) xfade entre n vídeos de duração segment_duration cada.

    transition padrão = 'slideleft' (próxima imagem entra da direita para a esquerda,
    como um clique de avançar no carrossel). Outras opções úteis do FFmpeg: slideright,
    smoothleft, wipeleft, fade.
    """
    cur = "0:v"
    prev_dur = segment_duration
    parts: list[str] = []
    for i in range(1, n):
        off = prev_dur - xfade_duration
        label = f"vx{i}" if i < n - 1 else "outv"
        parts.append(
            f"[{cur}][{i}:v]xfade=transition={transition}:"
            f"duration={xfade_duration:.6f}:offset={off:.6f}[{label}]"
        )
        cur = label
        prev_dur = prev_dur + segment_duration - xfade_duration
    return ";".join(parts)


def merge_segments_xfade(
    segment_paths: list[str],
    output_mp4_path: str,
    *,
    segment_duration: float,
    xfade_duration: float,
    total_timeout: float,
    transition: str = "slideleft",
) -> None:
    from fastapi import HTTPException, status

    exe = ffmpeg_binary()
    if not exe:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="FFmpeg não está instalado no servidor.",
        )
    n = len(segment_paths)
    if n < 2:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="merge_segments_xfade exige ao menos 2 segmentos.",
        )
    fc = _xfade_filter_complex(n, segment_duration, xfade_duration, transition=transition)
    cmd = [exe, "-hide_banner", "-loglevel", "error", "-y"]
    for p in segment_paths:
        cmd.extend(["-i", p])
    cmd.extend(
        [
            "-filter_complex",
            fc,
            "-map",
            "[outv]",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-an",
            output_mp4_path,
        ]
    )
    _run_ffmpeg(cmd, total_timeout)
    if not os.path.isfile(output_mp4_path) or os.path.getsize(output_mp4_path) < 1024:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="FFmpeg não produziu o vídeo final (xfade).",
        )


def build_montagem_video(
    input_jpeg_path: str,
    output_mp4_path: str,
    *,
    aspect: AspectKey,
    duration_sec: int,
) -> None:
    """
    Um único JPEG: MP4 H.264 sem áudio (reels/feed), zoom suave + fade in/out.
    """
    from fastapi import HTTPException, status

    exe = ffmpeg_binary()
    if not exe:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="FFmpeg não está instalado no servidor. Instale o pacote ffmpeg e reinicie o serviço.",
        )

    if duration_sec not in ALLOWED_DURATION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Duração deve ser uma de: {', '.join(str(x) for x in ALLOWED_DURATION)} segundos.",
        )

    w, h = dimensions_for_aspect(aspect)
    vf = _zoompan_vf(w, h, float(duration_sec))
    cmd = [
        exe,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-loop",
        "1",
        "-i",
        input_jpeg_path,
        "-vf",
        vf,
        "-t",
        str(duration_sec),
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        "-an",
        output_mp4_path,
    ]

    _run_ffmpeg(cmd, float(duration_sec) + 120.0)

    if not os.path.isfile(output_mp4_path) or os.path.getsize(output_mp4_path) < 1024:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="FFmpeg não produziu um arquivo de vídeo válido.",
        )


def build_montagem_video_multi(
    jpeg_paths: list[str],
    output_mp4_path: str,
    *,
    aspect: AspectKey,
    duration_sec: int,
) -> None:
    """
    Vários JPEGs (ordem do carrossel): gera um clipe com transição suave (xfade) entre slides,
    mantendo duração total = duration_sec.
    """
    from fastapi import HTTPException, status

    n = len(jpeg_paths)
    if n < 2:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="build_montagem_video_multi exige ao menos 2 imagens.",
        )
    if duration_sec not in ALLOWED_DURATION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Duração deve ser uma de: {', '.join(str(x) for x in ALLOWED_DURATION)} segundos.",
        )

    exe = ffmpeg_binary()
    if not exe:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="FFmpeg não está instalado no servidor. Instale o pacote ffmpeg e reinicie o serviço.",
        )

    xfade_d = min(0.40, max(0.22, float(duration_sec) / (3.5 * n)))
    seg_t = (float(duration_sec) + (n - 1) * xfade_d) / n
    if seg_t < xfade_d + 0.2:
        xfade_d = max(0.18, xfade_d * 0.65)
        seg_t = (float(duration_sec) + (n - 1) * xfade_d) / n
    if seg_t < 0.35:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Muitas imagens para a duração escolhida. Reduza o número de fotos ou aumente a duração.",
        )

    tmp = tempfile.mkdtemp(prefix="ma_vid_multi_")
    seg_files: list[str] = []
    try:
        for i, jp in enumerate(jpeg_paths):
            seg = os.path.join(tmp, f"seg_{i}.mp4")
            # Em slideleft, fade-in/out por segmento causaria flash bege durante o slide.
            # Mantemos só fade-in no primeiro e fade-out no último; segmentos do meio sem fade.
            seg_fade_in = i == 0
            seg_fade_out = i == n - 1
            build_one_zoom_segment(
                jp,
                seg,
                aspect=aspect,
                segment_duration=seg_t,
                exe=exe,
                fade_in=seg_fade_in,
                fade_out=seg_fade_out,
            )
            seg_files.append(seg)
        merge_segments_xfade(
            seg_files,
            output_mp4_path,
            segment_duration=seg_t,
            xfade_duration=xfade_d,
            total_timeout=float(duration_sec) + 240.0,
            transition="slideleft",
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def montagem_video_temp_paths(suffix_in: str = ".jpg") -> tuple[str, str]:
    """Retorna (path_entrada, path_saida) em diretório temporário."""
    fd_in, path_in = tempfile.mkstemp(suffix=suffix_in, prefix="ma_vid_in_")
    os.close(fd_in)
    _, path_out = tempfile.mkstemp(suffix=".mp4", prefix="ma_vid_out_")
    os.unlink(path_out)
    return path_in, path_out


def montagem_multi_temp_dir() -> str:
    return tempfile.mkdtemp(prefix="ma_vid_frames_")


# ---------------------------------------------------------------------------
# Modo overlay: card fixo como fundo + apenas a foto do carrossel troca
# ---------------------------------------------------------------------------


def _photo_segment_vf(w: int, h: int, fps: int = 30) -> str:
    """Foto pura do carrossel: scale (object-fit: cover) + crop centralizado, sem zoom/fade."""
    return (
        f"scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos,"
        f"crop={w}:{h},"
        f"fps={fps},setsar=1,format=yuv420p"
    )


def build_one_photo_segment(
    input_jpeg_path: str,
    output_mp4_path: str,
    *,
    w: int,
    h: int,
    segment_duration: float,
    exe: str,
) -> None:
    from fastapi import HTTPException, status

    if segment_duration < 0.20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duração por foto insuficiente para o número de imagens.",
        )
    if w <= 0 or h <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dimensão de slot inválida para a foto do carrossel.",
        )
    vf = _photo_segment_vf(w, h)
    cmd = [
        exe,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-loop",
        "1",
        "-i",
        input_jpeg_path,
        "-vf",
        vf,
        "-t",
        f"{segment_duration:.6f}",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-an",
        output_mp4_path,
    ]
    _run_ffmpeg(cmd, float(segment_duration) + 60.0)
    if not os.path.isfile(output_mp4_path) or os.path.getsize(output_mp4_path) < 256:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="FFmpeg não gerou um segmento de foto válido.",
        )


def build_montagem_video_overlay(
    bg_jpeg_path: str,
    photo_jpeg_paths: list[str],
    output_mp4_path: str,
    *,
    aspect: AspectKey,
    duration_sec: int,
    slot_x: int,
    slot_y: int,
    slot_w: int,
    slot_h: int,
) -> None:
    """
    Mantém o card (BG) estático durante todo o vídeo e só troca a foto do carrossel
    com transição slideleft, sobreposta sobre o BG na posição (slot_x, slot_y).
    """
    from fastapi import HTTPException, status

    n = len(photo_jpeg_paths)
    if n < 2:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="build_montagem_video_overlay exige ao menos 2 fotos.",
        )
    if duration_sec not in ALLOWED_DURATION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Duração deve ser uma de: {', '.join(str(x) for x in ALLOWED_DURATION)} segundos.",
        )

    exe = ffmpeg_binary()
    if not exe:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="FFmpeg não está instalado no servidor.",
        )

    final_w, final_h = dimensions_for_aspect(aspect)

    if (
        slot_w <= 0
        or slot_h <= 0
        or slot_x < 0
        or slot_y < 0
        or slot_x + slot_w > final_w
        or slot_y + slot_h > final_h
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Coordenadas do slot do carrossel inválidas para o formato escolhido "
                f"({final_w}x{final_h})."
            ),
        )

    # Mesma matemática do modo "muda card todo": cada foto fica visível seg_t segundos,
    # com crossfade xfade_d entre elas, somando duration_sec no total.
    xfade_d = min(0.40, max(0.22, float(duration_sec) / (3.5 * n)))
    seg_t = (float(duration_sec) + (n - 1) * xfade_d) / n
    if seg_t < xfade_d + 0.2:
        xfade_d = max(0.18, xfade_d * 0.65)
        seg_t = (float(duration_sec) + (n - 1) * xfade_d) / n
    if seg_t < 0.35:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Muitas fotos para a duração escolhida. Reduza o número de fotos ou aumente a duração.",
        )

    tmp = tempfile.mkdtemp(prefix="ma_vid_overlay_")
    photo_segs: list[str] = []
    carousel_path = os.path.join(tmp, "carousel.mp4")
    try:
        for i, jp in enumerate(photo_jpeg_paths):
            seg = os.path.join(tmp, f"photo_{i}.mp4")
            build_one_photo_segment(
                jp,
                seg,
                w=slot_w,
                h=slot_h,
                segment_duration=seg_t,
                exe=exe,
            )
            photo_segs.append(seg)

        merge_segments_xfade(
            photo_segs,
            carousel_path,
            segment_duration=seg_t,
            xfade_duration=xfade_d,
            total_timeout=float(duration_sec) + 240.0,
            transition="slideleft",
        )

        # Compose: BG estático (loop) + overlay do vídeo do carrossel
        fc = (
            f"[0:v]scale={final_w}:{final_h}:flags=lanczos,setsar=1,format=yuv420p[bg];"
            f"[bg][1:v]overlay=x={slot_x}:y={slot_y}:format=auto[outv]"
        )
        cmd = [
            exe,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-loop",
            "1",
            "-t",
            f"{duration_sec}",
            "-i",
            bg_jpeg_path,
            "-i",
            carousel_path,
            "-filter_complex",
            fc,
            "-map",
            "[outv]",
            "-t",
            f"{duration_sec}",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-an",
            output_mp4_path,
        ]
        _run_ffmpeg(cmd, float(duration_sec) + 240.0)
        if not os.path.isfile(output_mp4_path) or os.path.getsize(output_mp4_path) < 1024:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="FFmpeg não produziu o vídeo final (overlay).",
            )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
