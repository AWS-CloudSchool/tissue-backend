# app/workflows/visualization_generator.py
import os
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


class SmartVisualAgent(Runnable):
    """요약 내용을 분석하여 최적의 시각화를 자동 생성하는 스마트 에이전트"""

    def __init__(self):
        self.llm = ChatBedrock(
            client=boto3.client("bedrock-runtime", region_name=settings.AWS_REGION),
            model_id=settings.BEDROCK_MODEL_ID,
            model_kwargs={"temperature": 0.7, "max_tokens": settings.BEDROCK_MAX_TOKENS}
        )

    def invoke(self, state: dict, config=None) -> dict:
        """요약을 분석하여 시각화 생성"""
        summary = state.get("summary", "")
        job_id = state.get("job_id")
        user_id = state.get("user_id")

        logger.info("🎯 스마트 시각화 생성 시작...")

        # 진행률 업데이트
        if job_id:
            try:
                state_manager.update_progress(job_id, 60, "🎨 스마트 시각화 생성 중...")
            except Exception as e:
                logger.warning(f"진행률 업데이트 실패 (무시됨): {e}")

        if not summary or len(summary) < 100:
            logger.warning("유효한 요약이 없습니다.")
            return {**state, "visual_sections": []}

        try:
            # 1단계: 컨텍스트 분석
            logger.info("🧠 1단계: 컨텍스트 분석 시작...")
            context = self._analyze_context(summary)

            if not context or "error" in context:
                logger.error(f"컨텍스트 분석 실패: {context}")
                return {**state, "visual_sections": []}

            # 2단계: 시각화 기회별로 최적의 시각화 생성
            logger.info(f"🎯 2단계: {len(context.get('visualization_opportunities', []))}개의 시각화 기회 발견")
            visual_sections = []

            for i, opportunity in enumerate(context.get('visualization_opportunities', [])):
                logger.info(f"🎨 시각화 {i + 1} 생성 중...")
                visualization = self._generate_smart_visualization(context, opportunity)

                if visualization and "error" not in visualization:
                    # 요약 내 적절한 위치 찾기
                    position = self._find_best_position(summary, opportunity)

                    visual_section = {
                        "position": position,
                        "type": "visualization",
                        "title": visualization.get('title', opportunity.get('content', '시각화')[:50]),
                        "visualization_type": visualization.get('type'),
                        "data": self._standardize_visualization_data(visualization),
                        "insight": visualization.get('insight', ''),
                        "purpose": opportunity.get('purpose', ''),
                        "user_benefit": opportunity.get('user_benefit', '')
                    }
                    visual_sections.append(visual_section)
                    logger.info(f"✅ 시각화 생성 성공: {visualization.get('type')}")
                else:
                    logger.warning(f"⚠️ 시각화 {i + 1} 생성 실패")

            logger.info(f"📊 총 {len(visual_sections)}개의 시각화 생성 완료")
            return {**state, "visual_sections": visual_sections}

        except Exception as e:
            logger.error(f"시각화 생성 중 오류: {str(e)}")
            return {**state, "visual_sections": []}

    def _analyze_context(self, summary: str) -> Dict[str, Any]:
        """요약 내용의 맥락을 깊이 분석"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """당신은 텍스트를 분석하여 시각화가 필요한 부분을 찾아내는 전문가입니다.

주어진 요약을 분석하여 독자의 이해를 크게 향상시킬 수 있는 시각화 기회를 찾아주세요.

**분석 기준:**
1. **복잡한 개념**: 텍스트만으로는 이해하기 어려운 추상적 개념
2. **프로세스/절차**: 단계별 과정이나 흐름
3. **비교/대조**: 여러 항목 간의 차이점이나 유사점
4. **데이터/수치**: 통계, 비율, 추세 등 수치 정보
5. **관계/구조**: 요소들 간의 연결이나 계층 구조
6. **시간 흐름**: 시간에 따른 변화나 타임라인

**중요**: 시각화는 "있으면 좋은" 것이 아니라 "반드시 필요한" 경우에만 제안하세요.
각 시각화는 명확한 목적과 사용자 가치를 가져야 합니다.

**응답 형식 (JSON):**
{{
  "main_topic": "전체 주제",
  "key_concepts": ["핵심개념1", "핵심개념2", "핵심개념3"],
  "content_structure": {{
    "has_process": true/false,
    "has_comparison": true/false,
    "has_data": true/false,
    "has_timeline": true/false,
    "has_hierarchy": true/false
  }},
  "visualization_opportunities": [
    {{
      "content": "시각화할 구체적 내용",
      "location_hint": "요약 내 대략적 위치 (처음/중간/끝)",
      "purpose": "overview|detail|comparison|process|data|timeline|structure",
      "why_necessary": "왜 이 시각화가 필수적인지",
      "user_benefit": "독자가 얻을 구체적 이익",
      "suggested_type": "chart|diagram|table|mindmap|timeline|flowchart",
      "key_elements": ["포함해야 할 핵심 요소들"]
    }}
  ]
}}

JSON만 출력하세요."""),
            ("human", "{summary}")
        ])

        try:
            response = self.llm.invoke(prompt.format_messages(summary=summary))
            content = response.content.strip()

            # JSON 추출
            start_idx = content.find('{')
            end_idx = content.rfind('}')

            if start_idx != -1 and end_idx != -1:
                json_str = content[start_idx:end_idx + 1]
                return json.loads(json_str)
            else:
                return {"error": "JSON 파싱 실패"}

        except Exception as e:
            logger.error(f"컨텍스트 분석 오류: {e}")
            return {"error": str(e)}

    def _generate_smart_visualization(self, context: Dict[str, Any], opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """주어진 기회에 대해 최적의 시각화 생성"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """당신은 주어진 내용을 가장 효과적으로 시각화하는 전문가입니다.

**상황:**
- 주제: {main_topic}
- 시각화 목적: {purpose}
- 필요한 이유: {why_necessary}
- 사용자 이익: {user_benefit}

**시각화할 내용:**
{content}

**핵심 요소:**
{key_elements}

**당신의 임무:**
1. 이 내용을 가장 명확하고 직관적으로 표현할 시각화 방법 결정
2. 실제 데이터를 추출하거나 합리적으로 생성
3. 구체적인 시각화 설정 제공

**사용 가능한 시각화 유형:**

1. **차트 (Chart.js)**
   - bar: 항목 간 비교, 순위
   - line: 시간에 따른 변화, 추세
   - pie/doughnut: 구성 비율, 점유율
   - radar: 다차원 비교
   - scatter: 상관관계, 분포

2. **네트워크 다이어그램 (vis.js)**
   - network: 관계도, 연결망 시각화
   - hierarchy: 계층 구조 표현
   - cluster: 그룹화된 노드 표현

3. **플로우 차트 (React Flow)**
   - flowchart: 프로세스, 의사결정 흐름
   - workflow: 작업 흐름도
   - mindmap: 개념 구조, 분류 체계

4. **고급 시각화 (D3.js)**
   - timeline: 시간 순서, 역사적 사건
   - treemap: 계층적 데이터 구조
   - sankey: 흐름 다이어그램
   - force: 힘 기반 다이어그램

5. **테이블 (HTML)**
   - 정확한 수치 비교
   - 다양한 속성을 가진 항목들
   - 체크리스트, 기능 비교표

**네트워크 다이어그램 작성 규칙 (vis.js):**
- nodes: 노드 배열 [노드1, 노드2, ...]
- edges: 연결 배열 [연결1, 연결2, ...]
- 노드 속성: id, label, title, color, shape
- 연결 속성: from, to, label, arrows, color
- 그룹화: group 속성 사용

**플로우 차트 작성 규칙 (React Flow):**
- nodes: 노드 배열 [노드1, 노드2, ...]
- edges: 연결 배열 [연결1, 연결2, ...]
- 노드 속성: id, type, position, data
- 연결 속성: id, source, target, type, label
- 노드 타입: default, input, output, custom

**응답 형식 (반드시 다음 중 하나):**

**옵션 1 - 차트:**
{{
  "type": "chart",
  "library": "chartjs",
  "title": "명확한 제목",
  "chart_type": "bar|line|pie|radar|scatter",
  "data": {{
    "labels": ["레이블1", "레이블2", ...],
    "datasets": [
      {{
        "label": "데이터셋 이름",
        "data": [숫자1, 숫자2, ...],
        "backgroundColor": ["#667eea", "#f093fb", "#4facfe", "#43e97b"]
      }}
    ]
  }},
  "options": {{
    "responsive": true,
    "plugins": {{
      "title": {{ "display": true, "text": "차트 제목" }},
      "legend": {{ "position": "top" }}
    }}
  }},
  "insight": "이 차트가 보여주는 핵심 인사이트"
}}

**옵션 2 - 네트워크 다이어그램 (vis.js):**
{{
  "type": "network",
  "library": "visjs",
  "title": "명확한 제목",
  "network_type": "relationship|hierarchy|cluster",
  "data": {{
    "nodes": [
      {{ "id": 1, "label": "노드1", "title": "설명", "color": "#667eea" }},
      {{ "id": 2, "label": "노드2", "title": "설명", "color": "#f093fb" }}
    ],
    "edges": [
      {{ "from": 1, "to": 2, "label": "연결", "arrows": "to" }}
    ]
  }},
  "options": {{
    "layout": {{ "hierarchical": {{ "enabled": true, "direction": "LR" }} }},
    "physics": {{ "enabled": true }}
  }},
  "insight": "이 네트워크 다이어그램이 보여주는 핵심 관계"
}}

**옵션 3 - 플로우 차트 (React Flow):**
{{
  "type": "flow",
  "library": "reactflow",
  "title": "명확한 제목",
  "flow_type": "flowchart|workflow|mindmap",
  "data": {{
    "nodes": [
      {{ "id": "1", "type": "input", "position": {{ "x": 0, "y": 0 }}, "data": {{ "label": "시작" }} }},
      {{ "id": "2", "position": {{ "x": 100, "y": 100 }}, "data": {{ "label": "과정" }} }},
      {{ "id": "3", "type": "output", "position": {{ "x": 200, "y": 200 }}, "data": {{ "label": "완료" }} }}
    ],
    "edges": [
      {{ "id": "e1-2", "source": "1", "target": "2", "label": "연결 1" }},
      {{ "id": "e2-3", "source": "2", "target": "3", "label": "연결 2" }}
    ]
  }},
  "options": {{
    "direction": "LR",
    "fitView": true
  }},
  "insight": "이 플로우 차트가 보여주는 프로세스 흐름"
}}

**옵션 4 - 고급 시각화 (D3.js):**
{{
  "type": "d3",
  "library": "d3js",
  "title": "명확한 제목",
  "visualization_type": "timeline|treemap|sankey|force",
  "data": {{
    "nodes": [
      {{ "id": "node1", "name": "노드1", "value": 10 }},
      {{ "id": "node2", "name": "노드2", "value": 20 }}
    ],
    "links": [
      {{ "source": "node1", "target": "node2", "value": 5 }}
    ]
  }},
  "config": {{
    "width": 800,
    "height": 600,
    "colors": ["#667eea", "#f093fb", "#4facfe", "#43e97b"]
  }},
  "insight": "이 고급 시각화가 보여주는 핵심 패턴"
}}

**옵션 5 - 테이블:**
{{
  "type": "table",
  "title": "명확한 제목",
  "headers": ["열1", "열2", "열3"],
  "rows": [
    ["데이터1-1", "데이터1-2", "데이터1-3"],
    ["데이터2-1", "데이터2-2", "데이터2-3"]
  ],
  "styling": {{
    "highlight_column": 0,
    "sortable": true
  }},
  "insight": "이 표가 보여주는 핵심 정보"
}}

**중요 지침:**
- 내용에서 실제 데이터를 추출하세요
- 데이터가 없다면 내용을 기반으로 합리적으로 생성하세요
- 색상은 의미를 담아 선택하세요 (증가=녹색, 감소=빨강 등)
- 제목과 레이블은 명확하고 구체적으로 작성하세요
- insight는 단순 설명이 아닌 "발견"이어야 합니다
- 데이터 구조는 선택한 라이브러리에 맞게 정확하게 작성하세요

JSON만 출력하세요."""),
            ("human", "시각화를 생성해주세요.")
        ])

        try:
            # 컨텍스트 정보 포맷팅
            formatted_prompt = prompt.format_messages(
                main_topic=context.get('main_topic', ''),
                purpose=opportunity.get('purpose', ''),
                why_necessary=opportunity.get('why_necessary', ''),
                user_benefit=opportunity.get('user_benefit', ''),
                content=opportunity.get('content', ''),
                key_elements=', '.join(opportunity.get('key_elements', []))
            )

            response = self.llm.invoke(formatted_prompt)
            content = response.content.strip()

            # JSON 추출
            start_idx = content.find('{')
            end_idx = content.rfind('}')

            if start_idx != -1 and end_idx != -1:
                json_str = content[start_idx:end_idx + 1]
                try:
                    result = json.loads(json_str)
                    # 시각화 데이터 후처리
                    viz_type = result.get('type')
                    if viz_type in ['network', 'flow', 'd3'] and 'data' in result:
                        result['data'] = self._validate_visualization_data(result['data'], viz_type)
                    return result
                except json.JSONDecodeError as e:
                    logger.error(f"JSON 파싱 오류: {e}")
                    logger.error(f"파싱 시도한 JSON: {json_str[:500]}...")
                    return self._create_fallback_visualization()
            else:
                logger.error("JSON 블록을 찾을 수 없음")
                return self._create_fallback_visualization()

        except Exception as e:
            logger.error(f"시각화 생성 오류: {e}")
            return self._create_fallback_visualization()
    
    def _create_fallback_visualization(self):
        """폴백 시각화 생성"""
        return {
            "type": "chart",
            "library": "chartjs",
            "title": "기본 차트",
            "chart_type": "bar",
            "data": {
                "labels": ["항목 1", "항목 2", "항목 3"],
                "datasets": [{
                    "label": "데이터",
                    "data": [10, 20, 15],
                    "backgroundColor": ["#667eea", "#f093fb", "#4facfe"]
                }]
            },
            "options": {
                "responsive": True,
                "plugins": {
                    "title": {"display": True, "text": "기본 차트"}
                }
            },
            "insight": "시각화 생성 중 오류가 발생하여 기본 차트를 표시합니다."
        }

    def _validate_visualization_data(self, data: Dict[str, Any], viz_type: str) -> Dict[str, Any]:
        """시각화 데이터 검증 및 수정"""
        try:
            if viz_type == 'network':
                # vis.js 네트워크 데이터 검증
                if 'nodes' not in data or not data['nodes']:
                    data['nodes'] = [
                        {"id": 1, "label": "노드1", "color": "#667eea"},
                        {"id": 2, "label": "노드2", "color": "#f093fb"}
                    ]
                if 'edges' not in data or not data['edges']:
                    data['edges'] = [{"from": 1, "to": 2, "label": "연결"}]
                
                # 노드 ID 확인
                for node in data['nodes']:
                    if 'id' not in node:
                        node['id'] = hash(str(node)) % 10000
                
                logger.info(f"✅ 네트워크 데이터 검증 완료: {len(data['nodes'])} 노드, {len(data['edges'])} 연결")
                
            elif viz_type == 'flow':
                # React Flow 데이터 검증
                if 'nodes' not in data or not data['nodes']:
                    data['nodes'] = [
                        {"id": "1", "type": "input", "position": {"x": 0, "y": 0}, "data": {"label": "시작"}},
                        {"id": "2", "position": {"x": 100, "y": 100}, "data": {"label": "과정"}},
                        {"id": "3", "type": "output", "position": {"x": 200, "y": 200}, "data": {"label": "완료"}}
                    ]
                if 'edges' not in data or not data['edges']:
                    data['edges'] = [
                        {"id": "e1-2", "source": "1", "target": "2"},
                        {"id": "e2-3", "source": "2", "target": "3"}
                    ]
                
                # 노드 위치 확인
                for i, node in enumerate(data['nodes']):
                    if 'position' not in node:
                        node['position'] = {"x": i * 100, "y": i * 100}
                    if 'data' not in node or 'label' not in node['data']:
                        node['data'] = {"label": f"노드 {i+1}"}
                
                logger.info(f"✅ 플로우 차트 데이터 검증 완료: {len(data['nodes'])} 노드, {len(data['edges'])} 연결")
                
            elif viz_type == 'd3':
                # D3.js 데이터 검증
                if 'nodes' not in data or not data['nodes']:
                    data['nodes'] = [
                        {"id": "node1", "name": "노드1", "value": 10},
                        {"id": "node2", "name": "노드2", "value": 20}
                    ]
                if 'links' not in data and 'edges' in data:
                    data['links'] = data['edges']
                elif 'links' not in data:
                    data['links'] = [{"source": "node1", "target": "node2", "value": 5}]
                
                logger.info(f"✅ D3 데이터 검증 완료: {len(data['nodes'])} 노드, {len(data['links'])} 연결")
            
            return data
            
        except Exception as e:
            logger.error(f"시각화 데이터 검증 실패: {e}")
            # 기본 데이터 반환
            if viz_type == 'network':
                return {
                    "nodes": [{"id": 1, "label": "기본 노드"}],
                    "edges": []
                }
            elif viz_type == 'flow':
                return {
                    "nodes": [{"id": "1", "position": {"x": 0, "y": 0}, "data": {"label": "기본 노드"}}],
                    "edges": []
                }
            elif viz_type == 'd3':
                return {
                    "nodes": [{"id": "node1", "name": "기본 노드", "value": 10}],
                    "links": []
                }
            else:
                return {}

    def _find_best_position(self, summary: str, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """요약 내에서 시각화를 배치할 최적의 위치 찾기"""
        content = opportunity.get('content', '')
        location_hint = opportunity.get('location_hint', 'middle')

        # 간단한 휴리스틱으로 위치 결정
        paragraphs = summary.split('\n\n')
        total_paragraphs = len(paragraphs)

        # 관련 키워드 찾기
        keywords = content.lower().split()[:5]  # 처음 5개 단어

        best_position = 0
        max_score = 0

        for i, paragraph in enumerate(paragraphs):
            paragraph_lower = paragraph.lower()
            score = sum(1 for keyword in keywords if keyword in paragraph_lower)

            # 위치 힌트에 따른 가중치
            if location_hint == "beginning" and i < total_paragraphs // 3:
                score += 2
            elif location_hint == "middle" and total_paragraphs // 3 <= i < 2 * total_paragraphs // 3:
                score += 2
            elif location_hint == "end" and i >= 2 * total_paragraphs // 3:
                score += 2

            if score > max_score:
                max_score = score
                best_position = i

        return {
            "after_paragraph": best_position,
            "relevance_score": max_score
        }

    def _standardize_visualization_data(self, visualization: Dict[str, Any]) -> Dict[str, Any]:
        """다양한 시각화 형식을 표준화"""
        viz_type = visualization.get('type')
        
        # diagram 타입을 network 타입으로 변환
        if viz_type == 'diagram':
            logger.info("Mermaid 다이어그램을 Network 다이어그램으로 변환합니다")
            # 기본 네트워크 데이터 생성
            nodes = [
                {"id": 1, "label": "노드 1", "color": "#667eea"},
                {"id": 2, "label": "노드 2", "color": "#f093fb"},
                {"id": 3, "label": "노드 3", "color": "#4facfe"}
            ]
            edges = [
                {"from": 1, "to": 2, "label": "연결 1-2"},
                {"from": 2, "to": 3, "label": "연결 2-3"}
            ]
            
            return {
                "type": "network",
                "library": "visjs",
                "network_type": "relationship",
                "data": {
                    "nodes": nodes,
                    "edges": edges
                },
                "options": {
                    "layout": {"hierarchical": {"enabled": True, "direction": "LR"}},
                    "physics": {"enabled": True}
                }
            }

        if viz_type == 'chart':
            return {
                "type": "chart",
                "library": visualization.get('library', 'chartjs'),
                "config": {
                    "type": visualization.get('chart_type', 'bar'),
                    "data": visualization.get('data', {}),
                    "options": visualization.get('options', {})
                }
            }

        elif viz_type == 'network':
            return {
                "type": "network",
                "library": visualization.get('library', 'visjs'),
                "network_type": visualization.get('network_type', 'relationship'),
                "data": visualization.get('data', {}),
                "options": visualization.get('options', {})
            }
            
        elif viz_type == 'flow':
            return {
                "type": "flow",
                "library": visualization.get('library', 'reactflow'),
                "flow_type": visualization.get('flow_type', 'flowchart'),
                "data": visualization.get('data', {}),
                "options": visualization.get('options', {})
            }
            
        elif viz_type == 'd3':
            return {
                "type": "d3",
                "library": visualization.get('library', 'd3js'),
                "visualization_type": visualization.get('visualization_type', 'force'),
                "data": visualization.get('data', {}),
                "config": visualization.get('config', {})
            }

        elif viz_type == 'table':
            return {
                "type": "table",
                "headers": visualization.get('headers', []),
                "rows": visualization.get('rows', []),
                "styling": visualization.get('styling', {})
            }

        else:
            return visualization