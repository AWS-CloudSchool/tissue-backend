from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from app.database.models.database_models import UserAnalysisJob, UserReport, UserAudioFile
from app.database.core.database import get_db

class DatabaseService:
    def create_analysis_job(self, db: Session, user_id: str, job_type: str, input_data: dict) -> UserAnalysisJob:
        """분석 작업 생성"""
        job = UserAnalysisJob(
            user_id=user_id,
            job_type=job_type,
            input_data=input_data,
            status="processing"
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job
    
    def update_job_status(self, db: Session, job_id: str, status: str, result_s3_key: str = None):
        """작업 상태 업데이트"""
        # job_id가 str이면 UUID로 변환
        if isinstance(job_id, str):
            try:
                job_id_uuid = uuid.UUID(job_id)
            except Exception:
                job_id_uuid = job_id
        else:
            job_id_uuid = job_id
        job = db.query(UserAnalysisJob).filter(UserAnalysisJob.id == job_id_uuid).first()
        if job:
            job.status = status
            if result_s3_key:
                job.result_s3_key = result_s3_key
            if status == "completed":
                job.completed_at = datetime.utcnow()
            db.commit()
    
    def get_user_jobs(self, db: Session, user_id: str, limit: int = 50) -> List[UserAnalysisJob]:
        """사용자 작업 목록 조회"""
        return db.query(UserAnalysisJob).filter(
            UserAnalysisJob.user_id == user_id
        ).order_by(UserAnalysisJob.created_at.desc()).limit(limit).all()
    
    def get_job_by_id(self, db: Session, job_id: str, user_id: str) -> Optional[UserAnalysisJob]:
        """작업 ID로 조회 (사용자 권한 확인)"""
        # job_id가 str이면 UUID로 변환
        if isinstance(job_id, str):
            try:
                job_id_uuid = uuid.UUID(job_id)
            except Exception:
                job_id_uuid = job_id
        else:
            job_id_uuid = job_id
        return db.query(UserAnalysisJob).filter(
            UserAnalysisJob.id == job_id_uuid,
            UserAnalysisJob.user_id == user_id
        ).first()
    
    def create_user_report(self, db: Session, job_id: str, user_id: str, title: str, s3_key: str, file_type: str) -> UserReport:
        """사용자 보고서 생성"""
        # job_id, user_id가 str이면 UUID로 변환
        if isinstance(job_id, str):
            job_id = uuid.UUID(job_id)
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)
        report = UserReport(
            job_id=job_id,
            user_id=user_id,
            title=title,
            s3_key=s3_key,
            file_type=file_type
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        return report
    
    def create_user_audio(self, db: Session, job_id: str, user_id: str, s3_key: str, duration: int) -> UserAudioFile:
        """사용자 오디오 파일 생성"""
        # job_id, user_id가 str이면 UUID로 변환
        if isinstance(job_id, str):
            job_id = uuid.UUID(job_id)
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)
        audio = UserAudioFile(
            job_id=job_id,
            user_id=user_id,
            s3_key=s3_key,
            duration=duration
        )
        db.add(audio)
        db.commit()
        db.refresh(audio)
        return audio
    
    def get_user_reports(self, db: Session, user_id: str, limit: int = 50) -> List[UserReport]:
        """사용자 보고서 목록"""
        return db.query(UserReport).filter(
            UserReport.user_id == user_id
        ).order_by(UserReport.created_at.desc()).limit(limit).all()
    
    def get_user_audio_files(self, db: Session, user_id: str, limit: int = 50) -> List[UserAudioFile]:
        """사용자 오디오 파일 목록"""
        return db.query(UserAudioFile).filter(
            UserAudioFile.user_id == user_id
        ).order_by(UserAudioFile.created_at.desc()).limit(limit).all()
    
    def delete_job(self, db: Session, job_id: str, user_id: str) -> bool:
        """작업 삭제 (사용자 권한 확인)"""
        # job_id가 str이면 UUID로 변환
        if isinstance(job_id, str):
            try:
                job_id_uuid = uuid.UUID(job_id)
            except Exception:
                job_id_uuid = job_id
        else:
            job_id_uuid = job_id
        job = db.query(UserAnalysisJob).filter(
            UserAnalysisJob.id == job_id_uuid,
            UserAnalysisJob.user_id == user_id
        ).first()
        
        if job:
            # 관련 보고서와 오디오 파일도 삭제
            db.query(UserReport).filter(UserReport.job_id == job_id_uuid).delete()
            db.query(UserAudioFile).filter(UserAudioFile.job_id == job_id_uuid).delete()
            db.delete(job)
            db.commit()
            return True
        return False

database_service = DatabaseService()

# 비동기 함수들 (프론트엔드 호환성을 위해)
async def get_user_jobs(username: str):
    """사용자 작업 목록 조회 (비동기)"""
    db = next(get_db())
    try:
        jobs = database_service.get_user_jobs(db, username)
        return [{
            "id": job.id,
            "status": job.status,
            "job_type": job.job_type,
            "input_data": job.input_data,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None
        } for job in jobs]
    finally:
        db.close()

async def get_job_progress(job_id: str):
    """작업 진행률 조회 (비동기)"""
    # Redis나 다른 저장소에서 진행률 정보를 가져오는 로직
    # 현재는 기본값 반환
    return {
        "progress": 50,
        "message": "분석 진행 중...",
        "status": "processing"
    }