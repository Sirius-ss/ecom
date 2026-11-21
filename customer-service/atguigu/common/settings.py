from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE_PATH = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    database_url: str = Field(
        "postgresql+psycopg://customer_service:customer_service@192.168.200.166:5432/customer_service",
        description="PgSql数据库地址")
    jwt_secret: str = Field("ecommerce-secret", description="JWT密钥")
    jwt_algorithm: str = Field("HS256", description="JWT加密方式")
    api_host: str = Field("0.0.0.0", description="服务的域名访问")
    api_port: int = Field("8000", description="服务的端口")
    cors_origins: list[str] = Field(
        ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"],
        description="服务端允许的源")
    conversation_idle_timeout_minutes: int = Field("30", description="AI模式下会话的有效时间")
    message_merge_delay_ms: int = Field(800, description="AI模式下消息的防抖时间窗口阈值")

    internal_service_token: str = Field("customer-internal-token", description="服务内部访问令牌")
    ai_worker_poll_interval_ms: int = Field(100, description="Woker领取Turn时间")
    ai_timeout_seconds: int = Field(30, description="请求AI Service的http超时时间")
    ai_service_url: str = Field("http://127.0.0.1:8002", description="AI Service服务地址")
    ai_worker_max_attempts: int = Field(3, description="当前轮次重试AI Service调用次数")
    ai_worker_retry_delay_seconds: int = Field(2, description="重试延时")

    model_config = SettingsConfigDict(env_file=ENV_FILE_PATH, extra="ignore")


@lru_cache
def get_settings():
    return Settings()


if __name__ == '__main__':
    print(get_settings().jwt_algorithm)