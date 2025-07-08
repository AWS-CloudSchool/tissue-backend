import time
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

class MetricsMiddleware(BaseHTTPMiddleware):
    """API 요청 메트릭을 수집하는 미들웨어"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # 요청 처리
        response = await call_next(request)
        
        # 처리 시간 계산
        process_time = time.time() - start_time
        
        try:
            # 메트릭 업데이트
            from app.monitoring.services.metrics_service import metrics_service
            
            # API 요청 메트릭 기록
            method = request.method
            path = request.url.path
            status_code = response.status_code
            
            # 경로 정규화 (파라미터 제거)
            normalized_path = self._normalize_path(path)
            
            logger.info(f"{method} {normalized_path} - {status_code} ({process_time:.3f}s)")
            
        except Exception as e:
            logger.warning(f"메트릭 수집 실패: {e}")
        
        # 응답 헤더에 처리 시간 추가
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
    
    def _normalize_path(self, path: str) -> str:
        """경로 정규화 (ID 등을 파라미터로 변환)"""
        import re
        
        # UUID 패턴을 {id}로 변환
        path = re.sub(r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '/{id}', path)
        
        # 일반적인 ID 패턴을 {id}로 변환
        path = re.sub(r'/\d+', '/{id}', path)
        
        return path