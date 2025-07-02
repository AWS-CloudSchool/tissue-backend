from pydantic import BaseModel
from typing import Optional

class AudioRequest(BaseModel):
    text: str
    voice_id: Optional[str] = "Seoyeon"

class AudioResponse(BaseModel):
    job_id: str
    audio_info: dict
    text_length: int
    voice_id: str
    generated_at: str

class AudioStreamResponse(BaseModel):
    audio_url: str
    content_type: str = "audio/mpeg"
    filename: str 