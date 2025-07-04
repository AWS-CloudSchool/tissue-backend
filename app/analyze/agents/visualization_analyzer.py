import json
import boto3
from typing import Dict, List, Any, Optional
from langchain_aws import ChatBedrock
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from app.core.config import settings
from app.analyze.services.state_manager import state_manager
import logging

logger = logging.getLogger(__name__)

CONTEXT_ANALYSIS_PROMPT = """
## 임무
1. 보고서 내용을 깊이 분석
2. 시각화가 효과적인 내용 전달에 도움될 부분 식별 
3. 시각화와 관련된 **정확한 원본 텍스트 문단** 추출

## 보고서 분석
{summary}

## 작업 단계
1. **전체 주제와 흐름 파악**
2. **시각화가 도움될 부분 식별** (비교, 과정, 개념, 데이터, 구조, 흐름 등)
3. **시각화와 직접 관련된 완전한 문단 추출**

## 중요 지침
- **related_content**에는 시각화와 직접 관련된 **완전한 문단**을 포함하세요
- 문장이 중간에 끊기지 않도록 **완성된 문장들**로 구성
- 시각화 주제와 **정확히 일치하는 내용**만 선택
- 최소 100자 이상의 의미 있는 텍스트 블록 제공

## 출력 형식
```json
{{
  "visualization_requests": [
    {{
      "purpose": "comparison|process|concept|overview|detail",
      "content_description": "시각화할 구체적 내용",
      "related_content": "시각화와 직접 관련된 완전한 원본 문단"
    }}
  ]
}}
```

JSON만 출력하세요.
"""

class VisualizationAnalyzer(Runnable):
    """
    요약 텍스트를 분석하여 시각화가 필요한 부분을 선별하고
    구체적인 시각화 요청을 생성하는 에이전트
    """
    def __init__(self):
        self.llm = ChatBedrock(
            client=boto3.client("bedrock-runtime", region_name=settings.AWS_REGION),
            model=settings.BEDROCK_MODEL_ID,
            model_kwargs={
                "temperature": 0.3,
                "max_tokens": settings.BEDROCK_MAX_TOKENS
            }
        )

    def invoke(self, state: dict, config=None) -> dict:
        summary = state.get("summary", "")
        job_id = state.get("job_id")
        logger.info("🔍 시각화 분석 시작...")
        if job_id:
            try:
                state_manager.update_progress(job_id, 60, "🔍 시각화 분석 중...")
            except Exception as e:
                logger.warning(f"진행률 업데이트 실패 (무시됨): {e}")
        if not summary or len(summary.strip()) < 50:
            logger.warning("요약 내용이 너무 짧거나 없습니다.")
            return {**state, "visualization_requests": []}
        try:
            prompt = CONTEXT_ANALYSIS_PROMPT.format(summary=summary)
            response = self.llm.invoke(prompt)
            content = response
            # LLM 응답이 list일 경우 첫 번째 요소 사용
            if isinstance(content, list):
                content = content[0]
            if hasattr(content, "content"):
                content = content.content
            content = str(content).strip()
            start_idx = content.find('{')
            end_idx = content.rfind('}')
            if start_idx != -1 and end_idx != -1:
                json_part = content[start_idx:end_idx + 1]
                result = json.loads(json_part)
                viz_requests = result.get('visualization_requests', [])
                logger.info(f"✅ 분석 완료: {len(viz_requests)}개 시각화 요청")
                for i, req in enumerate(viz_requests):
                    content_len = len(req.get('related_content', ''))
                    logger.info(f"   요청 {i + 1}: {req.get('purpose', 'unknown')} - {content_len}자")
                return {**state, "visualization_requests": viz_requests}
            else:
                logger.error("JSON 파싱 실패")
                return {**state, "visualization_requests": []}
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 오류: {e}")
            return {**state, "visualization_requests": []}
        except Exception as e:
            logger.error(f"시각화 요청 분석 실패: {e}")
            return {**state, "visualization_requests": []} 