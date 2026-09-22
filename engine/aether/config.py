from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AETHER_", extra="ignore")

    data_dir: Path = Path("./data")
    cors_origins: str = "http://localhost:3000"
    max_samples: int = 200
    lookback_months: int = 24
    default_horizon_months: int = 24
    license_allowlist: str = "MIT,Apache-2.0,BSD-2-Clause,BSD-3-Clause"

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def allowed_licenses(self) -> set[str]:
        return {x.strip() for x in self.license_allowlist.split(",") if x.strip()}


settings = Settings()
