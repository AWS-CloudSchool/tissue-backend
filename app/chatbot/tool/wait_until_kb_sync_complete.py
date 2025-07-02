#tool/wait_until_kb_sync_complete.py
import boto3
import time
import sys
import os

# 상위 디렉토리의 app.core.config를 사용하기 위한 경로 설정
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from app.core.config import settings

def get_ingestion_job_status(job_id: str) -> str:
    """KB 동기화 Job 상태 조회"""
    try:
        bedrock_client = boto3.client("bedrock-agent", region_name=settings.AWS_REGION)
        response = bedrock_client.get_ingestion_job(
            knowledgeBaseId=settings.BEDROCK_KB_ID,
            dataSourceId=settings.BEDROCK_DS_ID,
            ingestionJobId=job_id
        )
        return response["ingestionJob"]["status"]
    except Exception as e:
        print(f"⚠️ Job 상태 조회 실패: {e}")
        return "UNKNOWN"

def wait_until_kb_sync_complete(job_id: str, max_wait_sec: int = 60) -> str:
    """KB 동기화 Job 완료까지 대기"""
    print(f"⏳ KB 동기화 완료 대기 중... (최대 {max_wait_sec}초)")
    
    start_time = time.time()
    while time.time() - start_time < max_wait_sec:
        try:
            status = get_ingestion_job_status(job_id)
            if status in ["COMPLETE", "FAILED", "STOPPED"]:
                if status == "COMPLETE":
                    print("✅ KB 동기화 완료!")
                else:
                    print(f"❌ KB 동기화 실패: {status}")
                return status
            
            # 5초 대기
            time.sleep(5)
            
        except Exception as e:
            print(f"⚠️ 상태 확인 중 오류: {e}")
            time.sleep(2)
    
    print(f"⏰ 시간 초과 ({max_wait_sec}초)")
    return "TIMEOUT"