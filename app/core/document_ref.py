"""Referências de documentos (venda, OS, orçamento, pedido) — formato compacto e compatível com legado."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Iterable, Optional, Tuple

_DOC_REF_PATTERN = re.compile(
    r"^(?P<prefix>VENDA|V|OS|ORC|PED)-(?P<year>\d{2,4})-(?P<seq>\d+)$",
    re.IGNORECASE,
)

_PREFIX_COMPACT = {
    "VENDA": "V",
    "V": "V",
    "OS": "OS",
    "ORC": "ORC",
    "PED": "PED",
}


def _normalize_prefix(prefix: str) -> str:
    key = (prefix or "").strip().upper()
    return _PREFIX_COMPACT.get(key, key)


def _normalize_year(year: str) -> Tuple[int, str]:
    y = (year or "").strip()
    if len(y) == 2:
        century = datetime.now().year // 100
        full = century * 100 + int(y)
        return full, y
    if len(y) == 4:
        return int(y), y[2:]
    raise ValueError(f"Ano inválido em referência: {year!r}")


def parse_doc_ref(ref: Optional[str]) -> Optional[Tuple[str, int, int]]:
    """Retorna (prefixo_compacto, ano_completo, sequência) ou None."""
    if not ref:
        return None
    m = _DOC_REF_PATTERN.match(str(ref).strip())
    if not m:
        return None
    prefix = _normalize_prefix(m.group("prefix"))
    year_full, _ = _normalize_year(m.group("year"))
    seq = int(m.group("seq"))
    return prefix, year_full, seq


def compact_doc_ref(ref: Optional[str], *, fallback: str = "—") -> str:
    """Exibe referência no padrão compacto (ex.: VENDA-2026-000057 → V-26-57)."""
    parsed = parse_doc_ref(ref)
    if not parsed:
        return str(ref).strip() if ref else fallback
    prefix, year_full, seq = parsed
    yy = str(year_full)[2:]
    return f"{prefix}-{yy}-{seq}"


def build_doc_ref(prefix: str, seq: int, year: Optional[int] = None) -> str:
    """Gera referência no formato compacto padrão (ex.: V-26-57)."""
    if year is None:
        year = datetime.now().year
    compact_prefix = _normalize_prefix(prefix)
    yy = str(year)[2:]
    return f"{compact_prefix}-{yy}-{int(seq)}"


def next_seq_for_year(refs: Iterable[Optional[str]], year: int, prefix: Optional[str] = None) -> int:
    """Maior sequência do ano (e prefixo, se informado) + 1."""
    max_seq = 0
    expected_prefix = _normalize_prefix(prefix) if prefix else None
    for ref in refs:
        parsed = parse_doc_ref(ref)
        if not parsed:
            continue
        ref_prefix, ref_year, ref_seq = parsed
        if ref_year != year:
            continue
        if expected_prefix and ref_prefix != expected_prefix:
            continue
        max_seq = max(max_seq, ref_seq)
    return max_seq + 1


def doc_ref_like_patterns(prefix: str, year: int) -> Tuple[str, ...]:
    """Padrões SQL LIKE para buscar refs legadas e compactas do mesmo ano."""
    compact_prefix = _normalize_prefix(prefix)
    yy = str(year)[2:]
    patterns = [f"{compact_prefix}-{yy}-%"]
    if compact_prefix == "V":
        patterns.append(f"VENDA-{year}-%")
    elif compact_prefix in {"OS", "ORC", "PED"}:
        patterns.append(f"{compact_prefix}-{year}-%")
    return tuple(patterns)
