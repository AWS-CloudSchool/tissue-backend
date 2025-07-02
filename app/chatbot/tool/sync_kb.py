# tools/sync_kb.py

import boto3
import json
import sys
import os
from botocore.exceptions import ClientError

# 상위 디렉토리의 app.core.config를 사용하기 위한 경로 설정
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from app.core.config import settings

def sync_kb():
    """Bedrock Knowledge Base 동기화 Job 시작"""
    try:
        bedrock_client = boto3.client("bedrock-agent", region_name=settings.AWS_REGION)
        
        response = bedrock_client.start_ingestion_job(
            knowledgeBaseId=settings.BEDROCK_KB_ID,
            dataSourceId=settings.BEDROCK_DS_ID
        )
        
        job_id = response["ingestionJob"]["ingestionJobId"]
        print(f"📋 KB 동기화 Job 시작: {job_id}")
        return job_id
        
    except Exception as e:
        print(f"❌ KB 동기화 Job 시작 실패: {e}")
        return None

    print("===== Lambda sync_kb ENTRY =====")
    print("MODULE FILE:", __file__)
    print("BEDROCK_DS_ID current:", settings.BEDROCK_DS_ID, type(settings.BEDROCK_DS_ID))
    print("BEDROCK_KB_ID current:", settings.BEDROCK_KB_ID, type(settings.BEDROCK_KB_ID))
    print("AWS_REGION current:", settings.AWS_REGION, type(settings.AWS_REGION))

    # 환경 변수 검증
    if not settings.BEDROCK_KB_ID or not settings.BEDROCK_DS_ID:
        print("❌ KB 동기화 실패: BEDROCK_KB_ID 또는 BEDROCK_DS_ID가 설정되지 않음")
        print(f"BEDROCK_KB_ID: {settings.BEDROCK_KB_ID}")
        print(f"BEDROCK_DS_ID: {settings.BEDROCK_DS_ID}")
        return None

    print("✅ 환경 변수 검증 통과")
    kb_client = boto3.client("bedrock-agent", region_name=settings.AWS_REGION)
    print("✅ Bedrock Agent 클라이언트 생성 완료")

    # ① 진행 중인 Job 확인
    try:
        print("🔍 기존 Job 확인 중...")
        jobs = kb_client.list_ingestion_jobs(
            knowledgeBaseId=settings.BEDROCK_KB_ID,
            dataSourceId=settings.BEDROCK_DS_ID
        )
        print(f"📋 발견된 Job 수: {len(jobs.get('ingestionJobSummaries', []))}")
        
        for job in jobs.get("ingestionJobSummaries", []):
            print(f"  - Job ID: {job.get('ingestionJobId')}, Status: {job.get('status')}")
            if (
                str(job.get("dataSourceId")) == str(settings.BEDROCK_DS_ID) and
                job.get("status") in ["STARTING", "IN_PROGRESS", "COMPLETE"]
            ):
                job_id = job["ingestionJobId"]
                print(f"⚠️ 진행 중인 Job이 있습니다: {job_id} → 재사용")
                return str(job_id)
    except Exception as e:
        print(f"⚠️ 기존 Job 확인 중 오류: {e}")

    # ② 새로 요청
    try:
        # AWS Bedrock Agent API의 정확한 파라미터명 사용 (camelCase)
        params = {
            "knowledgeBaseId": str(settings.BEDROCK_KB_ID),
            "dataSourceId": str(settings.BEDROCK_DS_ID)
        }
        print("🚀 새로운 Ingestion Job 시작 요청...")
        print("Calling start_ingestion_job params:", params)
        print("파라미터 타입:", {k: type(v) for k, v in params.items()})
        print("파라미터 값 확인:")
        print(f"  knowledgeBaseId: '{params['knowledgeBaseId']}' (길이: {len(params['knowledgeBaseId'])})")
        print(f"  dataSourceId: '{params['dataSourceId']}' (길이: {len(params['dataSourceId'])})")

        response = kb_client.start_ingestion_job(**params)
        job_id = response["ingestionJob"]["ingestionJobId"]
        print("✅ Job Started:", job_id)
        return str(job_id)

    except ClientError as e:
        print("❌ AWS CLIENT ERROR 발생")
        print("💥", str(e))
        print("🧪 RAW AWS RESPONSE:", json.dumps(e.response, indent=2, ensure_ascii=False))
        return None
    except Exception as e:
        print("❌ 일반 EXCEPTION 발생")
        print("💥", str(e))
        return None