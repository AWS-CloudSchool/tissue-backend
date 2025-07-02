import os
from dotenv import load_dotenv
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from functools import lru_cache

load_dotenv()

class Settings(BaseSettings):
    # AWS Cognito 설정
    COGNITO_USER_POOL_ID: Optional[str] = None
    COGNITO_CLIENT_ID: Optional[str] = None
    COGNITO_CLIENT_SECRET: Optional[str] = None
    AWS_REGION: str = "us-west-2"
    
    model_config = ConfigDict(
        env_file=".env",
        extra="allow"
    )

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()