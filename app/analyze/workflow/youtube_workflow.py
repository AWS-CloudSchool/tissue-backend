# app/agents/graph_workflow.py
from typing import TypedDict, Dict, Any, List
from langgraph.graph import StateGraph
from app.analyze.agents.caption_extractor import CaptionAgent
from app.analyze.agents.content_summarizer import SummaryAgent
from app.analyze.agents.visualization_generator import SmartVisualAgent
from app.analyze.agents.report_builder import ReportAgent
from app.analyze.services.state_manager import state_manager
import logging

logger = logging.getLogger(__name__)


class GraphState(TypedDict):
    """워크플로우 상태 정의 - taeho 백엔드 통합 버전"""
    job_id: str
    user_id: str
    youtube_url: str
    caption: str
    summary: str
    visual_sections: List[Dict[str, Any]]
    report_result: Dict[str, Any]
    final_output: Dict[str, Any]


class YouTubeReporterWorkflow:
    """YouTube 영상 분석 및 리포트 생성 워크플로우 - taeho 백엔드 통합 버전"""

    def __init__(self):
        logger.info("YouTube Reporter 워크플로우 초기화 중...")
        self.caption_agent = CaptionAgent()
        self.summary_agent = SummaryAgent()
        self.visual_agent = SmartVisualAgent()
        self.report_agent = ReportAgent()
        self.graph = self._build_graph()
        logger.info("✅ YouTube Reporter 워크플로우 초기화 완료")

    def _build_graph(self):
        """LangGraph 워크플로우 구성"""
        builder = StateGraph(state_schema=GraphState)

        # 노드 추가
        builder.add_node("caption_node", self.caption_agent)
        builder.add_node("summary_node", self.summary_agent)
        builder.add_node("visual_node", self.visual_agent)
        builder.add_node("report_node", self.report_agent)
        builder.add_node("finalize_node", self._finalize_result)

        # 엣지 연결 - 순차적 실행
        builder.set_entry_point("caption_node")
        builder.add_edge("caption_node", "summary_node")
        builder.add_edge("summary_node", "visual_node")
        builder.add_edge("visual_node", "report_node")
        builder.add_edge("report_node", "finalize_node")
        builder.add_edge("finalize_node", "__end__")

        return builder.compile()

    def _finalize_result(self, state: dict, config=None) -> dict:
        """최종 결과 정리 및 포맷팅"""
        report_result = state.get("report_result", {})
        job_id = state.get("job_id")
        user_id = state.get("user_id")

        logger.info("🎯 최종 결과 정리 중...")

        # 진행률 업데이트
        if job_id:
            try:
                state_manager.update_progress(job_id, 100, "✅ 분석 완료!")
            except Exception as e:
                logger.warning(f"진행률 업데이트 실패 (무시됨): {e}")

        # 최종 출력 구조화
        final_output = {
            "success": not report_result.get("metadata", {}).get("error", False),
            "title": report_result.get("title", "YouTube 영상 분석 리포트"),
            "summary": report_result.get("summary_brief", ""),
            "sections": report_result.get("sections", []),
            "statistics": {
                "total_sections": report_result.get("metadata", {}).get("total_sections", 0),
                "text_sections": report_result.get("metadata", {}).get("text_sections", 0),
                "visualizations": report_result.get("metadata", {}).get("visual_sections", 0)
            },
            "process_info": {
                "youtube_url": state.get("youtube_url", ""),
                "caption_length": len(state.get("caption", "")),
                "summary_length": len(state.get("summary", "")),
                "user_id": user_id,
                "job_id": job_id,
                "generated_at": report_result.get("metadata", {}).get("generated_at", "")
            }
        }

        # 시각화 데이터 검증 및 정리
        for i, section in enumerate(final_output["sections"]):
            if not isinstance(section, dict):
                logger.warning("잘못된 섹션 형식 감지: %s", section)
                final_output["sections"][i] = {
                    "id": f"section_{i + 1}",
                    "title": f"섹션 {i + 1}",
                    "type": "text",
                    "content": str(section),
                }
                section = final_output["sections"][i]

            if section.get("type") == "visualization":
                if not section.get("data"):
                    logger.warning("시각화 섹션 '%s' 데이터 누락", section.get("title"))
                    section["error"] = "시각화 데이터가 없습니다"
                else:
                    viz_info = section.get("visualization_type")
                    if isinstance(viz_info, dict):
                        viz_type = viz_info.get("type")
                    else:
                        if viz_info and not isinstance(viz_info, str):
                            logger.warning("Unexpected visualization_type format: %s", viz_info)
                        viz_type = viz_info

                    if viz_type == "chart" and not section["data"].get("config"):
                        section["error"] = "차트 설정이 없습니다"
                    elif viz_type == "network" and not section["data"].get("data"):
                        section["error"] = "네트워크 데이터가 없습니다"
                    elif viz_type == "flow" and not section["data"].get("data"):
                        section["error"] = "플로우 데이터가 없습니다"

        logger.info("📊 최종 리포트 생성 완료:")
        logger.info(f"   - 제목: {final_output['title']}")
        logger.info(f"   - 전체 섹션: {final_output['statistics']['total_sections']}개")
        logger.info(f"   - 텍스트: {final_output['statistics']['text_sections']}개")
        logger.info(f"   - 시각화: {final_output['statistics']['visualizations']}개")

        return {**state, "final_output": final_output}

    def process(self, youtube_url: str, job_id: str = None, user_id: str = None) -> dict:
        """YouTube URL을 처리하여 리포트 생성"""
        logger.info(f"\n{'=' * 60}")
        logger.info(f"🎬 YouTube Reporter 시작: {youtube_url}")
        logger.info(f"🆔 Job ID: {job_id}")
        logger.info(f"👤 User ID: {user_id}")
        logger.info(f"{'=' * 60}\n")

        initial_state = {
            "job_id": job_id,
            "user_id": user_id,
            "youtube_url": youtube_url,
            "caption": "",
            "summary": "",
            "visual_sections": [],
            "report_result": {},
            "final_output": {}
        }

        try:
            # 진행률 초기화
            if job_id:
                try:
                    state_manager.update_progress(job_id, 0, "🚀 분석 시작...")
                except Exception as e:
                    logger.warning(f"진행률 초기화 실패 (무시됨): {e}")

            logger.info("📝 1단계: 자막 추출 시작...")
            result = self.graph.invoke(initial_state)

            final_output = result.get("final_output", {})

            if final_output.get("success"):
                logger.info("\n✅ 리포트 생성 성공!")
            else:
                logger.warning("\n⚠️ 리포트 생성 중 일부 문제 발생")

            return final_output

        except Exception as e:
            logger.error(f"\n❌ 워크플로우 실행 실패: {str(e)}")

            # 실패 시 진행률 업데이트
            if job_id:
                try:
                    state_manager.update_progress(job_id, -1, f"❌ 분석 실패: {str(e)}")
                except Exception as progress_error:
                    logger.warning(f"진행률 업데이트 실패 (무시됨): {progress_error}")

            return {
                "success": False,
                "title": "리포트 생성 실패",
                "summary": f"워크플로우 실행 중 오류가 발생했습니다: {str(e)}",
                "sections": [],
                "statistics": {
                    "total_sections": 0,
                    "text_sections": 0,
                    "visualizations": 0
                },
                "process_info": {
                    "youtube_url": youtube_url,
                    "user_id": user_id,
                    "job_id": job_id,
                    "error": str(e)
                }
            }