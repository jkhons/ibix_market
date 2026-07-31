"""Testes unitários — gating de módulos por marca (Fase 2 multi-brand)."""
from app.core.brand_module_gating import path_requires_marketplace_module


def test_path_requires_marketplace_vitrine_publica():
    assert path_requires_marketplace_module("/") is True
    assert path_requires_marketplace_module("/loja/carrinho") is True
    assert path_requires_marketplace_module("/categoria/eletronicos") is True
    assert path_requires_marketplace_module("/minha-loja-parceira") is True


def test_path_requires_marketplace_api():
    assert path_requires_marketplace_module("/api/v1/loja/produtos") is True
    assert path_requires_marketplace_module("/api/v1/marketplace/pedidos") is True
    assert path_requires_marketplace_module("/api/v1/marketing-vitrine/config") is True
    assert path_requires_marketplace_module("/ws/loja/consumidor") is True


def test_path_requires_marketplace_negocio_admin():
    assert path_requires_marketplace_module("/negocio/marketplace") is True
    assert path_requires_marketplace_module("/negocio/marketplace/minha-loja") is True
    assert path_requires_marketplace_module("/admin/marketing-vitrine") is True
    assert path_requires_marketplace_module("/admin/marketplace-seo-lojas") is True
    assert path_requires_marketplace_module("/admin/lojas_produtos") is True


def test_path_requires_marketplace_nao_bloqueia_core():
    assert path_requires_marketplace_module("/login") is False
    assert path_requires_marketplace_module("/dashboard") is False
    assert path_requires_marketplace_module("/api/v1/negocios/dashboard") is False
    assert path_requires_marketplace_module("/static/img/ibix/cab.png") is False
    assert path_requires_marketplace_module("/sitemap.xml") is False


def test_path_requires_marketplace_sitemap_marketplace():
    assert path_requires_marketplace_module("/sitemap-produtos.xml") is True
    assert path_requires_marketplace_module("/sitemap-categorias.xml") is True
