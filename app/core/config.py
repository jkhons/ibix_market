# PDV Ibix - Configuração centralizada (pydantic-settings)
"""Fonte única de configuração. Auth usa settings.SECRET_KEY e settings.ACCESS_TOKEN_EXPIRE_MINUTES.
Nunca usar os.getenv direto para variáveis de auth."""
from pathlib import Path
from typing import Optional

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Raiz do projeto (pasta que contém main.py). Usado para uploads fiscais com path absoluto.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
FISCAL_UPLOADS_DIR = PROJECT_ROOT / "uploads" / "fiscal"


class Settings(BaseSettings):
    """Configurações da aplicação via variáveis de ambiente (pydantic-settings)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Nome do sistema para exibição (templates, respostas)
    APP_DISPLAY_NAME: str = "PDV Ibix"
    APP_DISPLAY_NAME_SHORT: str = "PDV Ibix"

    # Auth (obrigatório usar aqui, não os.getenv em auth.py)
    SECRET_KEY: str = "pdv_solumatica_secret_key_change_in_production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 horas
    ALGORITHM: str = "HS256"

    # Banco de dados
    DB_HOST: Optional[str] = None
    DB_PORT: Optional[str] = None
    DB_USER: Optional[str] = None
    DB_PASSWORD: Optional[str] = None
    DB_NAME: Optional[str] = None

    # Debug
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Acesso pela internet (produção)
    APP_URL: Optional[str] = None   # ex: https://www.ibix.com.br
    # URL pública canônica para SEO (canonical, OG, sitemap). Domínio oficial da vitrine no Google (ex.: ibix.com.br).
    # Evita conflito quando APP_URL ou outro host diverge do domínio público principal.
    SEO_PUBLIC_BASE_URL: Optional[str] = None  # ex: https://www.ibix.com.br
    # Meta Open Graph — App ID (Sharing Debugger / analytics Meta). Aceita FB_APP_ID ou SEO_FB_APP_ID no .env
    SEO_FB_APP_ID: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("SEO_FB_APP_ID", "FB_APP_ID"),
    )
    # Fase 02: redirect produto com UTM → cookie de atribuição + URL limpa (canonical/OG)
    VITRINE_UTM_ATTRIBUTION_ENABLED: bool = True
    # Com SEO_REDIRECT_LEGACY_HOSTS: "public" = só rotas de vitrine/institucional; "all" = tudo exceto /api, /static, /dashboard, /admin
    SEO_REDIRECT_LEGACY_PATH_MODE: str = "public"
    ENV: str = "development"       # production | development

    # OAuth consumidor (vitrine /loja) — Client ID é exposto ao front via GET /loja/auth/social/config
    LOJA_OAUTH_GOOGLE_CLIENT_ID: Optional[str] = None
    # Client Secret OAuth (Google): só servidor; não expor; fluxo atual GSI usa token no browser — reservado para troca server-side futura
    LOJA_OAUTH_GOOGLE_CLIENT_SECRET: Optional[str] = None
    LOJA_OAUTH_FACEBOOK_APP_ID: Optional[str] = None
    LOJA_OAUTH_APPLE_CLIENT_ID: Optional[str] = None

    # Apple Sign-In (server-side) — Service ID para validar id_token
    LOJA_OAUTH_APPLE_SERVICE_ID: Optional[str] = None

    # Firebase (push notifications mobile)
    FIREBASE_CREDENTIALS_JSON: Optional[str] = None

    # Refresh token para consumidor mobile (dias)
    CONSUMIDOR_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Deep Links (mobile app)
    ANDROID_PACKAGE_NAME: Optional[str] = None
    ANDROID_SHA256_FINGERPRINT: Optional[str] = None
    IOS_BUNDLE_ID: Optional[str] = None
    IOS_TEAM_ID: Optional[str] = None

    # Google Custom Search JSON API (cadastro de produto: busca de imagens). Key + Search engine ID (cx).
    GOOGLE_CUSTOM_SEARCH_API_KEY: Optional[str] = None
    GOOGLE_CUSTOM_SEARCH_ENGINE_ID: Optional[str] = None

settings = Settings()

# Fail-fast em produção: SECRET_KEY não pode ser o default
_DEFAULT_SECRET = "pdv_solumatica_secret_key_change_in_production"
if (settings.ENV or "").lower() == "production" and settings.SECRET_KEY == _DEFAULT_SECRET:
    raise RuntimeError(
        "SECRET_KEY não pode ser o valor default em produção. "
        "Defina SECRET_KEY nas variáveis de ambiente."
    )
