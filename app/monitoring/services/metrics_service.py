import time
import psutil
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from app.core.config import settings
from app.monitoring.models.metrics import SystemMetrics, HealthCheckResponse
import logging

logger = logging.getLogger(__name__)

class MetricsService:
    def __init__(self):
        self.start_time = time.time()
    
    def get_prometheus_metrics(self) -> str:
        """Prometheus 형식의 메트릭 반환"""
        try:
            # 시스템 메트릭 업데이트
            self.update_system_metrics()
            return generate_latest().decode('utf-8')
        except Exception as e:
            logger.error(f"메트릭 생성 실패: {e}")
            return "# 메트릭 생성 실패"
    
    def update_system_metrics(self):
        """시스템 메트릭 업데이트"""
        try:
            from app.metrics import cpu_usage, memory_usage
            cpu_usage.set(psutil.cpu_percent())
            memory_usage.set(psutil.virtual_memory().percent)
        except Exception as e:
            logger.warning(f"시스템 메트릭 업데이트 실패: {e}")
    
    def get_system_metrics(self) -> SystemMetrics:
        """시스템 메트릭 반환"""
        return SystemMetrics(
            cpu_usage=psutil.cpu_percent(),
            memory_usage=psutil.virtual_memory().percent,
            disk_usage=psutil.disk_usage('/').percent
        )
    
    async def get_health_check(self) -> HealthCheckResponse:
        """헬스체크 정보 반환"""
        uptime = time.time() - self.start_time
        
        # 데이터베이스 상태 확인
        db_status = await self._check_database()
        
        # S3 상태 확인
        s3_status = await self._check_s3()
        
        # 전체 상태 결정
        overall_status = "healthy" if db_status and s3_status else "degraded"
        
        return HealthCheckResponse(
            status=overall_status,
            version=settings.VERSION,
            uptime=uptime,
            database_status="healthy" if db_status else "unhealthy",
            s3_status="healthy" if s3_status else "unhealthy",
            services={
                "database": db_status,
                "s3": s3_status,
                "bedrock": True,  # 실제로는 확인 로직 필요
                "cognito": True   # 실제로는 확인 로직 필요
            }
        )
    
    async def _check_database(self) -> bool:
        """데이터베이스 연결 상태 확인"""
        try:
            from app.database.core.database import engine
            from sqlalchemy import text
            
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"데이터베이스 헬스체크 실패: {e}")
            return False
    
    async def _check_s3(self) -> bool:
        """S3 연결 상태 확인"""
        try:
            from app.s3.services.s3_service import s3_service
            
            # 간단한 S3 작업으로 상태 확인
            s3_service.s3_client.head_bucket(Bucket=s3_service.bucket_name)
            return True
        except Exception as e:
            logger.error(f"S3 헬스체크 실패: {e}")
            return False

metrics_service = MetricsService()