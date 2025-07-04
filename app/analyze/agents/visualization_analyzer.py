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

# 시각화가 필요한 부분을 식별하는 프롬프트 (원래 의도대로)
CONTEXT_ANALYSIS_PROMPT = """
당신은 보고서를 분석하여 시각화가 필요한 부분을 식별하는 전문가입니다.

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

    Input: summary (str) - SummaryAgent에서 생성된 요약 텍스트
    Output: visualization_requests (List[Dict]) - 시각화 요청 목록
    """

    def __init__(self):
        """LLM 초기화"""
        self.llm = ChatBedrock(
            client=boto3.client("bedrock-runtime", region_name=settings.AWS_REGION),
            model_id=settings.BEDROCK_MODEL_ID,
            model_kwargs={
                "temperature": 0.3,  # 일관성 있는 분석을 위해 낮은 temperature
                "max_tokens": settings.BEDROCK_MAX_TOKENS
            }
        )

    def invoke(self, state: dict, config=None) -> dict:
        """
        요약 내용을 분석하여 시각화 요청 생성

        Args:
            state: GraphState - summary 포함
            config: 실행 설정 (선택)

        Returns:
            업데이트된 state - visualization_requests 추가
        """
        summary = state.get("summary", "")  # ← workflow에 맞게 수정
        job_id = state.get("job_id")

        logger.info("🔍 시각화 분석 시작...")

        # 진행률 업데이트 (60%)
        if job_id:
            try:
                state_manager.update_progress(job_id, 60, "🔍 시각화 분석 중...")
            except Exception as e:
                logger.warning(f"진행률 업데이트 실패 (무시됨): {e}")

        # 입력 검증
        if not summary or len(summary.strip()) < 50:
            logger.warning("요약 내용이 너무 짧거나 없습니다.")
            return {**state, "visualization_requests": []}

        try:
            # correct-visualization-agents 브랜치 로직과 동일하게 처리
            prompt = CONTEXT_ANALYSIS_PROMPT.format(summary=summary)
            response = self.llm.invoke(prompt)
            content = response.content.strip()

            # JSON 추출
            start_idx = content.find('{')
            end_idx = content.rfind('}')

            if start_idx != -1 and end_idx != -1:
                json_part = content[start_idx:end_idx + 1]
                result = json.loads(json_part)

                viz_requests = result.get('visualization_requests', [])

                # 로깅 (correct-visualization-agents 브랜치와 동일)
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