import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

class SimpleStateManager:
    """Redis 없이 로깅만 하는 간단한 상태 관리자"""
    
    def update_progress(self, job_id: str, progress: int, message: str = ""):
        """진행률 업데이트 (로깅만)"""
        logger.info(f"Job {job_id}: {progress}% - {message}")
    
    def get_progress(self, job_id: str) -> Optional[dict]:
        """진행률 조회 (기본값 반환)"""
        return {"progress": 0, "message": "처리 중..."}

state_manager = SimpleStateManager()