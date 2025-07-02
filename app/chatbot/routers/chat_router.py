from fastapi import APIRouter, HTTPException
from typing import List
from pydantic import BaseModel
import datetime
from app.chatbot.agents.bedrock_agent import answer_question
from app.chatbot.tool.youtube_lambda import process_user_job

# Pydantic 모델 정의
class QuestionRequest(BaseModel):
    question: str

class QuestionResponse(BaseModel):
    answer: str
    success: bool
    error: str = None

class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: str

router = APIRouter()

chat_history: List[ChatMessage] = []

@router.get("/")
async def root():
    return {"message": "Bedrock Chatbot API is running!"}

class ChatResponse(BaseModel):
    answer: str
    success: bool
    error: str = None
    source_type: str = None  # "KB" 또는 "FALLBACK"
    documents_found: int = 0
    relevance_scores: list = []

@router.post("/api/chat", response_model=ChatResponse)
async def chat(request: QuestionRequest):
    try:
        result = answer_question(request.question)
        
        # answer_question에서 더 자세한 정보를 반환하도록 수정 필요
        if isinstance(result, dict):
            answer = result.get('answer', '')
            source_type = result.get('source_type', 'UNKNOWN')
            documents_found = result.get('documents_found', 0)
            relevance_scores = result.get('relevance_scores', [])
        else:
            answer = str(result)
            source_type = 'UNKNOWN'
            documents_found = 0
            relevance_scores = []
            
        chat_history.append(ChatMessage(
            role="user",
            content=request.question,
            timestamp=datetime.datetime.now().isoformat()
        ))
        chat_history.append(ChatMessage(
            role="assistant",
            content=answer,
            timestamp=datetime.datetime.now().isoformat()
        ))
        
        return ChatResponse(
            answer=answer, 
            success=True,
            source_type=source_type,
            documents_found=documents_found,
            relevance_scores=relevance_scores
        )
    except Exception as e:
        return ChatResponse(
            answer="",
            success=False,
            error=str(e)
        )



@router.get("/api/chat-history")
async def get_chat_history():
    return chat_history

@router.delete("/api/chat-history")
async def clear_chat_history():
    chat_history.clear()
    return {"message": "Chat history cleared."}



class SyncKBRequest(BaseModel):
    user_id: str
    job_id: str

@router.post("/api/sync-kb")
async def sync_kb_endpoint(request: SyncKBRequest):
    print(f"🔥 /api/sync-kb 엔드포인트 호출됨!")
    print(f"📥 요청 데이터: {request}")
    try:
        print(f"📥 KB 동기화 요청: user_id={request.user_id}, job_id={request.job_id}")
        sync_job_id = process_user_job(request.user_id, request.job_id)
        return {
            "success": True,
            "message": "KB 동기화가 시작되었습니다.",
            "sync_job_id": sync_job_id,
            "kb_id": sync_job_id,
            "status": "CREATING",
            "user_id": request.user_id,
            "job_id": request.job_id
        }
    except Exception as e:
        print(f"❌ KB 동기화 실패: {str(e)}")
        print(f"❌ 에러 상세: {type(e).__name__}: {e}")
        import traceback
        print(f"❌ 스택 트레이스: {traceback.format_exc()}")
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/api/kb-status/{job_id}")
async def get_kb_status(job_id: str):
    try:
        from app.chatbot.tool.wait_until_kb_sync_complete import get_ingestion_job_status
        status = get_ingestion_job_status(job_id)
        
        # Bedrock 상태를 프론트엔드 상태로 매핑
        if status == "COMPLETE":
            frontend_status = "READY"
        elif status in ["STARTING", "IN_PROGRESS"]:
            frontend_status = "CREATING"
        elif status in ["FAILED", "STOPPED"]:
            frontend_status = "ERROR"
        else:
            frontend_status = "CREATING"
            
        return {
            "status": frontend_status,
            "bedrock_status": status
        }
    except Exception as e:
        print(f"❌ KB 상태 조회 실패: {str(e)}")
        return {
            "status": "ERROR",
            "error": str(e)
        } 