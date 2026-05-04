# PDV Ibix — validação e gravação de arquivos do cadastro entregador (CNH / documento veículo)
import os
import re
import uuid
from decimal import Decimal
from typing import Literal, Optional, Tuple

from fastapi import HTTPException, UploadFile, status

MAX_CNH_BYTES = 8 * 1024 * 1024
MAX_DOC_VEIC_BYTES = 12 * 1024 * 1024

MAGIC_JPEG = (b"\xff\xd8\xff",)
MAGIC_PNG = (b"\x89PNG\r\n\x1a\n",)
MAGIC_WEBP = (b"RIFF", b"WEBP")  # WEBP at offset 8
MAGIC_PDF = (b"%PDF",)


def _read_head(upload: UploadFile, n: int = 32) -> bytes:
    upload.file.seek(0)
    chunk = upload.file.read(n)
    upload.file.seek(0)
    return chunk or b""


def validar_assinatura_arquivo(conteudo: bytes, categoria: Literal["cnh", "veiculo"]) -> Tuple[str, str]:
    """Retorna (ext_com_ponto, tipo_logico)."""
    if categoria == "cnh":
        if any(conteudo.startswith(m) for m in MAGIC_JPEG):
            return ".jpg", "image/jpeg"
        if conteudo.startswith(MAGIC_PNG[0]):
            return ".png", "image/png"
        if len(conteudo) >= 12 and conteudo.startswith(MAGIC_WEBP[0]) and conteudo[8:12] == MAGIC_WEBP[1]:
            return ".webp", "image/webp"
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CNH: envie imagem JPEG, PNG ou WebP válida")
    # veiculo: imagem ou PDF
    if conteudo.startswith(MAGIC_PDF[0]):
        return ".pdf", "application/pdf"
    if any(conteudo.startswith(m) for m in MAGIC_JPEG):
        return ".jpg", "image/jpeg"
    if conteudo.startswith(MAGIC_PNG[0]):
        return ".png", "image/png"
    if len(conteudo) >= 12 and conteudo.startswith(MAGIC_WEBP[0]) and conteudo[8:12] == MAGIC_WEBP[1]:
        return ".webp", "image/webp"
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Documento do veículo: envie PDF ou imagem JPEG, PNG ou WebP válida",
    )


async def ler_e_validar_upload(
    upload: UploadFile,
    categoria: Literal["cnh", "veiculo"],
) -> Tuple[bytes, str]:
    max_b = MAX_CNH_BYTES if categoria == "cnh" else MAX_DOC_VEIC_BYTES
    raw = await upload.read()
    if len(raw) > max_b:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Arquivo excede o tamanho máximo permitido")
    if len(raw) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivo inválido ou corrompido")
    head = raw[: min(len(raw), 64)]
    _, mime = validar_assinatura_arquivo(head, categoria)
    return raw, mime


def gravar_em_entregador_dir(entregador_id: int, nome_base: str, ext: str, conteudo: bytes) -> str:
    """Retorna caminho relativo tipo uploads/entregadores/{id}/arquivo.ext"""
    safe_base = re.sub(r"[^a-zA-Z0-9_-]", "_", nome_base)[:80]
    fname = f"{safe_base}_{uuid.uuid4().hex[:10]}{ext}"
    rel_dir = os.path.join("uploads", "entregadores", str(entregador_id))
    abs_dir = os.path.abspath(rel_dir)
    os.makedirs(abs_dir, exist_ok=True)
    abs_path = os.path.join(abs_dir, fname)
    with open(abs_path, "wb") as f:
        f.write(conteudo)
    return os.path.join(rel_dir, fname).replace("\\", "/")


def caminho_absoluto_seguro(rel_path: str) -> Optional[str]:
    """Resolve path relativo do projeto; None se fora de uploads/entregadores."""
    if not rel_path or ".." in rel_path or rel_path.startswith("/"):
        return None
    base = os.path.abspath(os.path.join("uploads", "entregadores"))
    full = os.path.abspath(rel_path)
    if not full.startswith(base + os.sep) and full != base:
        return None
    if not os.path.isfile(full):
        return None
    return full


def normalizar_placa(placa: Optional[str]) -> Optional[str]:
    if not placa:
        return None
    p = re.sub(r"\s+", "", (placa or "").strip().upper())
    return p[:10] if p else None


def normalizar_tipo_veiculo(t: str) -> str:
    x = (t or "").strip().lower()
    if x not in ("moto", "carro", "utilitario"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="tipo_veiculo deve ser moto, carro ou utilitario")
    return x


def parse_capacidade_kg(raw: Optional[str]) -> Optional[Decimal]:
    if raw is None or str(raw).strip() == "" or str(raw).strip() == "-":
        return None
    try:
        return Decimal(str(raw).strip().replace(",", "."))
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="capacidade_kg inválida")
