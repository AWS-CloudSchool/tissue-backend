# chains/qa_chain.py
from langchain_core.prompts import ChatPromptTemplate
from langchain_aws import ChatBedrock
import boto3
import sys
import os

# 상위 디렉토리의 app.core.config를 사용하기 위한 경로 설정
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from app.core.config import settings

def build_qa_chain():
    """QA 체인 빌드"""
    llm = ChatBedrock(
        client=boto3.client("bedrock-runtime", region_name=settings.AWS_REGION),
        model_id=settings.BEDROCK_MODEL_ID,
        model_kwargs={"temperature": 0.0, "max_tokens": 4096}
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant. Answer the question based on the provided context."),
        ("human", "Context: {context}\n\nQuestion: {question}")
    ])
    
    return prompt | llm