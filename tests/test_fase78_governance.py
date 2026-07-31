# PDV Ibix — validação Fase 7 (regras Cursor) e Fase 8 (mapas multi-brand)
"""Smoke de governança: arquivos obrigatórios existem e referências cruzadas batem."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FASE7_RULES = (
    "multibrand-no-hardcode.mdc",
    "modulo-gating.mdc",
    "tenant-rls.mdc",
    "conflito-dados-migracao.mdc",
    "seguranca-dominio.mdc",
)

RULE_KEYWORDS = {
    "multibrand-no-hardcode.mdc": ("request.state.brand", "MAPA_MULTIBRAND"),
    "modulo-gating.mdc": ("403", "brand_module_gating"),
    "tenant-rls.mdc": ("tenant_id NOT NULL", "open_db_session"),
    "conflito-dados-migracao.mdc": ("brand_id, slug", "ON CONFLICT"),
    "seguranca-dominio.mdc": ("brand_domains", "brand_cookie"),
}


def test_fase7_cursor_rules_exist_with_content():
    rules_dir = ROOT / ".cursor" / "rules"
    for name in FASE7_RULES:
        path = rules_dir / name
        assert path.is_file(), f"Regra Cursor ausente: {name}"
        text = path.read_text(encoding="utf-8")
        assert "description:" in text, f"Frontmatter ausente em {name}"
        for kw in RULE_KEYWORDS[name]:
            assert kw in text, f"{name} deve mencionar {kw!r}"


def test_fase8_mapa_multibrand_and_cross_refs():
    mapa = ROOT / "MAPA_SISTEMA" / "MAPA_MULTIBRAND.md"
    assert mapa.is_file()
    text = mapa.read_text(encoding="utf-8")
    for section in ("brands", "brand_domains", "brand_modules", "RLS", "Planos legados"):
        assert section in text, f"MAPA_MULTIBRAND deve conter {section!r}"

    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "MAPA_MULTIBRAND" in agents
    assert ".cursor/rules/" in agents

    indice = (ROOT / "MAPA_SISTEMA" / "INDICE.md").read_text(encoding="utf-8")
    assert "MAPA_MULTIBRAND.md" in indice
    assert "2026-06-18" in indice

    skill = (ROOT / ".cursor" / "skills" / "saas-golden-rules" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "## 6. Multi-brand" in skill

    for fname, marker in (
        ("MAPA_DO_SISTEMA.md", "MAPA_MULTIBRAND"),
        ("MAPA_RBAC.md", "0.13 Multi-brand"),
        ("MAPA_DE_API.md", "## 20. MULTI-BRAND"),
        ("MAPA_DEPLOY_SERVICOS.md", "### 2.1 Multi-brand"),
    ):
        content = (ROOT / "MAPA_SISTEMA" / fname).read_text(encoding="utf-8")
        assert marker in content, f"{fname} deve referenciar {marker!r}"
