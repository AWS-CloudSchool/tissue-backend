import boto3
import json
import time
from typing import Dict, Any, List
from datetime import datetime
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class UserS3Service:
    def __init__(self):
        self.s3_client = boto3.client('s3', region_name=settings.AWS_REGION)
        self.bucket_name = settings.AWS_S3_BUCKET
    
    def upload_user_report(self, user_id: str, job_id: str, content: str, file_type: str = "json") -> str:
        """
        보고서 업로드 (대시보드 호환 경로: reports/{user_id}/{job_id}_report.{file_type})
        """
        start_time = time.time()
        try:
            key = f"reports/{user_id}/{job_id}_report.{file_type}"
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=content,
                ContentType=f"application/{file_type}",
                Metadata={
                    "user_id": user_id,
                    "job_id": job_id,
                    "created_at": datetime.utcnow().isoformat()
                }
            )
            
            # S3 업로드 성공 메트릭 업데이트
            duration = time.time() - start_time
            try:
                from app.monitoring.services.metrics import s3_uploads_total, s3_upload_duration
                s3_uploads_total.labels(status='success').inc()
                s3_upload_duration.observe(duration)
                logger.info(f"✅ S3 보고서 업로드 메트릭 업데이트: {key}")
            except Exception as metric_error:
                logger.error(f"❌ S3 업로드 메트릭 업데이트 실패: {metric_error}")
            
            return key
        except Exception as e:
            # S3 업로드 실패 메트릭 업데이트
            duration = time.time() - start_time
            try:
                from app.monitoring.services.metrics import s3_uploads_total, s3_upload_duration
                s3_uploads_total.labels(status='failed').inc()
                s3_upload_duration.observe(duration)
                logger.info(f"🔴 S3 보고서 업로드 실패 메트릭 업데이트")
            except Exception as metric_error:
                logger.error(f"❌ S3 업로드 실패 메트릭 업데이트 실패: {metric_error}")
            
            raise Exception(f"보고서 업로드 실패: {str(e)}")
    
    def upload_user_audio(self, user_id: str, job_id: str, audio_data: bytes) -> str:
        """
        사용자별 오디오 파일 업로드
        """
        start_time = time.time()
        try:
            key = f"audio/{user_id}/{job_id}_audio.mp3"
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=audio_data,
                ContentType="audio/mpeg",
                Metadata={
                    "user_id": user_id,
                    "job_id": job_id,
                    "created_at": datetime.utcnow().isoformat()
                }
            )
            
            # S3 업로드 성공 메트릭 업데이트
            duration = time.time() - start_time
            try:
                from app.monitoring.services.metrics import s3_uploads_total, s3_upload_duration
                s3_uploads_total.labels(status='success').inc()
                s3_upload_duration.observe(duration)
                logger.info(f"✅ S3 오디오 업로드 메트릭 업데이트: {key}")
            except Exception as metric_error:
                logger.error(f"❌ S3 오디오 업로드 메트릭 업데이트 실패: {metric_error}")
            
            return key
        except Exception as e:
            # S3 업로드 실패 메트릭 업데이트
            duration = time.time() - start_time
            try:
                from app.monitoring.services.metrics import s3_uploads_total, s3_upload_duration
                s3_uploads_total.labels(status='failed').inc()
                s3_upload_duration.observe(duration)
                logger.info(f"🔴 S3 오디오 업로드 실패 메트릭 업데이트")
            except Exception as metric_error:
                logger.error(f"❌ S3 오디오 업로드 실패 메트릭 업데이트 실패: {metric_error}")
            
            raise Exception(f"오디오 업로드 실패: {str(e)}")
  
    
    def get_user_files(self, user_id: str, file_type: str = None) -> List[Dict]:
        """
        사용자 파일 목록 조회 (reports, audio, visuals)
        """
        try:
            if file_type:
                prefix = f"{file_type}/{user_id}/"
            else:
                prefix = f"{user_id}/"
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            files = []
            for obj in response.get('Contents', []):
                metadata_response = self.s3_client.head_object(
                    Bucket=self.bucket_name,
                    Key=obj['Key']
                )
                files.append({
                    "key": obj['Key'],
                    "size": obj['Size'],
                    "last_modified": obj['LastModified'].isoformat(),
                    "metadata": metadata_response.get('Metadata', {})
                })
            return files
        except Exception as e:
            raise Exception(f"파일 목록 조회 실패: {str(e)}")
    
    def get_presigned_url(self, s3_key: str, expires_in: int = 3600) -> str:
        """
        사전 서명된 URL 생성
        """
        try:
            return self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expires_in
            )
        except Exception as e:
            raise Exception(f"URL 생성 실패: {str(e)}")
    
    def upload_text_content(self, s3_key: str, content: str) -> str:
        """
        텍스트 내용을 S3에 업로드
        """
        start_time = time.time()
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=content,
                ContentType="text/plain",
                Metadata={
                    "created_at": datetime.utcnow().isoformat()
                }
            )
            
            # S3 업로드 성공 메트릭 업데이트
            duration = time.time() - start_time
            try:
                from app.monitoring.services.metrics import s3_uploads_total, s3_upload_duration
                s3_uploads_total.labels(status='success').inc()
                s3_upload_duration.observe(duration)
                logger.info(f"✅ S3 텍스트 업로드 메트릭 업데이트: {s3_key}")
            except Exception as metric_error:
                logger.error(f"❌ S3 텍스트 업로드 메트릭 업데이트 실패: {metric_error}")
            
            return s3_key
        except Exception as e:
            # S3 업로드 실패 메트릭 업데이트
            duration = time.time() - start_time
            try:
                from app.monitoring.services.metrics import s3_uploads_total, s3_upload_duration
                s3_uploads_total.labels(status='failed').inc()
                s3_upload_duration.observe(duration)
                logger.info(f"🔴 S3 텍스트 업로드 실패 메트릭 업데이트")
            except Exception as metric_error:
                logger.error(f"❌ S3 텍스트 업로드 실패 메트릭 업데이트 실패: {metric_error}")
            
            raise Exception(f"텍스트 업로드 실패: {str(e)}")
    
    def get_file_content(self, s3_key: str) -> str:
        """
        파일 내용 가져오기
        """
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return response['Body'].read().decode('utf-8')
        except Exception as e:
            logger.error(f"파일 내용 조회 실패: {str(e)}")
            return ""
    
    def delete_user_file(self, s3_key: str):
        """
        사용자 파일 삭제
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
        except Exception as e:
            raise Exception(f"파일 삭제 실패: {str(e)}")

user_s3_service = UserS3Service()