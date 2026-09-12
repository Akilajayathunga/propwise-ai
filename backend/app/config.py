from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    project_name: str = "PropWise AI"
    app_env: str = "development"

    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    llm_provider: str = "openai"
    openai_api_key: str = ""
    gemini_api_key: str = ""
    llm_model: str = ""

    property_dataset_path: str = ""
    cleaned_dataset_path: str = ""

    development_sample_size: int = 10000
    git_sample_size: int = 500
    random_seed: int = 42


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

