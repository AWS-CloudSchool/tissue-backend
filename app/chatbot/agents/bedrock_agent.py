#agents/bedrock_agent.py
from app.chatbot.chains.qa_chain import build_qa_chain
from app.chatbot.retrievers.kb_retriever import get_kb_retriever, get_llm
import re

# 검색 score 기준 (이하일 경우 실패로 간주)
RELEVANCE_THRESHOLD = 0.5

def extract_best_time_and_text_with_ai(content: str, question: str, llm) -> str:
    """AI를 활용하여 질문과 가장 관련있는 자막 구문을 선택"""
    pattern = r'\[at (\d+\.?\d*) seconds?\]\s*([^\n\r]+)'
    matches = re.findall(pattern, content)
    
    if not matches:
        return "시간 정보 없음"
    
    if len(matches) == 1:
        # 하나만 있으면 바로 반환
        #123.45초를 "2분 3초" 식으로 보기 좋게 바꾸는 거야
        # 즉, 시간을 사람이 이해하기 쉬운 형식으로 변환
        sec, txt = matches[0]
        seconds = float(sec)
        minutes = int(seconds // 60)
        remaining_seconds = int(seconds % 60)
        if minutes > 0:
            time_str = f"{minutes}:{remaining_seconds:02d}"
        else:
            time_str = f"{remaining_seconds}초"
        return f"{time_str}: {txt.strip()}"
    
    # 여러 개가 있으면 AI로 평가
    try:
        # 각 구문을 평가할 프롬프트 생성
        evaluation_prompt = f"""
다음 질문과 가장 관련있는 자막 구문을 선택해주세요.

질문: {question}

자막 구문들:
"""
        for i, (sec, txt) in enumerate(matches, 1):
            evaluation_prompt += f"{i}. {txt.strip()}\n"
        
        evaluation_prompt += """
위 자막 구문들 중에서 질문과 가장 관련있는 구문의 번호만 숫자로 답해주세요.
"""
        # AI 평가
        response = llm.invoke(evaluation_prompt)
        if hasattr(response, 'content'):
            result = response.content.strip()
        else:
            result = str(response).strip()
        
        # 숫자 추출
        # 이건 Claude가 준 **"답변 문자열"**에서
        # 숫자만 뽑아내서 → 몇 번째 문장을 선택했는지 파악
        # 그 다음에 해당 matches[index]를 다시 꺼내서 위처럼 시간 형식으로 출력
        number_match = re.search(r'\d+', result)
        if number_match:
            selected_idx = int(number_match.group()) - 1
            if 0 <= selected_idx < len(matches):
                sec, txt = matches[selected_idx]
                seconds = float(sec)
                minutes = int(seconds // 60)
                remaining_seconds = int(seconds % 60)
                if minutes > 0:
                    time_str = f"{minutes}:{remaining_seconds:02d}"
                else:
                    time_str = f"{remaining_seconds}초"
                return f"{time_str}: {txt.strip()}"
    
    except Exception as e:
        print(f"   - ⚠️ AI 평가 중 오류: {e}")
    
    # AI 평가 실패시 첫 번째 구문 반환
    sec, txt = matches[0]
    seconds = float(sec)
    minutes = int(seconds // 60)
    remaining_seconds = int(seconds % 60)
    if minutes > 0:
        time_str = f"{minutes}:{remaining_seconds:02d}"
    else:
        time_str = f"{remaining_seconds}초"
    return f"{time_str}: {txt.strip()}"

def extract_video_id_from_content(content: str) -> str:
    """자막 내용에서 비디오 ID나 파일명 추출 시도"""
    # 파일명 패턴 찾기 (예: OA7LIkxp3_o_xxx.txt)
    video_pattern = r'([A-Za-z0-9_-]{11})_[a-f0-9]+\.txt'
    matches = re.findall(video_pattern, content)
    
    if matches:
        return f"YouTube ID: {matches[0]}"
    
    return "동영상 정보 없음"

def answer_question(question: str):
    retriever = get_kb_retriever()
    llm = get_llm()

    docs = retriever(question)

    # Bedrock에서 반환한 score 확인
    high_quality_docs = [
        doc for doc in docs
        if doc.metadata.get("score", 1.0) >= RELEVANCE_THRESHOLD
    ]
    
    relevance_scores = [doc.metadata.get("score", 0.0) for doc in docs]

    if high_quality_docs:
        print("📚 ✅ KB 검색 성공 → Claude + KB 체인 사용")
        
        # 중복 제거: 같은 시간과 텍스트를 가진 문서는 하나만 표시
        unique_docs = []
        seen_content = set()
        
        for doc in high_quality_docs:
            time_and_text = extract_best_time_and_text_with_ai(doc.page_content, question, llm)
            if time_and_text not in seen_content:
                seen_content.add(time_and_text)
                unique_docs.append((doc, time_and_text))
        
        # 고유한 문서만 표시
        for i, (doc, time_and_text) in enumerate(unique_docs, 1):
            print(f"   - 🔗 문서 {i}: {time_and_text}")
        
        # KB 검색 결과를 context로 사용
        context = "\n".join([doc.page_content for doc in high_quality_docs])
        qa_chain = build_qa_chain()
        response = qa_chain.invoke({"context": context, "question": question})
        
        # 응답에서 content만 추출
        if hasattr(response, 'content'):
            answer = response.content
        else:
            answer = str(response)
            
        return {
            'answer': answer,
            'source_type': 'KB',
            'documents_found': len(high_quality_docs),
            'relevance_scores': relevance_scores[:5]  # 상위 5개만
        }

    else:
        print("🌐 ❗ KB 검색 실패 → Claude 단독 응답(Fallback)")
        response = llm.invoke(question)
        
        # 응답에서 content만 추출
        if hasattr(response, 'content'):
            answer = response.content
        else:
            answer = str(response)
            
        return {
            'answer': answer,
            'source_type': 'FALLBACK',
            'documents_found': 0,
            'relevance_scores': relevance_scores[:5] if relevance_scores else []
        }