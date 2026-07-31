"""Logo exibível por marca — sem asset Ibix em marcas derivadas."""
from app.services.brand_service import (
    BrandContext,
    brand_logo_display_url,
    brand_logo_footer_display_url,
)

SOLUMATICA = BrandContext(
    id=2,
    slug="solumatica",
    nome_exibicao="PDV Solumática",
    nome_curto="Solumática",
    logo_url="/static/img/solumatica/cab.png",
    logo_footer_url="/static/img/solumatica/rodape.png",
    favicon_url="/static/img/arte-pdv.png",
    telefone="",
    whatsapp="",
    email_remetente="",
    cor_primaria="#2c3e50",
    cor_secundaria="#34495e",
    seo_base_url="https://www.solumatica.com.br",
    is_origem=False,
)

IBIX = BrandContext(
    id=1,
    slug="ibix",
    nome_exibicao="PDV Ibix",
    nome_curto="Ibix",
    logo_url="/static/img/ibix/cab.png",
    logo_footer_url="/static/img/ibix/rodape.png",
    favicon_url="/static/img/arte-pdv.png",
    telefone="",
    whatsapp="",
    email_remetente="",
    cor_primaria="#C47A44",
    cor_secundaria="#2F3A44",
    seo_base_url="https://www.ibix.com.br",
    is_origem=True,
)


def test_solumatica_sem_logo_ibix_placeholder():
    assert brand_logo_display_url(SOLUMATICA) == ""
    assert brand_logo_footer_display_url(SOLUMATICA) == ""


def test_ibix_mantem_logo():
    assert brand_logo_display_url(IBIX) == "/static/img/ibix/cab.png"
    assert brand_logo_footer_display_url(IBIX) == "/static/img/ibix/rodape.png"


def test_marca_derivada_com_logo_proprio():
    ctx = BrandContext(
        id=3,
        slug="solumatica",
        nome_exibicao="Solumática",
        nome_curto="Solumática",
        logo_url="/static/img/solumatica/logo-real.png",
        logo_footer_url="/static/img/solumatica/logo-real.png",
        favicon_url="",
        telefone="",
        whatsapp="",
        email_remetente="",
        cor_primaria="",
        cor_secundaria="",
        seo_base_url="",
        is_origem=False,
    )
    assert brand_logo_display_url(ctx) == "/static/img/solumatica/logo-real.png"
