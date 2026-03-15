"""搜索相关的API schemas"""

from typing import Any

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """搜索请求"""
    query: str = Field(..., min_length=1, max_length=500)
    user_id: str | None = None
    session_id: str | None = None
    context: dict[str, Any] | None = None  # 额外的上下文信息


class SearchSuggestion(BaseModel):
    """搜索建议"""
    text: str
    type: str  # keyword, route, poi, location
    relevance: float


class SearchResult(BaseModel):
    """单个搜索结果"""
    id: str
    name: str
    type: str  # route, poi
    description: str | None = None
    preview_image: str | None = None
    relevance_score: float
    metadata: dict[str, Any] | None = None


class SearchResponse(BaseModel):
    """搜索响应"""
    query: str
    results: list[SearchResult]
    total: int
    has_more: bool
    suggestions: list[SearchSuggestion] | None = None
    message: str | None = None  # AI生成的解释文本
