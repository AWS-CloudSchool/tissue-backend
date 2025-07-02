from fastapi import APIRouter, HTTPException
from app.audio.models.audio import AudioRequest, AudioResponse
from app.audio.services.audio_service import audio_service
from datetime import datetime

router = APIRouter(prefix="/audio", tags=["audio"])

@router.post("/generate", response_model=AudioResponse)
async def generate_audio(request: AudioRequest):
    """텍스트를 Polly로 음성 변환"""
    try:
        job_id = f"audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        result = await audio_service.generate_audio(request.text, job_id, request.voice_id)
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return AudioResponse(
            job_id=job_id,
            audio_info=result,
            text_length=len(request.text),
            voice_id=request.voice_id,
            generated_at=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"음성 생성 실패: {str(e)}")

@router.get("/stream/{audio_id}")
async def stream_audio(audio_id: str):
    """S3에서 오디오 파일 스트리밍 재생"""
    try:
        audio_s3_key = await audio_service.find_audio_file(audio_id)
        return await audio_service.stream_audio(audio_s3_key)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"오디오 스트리밍 실패: {str(e)}") 