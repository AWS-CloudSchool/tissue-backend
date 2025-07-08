from fastapi import APIRouter, Response, HTTPException
from app.monitoring.services.metrics_service import metrics_service
from app.monitoring.models.metrics import (
    SystemMetrics, 
    HealthCheckResponse, 
    MetricsResponse
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """애플리케이션 헬스체크"""
    try:
        health_status = await metrics_service.get_health_check()
        return health_status
    except Exception as e:
        logger.error(f"헬스체크 실패: {e}")
        raise HTTPException(status_code=500, detail=f"헬스체크 실패: {str(e)}")

@router.get("/metrics")
async def get_prometheus_metrics():
    """Prometheus 형식의 메트릭 반환"""
    try:
        metrics_data = metrics_service.get_prometheus_metrics()
        return Response(
            content=metrics_data,
            media_type="text/plain; version=0.0.4; charset=utf-8"
        )
    except Exception as e:
        logger.error(f"메트릭 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"메트릭 조회 실패: {str(e)}")

@router.get("/system", response_model=SystemMetrics)
async def get_system_metrics():
    """시스템 메트릭 조회"""
    try:
        system_metrics = metrics_service.get_system_metrics()
        return system_metrics
    except Exception as e:
        logger.error(f"시스템 메트릭 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"시스템 메트릭 조회 실패: {str(e)}")

@router.get("/status")
async def get_service_status():
    """간단한 서비스 상태 확인"""
    return {
        "status": "healthy",
        "service": "tissue-backend",
        "version": "1.0.0",
        "timestamp": metrics_service.start_time
    }