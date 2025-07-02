# app/agents/report_agent.py
import os
import json
import boto3
from typing import Dict, List, Any
from langchain_aws import ChatBedrock
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from app.core.config import settings
from app.analyze.services.state_manager import state_manager
import logging

logger = logging.getLogger(__name__)


class ReportAgent(Runnable):
    """요약과 시각화를 결합하여 최종 리포트를 생성하는 에이전트 - taeho 백엔드 통합 버전"""

    def __init__(self):
        self.llm = ChatBedrock(
            client=boto3.client("bedrock-runtime", region_name=settings.AWS_REGION),
            model_id=settings.BEDROCK_MODEL_ID,
            model_kwargs={"temperature": settings.BEDROCK_TEMPERATURE, "max_tokens": settings.BEDROCK_MAX_TOKENS}
        )

    def invoke(self, state: dict, config=None) -> dict:
        """요약과 시각화를 결합하여 최종 리포트 생성"""
        summary = state.get("summary", "")
        visual_sections = state.get("visual_sections", [])
        job_id = state.get("job_id")
        user_id = state.get("user_id")

        logger.info("📊 최종 리포트 생성 시작...")

        # 진행률 업데이트
        if job_id:
            try:
                state_manager.update_progress(job_id, 80, "📊 최종 리포트 생성 중...")
            except Exception as e:
                logger.warning(f"진행률 업데이트 실패 (무시됨): {e}")

        if not summary:
            logger.warning("요약이 없습니다.")
            return {**state, "report_result": self._create_error_report("요약을 생성할 수 없습니다.")}

        try:
            # 1. 요약을 섹션으로 구조화
            logger.info("📝 요약을 섹션으로 구조화 중...")
            structured_sections = self._structure_summary(summary)

            # 2. 시각화를 적절한 위치에 삽입
            logger.info(f"🎨 {len(visual_sections)}개의 시각화를 배치 중...")
            final_sections = self._merge_visualizations(structured_sections, visual_sections)

            # 3. 최종 리포트 생성
            report_result = {
                "title": self._extract_title(summary),
                "summary_brief": self._create_brief_summary(summary),
                "sections": final_sections,
                "metadata": {
                    "total_sections": len(final_sections),
                    "text_sections": len([s for s in final_sections if s.get("type") == "text"]),
                    "visual_sections": len([s for s in final_sections if s.get("type") == "visualization"]),
                    "generated_at": "",
                    "user_id": user_id,
                    "job_id": job_id
                }
            }

            logger.info(f"✅ 리포트 생성 완료: {len(final_sections)}개 섹션")
            return {**state, "report_result": report_result}

        except Exception as e:
            logger.error(f"리포트 생성 실패: {str(e)}")
            return {**state, "report_result": self._create_error_report(str(e))}

    def _structure_summary(self, summary: str) -> List[Dict[str, Any]]:
        """요약을 논리적 섹션으로 구조화"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """주어진 요약을 논리적인 섹션으로 구조화해주세요.

**구조화 원칙:**
1. 각 섹션은 하나의 주제나 개념을 다룹니다
2. 섹션 제목은 명확하고 구체적이어야 합니다
3. 내용의 흐름이 자연스럽게 이어져야 합니다
4. 너무 짧거나 긴 섹션은 피합니다 (이상적: 100-300자)

**응답 형식 (JSON):**
{
  "sections": [
    {
      "id": "section_1",
      "title": "섹션 제목",
      "type": "text",
      "content": "섹션 내용",
      "level": 1,
      "keywords": ["키워드1", "키워드2"]
    }
  ]
}

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
                result = json.loads(json_str)
                return result.get('sections', [])
            else:
                # 폴백: 단락 기반 섹션 생성
                return self._fallback_sectioning(summary)

        except Exception as e:
            logger.error(f"섹션 구조화 오류: {e}")
            return self._fallback_sectioning(summary)

    def _fallback_sectioning(self, summary: str) -> List[Dict[str, Any]]:
        """폴백: 단순 단락 기반 섹션 생성"""
        paragraphs = summary.split('\n\n')
        sections = []

        for i, paragraph in enumerate(paragraphs):
            if len(paragraph.strip()) > 50:  # 너무 짧은 단락 제외
                sections.append({
                    "id": f"section_{i + 1}",
                    "title": f"섹션 {i + 1}",
                    "type": "text",
                    "content": paragraph.strip(),
                    "level": 2,
                    "keywords": []
                })

        return sections

    def _merge_visualizations(self, text_sections: List[Dict], visual_sections: List[Dict]) -> List[Dict]:
        """텍스트 섹션과 시각화를 적절히 병합"""
        if not visual_sections:
            return text_sections

        # 시각화를 위치 정보로 정렬
        sorted_visuals = sorted(visual_sections,
                                key=lambda x: x.get('position', {}).get('after_paragraph', 999))

        final_sections = []
        visual_index = 0

        for i, text_section in enumerate(text_sections):
            # 텍스트 섹션 추가
            final_sections.append(text_section)

            # 이 위치에 삽입할 시각화 확인
            while (visual_index < len(sorted_visuals) and
                   sorted_visuals[visual_index].get('position', {}).get('after_paragraph', 999) <= i):
                visual = sorted_visuals[visual_index]
                final_sections.append({
                    "id": f"visual_{visual_index + 1}",
                    "title": visual.get('title', '시각화'),
                    "type": "visualization",
                    "visualization_type": visual.get("visualization_type"),
                    "data": visual.get('data'),
                    "insight": visual.get('insight', ''),
                    "purpose": visual.get('purpose', ''),
                    "user_benefit": visual.get('user_benefit', '')
                })
                visual_index += 1

        # 남은 시각화 추가
        while visual_index < len(sorted_visuals):
            visual = sorted_visuals[visual_index]
            final_sections.append({
                "id": f"visual_{visual_index + 1}",
                "title": visual.get('title', '시각화'),
                "type": "visualization",
                "visualization_type": visual.get('visualization_type'),
                "data": visual.get('data'),
                "insight": visual.get('insight', ''),
                "purpose": visual.get('purpose', ''),
                "user_benefit": visual.get('user_benefit', '')
            })
            visual_index += 1

        return final_sections

    def _extract_title(self, summary: str) -> str:
        """요약에서 적절한 제목 추출"""
        # 첫 문장이나 첫 줄을 제목으로 사용
        first_line = summary.split('\n')[0]
        if len(first_line) > 100:
            first_line = first_line[:97] + "..."

        # 제목 다듬기
        if "개요" in first_line or "요약" in first_line:
            # 더 구체적인 제목 생성 시도
            sentences = summary.split('.')[:3]
            for sentence in sentences:
                if len(sentence) > 20 and len(sentence) < 80:
                    return sentence.strip()

        return first_line.strip()

    def _create_brief_summary(self, summary: str) -> str:
        """전체 요약의 간단한 요약 생성 (2-3문장)"""
        sentences = summary.replace('\n', ' ').split('.')

        # 중요한 문장 선택
        important_sentences = []
        importance_keywords = ['핵심', '중요', '주요', '결론', '목적', '요약']

        for sentence in sentences[:10]:  # 처음 10문장 중에서
            if any(keyword in sentence for keyword in importance_keywords):
                important_sentences.append(sentence.strip())

        # 중요 문장이 없으면 처음 2문장 사용
        if not important_sentences:
            important_sentences = [s.strip() for s in sentences[:2] if s.strip()]

        # 최대 2문장만 반환
        brief = '. '.join(important_sentences[:2])
        if not brief.endswith('.'):
            brief += '.'

        return brief

    def _create_error_report(self, error_message: str) -> Dict[str, Any]:
        """오류 발생 시 기본 리포트 생성"""
        return {
            "title": "리포트 생성 실패",
            "summary_brief": f"리포트 생성 중 오류가 발생했습니다: {error_message}",
            "sections": [
                {
                    "id": "error_section",
                    "title": "오류 정보",
                    "type": "text",
                    "content": f"죄송합니다. 리포트 생성 중 다음과 같은 오류가 발생했습니다:\n\n{error_message}\n\n다시 시도해 주시거나, 다른 영상으로 시도해 보세요.",
                    "level": 1,
                    "keywords": ["오류", "실패"]
                }
            ],
            "metadata": {
                "total_sections": 1,
                "text_sections": 1,
                "visual_sections": 0,
                "error": True
            }
        }