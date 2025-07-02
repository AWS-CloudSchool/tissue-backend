#tool/youtube_lambda.py
import json
import sys
import os
import boto3

# 상위 디렉토리의 app.core.config를 사용하기 위한 경로 설정
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from app.core.config import settings
from app.chatbot.tool.sync_kb import sync_kb

def lambda_handler(event, context):
    try:
        print("📥 이벤트 수신:", event)
        body = json.loads(event["body"]) if "body" in event else event
        user_id = body.get("user_id")
        job_id = body.get("job_id")
        
        if not user_id or not job_id:
            return {"statusCode": 400, "body": "Missing user_id or job_id"}

        # 해당 사용자의 특정 작업 파일 확인
        s3_key = f"captions/{user_id}/{job_id}_caption.txt"
        
        # S3에 파일 존재 확인
        s3 = boto3.client("s3")
        try:
            s3.head_object(Bucket=settings.AWS_S3_BUCKET, Key=s3_key)
            print(f"✅ 파일 확인: {s3_key}")
        except:
            return {
                "statusCode": 404, 
                "body": json.dumps({"error": f"File not found: {s3_key}"})
            }

        # KB 동기화 시작
        sync_job_id = sync_kb()
        
        if sync_job_id:
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "message": "KB sync started for specific file",
                    "sync_job_id": sync_job_id,
                    "user_id": user_id,
                    "job_id": job_id,
                    "s3_key": s3_key
                })
            }
        else:
            return {
                "statusCode": 500,
                "body": json.dumps({"error": "Failed to start KB sync"})
            }

    except Exception as e:
        print("lambda 에러 발생:", str(e))
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }

def process_user_job(user_id: str, job_id: str) -> str:
    print(f"process_user_job 시작: user_id={user_id}, job_id={job_id}")
    event = {"user_id": user_id, "job_id": job_id}
    result = lambda_handler(event, None)
    
    print(f"lambda_handler 결과: {result}")
    body = json.loads(result["body"])
    if result["statusCode"] == 200:
        return body.get("sync_job_id", "KB 동기화 완료")
    else:
        raise Exception(body.get("error", "Unknown error"))
