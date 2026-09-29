from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://codejudge:codejudge@localhost:5432/codejudge"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "dev-only-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    app_name: str = "CodeJudge API"

    time_limit_seconds: float = 2.0
    memory_limit_mb: int = 256
    cpu_limit: float = 0.5
    pids_limit: int = 128
    wall_timeout_seconds: int = 20

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
