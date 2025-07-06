from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Dict, Any, List, Optional
from app.s3.services.s3_service import s3_service
from app.s3.services.user_s3_service import user_s3_service
from app.s3.services.pdf_service import pdf_service
from app.core.config import settings
from app.auth.core.auth import get_current_user
from fastapi.responses import Response
import json

router = APIRouter(
    prefix="/s3",
    tags=["s3"]
)

@router.get("/list")
async def list_s3_objects(
    prefix: str = Query("", description="S3 객체 경로 접두사"),
    max_keys: int = Query(100, description="최대 객체 수")
) -> Dict[str, Any]:
    """
    S3 버킷 내 객체 목록 조회
    
    - **prefix**: 객체 경로 접두사 (예: 'reports/')
    - **max_keys**: 최대 객체 수
    """
    try:
        objects = s3_service.list_objects(prefix=prefix, max_keys=max_keys)
        
        return {
            "bucket": s3_service.bucket_name,
            "region": settings.AWS_REGION,
            "prefix": prefix,
            "objects": [
                {
                    "Key": obj.get("Key", ""),
                    "Size": obj.get("Size", 0),
                    "LastModified": obj.get("LastModified", "").isoformat() if hasattr(obj.get("LastModified", ""), "isoformat") else obj.get("LastModified", ""),
                    "ETag": obj.get("ETag", ""),
                    "StorageClass": obj.get("StorageClass", "")
                }
                for obj in objects
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"S3 객체 목록 조회 실패: {str(e)}")

@router.get("/object/{key:path}")
async def get_s3_object(key: str) -> Dict[str, Any]:
    """
    S3 객체 정보 조회
    
    - **key**: 객체 키 (경로)
    """
    try:
        # S3 객체 헤더 조회
        response = s3_service.s3_client.head_object(
            Bucket=s3_service.bucket_name,
            Key=key
        )
        
        # 미리 서명된 URL 생성
        url = s3_service.s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': s3_service.bucket_name, 'Key': key},
            ExpiresIn=3600
        )
        
        return {
            "key": key,
            "size": response.get("ContentLength", 0),
            "last_modified": response.get("LastModified", "").isoformat() if hasattr(response.get("LastModified", ""), "isoformat") else response.get("LastModified", ""),
            "content_type": response.get("ContentType", ""),
            "metadata": response.get("Metadata", {}),
            "url": url
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"S3 객체를 찾을 수 없음: {str(e)}")

@router.get("/reports/list")
async def list_reports_with_metadata(current_user: dict = Depends(get_current_user)) -> List[Dict[str, Any]]:
    """
    보고서 목록 조회 (메타데이터 포함, 사용자별)
    """
    try:
        user_id = current_user["user_id"]
        # 보고서 파일 목록 가져오기 (사용자별)
        report_objects = s3_service.list_objects(prefix=f"reports/{user_id}/", max_keys=100)
        
        reports = []
        for obj in report_objects:
            if obj.get("Key", "").endswith("_report.json"):
                try:
                    # 보고서 파일 내용 가져오기
                    report_content = s3_service.get_file_content(obj.get("Key", ""))
                    if report_content:
                        report_data = json.loads(report_content)
                        
                        # job_id 추출
                        job_id = obj.get("Key", "").replace(f"reports/{user_id}/", "").replace("_report.json", "")
                        
                        # 보고서 내부 메타데이터 사용
                        metadata = report_data.get("metadata", {})
                        
                        # 미리 서명된 URL 생성
                        report_url = s3_service.s3_client.generate_presigned_url(
                            'get_object',
                            Params={'Bucket': s3_service.bucket_name, 'Key': obj.get("Key", "")},
                            ExpiresIn=3600
                        )
                        
                        reports.append({
                            "id": job_id,
                            "key": obj.get("Key", ""),
                            "title": metadata.get("youtube_title", f"YouTube 분석 리포트 - {job_id[:8]}"),
                            "youtube_url": metadata.get("youtube_url", ""),
                            "youtube_channel": metadata.get("youtube_channel", "Unknown Channel"),
                            "youtube_duration": metadata.get("youtube_duration", "Unknown"),
                            "youtube_thumbnail": metadata.get("youtube_thumbnail", ""),
                            "video_id": metadata.get("video_id", ""),
                            "type": "YouTube",
                            "analysis_type": metadata.get("analysis_type", "youtube_analysis"),
                            "status": metadata.get("status", "completed"),
                            "last_modified": obj.get("LastModified", "").isoformat() if hasattr(obj.get("LastModified", ""), "isoformat") else obj.get("LastModified", ""),
                            "url": report_url,
                            "metadata": metadata
                        })
                        
                except Exception as e:
                    print(f"보고서 처리 실패: {obj.get('Key', '')} - {e}")
                    continue
        
        # 최신순 정렬
        reports.sort(key=lambda x: x.get("last_modified", ""), reverse=True)
        
        return reports
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"보고서 목록 조회 실패: {str(e)}")

@router.delete("/reports/{job_id}")
async def delete_report(job_id: str, current_user: dict = Depends(get_current_user)) -> Dict[str, str]:
    """
    보고서 삭제
    
    - **job_id**: 삭제할 보고서의 작업 ID
    """
    try:
        user_id = current_user["user_id"]
        report_key = f"reports/{user_id}/{job_id}_report.json"
        
        # 파일 존재 확인
        try:
            s3_service.s3_client.head_object(
                Bucket=s3_service.bucket_name,
                Key=report_key
            )
        except:
            raise HTTPException(status_code=404, detail="보고서를 찾을 수 없습니다")
        
        # 보고서 삭제
        user_s3_service.delete_user_file(report_key)
        
        return {"message": "보고서가 성공적으로 삭제되었습니다", "job_id": job_id}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"보고서 삭제 실패: {str(e)}")

@router.get("/reports/{job_id}/pdf")
async def download_report_pdf(job_id: str, current_user: dict = Depends(get_current_user)):
    """
    보고서 PDF 다운로드
    
    - **job_id**: PDF로 변환할 보고서의 작업 ID
    """
    try:
        user_id = current_user["user_id"]
        report_key = f"reports/{user_id}/{job_id}_report.json"
        
        # 보고서 데이터 가져오기
        report_content = s3_service.get_file_content(report_key)
        if not report_content:
            raise HTTPException(status_code=404, detail="보고서를 찾을 수 없습니다")
        
        report_data = json.loads(report_content)
        
        # PDF 생성
        pdf_bytes = pdf_service.generate_report_pdf(report_data)
        
        # 파일명 설정
        metadata = report_data.get('metadata', {})
        title = metadata.get('youtube_title', f'report_{job_id}')
        filename = f"{title[:50]}_{job_id[:8]}.pdf".replace('/', '_').replace('\\', '_')
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF 생성 실패: {str(e)}")