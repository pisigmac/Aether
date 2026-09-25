from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthSettings(BaseSettings):
    """OpenDesk Auth coordinates. Aether does not store passwords."""

    model_config = SettingsConfigDict(env_prefix="AETHER_AUTH_", extra="ignore")

    jwks_url: str = ""
    issuer: str = "https://auth.pisigma.local"
    audience: str = "aether"


def get_auth_settings() -> AuthSettings:
    return AuthSettings()
