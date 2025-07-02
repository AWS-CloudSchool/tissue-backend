# retrievers/kb_retriever.py
import boto3
import sys
import os
from langchain_aws import ChatBedrock

# 상위 디렉토리의 app.core.config를 사용하기 위한 경로 설정
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from app.core.config import settings

def get_llm():
    """Bedrock LLM 클라이언트 반환"""
    return ChatBedrock(
        client=boto3.client("bedrock-runtime", region_name=settings.AWS_REGION),
        model_id=settings.BEDROCK_MODEL_ID,
        model_kwargs={"temperature": 0.0, "max_tokens": 4096}
    )

def get_kb_retriever():
    """Bedrock Knowledge Base 검색기 반환"""
    bedrock_client = boto3.client("bedrock-agent-runtime", region_name=settings.AWS_REGION)
    
    def retrieve(query: str):
        try:
            response = bedrock_client.retrieve(
                knowledgeBaseId=settings.BEDROCK_KB_ID,
                retrievalQuery={
                    "text": query
                },
                retrievalConfiguration={
                    "vectorSearchConfiguration": {
                        "numberOfResults": 5
                    }
                }
            )
            
            # LangChain Document 형식으로 변환
            from langchain_core.documents import Document
            documents = []
            
            for result in response.get("retrievalResults", []):
                doc = Document(
                    page_content=result.get("content", {}).get("text", ""),
                    metadata={
                        "score": result.get("score", 0.0),
                        "location": result.get("location", {}),
                        "metadata": result.get("metadata", {})
                    }
                )
                documents.append(doc)
            
            return documents
            
        except Exception as e:
            print(f"❌ KB 검색 실패: {e}")
            return []
    
    return retrieve