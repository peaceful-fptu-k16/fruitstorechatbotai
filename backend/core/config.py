from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Fruit Chatbot API"
    environment: str = "development"
    api_prefix: str = "/api"
    database_url: str = "sqlite:///./backend/data/fruit_chatbot.db"
    admin_jwt_secret: str = "change-me-in-env"
    admin_jwt_algorithm: str = "HS256"
    admin_access_token_expire_minutes: int = 120
    admin_username: str = "admin"
    admin_password: str = "admin123"
    rate_limit_requests: int = 30
    rate_limit_window_seconds: int = 60
    cors_origins: List[str] = ["*"]
    use_chroma: bool = False
    allow_remote_model_download: bool = True
    use_pretrained_intent_router: bool = True
    pretrained_intent_model_name: str = "BAAI/bge-m3"
    pretrained_intent_min_confidence: float = 0.55
    embedding_backend: str = "sentence_transformers"
    embedding_model_name: str = "BAAI/bge-m3"
    use_pretrained_reranker: bool = True
    pretrained_reranker_model_name: str = "BAAI/bge-reranker-v2-m3"
    reranker_candidate_pool: int = 30
    response_generation_mode: str = "lm_studio"
    enable_llm_response_rewrite: bool = True
    gemini_api_key: str = ""
    gemini_model_name: str = "gemini-1.5-flash"
    gemini_timeout_seconds: float = 6.0
    gemini_temperature: float = 0.2
    lm_studio_base_url: str = "http://localhost:1234/v1"
    lm_studio_model_name: str = ""
    lm_studio_timeout_seconds: float = 15.0
    lm_studio_temperature: float = 0.2
    enable_user_query_logging: bool = True
    user_query_log_path: str = "ai_log/user_questions.jsonl"
    enable_qa_pair_logging: bool = True
    qa_pair_log_path: str = "ai_log/qa_pairs.jsonl"
    enable_answer_quality_review: bool = True
    facebook_verify_token: str = ""
    facebook_page_access_token: str = ""
    facebook_page_id: str = "me"
    facebook_app_secret: str = ""
    facebook_graph_api_version: str = "v22.0"
    facebook_request_timeout_seconds: float = 8.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    env_file = ".env.secret" if Path(".env.secret").exists() else ".env"
    return Settings(_env_file=env_file)
