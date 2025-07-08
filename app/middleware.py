# app/middleware.py (새 파일)
import time
import re
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.metrics import api_request_duration, api_request_count, update_system_metrics

class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # 10% 확률로 시스템 메트릭 업데이트
        if hash(str(time.time())) % 10 == 0:
            update_system_metrics()
        
        try:
            response = await call_next(request)
            status_code = str(response.status_code)
        except Exception:
            status_code = "500"
            raise
        
        # 메트릭 수집
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
        
        return response
    
    def _normalize_path(self, path: str) -> str:
        """경로 정규화 (ID 제거)"""
        # UUID 패턴 제거
        path = re.sub(r'/[0-9a-f-]{36}', '/:id', path)
        # 숫자 패턴 제거  
        path = re.sub(r'/\d+', '/:id', path)
        return path