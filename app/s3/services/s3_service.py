import boto3
import os
from app.core.config import settings

class S3Service:
    def __init__(self):
        # 명시적으로 자격 증명 설정
        self.s3_client = boto3.client(
            's3', 
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        self.bucket_name = settings.AWS_S3_BUCKET
        print(f"🪣 S3 서비스 초기화: 버킷={self.bucket_name}, 리전={settings.AWS_REGION}")
    
    def upload_file(self, file_path, object_name=None, content_type=None, acl="public-read"):
        """
        파일을 S3에 업로드
        업로드 성공 시 URL 반환, 실패 시 에러 메시지 문자열 반환
        """
        try:
            if object_name is None:
                object_name = os.path.basename(file_path)
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"파일을 찾을 수 없음: {file_path}")
            file_size = os.path.getsize(file_path)
            extra_args = {"ACL": acl}
            if content_type:
                extra_args["ContentType"] = content_type
            print(f"📤 S3 업로드 시작: {file_path} → {object_name} (크기: {file_size} 바이트)")
            with open(file_path, 'rb') as file_data:
                self.s3_client.upload_fileobj(
                    file_data,
                    self.bucket_name,
                    object_name,
                    ExtraArgs=extra_args
                )
            url = f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{object_name}"
            print(f"✅ S3 업로드 성공: {url}")
            return url
        except Exception as e:
            error_msg = f"❌ S3 업로드 실패: {str(e)}"
            print(error_msg)
            return f"[S3 upload failed: {str(e)}]"
    
    def list_objects(self, prefix="", max_keys=100):
        """S3 버킷 내 객체 목록 조회"""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )
            if 'Contents' in response:
                return response['Contents']
            return []
        except Exception as e:
            print(f"❌ S3 객체 목록 조회 실패: {str(e)}")
            return []

    def get_file_content(self, object_name: str) -> str:
        """S3에서 파일 내용을 문자열로 읽어오기"""
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=object_name
            )
            content = response['Body'].read().decode('utf-8')
            print(f"✅ S3 파일 내용 읽기 성공: {object_name}")
            return content
        except Exception as e:
            print(f"❌ S3 파일 내용 읽기 실패: {object_name} - {str(e)}")
            return ""

# 싱글톤 인스턴스
s3_service = S3Service()