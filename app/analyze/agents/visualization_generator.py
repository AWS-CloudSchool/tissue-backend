import json
import boto3
from typing import Dict, List, Any, Optional
from langchain_aws import ChatBedrock
from langchain_core.runnables import Runnable
from app.core.config import settings
from app.analyze.services.state_manager import state_manager
import logging

logger = logging.getLogger(__name__)

# 고품질 시각화 생성을 위한 개선된 프롬프트
VISUALIZATION_GENERATION_PROMPT = """
당신은 데이터 시각화 전문가입니다. 제공된 정보를 바탕으로 정확하고 아름다운 시각화를 생성해주세요.

## 📊 시각화 요청 정보
- **목적**: {purpose}
- **내용**: {content_description}

## 📝 원본 텍스트 (반드시 이 정보만 사용하세요)
{related_content}

## 🎬 전체 자막 (추가 참고용)
{caption_context}

## 🎯 핵심 지침
1. **정확성**: 원본 텍스트에 명시된 구체적 수치, 데이터, 관계만 사용
2. **구체성**: 추상적 개념보다는 구체적이고 측정 가능한 데이터 우선
3. **아름다움**: 색상 조화, 레이아웃, 타이포그래피를 고려한 시각적 매력
4. **명확성**: 한눈에 이해할 수 있는 직관적 구조
5. **일관성**: 전체 리포트와 조화로운 디자인

## 🎨 디자인 원칙
- **색상 팔레트**: 전문적이고 조화로운 색상 사용
- **레이아웃**: 여백과 균형을 고려한 깔끔한 배치
- **타이포그래피**: 가독성 높은 폰트 크기와 스타일
- **인터랙션**: 가능한 경우 사용자 상호작용 요소 추가

## 사용 가능한 시각화 타입
- **chartjs**: 데이터 비교, 트렌드, 비율
- **plotly**: 수학적/과학적 그래프, 복잡한 데이터
- **table**: 구조화된 정보, 비교표
- **vis.js**: 관계도, 계층 구조 표현, 그룹화된 노드 표현
- **React Flow**: 프로세스, 의사결정 흐름, 작업 흐름도, 마인드맵, 플로우차트, 개념 관계, 분류 체계
- **D3.js**: 타임라인, 역사적 사건

다음 중 하나의 형식으로 응답하세요:

**1. Chart.js 차트 (고품질):**
{{
  "type": "chartjs",
  "chart_type": "bar|line|pie|radar|scatter|doughnut",
  "title": "차트 제목",
  "config": {{
    "type": "bar",
    "data": {{
      "labels": ["항목1", "항목2", "항목3"],
      "datasets": [{{
        "label": "데이터셋 이름",
        "data": [10, 20, 30],
        "backgroundColor": ["#667eea", "#764ba2", "#f093fb"],
        "borderColor": ["#5a6fd8", "#6a4190", "#e085e9"],
        "borderWidth": 2,
        "borderRadius": 8,
        "hoverBackgroundColor": ["#5a6fd8", "#6a4190", "#e085e9"]
      }}]
    }},
    "options": {{
      "responsive": true,
      "maintainAspectRatio": false,
      "plugins": {{
        "legend": {{
          "position": "top",
          "labels": {{
            "font": {{"size": 14, "weight": "600"}},
            "padding": 20,
            "usePointStyle": true
          }}
        }},
        "title": {{
          "display": true,
          "text": "차트 제목",
          "font": {{"size": 18, "weight": "700"}},
          "color": "#2d3748"
        }}
      }},
      "scales": {{
        "y": {{
          "beginAtZero": true,
          "grid": {{
            "color": "rgba(0,0,0,0.1)",
            "drawBorder": false
          }},
          "ticks": {{
            "font": {{"size": 12}},
            "color": "#4a5568"
          }}
        }},
        "x": {{
          "grid": {{
            "display": false
          }},
          "ticks": {{
            "font": {{"size": 12}},
            "color": "#4a5568"
          }}
        }}
      }},
      "elements": {{
        "bar": {{
          "borderRadius": 8
        }}
      }}
    }}
  }},
  "insight": "이 차트를 통해 얻을 수 있는 구체적 인사이트",
  "design_notes": "전문적이고 현대적인 디자인으로 데이터의 중요성을 강조"
}}

**2. Plotly 수학/과학:**
{{
  "type": "plotly", 
  "chart_type": "function|scatter|heatmap|3d|line|pie|bubble|histogram",
  "title": "그래프 제목",
  "config": {{
    "data": [{{
      "x": [1, 2, 3, 4],
      "y": [10, 11, 12, 13],
      "type": "scatter",
      "mode": "lines+markers"
    }}],
    "layout": {{
      "title": "그래프 제목",
      "xaxis": {{"title": "X축"}},
      "yaxis": {{"title": "Y축"}}
    }}
  }},
  "insight": "이 그래프를 통해 얻을 수 있는 인사이트"
}}

**3. HTML 테이블:**
{{
  "type": "table",
  "title": "표 제목", 
  "data": {{
    "headers": ["항목", "값", "설명"],
    "rows": [
      ["항목1", "값1", "설명1"],
      ["항목2", "값2", "설명2"]
    ]
  }},
  "insight": "이 표를 통해 얻을 수 있는 인사이트"
}}

**4. Vis.js 네트워크 (고품질):**
{{
  "type": "visjs",
  "network_type": "network|hierarchy|cluster",
  "title": "네트워크 제목",
  "config": {{
    "nodes": [
      {{"id": 1, "label": "중심 개념", "group": "main", "size": 25, "font": {{"size": 16, "weight": "bold"}}}},
      {{"id": 2, "label": "하위 개념 1", "group": "sub", "size": 20, "font": {{"size": 14}}}},
      {{"id": 3, "label": "하위 개념 2", "group": "sub", "size": 20, "font": {{"size": 14}}}}
    ],
    "edges": [
      {{"from": 1, "to": 2, "label": "관계1", "width": 3, "color": {{"color": "#667eea", "highlight": "#5a6fd8"}}}},
      {{"from": 1, "to": 3, "label": "관계2", "width": 3, "color": {{"color": "#764ba2", "highlight": "#6a4190"}}}}
    ],
    "options": {{
      "groups": {{
        "main": {{
          "color": {{"background": "#667eea", "border": "#5a6fd8", "highlight": {{"background": "#5a6fd8", "border": "#4a5fc6"}}}},
          "font": {{"color": "#ffffff", "size": 16, "weight": "bold"}},
          "shape": "circle",
          "size": 25
        }},
        "sub": {{
          "color": {{"background": "#764ba2", "border": "#6a4190", "highlight": {{"background": "#6a4190", "border": "#5a3780"}}}},
          "font": {{"color": "#ffffff", "size": 14}},
          "shape": "box",
          "size": 20
        }}
      }},
      "physics": {{
        "enabled": true,
        "hierarchicalRepulsion": {{
          "centralGravity": 0.0,
          "springLength": 150,
          "springConstant": 0.01,
          "nodeDistance": 200
        }},
        "solver": "hierarchicalRepulsion"
      }},
      "layout": {{
        "hierarchical": {{
          "enabled": true,
          "direction": "LR",
          "sortMethod": "directed",
          "levelSeparation": 200,
          "nodeSpacing": 150
        }}
      }},
      "edges": {{
        "smooth": {{
          "type": "cubicBezier",
          "forceDirection": "none"
        }},
        "font": {{
          "size": 12,
          "color": "#4a5568",
          "strokeWidth": 0,
          "strokeColor": "#ffffff"
        }},
        "arrows": {{
          "to": {{
            "enabled": true,
            "scaleFactor": 1.5
          }}
        }}
      }},
      "interaction": {{
        "hover": true,
        "navigationButtons": true,
        "keyboard": true
      }}
    }}
  }},
  "insight": "이 관계도를 통해 얻을 수 있는 구체적 인사이트",
  "design_notes": "계층적 구조와 색상 구분으로 관계의 중요도를 시각적으로 표현"
}}

**5. React Flow 흐름도:**
{{
  "type": "reactflow",
  "flow_type": "flowchart|mindmap|process|decision",
  "title": "흐름도 제목",
  "config": {{
    "nodes": [
      {{"id": "1", "type": "input", "data": {{"label": "시작"}}, "position": {{"x": 100, "y": 100}}}},
      {{"id": "2", "type": "default", "data": {{"label": "프로세스"}}, "position": {{"x": 100, "y": 200}}}},
      {{"id": "3", "type": "output", "data": {{"label": "종료"}}, "position": {{"x": 100, "y": 300}}}}
    ],
    "edges": [
      {{"id": "e1-2", "source": "1", "target": "2", "label": "다음"}},
      {{"id": "e2-3", "source": "2", "target": "3", "label": "완료"}}
    ],
    "options": {{
      "nodeTypes": {{"custom": "customNode"}},
      "edgeTypes": {{"custom": "customEdge"}}
    }}
  }},
  "insight": "이 흐름도를 통해 얻을 수 있는 인사이트"
}}

**6. D3.js 타임라인:**
{{
  "type": "d3js",
  "chart_type": "timeline|gantt|calendar|tree",
  "title": "타임라인 제목",
  "config": {{
    "data": [
      {{"date": "2020-01-01", "event": "사건 1", "category": "기술"}},
      {{"date": "2021-06-15", "event": "사건 2", "category": "정책"}},
      {{"date": "2023-12-31", "event": "사건 3", "category": "사회"}}
    ],
    "options": {{
      "width": 800,
      "height": 400,
      "margin": {{"top": 20, "right": 20, "bottom": 30, "left": 40}},
      "timeFormat": "%Y-%m-%d",
      "colors": {{"기술": "#FF6B6B", "정책": "#4ECDC4", "사회": "#45B7D1"}}
    }}
  }},
  "insight": "이 타임라인을 통해 얻을 수 있는 인사이트"
}}

**7. 창의적 제안:**
{{
  "type": "creative",
  "method": "제안하는 방법",
  "description": "어떻게 구현할지",
  "insight": "왜 이 방법이 최적인지"
}}

## 🔍 실제 작업 과정

1. **원본 텍스트 분석**: 구체적 수치, 항목, 관계 추출
2. **데이터 유형 판단**: 수치형/구조형/개념형 구분
3. **적절한 타입 선택**: 위 가이드에 따라 선택
4. **원본 기반 생성**: 추출된 정보만으로 시각화 구성
5. **data_source 추가**: 원본에서 인용한 구체적 부분 명시

JSON만 출력하세요.
"""


class SmartVisualAgent(Runnable):
    """
    VisualizationAnalyzer에서 분석된 시각화 요청을 바탕으로
    실제 시각화 데이터를 생성하는 스마트 에이전트

    Input: visualization_requests (List[Dict]) - VisualizationAnalyzer에서 생성된 시각화 요청 목록
    Output: visual_sections (List[Dict]) - 생성된 시각화 데이터 목록
    """

    def __init__(self):
        """LLM 초기화"""
        self.llm = ChatBedrock(
            client=boto3.client("bedrock-runtime", region_name=settings.AWS_REGION),
            model_id=settings.BEDROCK_MODEL_ID,
            model_kwargs={
                "temperature": 0.3,  # 일관성 있는 시각화를 위해 낮은 temperature
                "max_tokens": settings.BEDROCK_MAX_TOKENS
            }
        )

    def invoke(self, state: dict, config=None) -> dict:
        """
        시각화 요청을 바탕으로 실제 시각화 데이터 생성

        Args:
            state: GraphState - visualization_requests 포함
            config: 실행 설정 (선택)

        Returns:
            업데이트된 state - visual_sections 추가
        """
        visualization_requests = state.get("visualization_requests", [])
        caption_context = state.get("caption", "")
        job_id = state.get("job_id")

        logger.info("🎨 시각화 생성 시작...")

        # 진행률 업데이트 (70%)
        if job_id:
            try:
                state_manager.update_progress(job_id, 70, "🎨 시각화 생성 중...")
            except Exception as e:
                logger.warning(f"진행률 업데이트 실패 (무시됨): {e}")

        # 입력 검증
        if not visualization_requests:
            logger.info("❌ 시각화 요청이 없습니다.")
            return {**state, "visual_sections": []}

        logger.info(f"🎯 {len(visualization_requests)}개 시각화 생성 시작...")

        visual_sections = []

        for i, req in enumerate(visualization_requests):
            viz_id = f"viz_{i + 1:03d}"  # viz_001, viz_002, ...
            logger.info(f"🎯 시각화 {i + 1}/{len(visualization_requests)} 생성 중... (ID: {viz_id})")

            try:
                # correct-visualization-agents와 동일한 프롬프트 형식
                prompt = VISUALIZATION_GENERATION_PROMPT.format(
                    purpose=req.get('purpose', ''),
                    content_description=req.get('content_description', ''),
                    related_content=req.get('related_content', ''),
                    caption_context=caption_context[:1000]  # 길이 제한
                )

                response = self.llm.invoke(prompt)
                content = response.content.strip()

                # JSON 추출 (TaggingAgent와 동일한 방식)
                start_idx = content.find('{')
                end_idx = content.rfind('}')

                if start_idx != -1 and end_idx != -1:
                    json_part = content[start_idx:end_idx + 1]
                    viz_result = json.loads(json_part)

                    # ReportAgent(yesol 브랜치)에 맞는 형식으로 변환
                    visual_section = {
                        "title": viz_result.get('title', f'시각화 {i + 1}'),
                        "visualization_type": self._convert_viz_type(viz_result.get('type')),
                        "data": viz_result,  # 전체 시각화 데이터
                        "insight": viz_result.get('insight', ''),
                        "position": {"after_paragraph": i},  # 순서대로 배치
                        "purpose": req.get('purpose', ''),
                        "user_benefit": f"{req.get('content_description', '')}에 대한 시각적 이해를 돕습니다."
                    }

                    visual_sections.append(visual_section)

                    # 시각화 타입별 로깅
                    viz_type = viz_result.get('type', 'unknown')
                    viz_title = viz_result.get('title', '제목 없음')
                    logger.info(f"✅ 시각화 {viz_id} 생성 성공: {viz_type} - {viz_title}")

                else:
                    logger.warning(f"⚠️ 시각화 {viz_id} JSON 파싱 실패")

            except json.JSONDecodeError as e:
                logger.error(f"❌ 시각화 {viz_id} JSON 파싱 오류: {e}")
            except Exception as e:
                logger.error(f"❌ 시각화 {viz_id} 생성 실패: {e}")

        logger.info(f"🎨 시각화 생성 완료: {len(visual_sections)}/{len(visualization_requests)}개 성공")

        # yesol 브랜치 ReportAgent와 호환되도록 visual_sections에 저장
        return {**state, "visual_sections": visual_sections}

    def _convert_viz_type(self, viz_type: str) -> str:
        """새로운 시각화 타입을 ReportAgent가 이해할 수 있는 형식으로 변환"""
        type_mapping = {
            "chartjs": "chart",
            "plotly": "chart",
            "table": "table",
            "visjs": "network",
            "reactflow": "flow",
            "d3js": "timeline",
            "creative": "text"
        }
        return type_mapping.get(viz_type, "chart") 