# app/analyze/models/youtube_analyze.py
from pydantic import BaseModel, Field, HttpUrl
from typing import List, Dict, Any, Optional, Union
from datetime import datetime


class YouTubeReporterRequest(BaseModel):
    """YouTube Reporter 분석 요청 모델"""
    youtube_url: str = Field(..., description="분석할 YouTube 영상 URL")


class YouTubeReporterResponse(BaseModel):
    """YouTube Reporter 분석 응답 모델"""
    job_id: str = Field(..., description="작업 ID")
    status: str = Field(..., description="작업 상태")
    message: str = Field(..., description="상태 메시지")
    estimated_time: Optional[str] = Field(None, description="예상 소요 시간")


class VisualizationData(BaseModel):
    """시각화 데이터 모델"""
    type: str = Field(..., description="시각화 타입 (chart, network, flow, table)")
    config: Optional[Dict[str, Any]] = Field(None, description="Chart.js 설정 (chart 타입용)")
    data: Optional[Dict[str, Any]] = Field(None, description="vis.js/ReactFlow 데이터")
    options: Optional[Dict[str, Any]] = Field(None, description="시각화 옵션")
    headers: Optional[List[str]] = Field(None, description="테이블 헤더 (table 타입용)")
    rows: Optional[List[List[Any]]] = Field(None, description="테이블 데이터 (table 타입용)")
    styling: Optional[Dict[str, Any]] = Field(None, description="테이블 스타일링")


class ReportSection(BaseModel):
    """리포트 섹션 모델"""
    id: str = Field(..., description="섹션 ID")
    title: str = Field(..., description="섹션 제목")
    type: str = Field(..., description="섹션 타입 (text, visualization)")

    # 텍스트 섹션용 필드
    content: Optional[str] = Field(None, description="텍스트 내용")
    level: Optional[int] = Field(None, description="제목 레벨 (1: 대제목, 2: 중제목, 3: 소제목)")
    keywords: Optional[List[str]] = Field(default_factory=list, description="섹션 키워드")

    # 시각화 섹션용 필드
    visualization_type: Optional[str] = Field(None, description="시각화 타입")
    data: Optional[Union[VisualizationData, Dict[str, Any]]] = Field(None, description="시각화 데이터")
    insight: Optional[str] = Field(None, description="시각화 인사이트")
    purpose: Optional[str] = Field(None, description="시각화 목적")
    user_benefit: Optional[str] = Field(None, description="사용자 이익")
    error: Optional[str] = Field(None, description="에러 메시지")


class YouTubeReporterResult(BaseModel):
    """YouTube Reporter 최종 결과 모델"""
    success: bool = Field(..., description="분석 성공 여부")
    title: str = Field(..., description="리포트 제목")
    summary: str = Field(..., description="간단 요약")
    sections: List[ReportSection] = Field(..., description="리포트 섹션들")
    statistics: Dict[str, int] = Field(..., description="통계 정보")
    process_info: Dict[str, Any] = Field(..., description="처리 정보")
    s3_info: Optional[Dict[str, Any]] = Field(None, description="S3 저장 정보")

    created_at: Optional[datetime] = Field(None, description="생성 시간")


class JobProgressResponse(BaseModel):
    """작업 진행률 응답 모델"""
    job_id: str = Field(..., description="작업 ID")
    status: str = Field(..., description="작업 상태")
    progress: int = Field(..., description="진행률 (0-100)")
    message: str = Field(..., description="현재 상태 메시지")
    created_at: str = Field(..., description="작업 시작 시간")
    completed_at: Optional[str] = Field(None, description="작업 완료 시간")
    input_data: Dict[str, Any] = Field(..., description="입력 데이터")


class JobListResponse(BaseModel):
    """작업 목록 응답 모델"""
    jobs: List[Dict[str, Any]] = Field(..., description="작업 목록")
    total: int = Field(..., description="전체 작업 수")


class HealthCheckResponse(BaseModel):
    """헬스체크 응답 모델"""
    service: str = Field(..., description="서비스 이름")
    status: str = Field(..., description="서비스 상태")
    version: str = Field(..., description="서비스 버전")
    features: Dict[str, bool] = Field(..., description="지원 기능")
    supported_visualizations: List[str] = Field(..., description="지원 시각화 타입")


# 시각화 타입별 상세 모델들

class ChartVisualization(BaseModel):
    """Chart.js 시각화 모델"""
    type: str = Field("chart", description="시각화 타입")
    chart_type: str = Field(..., description="차트 타입 (bar, line, pie, radar, scatter)")
    data: Dict[str, Any] = Field(..., description="Chart.js 데이터")
    options: Dict[str, Any] = Field(..., description="Chart.js 옵션")


class NetworkVisualization(BaseModel):
    """vis.js 네트워크 시각화 모델"""
    type: str = Field("network", description="시각화 타입")
    nodes: List[Dict[str, Any]] = Field(..., description="네트워크 노드")
    edges: List[Dict[str, Any]] = Field(..., description="네트워크 엣지")
    options: Dict[str, Any] = Field(..., description="vis.js 옵션")


class FlowVisualization(BaseModel):
    """ReactFlow 시각화 모델"""
    type: str = Field("flow", description="시각화 타입")
    nodes: List[Dict[str, Any]] = Field(..., description="플로우 노드")
    edges: List[Dict[str, Any]] = Field(..., description="플로우 엣지")
    options: Dict[str, Any] = Field(..., description="ReactFlow 옵션")


class TableVisualization(BaseModel):
    """테이블 시각화 모델"""
    type: str = Field("table", description="시각화 타입")
    headers: List[str] = Field(..., description="테이블 헤더")
    rows: List[List[Any]] = Field(..., description="테이블 데이터")
    styling: Optional[Dict[str, Any]] = Field(None, description="테이블 스타일링")


# 에러 응답 모델

class ErrorResponse(BaseModel):
    """에러 응답 모델"""
    error: str = Field(..., description="에러 메시지")
    detail: Optional[str] = Field(None, description="상세 에러 정보")
    job_id: Optional[str] = Field(None, description="관련 작업 ID")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="에러 발생 시간")