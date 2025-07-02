import boto3
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from app.core.config import settings
from app.s3.services.s3_service import s3_service

class AudioService:
    def __init__(self):
        self.polly_client = boto3.client('polly', region_name=settings.AWS_REGION)
        self.voice_id = settings.POLLY_VOICE_ID

    async def generate_audio(self, text: str, job_id: str, voice_id: Optional[str] = None) -> Dict[str, Any]:
        """Polly를 사용하여 텍스트를 음성으로 변환"""
        try:
            voice_id = voice_id or self.voice_id
            
            # 텍스트 길이 확인 (Polly 제한: 3000자)
            if len(text) > 3000:
                # 텍스트를 청크로 분할
                chunks = [text[i:i+2800] for i in range(0, len(text), 2800)]
                audio_parts = []
                
                for i, chunk in enumerate(chunks):
                    response = self.polly_client.synthesize_speech(
                        Text=chunk,
                        OutputFormat='mp3',
                        VoiceId=voice_id,
                        Engine='neural' if voice_id in ['Seoyeon'] else 'standard'
                    )
                    audio_parts.append(response['AudioStream'].read())
                
                # 오디오 파트들을 하나로 합치기
                audio_data = b''.join(audio_parts)
                
            else:
                # 단일 요청으로 처리
                response = self.polly_client.synthesize_speech(
                    Text=text,
                    OutputFormat='mp3',
                    VoiceId=voice_id,
                    Engine='neural' if voice_id in ['Seoyeon'] else 'standard'
                )
                audio_data = response['AudioStream'].read()
            
            # S3에 오디오 파일 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            audio_s3_key = f"audio/{timestamp}_{job_id}.mp3"
            
            s3_service.s3_client.put_object(
                Bucket=s3_service.bucket_name,
                Key=audio_s3_key,
                Body=audio_data,
                ContentType='audio/mpeg',
                Metadata={
                    'job-id': job_id,
                    'voice-id': voice_id,
                    'created-at': timestamp,
                    'text-length': str(len(text))
                }
            )
            
            return {
                "success": True,
                "audio_s3_key": audio_s3_key,
                "bucket": s3_service.bucket_name,
                "voice_id": voice_id,
                "audio_url": f"s3://{s3_service.bucket_name}/{audio_s3_key}",
                "size": len(audio_data),
                "duration_estimate": len(text) / 200  # 대략적인 재생 시간 (초)
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Polly 음성 생성 실패: {str(e)}")

    async def stream_audio(self, audio_s3_key: str) -> StreamingResponse:
        """S3에서 오디오 파일 스트리밍"""
        try:
            response = s3_service.s3_client.get_object(
                Bucket=s3_service.bucket_name,
                Key=audio_s3_key
            )
            audio_stream = response['Body']
            
            def generate():
                try:
                    while True:
                        chunk = audio_stream.read(8192)
                        if not chunk:
                            break
                        yield chunk
                finally:
                    audio_stream.close()
            
            return StreamingResponse(
                generate(),
                media_type="audio/mpeg",
                headers={
                    "Content-Disposition": f"inline; filename={audio_s3_key.split('/')[-1]}",
                    "Accept-Ranges": "bytes"
                }
            )
            
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"오디오 파일을 찾을 수 없습니다: {str(e)}")

    async def find_audio_file(self, audio_id: str) -> str:
        """audio_id로 S3에서 오디오 파일 찾기"""
        if not audio_id.endswith('.mp3'):
            response = s3_service.s3_client.list_objects_v2(
                Bucket=s3_service.bucket_name,
                Prefix=f"audio/",
                MaxKeys=100
            )
            
            for obj in response.get('Contents', []):
                if audio_id in obj['Key'] and obj['Key'].endswith('.mp3'):
                    return obj['Key']
            
            raise HTTPException(status_code=404, detail=f"오디오 파일을 찾을 수 없습니다: {audio_id}")
        
        return f"audio/{audio_id}"

audio_service = AudioService() 