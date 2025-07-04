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

# 고품질 시각화 분석을 위한 개선된 프롬프트
CONTEXT_ANALYSIS_PROMPT = """
당신은 데이터 시각화 전문가입니다. 보고서 내용을 분석하여 가장 효과적이고 아름다운 시각화를 생성할 수 있는 부분을 식별해주세요.

## 📊 분석 대상
{summary}

## 🎯 핵심 임무
1. **데이터 기반 분석**: 구체적 수치, 통계, 비교 데이터가 있는 부분 우선
2. **구조적 분석**: 프로세스, 관계, 계층 구조가 명확한 부분 식별
3. **시각적 잠재력**: 차트, 그래프, 다이어그램으로 표현하기 좋은 내용 선별
4. **원본 텍스트 추출**: 시각화와 직접 관련된 완전한 문단 정확히 추출

## 🔍 분석 기준
- **정확성**: 구체적이고 측정 가능한 데이터 우선
- **구체성**: 추상적 개념보다는 명확한 수치나 관계
- **시각적 매력**: 색상, 형태, 레이아웃으로 표현하기 좋은 내용
- **사용자 가치**: 독자가 이해하기 쉽고 인사이트를 얻을 수 있는 내용

## 📋 시각화 유형별 선별 기준

### 📈 **Data Visualization (차트/그래프)**
- 수치 비교, 트렌드, 비율, 분포 데이터
- 구체적 퍼센트, 금액, 수량, 기간 등
- 예: "매출이 30% 증가", "5개 카테고리 중 3개가 상승"

### 🌐 **Network/Relationship (관계도)**
- 개념 간 연결, 영향 관계, 계층 구조
- 명확한 주체-객체 관계
- 예: "A가 B에 영향을 미침", "X, Y, Z로 구성됨"

### 🔄 **Process/Flow (프로세스)**
- 단계별 과정, 의사결정 흐름, 작업 순서
- 시간적 순서나 논리적 흐름
- 예: "1단계 → 2단계 → 3단계", "조건에 따른 분기"

### 📊 **Structure/Overview (구조도)**
- 전체 구성, 분류 체계, 조직 구조
- 카테고리별 분류나 구성 요소
- 예: "3가지 유형으로 나뉨", "주요 구성 요소는..."

## ⚠️ 중요 지침
- **related_content**는 시각화와 직접 관련된 **완전한 문단**만 포함
- 문장이 중간에 끊기지 않도록 **완성된 문장들**로 구성
- 최소 150자 이상의 의미 있는 텍스트 블록 제공
- 구체적 수치나 명확한 관계가 포함된 내용 우선

## 🎨 출력 형식
```json
{{
  "visualization_requests": [
    {{
      "purpose": "data|network|process|structure|comparison|timeline",
      "content_description": "구체적이고 명확한 시각화 목적 설명",
      "related_content": "시각화와 직접 관련된 완전한 원본 문단 (150자 이상)",
      "visualization_type": "chart|network|flow|table|timeline",
      "data_quality": "high|medium|low",
      "expected_impact": "시각화를 통해 얻을 수 있는 구체적 가치"
    }}
  ]
}}
```

## 📝 예시
**입력**: "2023년 매출은 전년 대비 25% 증가했으며, 온라인 채널(40%), 오프라인 매장(35%), 파트너십(25%)으로 구성됩니다."

**출력**:
```json
{{
  "purpose": "data",
  "content_description": "2023년 매출 증가율과 채널별 구성 비율을 시각화",
  "related_content": "2023년 매출은 전년 대비 25% 증가했으며, 온라인 채널(40%), 오프라인 매장(35%), 파트너십(25%)으로 구성됩니다.",
  "visualization_type": "chart",
  "data_quality": "high",
  "expected_impact": "매출 성장과 채널별 비중을 한눈에 파악 가능"
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