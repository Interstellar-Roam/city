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
    amap_api_key: str = ""

    # Agent配置
    max_iterations: int = 20
    context_window_tokens: int = 32_768


@lru_cache
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()
