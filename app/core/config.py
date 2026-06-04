from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "Job Portal"
    app_version: str = "1.0.0"
    debug: bool = False
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/job_portal"
    secret_key: str = "change-me-in-production"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    access_token_expire_minutes: int = 30
    resend_api_key: str = ""
    resend_from_email: str = "Job Portal <onboarding@resend.dev>"
    frontend_url: str = "http://localhost:3000"
    # comma-separated list of allowed origins, e.g. "https://myapp.vercel.app,http://localhost:3000"
    allowed_origins_str: str = "*"

    # ── Cloudflare R2 ─────────────────────────────────────────────────────────
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = ""

    @property
    def r2_endpoint_url(self) -> str:
        return f"https://{self.r2_account_id}.r2.cloudflarestorage.com"

    @property
    def r2_public_url(self) -> str:
        return f"https://pub-{self.r2_account_id}.r2.dev"

    # ── Redis (Upstash) ───────────────────────────────────────────────────────
    redis_url: str = ""
    redis_host: str = ""
    redis_port: int = 6379
    redis_password: str = ""
    redis_tls: bool = True

    @property
    def allowed_origins(self) -> list[str]:
        if self.allowed_origins_str.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.allowed_origins_str.split(",") if o.strip()]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
