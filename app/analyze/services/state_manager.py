import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

class SimpleStateManager:
    """메모리 기반 상태 관리자"""
    
    def __init__(self):
        self._progress_store = {}
    
    def update_progress(self, job_id: str, progress: int, message: str = ""):
        """진행률 업데이트"""
        self._progress_store[job_id] = {
            "progress": progress,
            "message": message,
            "updated_at": datetime.utcnow().isoformat()
        }
        logger.info(f"Job {job_id}: {progress}% - {message}")
    
    def get_progress(self, job_id: str) -> Optional[dict]:
        """진행률 조회"""
        return self._progress_store.get(job_id, {"progress": 0, "message": "처리 중..."})
    
    def remove_user_active_job(self, user_id: str, job_id: str):
        """작업 완료 시 진행률 정보 제거"""
        if job_id in self._progress_store:
            del self._progress_store[job_id]
            logger.info(f"진행률 정보 제거: {job_id}")
    
    def cancel_job(self, job_id: str):
        """작업 취소 요청"""
        if job_id in self._progress_store:
            self._progress_store[job_id]["cancelled"] = True
            self._progress_store[job_id]["message"] = "취소 요청됨"
            logger.info(f"작업 취소 요청: {job_id}")
    
    def is_cancelled(self, job_id: str) -> bool:
        """작업 취소 여부 확인"""
        return self._progress_store.get(job_id, {}).get("cancelled", False)

state_manager = SimpleStateManager()