from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.core.config import settings
from app.auth.routers.auth import router as auth_router
from app.analyze.routers.youtube_analyze import router as analyze_router
from app.audio.routers.audio_service import router as audio_router
from app.s3.routers.s3 import router as s3_router
from app.search.routers.youtube_search import router as search_router
from app.chatbot.routers.chat_router import router as chatbot_router
from app.monitoring.routers.metrics import router as monitoring_router

# 모니터링 import
from app.middleware import MetricsMiddleware

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="YouTube Analysis Backend API", version="1.0.0")

# 데이터베이스 연결 정보 로깅
logger.info(f"Database URL: {settings.database_url}")

# 모니터링 미들웨어 추가 (CORS 전에!)
app.add_middleware(MetricsMiddleware)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://www.tissue.cloud", "https://dltec80179zlu.cloudfront.net", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 데이터베이스 테이블 생성
@app.on_event("startup")
async def startup_event():
    try:
        from app.database.core.database import Base, engine
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")

# 라우터 등록 
app.include_router(auth_router)
app.include_router(analyze_router)
app.include_router(audio_router)
app.include_router(s3_router)
app.include_router(search_router)
app.include_router(chatbot_router)
app.include_router(monitoring_router) 

@app.get("/")
def root():
    return {"message": "Backend API is running!"}