# app/services/youtube_reporter_service.py
import uuid
import json
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.analyze.workflow.youtube_workflow import YouTubeReporterWorkflow
from app.database.services.database_service import database_service
from app.s3.services.user_s3_service import user_s3_service
from app.s3.services.s3_service import s3_service
from app.audio.services.audio_service import audio_service
from app.analyze.services.state_manager import state_manager
from app.analyze.services.youtube_metadata_service import youtube_metadata_service
import logging
# 

logger = logging.getLogger(__name__)


class YouTubeReporterService:
    """YouTube Reporter 서비스 - taeho 백엔드 통합 버전"""

    def __init__(self):
        self.workflow = YouTubeReporterWorkflow()
        logger.info("YouTube Reporter 서비스 초기화 완료")

    async def create_analysis_job(self, user_id: str, youtube_url: str, db: Session, include_audio: bool = True) -> str:
        """새로운 YouTube 분석 작업 생성"""
        try:
            # 데이터베이스에 작업 생성
            job = database_service.create_analysis_job(
                db=db,
                user_id=user_id,
                job_type="youtube_reporter",
                input_data={"youtube_url": youtube_url, "include_audio": include_audio}
            )

            job_id = str(job.id)
            logger.info(f"✅ YouTube Reporter 작업 생성: {job_id}")
            return job_id

        except Exception as e:
            logger.error(f"작업 생성 실패: {str(e)}")
            raise

    async def process_youtube_analysis(self, job_id: str, user_id: str, youtube_url: str,
                                       db: Session, include_audio: bool = True) -> Dict[str, Any]:
        """YouTube 분석 실행"""
        try:
            logger.info(f"🎬 YouTube 분석 시작: {job_id}")

            # LangGraph 워크플로우 실행
            result = self.workflow.process(
                youtube_url=youtube_url,
                job_id=job_id,
                user_id=user_id
            )

            # 결과를 S3에 저장
            s3_info = await self._save_report_to_s3(
                user_id=user_id,
                job_id=job_id,
                result=result,
                youtube_url=youtube_url
            )

            # 오디오 생성 (요청 시)
            audio_info = None
            if include_audio and result.get("success"):
                try:
                    audio_info = await self._generate_audio_summary(
                        user_id=user_id,
                        job_id=job_id,
                        summary=result.get("summary", "")
                    )
                except Exception as e:
                    logger.warning(f"오디오 생성 실패 (무시됨): {e}")
                    audio_info = {"success": False, "error": str(e)}

            # 데이터베이스 업데이트
            database_service.update_job_status(
                db=db,
                job_id=job_id,
                status="completed" if result.get("success") else "failed",
                result_s3_key=s3_info.get("s3_key") if s3_info.get("success") else None
            )

            # S3 보고서 정보를 데이터베이스에 저장
            if s3_info.get("success"):
                database_service.create_user_report(
                    db=db,
                    job_id=job_id,
                    user_id=user_id,
                    title=result.get("title", "YouTube 분석 리포트"),
                    s3_key=s3_info["s3_key"],
                    file_type="json"
                )

            # 오디오 정보를 데이터베이스에 저장
            if audio_info and audio_info.get("success"):
                database_service.create_user_audio(
                    db=db,
                    job_id=job_id,
                    user_id=user_id,
                    s3_key=audio_info["audio_s3_key"],
                    duration=audio_info.get("duration_estimate", 0)
                )

            # Redis 정리
            try:
                state_manager.remove_user_active_job(user_id, job_id)
            except Exception as e:
                logger.warning(f"Redis 정리 실패 (무시됨): {e}")

            # 최종 결과 구성
            final_result = {
                **result,
                "s3_info": s3_info,
                "audio_info": audio_info,
                "job_id": job_id,
                "user_id": user_id,
                "completed_at": datetime.utcnow().isoformat()
            }

            logger.info(f"✅ YouTube 분석 완료: {job_id}")
            return final_result

        except Exception as e:
            logger.error(f"YouTube 분석 실패: {job_id} - {str(e)}")

            # 실패 시 데이터베이스 업데이트
            database_service.update_job_status(db=db, job_id=job_id, status="failed")

            # Redis 정리
            try:
                state_manager.remove_user_active_job(user_id, job_id)
            except Exception as redis_error:
                logger.warning(f"Redis 정리 실패 (무시됨): {redis_error}")

            raise

    async def _save_report_to_s3(self, user_id: str, job_id: str, result: Dict[str, Any],
                                 youtube_url: str) -> Dict[str, Any]:
        """리포트를 S3에 저장"""
        try:
            logger.info(f"📤 S3에 리포트 저장 중: {job_id}")

            # YouTube 메타데이터 추출
            youtube_metadata = youtube_metadata_service.get_youtube_metadata(youtube_url)
            
            # JSON 형태로 리포트 저장
            report_data = {
                "report": result,
                "metadata": {
                    "job_id": job_id,
                    "user_id": user_id,
                    "youtube_url": youtube_url,
                    "created_at": datetime.utcnow().isoformat(),
                    "service": "youtube_reporter",
                    "analysis_type": "youtube_analysis",
                    "status": "completed",
                    # YouTube 메타데이터 추가
                    "youtube_title": youtube_metadata.get("youtube_title", ""),
                    "youtube_channel": youtube_metadata.get("youtube_channel", ""),
                    "youtube_duration": youtube_metadata.get("youtube_duration", ""),
                    "youtube_thumbnail": youtube_metadata.get("youtube_thumbnail", ""),
                    "video_id": youtube_metadata.get("video_id", "")
                }
            }

            # S3에 업로드
            s3_key = user_s3_service.upload_user_report(
                user_id=user_id,
                job_id=job_id,
                content=json.dumps(report_data, ensure_ascii=False, indent=2),
                file_type="json"
            )



            logger.info(f"✅ S3 리포트 저장 완료: {s3_key}")
            return {
                "success": True,
                "s3_key": s3_key,
                "bucket": user_s3_service.bucket_name
            }

        except Exception as e:
            logger.error(f"S3 리포트 저장 실패: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }



    async def _generate_audio_summary(self, user_id: str, job_id: str, summary: str) -> Dict[str, Any]:
        """요약 내용을 음성으로 변환"""
        try:
            logger.info(f"🎵 오디오 생성 시작: {job_id}")

            # 요약이 너무 길면 줄임
            if len(summary) > 2500:
                summary = summary[:2500] + "..."

            # Polly로 음성 생성
            audio_result = await audio_service.generate_audio(
                text=summary,
                job_id=job_id,
                voice_id="Seoyeon"
            )

            if audio_result.get("success"):
                logger.info(f"✅ 오디오 생성 완료: {job_id}")
                return audio_result
            else:
                logger.error(f"오디오 생성 실패: {audio_result}")
                return {"success": False, "error": "음성 생성 실패"}

        except Exception as e:
            logger.error(f"오디오 생성 중 오류: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_job_progress(self, job_id: str) -> Dict[str, Any]:
        """작업 진행률 조회"""
        try:
            progress = state_manager.get_progress(job_id)
            return progress or {"progress": 0, "message": "진행률 정보 없음"}
        except Exception as e:
            logger.warning(f"진행률 조회 실패: {e}")
            return {"progress": 0, "message": "진행률 조회 실패"}


# 싱글톤 인스턴스
youtube_reporter_service = YouTubeReporterService()