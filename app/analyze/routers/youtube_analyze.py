# app/analyze/routers/youtube_analyze.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.analyze.core.auth import get_current_user
from app.database.core.database import get_db
from app.analyze.services.youtube_analyze_service import youtube_reporter_service
from app.database.services.database_service import database_service
from app.analyze.models.youtube_analyze import YouTubeReporterRequest, YouTubeReporterResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analyze", tags=["YouTube Reporter"])


async def run_youtube_analysis(job_id: str, user_id: str, youtube_url: str, db: Session):
    """백그라운드에서 YouTube 분석 실행"""
    try:
        await youtube_reporter_service.process_youtube_analysis(
            job_id=job_id,
            user_id=user_id,
            youtube_url=youtube_url,
            db=db
        )
    except Exception as e:
        logger.error(f"백그라운드 YouTube 분석 실패: {job_id} - {str(e)}")


@router.post("/youtube", response_model=YouTubeReporterResponse)
async def create_youtube_analysis(
        request: YouTubeReporterRequest,
        background_tasks: BackgroundTasks,
        current_user: dict = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    YouTube 영상 분석 및 스마트 시각화 리포트 생성

    - **youtube_url**: 분석할 YouTube 영상 URL
    - **include_audio**: 음성 요약 생성 여부 (선택사항)
    - **options**: 추가 옵션 (선택사항)
    """
    try:
        user_id = current_user["user_id"]
        youtube_url = request.youtube_url

        logger.info(f"🎬 YouTube Reporter 분석 요청: {youtube_url} (User: {user_id})")

        # 1. 작업 생성
        job_id = await youtube_reporter_service.create_analysis_job(
            user_id=user_id,
            youtube_url=youtube_url,
            db=db
        )

        # 2. 백그라운드에서 분석 실행
        background_tasks.add_task(
            run_youtube_analysis,
            job_id=job_id,
            user_id=user_id,
            youtube_url=youtube_url,
            db=db
        )

        return YouTubeReporterResponse(
            job_id=job_id,
            status="processing",
            message="🚀 YouTube Reporter 분석이 시작되었습니다. AI가 영상을 분석하고 스마트 시각화를 생성하는 중입니다...",
            estimated_time="2-5분"
        )

    except Exception as e:
        logger.error(f"YouTube Reporter 분석 요청 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"YouTube Reporter 분석 시작 실패: {str(e)}"
        )


@router.get("/jobs/{job_id}/status")
async def get_analysis_status(
        job_id: str,
        current_user: dict = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    YouTube Reporter 분석 작업 상태 조회

    - **job_id**: 작업 ID
    """
    try:
        user_id = current_user["user_id"]

        # 데이터베이스에서 작업 정보 조회
        job = database_service.get_job_by_id(db, job_id, user_id)
        if not job:
            raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")

        # 진행률 정보 조회
        progress_info = youtube_reporter_service.get_job_progress(job_id)

        return {
            "job_id": job_id,
            "status": job.status,
            "progress": progress_info.get("progress", 0),
            "message": progress_info.get("message", f"상태: {job.status}"),
            "created_at": job.created_at.isoformat(),
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "input_data": job.input_data
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"작업 상태 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"작업 상태 조회 실패: {str(e)}"
        )


@router.get("/jobs/{job_id}/result")
async def get_analysis_result(
        job_id: str,
        current_user: dict = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    YouTube Reporter 분석 결과 조회

    - **job_id**: 작업 ID
    """
    try:
        user_id = current_user["user_id"]

        # 작업 상태 확인
        job = database_service.get_job_by_id(db, job_id, user_id)
        if not job:
            raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")

        if job.status == "processing":
            raise HTTPException(
                status_code=202,
                detail="아직 분석 중입니다. 잠시 후 다시 시도해주세요."
            )
        elif job.status == "failed":
            raise HTTPException(
                status_code=500,
                detail="분석이 실패했습니다."
            )
        elif job.status != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"작업 상태: {job.status}"
            )

        # 보고서 조회
        reports = database_service.get_user_reports(db, user_id)
        job_report = next((r for r in reports if str(r.job_id) == job_id), None)

        if not job_report:
            raise HTTPException(status_code=404, detail="분석 결과를 찾을 수 없습니다")

        # S3에서 리포트 내용 가져오기
        from app.s3.services.user_s3_service import user_s3_service
        import json

        try:
            download_url = user_s3_service.get_presigned_url(job_report.s3_key)
            
            # S3에서 리포트 내용 조회
            report_content = None
            try:
                content = user_s3_service.get_file_content(job_report.s3_key)
                if content and job_report.file_type == 'json':
                    report_content = json.loads(content)
                    logger.info(f"S3에서 리포트 내용 조회: {job_id}")
            except Exception as e:
                logger.warning(f"리포트 내용 조회 실패: {e}")

            return {
                "job_id": job_id,
                "status": "completed",
                "title": job_report.title,
                "created_at": job_report.created_at.isoformat(),
                "download_url": download_url,
                "s3_key": job_report.s3_key,
                "file_type": job_report.file_type,
                "content": report_content,  # S3에서 조회한 리포트 내용
                "message": "✅ YouTube Reporter 분석이 완료되었습니다!"
            }

        except Exception as e:
            logger.error(f"S3 결과 조회 실패: {e}")
            raise HTTPException(
                status_code=500,
                detail="분석 결과 조회 중 오류가 발생했습니다"
            )


    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"분석 결과 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"분석 결과 조회 실패: {str(e)}"
        )


@router.get("/jobs")
async def list_my_analyses(
        current_user: dict = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    내 YouTube Reporter 분석 작업 목록 조회 (로그인 선택적)
    """
    try:
        # 로그인하지 않은 경우 빈 목록 반환
        if not current_user:
            return {"jobs": [], "total": 0}
            
        user_id = current_user["user_id"]

        # YouTube Reporter 작업만 필터링
        all_jobs = database_service.get_user_jobs(db, user_id)
        youtube_jobs = [job for job in all_jobs if job.job_type == "youtube_reporter"]

        return {
            "jobs": [
                {
                    "id": str(job.id),
                    "status": job.status,
                    "youtube_url": job.input_data.get("youtube_url", ""),
                    "created_at": job.created_at.isoformat(),
                    "completed_at": job.completed_at.isoformat() if job.completed_at else None
                }
                for job in youtube_jobs
            ],
            "total": len(youtube_jobs)
        }

    except Exception as e:
        logger.error(f"작업 목록 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"작업 목록 조회 실패: {str(e)}"
        )


@router.delete("/jobs/{job_id}")
async def delete_analysis_job(
        job_id: str,
        current_user: dict = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    YouTube Reporter 분석 작업 삭제

    - **job_id**: 삭제할 작업 ID
    """
    try:
        user_id = current_user["user_id"]

        # 작업 삭제
        success = database_service.delete_job(db, job_id, user_id)
        if not success:
            raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")

        return {"message": f"작업 {job_id}이 삭제되었습니다"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"작업 삭제 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"작업 삭제 실패: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """YouTube Reporter 서비스 상태 확인"""
    try:
        return {
            "service": "YouTube Reporter",
            "status": "healthy",
            "version": "1.0.0",
            "features": {
                "smart_visualization": True,
                "comprehensive_summary": True,
                "context_analysis": True,
                "audio_generation": True
            },
            "supported_visualizations": [
                "charts", "network_diagrams", "flow_charts", "tables"
            ]
        }
    except Exception as e:
        logger.error(f"헬스체크 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"서비스 상태 확인 실패: {str(e)}"
        )