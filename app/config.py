"""配置管理模块"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # 应用配置
    app_name: str = "CityWalk"
    app_version: str = "1.0.0"
    debug: bool = False

    # MongoDB配置
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "citywalk"

    # LLM配置
    llm_provider: Literal["openai", "anthropic", "deepseek", "aliyun"] = "openai"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str = "https://api.openai.com/v1"

    # FalkorDB配置 (Graphiti后端)
    falkordb_host: str = "localhost"
    falkordb_port: int = 6379
    falkordb_password: str = ""
    falkordb_graph_name: str = "citywalk_kg"

    # 高德地图API
    amap_api_key: str = ""  # Web端(JS API) Key
    amap_api_key_backend: str = ""  # Web服务 Key (后端POI查询)
    amap_security_key: str = ""

    # JWT 认证配置
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # 短信验证码配置
    sms_mock: bool = True
    sms_resend_interval: int = 60
    sms_code_expire: int = 300

    # Agent配置
    max_iterations: int = 20
    context_window_tokens: int = 32_768


@lru_cache
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()
