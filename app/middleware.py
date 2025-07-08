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
            method = request.method
            path = request.url.path
            status_code = str(response.status_code)
            
            # 경로 정규화 (파라미터 제거)
            normalized_path = self._normalize_path(path)
            
            # API 요청 메트릭 기록
            try:
                from app.monitoring.services.metrics import api_request_count, api_request_duration
                
                api_request_count.labels(
                    method=method,
                    endpoint=normalized_path,
                    status_code=status_code
                ).inc()
                
                api_request_duration.labels(
                    method=method,
                    endpoint=normalized_path,
                    status_code=status_code
                ).observe(process_time)
                
                logger.info(f"✅ API 메트릭 업데이트: {method} {normalized_path} {status_code} ({process_time:.3f}s)")
                
            except ImportError as e:
                logger.error(f"❌ 메트릭 모듈 import 실패: {e}")
            except Exception as e:
                logger.error(f"❌ 메트릭 업데이트 실패: {e}")
            
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
        
        # S3 키 패턴 정규화
        path = re.sub(r'/[a-zA-Z0-9_-]+\.(json|txt|mp3|pdf)', '/{file}', path)
        
        return path