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
        logger.info("메트릭 서비스 초기화 완료")
    
    def get_prometheus_metrics(self) -> str:
        """Prometheus 형식의 메트릭 반환"""
        try:
            # 시스템 메트릭 업데이트
            self.update_system_metrics()
            
            # 활성 작업 수 업데이트
            self.update_active_jobs_count()
            
            metrics_output = generate_latest().decode('utf-8')
            logger.info("✅ Prometheus 메트릭 생성 완료")
            return metrics_output
        except Exception as e:
            logger.error(f"❌ 메트릭 생성 실패: {e}")
            return "# 메트릭 생성 실패"
    
    def update_system_metrics(self):
        """시스템 메트릭 업데이트"""
        try:
            from app.monitoring.services.metrics import cpu_usage, memory_usage, disk_usage
            
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory_percent = psutil.virtual_memory().percent
            disk_percent = psutil.disk_usage('/').percent
            
            cpu_usage.set(cpu_percent)
            memory_usage.set(memory_percent)
            disk_usage.set(disk_percent)
            
            logger.debug(f"시스템 메트릭 업데이트: CPU={cpu_percent}%, MEM={memory_percent}%, DISK={disk_percent}%")
            
        except ImportError as e:
            logger.error(f"❌ 시스템 메트릭 모듈 import 실패: {e}")
        except Exception as e:
            logger.error(f"❌ 시스템 메트릭 업데이트 실패: {e}")
    
    def update_active_jobs_count(self):
        """활성 작업 수 업데이트"""
        try:
            from app.monitoring.services.metrics import active_jobs
            from app.analyze.services.state_manager import state_manager
            
            # 현재 진행 중인 작업 수 계산
            active_count = len([
                job_id for job_id, progress in state_manager._progress_store.items()
                if not progress.get("cancelled", False) and progress.get("progress", 0) < 100
            ])
            
            active_jobs.set(active_count)
            logger.debug(f"활성 작업 수 업데이트: {active_count}")
            
        except ImportError as e:
            logger.error(f"❌ 활성 작업 메트릭 모듈 import 실패: {e}")
        except Exception as e:
            logger.error(f"❌ 활성 작업 메트릭 업데이트 실패: {e}")
    
    def get_system_metrics(self) -> SystemMetrics:
        """시스템 메트릭 반환"""
        try:
            return SystemMetrics(
                cpu_usage=psutil.cpu_percent(),
                memory_usage=psutil.virtual_memory().percent,
                disk_usage=psutil.disk_usage('/').percent
            )
        except Exception as e:
            logger.error(f"❌ 시스템 메트릭 조회 실패: {e}")
            return SystemMetrics(cpu_usage=0, memory_usage=0, disk_usage=0)
    
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
            logger.debug("✅ 데이터베이스 헬스체크 성공")
            return True
        except Exception as e:
            logger.error(f"❌ 데이터베이스 헬스체크 실패: {e}")
            return False
    
    async def _check_s3(self) -> bool:
        """S3 연결 상태 확인"""
        try:
            from app.s3.services.s3_service import s3_service
            
            # 간단한 S3 작업으로 상태 확인
            s3_service.s3_client.head_bucket(Bucket=s3_service.bucket_name)
            logger.debug("✅ S3 헬스체크 성공")
            return True
        except Exception as e:
            logger.error(f"❌ S3 헬스체크 실패: {e}")
            return False

metrics_service = MetricsService()