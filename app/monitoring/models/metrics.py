from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime

class SystemMetrics(BaseModel):
    """시스템 메트릭 모델"""
    cpu_usage: float = Field(..., description="CPU 사용률 (%)")
    memory_usage: float = Field(..., description="메모리 사용률 (%)")
    disk_usage: float = Field(..., description="디스크 사용률 (%)")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="메트릭 수집 시간")

class APIMetrics(BaseModel):
    """API 메트릭 모델"""
    total_requests: int = Field(..., description="총 요청 수")
    success_requests: int = Field(..., description="성공 요청 수")
    error_requests: int = Field(..., description="에러 요청 수")
    average_response_time: float = Field(..., description="평균 응답 시간 (초)")
    requests_per_minute: float = Field(..., description="분당 요청 수")

class JobMetrics(BaseModel):
    """작업 메트릭 모델"""
    total_jobs: int = Field(..., description="총 작업 수")
    completed_jobs: int = Field(..., description="완료된 작업 수")
    failed_jobs: int = Field(..., description="실패한 작업 수")
    active_jobs: int = Field(..., description="진행 중인 작업 수")
    average_processing_time: float = Field(..., description="평균 처리 시간 (초)")

class HealthCheckResponse(BaseModel):
    """헬스체크 응답 모델"""
    status: str = Field(..., description="전체 상태 (healthy/degraded/unhealthy)")
    version: str = Field(..., description="애플리케이션 버전")
    uptime: float = Field(..., description="가동 시간 (초)")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="체크 시간")
    
    # 서비스별 상태
    database_status: str = Field(..., description="데이터베이스 상태")
    s3_status: str = Field(..., description="S3 상태")
    bedrock_status: Optional[str] = Field(None, description="Bedrock 상태")
    cognito_status: Optional[str] = Field(None, description="Cognito 상태")
    
    # 상세 서비스 정보
    services: Dict[str, Any] = Field(default_factory=dict, description="서비스별 상세 정보")

class MetricsResponse(BaseModel):
    """종합 메트릭 응답 모델"""
    system: SystemMetrics
    api: APIMetrics
    jobs: JobMetrics
    timestamp: datetime = Field(default_factory=datetime.utcnow)