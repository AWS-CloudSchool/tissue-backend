import time
import re
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)

class MetricsMiddleware(BaseHTTPMiddleware):
    """Prometheus 메트릭 수집 미들웨어"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # 메트릭 수집에서 제외할 경로
        skip_paths = ["/metrics", "/health", "/docs", "/openapi.json"]
        if request.url.path in skip_paths:
            return await call_next(request)
        
        # 10% 확률로 시스템 메트릭 업데이트
        if hash(str(time.time())) % 10 == 0:
            try:
                from app.metrics import update_system_metrics
                update_system_metrics()
            except Exception as e:
                logger.warning(f"시스템 메트릭 업데이트 실패: {e}")
        
        response = None
        status_code = "500"
        
        try:
            response = await call_next(request)
            status_code = str(response.status_code)
        except Exception as e:
            logger.error(f"요청 처리 중 오류: {e}")
            status_code = "500"
            # 기본 에러 응답 생성
            response = Response(
                content=f"Internal Server Error: {str(e)}",
                status_code=500,
                media_type="text/plain"
            )
        
        # 메트릭 수집
        try:
            from app.metrics import api_request_duration, api_request_count
            
            duration = time.time() - start_time
            method = request.method
            endpoint = self._normalize_path(request.url.path)
            
            api_request_duration.labels(
                method=method,
                endpoint=endpoint, 
                status_code=status_code
            ).observe(duration)
            
            api_request_count.labels(
                method=method,
                endpoint=endpoint,
                status_code=status_code  
            ).inc()
            
        except Exception as e:
            logger.warning(f"메트릭 수집 실패: {e}")
        
        return response
    
    def _normalize_path(self, path: str) -> str:
        """경로 정규화 (ID 제거)"""
        try:
            # UUID 패턴 제거 (예: /jobs/12345678-1234-1234-1234-123456789012 -> /jobs/:id)
            path = re.sub(r'/[0-9a-f-]{36}', '/:id', path)
            
            # 숫자 패턴 제거 (예: /files/123 -> /files/:id)
            path = re.sub(r'/\d+', '/:id', path)
            
            # 파일 확장자나 특수 문자가 포함된 동적 경로 처리
            path = re.sub(r'/[^/]+\.(json|pdf|mp3|txt|csv)$', '/:file', path)
            
            return path
        except Exception as e:
            logger.warning(f"경로 정규화 실패: {e}")
            return path