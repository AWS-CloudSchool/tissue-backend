from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.routers.auth import router as auth_router

app = FastAPI(title="Backend API", version="1.0.0")

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

@app.get("/")
def root():
    return {"message": "Backend API is running!"}