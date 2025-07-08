# app/agents/caption_agent.py
import requests
from langchain_core.runnables import Runnable
from app.core.config import settings
from app.analyze.services.state_manager import state_manager
from app.s3.services.user_s3_service import user_s3_service
from app.decorators import track_youtube_job, track_api_performance
import logging

logger = logging.getLogger(__name__)


class CaptionAgent(Runnable):
    def __init__(self):
        self.api_key = settings.VIDCAP_API_KEY
        self.api_url = "https://vidcap.xyz/api/v1/youtube/caption"

    @track_youtube_job("caption_extraction")
    @track_api_performance("/analyze/caption")
    def invoke(self, state: dict, config=None):
        youtube_url = state.get("youtube_url")
        job_id = state.get("job_id")
        user_id = state.get("user_id")

        logger.info(f"🎬 자막 추출 시작: {youtube_url}")

        # 진행률 업데이트
        if job_id:
            try:
                state_manager.update_progress(job_id, 20, "📝 자막 추출 중...")
            except Exception as e:
                logger.warning(f"진행률 업데이트 실패 (무시됨): {e}")

        try:
            response = requests.get(
                self.api_url,
                params={"url": youtube_url, "locale": "ko"},
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=30  # 타임아웃 추가
            )
            response.raise_for_status()

            caption = response.json().get("data", {}).get("content", "")
            if not caption:
                caption = "자막을 찾을 수 없습니다."

            # 자막을 S3에 .txt 파일로 저장
            if job_id and user_id and caption != "자막을 찾을 수 없습니다.":
                try:
                    s3_key = f"captions/{user_id}/{job_id}_caption.txt"
                    user_s3_service.upload_text_content(s3_key, caption)
                    logger.info(f"📄 자막 S3 저장 완료: {s3_key}")
                    
                    # S3 업로드 성공 메트릭 수동 업데이트
                    try:
                        from app.monitoring.services.metrics import s3_uploads_total
                        s3_uploads_total.labels(status='success').inc()
                        logger.info("✅ S3 업로드 성공 메트릭 업데이트")
                    except Exception as metric_error:
                        logger.error(f"❌ S3 메트릭 업데이트 실패: {metric_error}")
                        
                except Exception as e:
                    logger.warning(f"자막 S3 저장 실패 (무시됨): {e}")
                    
                    # S3 업로드 실패 메트릭 수동 업데이트
                    try:
                        from app.monitoring.services.metrics import s3_uploads_total
                        s3_uploads_total.labels(status='failed').inc()
                        logger.info("🔴 S3 업로드 실패 메트릭 업데이트")
                    except Exception as metric_error:
                        logger.error(f"❌ S3 실패 메트릭 업데이트 실패: {metric_error}")

            logger.info(f"✅ 자막 추출 완료: {len(caption)}자")
            
            # 데코레이터가 성공 메트릭을 처리하므로 여기서는 제거
            return {**state, "caption": caption}

        except requests.RequestException as e:
            error_msg = f"자막 API 호출 실패: {str(e)}"
            logger.error(error_msg)
            
            # 데코레이터가 실패 메트릭을 처리하므로 여기서는 제거
            return {**state, "caption": error_msg}
        except Exception as e:
            error_msg = f"자막 추출 실패: {str(e)}"
            logger.error(error_msg)
            
            # 데코레이터가 실패 메트릭을 처리하므로 여기서는 제거
            return {**state, "caption": error_msg}