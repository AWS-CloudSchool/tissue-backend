import re
import requests
from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class YouTubeMetadataService:
    def __init__(self):
        pass
    
    def extract_video_id(self, youtube_url: str) -> Optional[str]:
        """YouTube URL에서 비디오 ID 추출"""
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([^&\n?#]+)',
            r'youtube\.com/v/([^&\n?#]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, youtube_url)
            if match:
                return match.group(1)
        return None
    
    def get_youtube_metadata(self, youtube_url: str) -> Dict[str, Any]:
        """YouTube URL에서 메타데이터 추출"""
        try:
            video_id = self.extract_video_id(youtube_url)
            if not video_id:
                logger.warning(f"비디오 ID 추출 실패: {youtube_url}")
                return self._get_default_metadata(youtube_url)
            
            # YouTube oEmbed API 사용 (공식 API, 키 불필요)
            oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
            
            try:
                response = requests.get(oembed_url, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                # 썸네일 URL 생성
                thumbnail_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
                
                return {
                    "youtube_title": data.get("title", "제목 없음"),
                    "youtube_channel": data.get("author_name", "채널 없음"),
                    "youtube_thumbnail": thumbnail_url,
                    "youtube_url": youtube_url,
                    "youtube_duration": "정보 없음",  # oEmbed에서 제공하지 않음
                    "video_id": video_id,
                    "created_at": datetime.utcnow().isoformat()
                }
                
            except Exception as e:
                logger.warning(f"oEmbed API 호출 실패: {e}")
                return self._get_default_metadata(youtube_url, video_id)
                
        except Exception as e:
            logger.error(f"YouTube 메타데이터 추출 실패: {e}")
            return self._get_default_metadata(youtube_url)
    
    def _get_default_metadata(self, youtube_url: str, video_id: str = None) -> Dict[str, Any]:
        """기본 메타데이터 생성"""
        thumbnail_url = ""
        if video_id:
            thumbnail_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
        
        return {
            "youtube_title": "YouTube 영상",
            "youtube_channel": "알 수 없음",
            "youtube_thumbnail": thumbnail_url,
            "youtube_url": youtube_url,
            "youtube_duration": "정보 없음",
            "video_id": video_id or "",
            "created_at": datetime.utcnow().isoformat()
        }

youtube_metadata_service = YouTubeMetadataService()