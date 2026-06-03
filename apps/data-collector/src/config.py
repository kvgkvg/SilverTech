from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="COLLECTOR_", env_file=".env", extra="ignore")

    data_dir: Path = Path("data")
    search_engine: str = "bing"
    user_agent: str = "PanelLensResearchBot/0.1"
    request_timeout: int = 20
    max_concurrent_downloads: int = 8
    results_per_query: int = 12
    crawl_delay_seconds: float = 1.5

    min_image_width: int = 300
    min_image_height: int = 300
    min_image_file_size_kb: int = 20
    max_aspect_ratio: float = 6.0

    @property
    def collected_dir(self) -> Path:
        return self.data_dir / "collected"

    @property
    def seeds_dir(self) -> Path:
        return self.data_dir / "seeds"


def get_settings() -> Settings:
    return Settings()
