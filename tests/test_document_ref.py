"""Testes do formato compacto de referências de documentos."""
from app.core.document_ref import build_doc_ref, compact_doc_ref, parse_doc_ref


def test_compact_doc_ref_legacy_venda():
    assert compact_doc_ref("VENDA-2026-000057") == "V-26-57"


def test_compact_doc_ref_new_format():
    assert compact_doc_ref("V-26-57") == "V-26-57"
    assert compact_doc_ref("ORC-26-12") == "ORC-26-12"


def test_compact_doc_ref_marketplace_unchanged():
    assert compact_doc_ref("58-999") == "58-999"


def test_build_doc_ref():
    assert build_doc_ref("VENDA", 57, 2026) == "V-26-57"
