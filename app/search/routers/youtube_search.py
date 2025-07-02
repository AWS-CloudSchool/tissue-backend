from fastapi import APIRouter, HTTPException, Body
from app.search.services.youtube_search_service import youtube_search_service
from app.search.models.youtube_search import YouTubeSearchRequest, YouTubeSearchResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["YouTube Search"])

@router.post("/youtube")
async def search_youtube_videos_post(
    request: YouTubeSearchRequest = Body(...)
) -> YouTubeSearchResponse:
    """
    YouTube 비디오 검색 (POST)
    
    - **query**: 검색할 키워드
    - **max_results**: 최대 결과 수 (1-50)
    """
    try:
        logger.info(f"YouTube 검색 요청 (POST): query={request.query}, max_results={request.max_results}")
        
        result = await youtube_search_service.search_videos(
            query=request.query,
            max_results=request.max_results
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"YouTube 검색 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"YouTube 검색 실패: {str(e)}"
        )