from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class YouTubeSearchRequest(BaseModel):
    """YouTube 검색 요청"""
    query: str = Field(..., description="검색어")
    max_results: int = Field(10, description="최대 결과 수", ge=1, le=50)

class YouTubeVideoInfo(BaseModel):
    video_id: str = Field(..., description="비디오 ID")
    title: str = Field(..., description="비디오 제목")
    description: str = Field(..., description="비디오 설명")
    channel_title: str = Field(..., description="채널 제목")
    published_at: str = Field(..., description="게시일")
    view_count: int = Field(..., description="조회수")
    like_count: int = Field(..., description="좋아요 수")
    comment_count: int = Field(..., description="댓글 수")
    duration: str = Field(..., description="재생 시간")
    thumbnail_url: str = Field(..., description="썸네일 URL")

class YouTubeSearchResponse(BaseModel):
    query: str = Field(..., description="검색 쿼리")
    total_results: int = Field(..., description="전체 검색 결과 수")
    videos: List[YouTubeVideoInfo] = Field(..., description="검색된 비디오 목록")
    next_page_token: Optional[str] = Field(None, description="다음 페이지 토큰")