from typing import List
from datetime import datetime
from fastapi import HTTPException
from youtube_search import YoutubeSearch
from app.search.models.youtube_search import YouTubeSearchResponse, YouTubeVideoInfo
import re
import logging

logger = logging.getLogger(__name__)

class YouTubeSearchService:
    def __init__(self):
        pass

    async def search_videos(self, query: str, max_results: int = 10) -> YouTubeSearchResponse:
        """YouTube 비디오 검색"""
        try:
            logger.info(f"YouTube 검색 시작: query={query}, max_results={max_results}")
            
            # 검색 요청
            search_results = YoutubeSearch(
                query,
                max_results=max_results
            ).to_dict()

            logger.info(f"검색 결과 수: {len(search_results)}")

            # 응답 생성
            videos = []
            for item in search_results:
                try:
                    # 조회수 문자열을 숫자로 변환
                    views = item.get('views', '0')
                    views = int(re.sub(r'[^\d]', '', views)) if views else 0

                    # 재생 시간 문자열을 초 단위로 변환
                    duration = item.get('duration', '0:00')
                    duration_seconds = 0
                    
                    if duration and ':' in duration:
                        try:
                            duration_parts = duration.split(':')
                            if len(duration_parts) == 2:  # MM:SS
                                minutes, seconds = map(int, duration_parts)
                                duration_seconds = minutes * 60 + seconds
                            elif len(duration_parts) == 3:  # HH:MM:SS
                                hours, minutes, seconds = map(int, duration_parts)
                                duration_seconds = hours * 3600 + minutes * 60 + seconds
                        except ValueError:
                            duration_seconds = 0

                    # YouTube Shorts 필터링 (60초 이하 제외)
                    if duration_seconds > 0 and duration_seconds <= 60:
                        logger.info(f"Shorts 영상 제외: {item['title']} ({duration_seconds}초)")
                        continue

                    video = YouTubeVideoInfo(
                        video_id=item['id'],
                        title=item['title'],
                        description=item.get('description', ''),
                        channel_title=item['channel'],
                        published_at=datetime.now().isoformat(),
                        view_count=views,
                        like_count=0,
                        comment_count=0,
                        duration=str(duration_seconds),
                        thumbnail_url=item['thumbnails'][0] if item.get('thumbnails') else ''
                    )
                    videos.append(video)
                except Exception as e:
                    logger.error(f"비디오 정보 변환 중 오류: {str(e)}")
                    continue

            logger.info(f"성공적으로 변환된 비디오 수: {len(videos)}")

            return YouTubeSearchResponse(
                query=query,
                total_results=len(videos),
                videos=videos,
                next_page_token=None
            )

        except Exception as e:
            logger.error(f"YouTube 검색 실패: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"YouTube 검색 실패: {str(e)}"
            )

youtube_search_service = YouTubeSearchService()