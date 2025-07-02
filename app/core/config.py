import os
from dotenv import load_dotenv
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from functools import lru_cache

load_dotenv()

class Settings(BaseSettings):
    # 프로젝트 설정
    PROJECT_NAME: str = "AI Analysis API"
    VERSION: str = "1.0.0"

    # AWS 설정
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-west-2"
    AWS_S3_BUCKET: Optional[str] = None
    S3_PREFIX: Optional[str] = None

    # Bedrock 설정 (bedrock_chatbot에서 통합)
    BEDROCK_KB_ID: Optional[str] = None
    BEDROCK_DS_ID: Optional[str] = None
    BEDROCK_MODEL_ID: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    BEDROCK_TEMPERATURE: float = 0.0
    BEDROCK_MAX_TOKENS: int = 4000
    YOUTUBE_LAMBDA_NAME: Optional[str] = None

    # Polly 설정
    POLLY_VOICE_ID: str = "Seoyeon"

    # CORS 설정
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    # API 키
    VIDCAP_API_KEY: str = ""

    # YouTube API 설정
    YOUTUBE_API_KEY: Optional[str] = None

    # LangChain 설정
    LANGCHAIN_API_KEY: Optional[str] = None
    LANGCHAIN_ENDPOINT: Optional[str] = None
    LANGCHAIN_PROJECT: Optional[str] = None
    LANGCHAIN_TRACING_V2: Optional[str] = None

    # AWS Cognito 설정
    COGNITO_USER_POOL_ID: Optional[str] = None
    COGNITO_CLIENT_ID: Optional[str] = None
    COGNITO_CLIENT_SECRET: Optional[str] = None
    
    # 데이터베이스 설정
    DATABASE_URL: Optional[str] = None

    model_config = ConfigDict(
        env_file=".env",
        extra="allow"
    )

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()