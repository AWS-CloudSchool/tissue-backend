from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.routers.auth import router as auth_router
from app.analyze.routers.youtube_analyze import router as analyze_router
from app.audio.routers.audio_service import router as audio_router
from app.s3.routers.s3 import router as s3_router
from app.search.routers.youtube_search import router as search_router
from app.chatbot.routers.chat_router import router as chatbot_router

app = FastAPI(title="YouTube Analysis Backend API", version="1.0.0")

# CORS 설정 (필요에 따라 origins 수정)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(auth_router)
app.include_router(analyze_router)
app.include_router(audio_router)
app.include_router(s3_router)
app.include_router(search_router)
app.include_router(chatbot_router)

@app.get("/")
def root():
    return {"message": "Backend API is running!"}