import os
import json
import time
import re
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import streamlit as st
from dataclasses import dataclass

# ===== 데이터 구조 =====
@dataclass
class CoverLetterProject:
    job_title: str
    jd_text: str
    resume_text: str
    questions: str
    draft: Optional[str] = None
    refined: Optional[str] = None
    keywords: Optional[List[str]] = None
    coverage: Optional[Dict] = None
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    target_len: int = 800
    tone: str = "정중하고 간결한"
    timestamp: float = 0.0

# ===== OpenAI API 래퍼 =====
class OpenAIClient:
    def __init__(self):
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        try:
            from openai import OpenAI
            api_key = os.getenv("OPENAI_API_KEY") or st.session_state.get("api_key", "")
            if api_key:
                self.client = OpenAI(api_key=api_key)
                self.is_v1 = True
            else:
                raise Exception("No API key found")
        except Exception:
            try:
                import openai
                api_key = os.getenv("OPENAI_API_KEY") or st.session_state.get("api_key", "")
                if api_key:
                    openai.api_key = api_key
                    self.client = openai
                    self.is_v1 = False
                else:
                    raise Exception("No API key found")
            except Exception as e:
                st.error(f"OpenAI 클라이언트 초기화 실패: {e}")
                self.client = None
    
    def call_openai(self, model: str, messages: List[Dict], temperature: float = 0.7, max_tokens: int = 1200) -> str:
        if not self.client:
            raise Exception("OpenAI 클라이언트가 초기화되지 않았습니다.")
        
        try:
            if self.is_v1:
                resp = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return resp.choices[0].message.content
            else:
                resp = self.client.ChatCompletion.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return resp["choices"][0]["message"]["content"]
        except Exception as e:
            if "rate limit" in str(e).lower():
                raise Exception("API 호출 한도 초과. 잠시 후 다시 시도해주세요.")
            elif "invalid api key" in str(e).lower():
                raise Exception("유효하지 않은 API 키입니다.")
            else:
                raise Exception(f"API 호출 실패: {str(e)}")

# ===== 유틸리티 함수들 =====
class TextAnalyzer:
    @staticmethod
    def count_korean_chars(text: str) -> int:
        """한글 문자 수 계산"""
        return len(re.sub(r'[^\uAC00-\uD7A3]', '', text))
    
    @staticmethod
    def analyze_readability(text: str) -> Dict:
        """가독성 분석"""
        sentences = re.split(r'[.!?]\s*', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return {"avg_sentence_length": 0, "long_sentences": 0, "readability_score": 0}
        
        sentence_lengths = [len(s) for s in sentences]
        avg_length = sum(sentence_lengths) / len(sentence_lengths)
        long_sentences = sum(1 for length in sentence_lengths if length > 100)
        
        # 간단한 가독성 점수 (100점 만점)
        readability_score = max(0, min(100, 100 - (avg_length - 50) * 2 - long_sentences * 10))
        
        return {
            "avg_sentence_length": round(avg_length, 1),
            "long_sentences": long_sentences,
            "readability_score": round(readability_score, 1),
            "total_sentences": len(sentences)
        }
    
    @staticmethod
    def detect_cliche_advanced(text: str) -> Dict:
        """고도화된 클리셰 감지"""
        cliche_patterns = {
            "과도한 형용사": ["매우", "정말", "너무", "굉장히", "엄청", "최고의", "완벽한"],
            "뻔한 표현": ["열정적으로", "끊임없이 노력", "항상 최선", "도전정신", "책임감", "소통능력"],
            "추상적 표현": ["시너지", "윈윈", "파라다임", "벤치마킹", "글로벌 마인드"],
            "과장 표현": ["혁신적인", "차별화된", "독창적인", "탁월한", "뛰어난"]
        }
        
        detected = {}
        total_cliche = 0
        
        for category, words in cliche_patterns.items():
            found = []
            for word in words:
                count = text.count(word)
                if count > 0:
                    found.append(f"{word}({count})")
                    total_cliche += count
            detected[category] = found
        
        return {
            "categories": detected,
            "total_cliche_count": total_cliche,
            "cliche_density": round(total_cliche / max(1, len(text)) * 1000, 2)  # 1000자당 클리셰 수
        }

class KeywordAnalyzer:
    def __init__(self, openai_client: OpenAIClient):
        self.client = openai_client
    
    def extract_keywords(self, text: str, top_k: int = 20) -> List[str]:
        """키워드 추출 (개선된 버전)"""
        if not text.strip():
            return []
        
        prompt = f"""
        아래 채용 공고/직무 설명서를 분석하여 중요한 키워드를 추출해주세요.
        
        추출 기준:
        1. 직무 관련 전문 용어 및 기술
        2. 필수 역량 및 자격요건
        3. 우대사항
        4. 회사/조직 문화 관련 키워드
        
        형식: 쉼표로 구분하여 중요도 순으로 최대 {top_k}개
        
        텍스트:
        {text}
        """
        
        try:
            response = self.client.call_openai("gpt-4o-mini", [
                {"role": "system", "content": "당신은 채용 전문가입니다. 정확하고 구체적인 키워드만 추출하세요."},
                {"role": "user", "content": prompt}
            ], temperature=0.1, max_tokens=400)
            
            keywords = [kw.strip().strip(".,·") for kw in response.split(",") if kw.strip()]
            return keywords[:top_k]
        except Exception as e:
            st.error(f"키워드 추출 실패: {e}")
            return []
    
    def analyze_coverage(self, draft: str, keywords: List[str]) -> Dict:
        """키워드 커버리지 분석 (개선된 버전)"""
        if not draft or not keywords:
            return {"covered": [], "missing": keywords, "coverage": 0.0, "partial_matches": []}
        
        draft_lower = draft.lower()
        covered = []
        partial_matches = []
        missing = []
        
        for keyword in keywords:
            kw_lower = keyword.lower()
            if kw_lower in draft_lower:
                covered.append(keyword)
            elif any(word in draft_lower for word in kw_lower.split()):
                partial_matches.append(keyword)
            else:
                missing.append(keyword)
        
        coverage = round(100.0 * len(covered) / max(1, len(keywords)), 1)
        partial_coverage = round(100.0 * len(partial_matches) / max(1, len(keywords)), 1)
        
        return {
            "covered": covered,
            "partial_matches": partial_matches,
            "missing": missing,
            "coverage": coverage,
            "partial_coverage": partial_coverage,
            "total_coverage": coverage + partial_coverage * 0.5
        }

class CoverLetterGenerator:
    def __init__(self, openai_client: OpenAIClient):
        self.client = openai_client
    
    def generate_draft(self, project: CoverLetterProject) -> str:
        """초안 생성"""
        context = self._build_context(project)
        
        prompt = f"""
        다음 정보를 바탕으로 한국어 자기소개서를 작성해주세요.
        
        {context}
        
        작성 가이드라인:
        1. 각 문항별로 구체적이고 차별화된 답변 작성
        2. STAR 기법 활용 (Situation, Task, Action, Result)
        3. 정량적 성과와 구체적 사례 포함
        4. {project.tone} 톤 유지
        5. 문항 제목을 **굵게** 표시
        6. 채용공고의 핵심 키워드 자연스럽게 포함
        
        금지사항:
        - 일반적이고 추상적인 표현 남발
        - 근거 없는 과장
        - 타인의 성과 도용
        """
        
        try:
            response = self.client.call_openai(project.model, [
                {"role": "system", "content": "당신은 전문 자기소개서 작성 컨설턴트입니다."},
                {"role": "user", "content": prompt}
            ], temperature=project.temperature, max_tokens=1500)
            
            return response
        except Exception as e:
            raise Exception(f"초안 생성 실패: {e}")
    
    def refine_text(self, text: str, project: CoverLetterProject) -> str:
        """텍스트 정제 및 길이 조정"""
        current_chars = TextAnalyzer.count_korean_chars(text)
        
        prompt = f"""
        다음 자기소개서를 개선해주세요.
        
        현재 길이: {current_chars}자
        목표 길이: {project.target_len}자 (±50자)
        톤: {project.tone}
        
        개선 사항:
        1. 목표 길이에 맞게 조정
        2. 문장 구조 개선 및 가독성 향상
        3. 불필요한 수식어 제거
        4. 구체적 수치와 성과는 보존
        5. 논리적 흐름 강화
        
        원문:
        {text}
        """
        
        try:
            response = self.client.call_openai(project.model, [
                {"role": "system", "content": "당신은 전문 에디터입니다. 정확한 길이 조정과 품질 향상을 동시에 수행합니다."},
                {"role": "user", "content": prompt}
            ], temperature=0.4, max_tokens=1200)
            
            return response
        except Exception as e:
            raise Exception(f"텍스트 정제 실패: {e}")
    
    def _build_context(self, project: CoverLetterProject) -> str:
        """컨텍스트 구성"""
        context_parts = []
        
        if project.job_title:
            context_parts.append(f"지원 직무/회사: {project.job_title}")
        
        if project.jd_text:
            context_parts.append(f"채용 공고/직무 기술서:\n{project.jd_text}")
        
        if project.resume_text:
            context_parts.append(f"지원자 이력/경험:\n{project.resume_text}")
        
        if project.questions:
            context_parts.append(f"자기소개서 문항:\n{project.questions}")
        
        return "\n\n".join(context_parts)

# ===== Streamlit 앱 =====
def initialize_session_state():
    """세션 상태 초기화"""
    defaults = {
        "project": CoverLetterProject("", "", "", ""),
        "openai_client": None,
        "keyword_analyzer": None,
        "generator": None,
        "api_key": ""
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def setup_sidebar():
    """사이드바 설정"""
    with st.sidebar:
        st.header("⚙️ 설정")
        
        # API 키 설정
        if not os.getenv("OPENAI_API_KEY"):
            api_key = st.text_input("OpenAI API Key", type="password", value=st.session_state.api_key)
            if api_key != st.session_state.api_key:
                st.session_state.api_key = api_key
                st.session_state.openai_client = None  # 클라이언트 재초기화 필요
        
        # 모델 설정
        project = st.session_state.project
        project.model = st.selectbox("모델", ["gpt-4o-mini", "gpt-4o", "gpt-4o-2024-08-06"], index=0)
        project.temperature = st.slider("창의성 (temperature)", 0.0, 1.2, 0.7, 0.1)
        project.target_len = st.number_input("목표 글자수(한글)", 200, 3000, 800, 50)
        project.tone = st.selectbox("톤/스타일", [
            "정중하고 간결한", "열정적이고 직설적인", "논리적이고 분석적인", 
            "따뜻하고 스토리텔링 위주", "창의적이고 도전적인"
        ])
        
        # 고급 옵션
        with st.expander("🔧 고급 옵션"):
            show_analysis = st.checkbox("상세 분석 표시", True)
            auto_save = st.checkbox("자동 저장", False)
            
        return show_analysis, auto_save

def initialize_clients():
    """클라이언트 초기화"""
    if st.session_state.openai_client is None:
        try:
            st.session_state.openai_client = OpenAIClient()
            st.session_state.keyword_analyzer = KeywordAnalyzer(st.session_state.openai_client)
            st.session_state.generator = CoverLetterGenerator(st.session_state.openai_client)
        except Exception as e:
            st.error(f"클라이언트 초기화 실패: {e}")
            return False
    return True

def render_input_form():
    """입력 폼 렌더링"""
    st.subheader("📝 1) 기본 정보 입력")
    
    project = st.session_state.project
    
    col1, col2 = st.columns(2)
    with col1:
        project.job_title = st.text_input(
            "지원 직무/회사", 
            value=project.job_title,
            placeholder="예: 데이터 분석가 - 삼성전자"
        )
        
        project.jd_text = st.text_area(
            "채용 공고/직무 기술서", 
            value=project.jd_text,
            height=200,
            placeholder="채용공고를 붙여넣으세요. 요구역량, 우대사항 등이 포함되면 더 좋습니다."
        )
    
    with col2:
        project.resume_text = st.text_area(
            "이력/경험 요약", 
            value=project.resume_text,
            height=200,
            placeholder="주요 프로젝트, 성과(정량적 수치), 보유 기술 등을 간략히 정리해주세요."
        )
    
    project.questions = st.text_area(
        "자기소개서 문항 (한 줄에 하나씩)",
        value=project.questions or ("지원 동기와 입사 후 포부를 작성해주세요.\n"
                                   "본인의 강점과 이를 증명하는 사례를 작성해주세요.\n"
                                   "협업 경험과 갈등 해결 사례를 작성해주세요."),
        height=120
    )
    
    # 입력 검증
    missing_fields = []
    if not project.job_title.strip():
        missing_fields.append("지원 직무/회사")
    if not project.questions.strip():
        missing_fields.append("자기소개서 문항")
    
    if missing_fields:
        st.warning(f"필수 입력 사항: {', '.join(missing_fields)}")
        return False
    
    return True

def render_generation_buttons():
    """생성 버튼 렌더링"""
    st.subheader("🚀 2) 생성")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        generate_draft = st.button("📄 초안 생성", use_container_width=True)
    with col2:
        refine_text = st.button("✨ 길이/톤 보정", use_container_width=True, 
                               disabled=not st.session_state.project.draft)
    with col3:
        generate_all = st.button("🎯 전체 생성", use_container_width=True)
    with col4:
        analyze_keywords = st.button("🔍 키워드 분석", use_container_width=True)
    
    return generate_draft, refine_text, generate_all, analyze_keywords

def process_generation(generate_draft, refine_text, generate_all, analyze_keywords):
    """생성 프로세스 처리"""
    project = st.session_state.project
    
    if not initialize_clients():
        return
    
    # 초안 생성
    if generate_draft or generate_all:
        with st.spinner("📝 초안을 생성하고 있습니다..."):
            try:
                project.draft = st.session_state.generator.generate_draft(project)
                project.timestamp = time.time()
                st.success("✅ 초안 생성 완료!")
            except Exception as e:
                st.error(f"❌ 초안 생성 실패: {e}")
                return
    
    # 길이/톤 보정
    if (refine_text or generate_all) and project.draft:
        with st.spinner("✨ 텍스트를 정제하고 있습니다..."):
            try:
                project.refined = st.session_state.generator.refine_text(project.draft, project)
                st.success("✅ 보정 완료!")
            except Exception as e:
                st.error(f"❌ 보정 실패: {e}")
    
    # 키워드 분석
    if (analyze_keywords or generate_all) and project.jd_text:
        with st.spinner("🔍 키워드를 분석하고 있습니다..."):
            try:
                project.keywords = st.session_state.keyword_analyzer.extract_keywords(project.jd_text)
                
                if project.refined or project.draft:
                    text_to_analyze = project.refined or project.draft
                    project.coverage = st.session_state.keyword_analyzer.analyze_coverage(
                        text_to_analyze, project.keywords
                    )
                
                st.success("✅ 키워드 분석 완료!")
            except Exception as e:
                st.error(f"❌ 키워드 분석 실패: {e}")

def render_results():
    """결과 렌더링"""
    st.subheader("📋 3) 결과")
    
    project = st.session_state.project
    
    # 탭으로 구성
    tab1, tab2, tab3 = st.tabs(["📄 초안", "✨ 보정본", "📊 비교"])
    
    with tab1:
        if project.draft:
            chars = TextAnalyzer.count_korean_chars(project.draft)
            st.metric("글자 수", f"{chars:,}자")
            st.markdown(project.draft)
        else:
            st.info("아직 초안이 생성되지 않았습니다.")
    
    with tab2:
        if project.refined:
            chars = TextAnalyzer.count_korean_chars(project.refined)
            target_diff = chars - project.target_len
            st.metric("글자 수", f"{chars:,}자", f"{target_diff:+}자 (목표 대비)")
            st.markdown(project.refined)
        else:
            st.info("아직 보정본이 생성되지 않았습니다.")
    
    with tab3:
        if project.draft and project.refined:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("초안")
                draft_chars = TextAnalyzer.count_korean_chars(project.draft)
                st.metric("글자 수", f"{draft_chars:,}자")
                st.text_area("", project.draft, height=300, disabled=True)
            
            with col2:
                st.subheader("보정본")
                refined_chars = TextAnalyzer.count_korean_chars(project.refined)
                char_diff = refined_chars - draft_chars
                st.metric("글자 수", f"{refined_chars:,}자", f"{char_diff:+}자")
                st.text_area("", project.refined, height=300, disabled=True)
        else:
            st.info("비교할 텍스트가 없습니다.")

def render_analysis(show_analysis):
    """분석 결과 렌더링"""
    if not show_analysis:
        return
    
    project = st.session_state.project
    text_to_analyze = project.refined or project.draft
    
    if not text_to_analyze:
        return
    
    st.subheader("📊 4) 상세 분석")
    
    # 키워드 커버리지
    if project.coverage and project.keywords:
        st.subheader("🎯 키워드 커버리지")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("완전 매칭", f"{project.coverage['coverage']:.1f}%")
        with col2:
            st.metric("부분 매칭", f"{project.coverage['partial_coverage']:.1f}%")
        with col3:
            st.metric("종합 점수", f"{project.coverage['total_coverage']:.1f}%")
        
        # 키워드 상세
        if project.coverage['covered']:
            st.success("✅ 포함된 키워드: " + ", ".join(project.coverage['covered']))
        
        if project.coverage['partial_matches']:
            st.warning("🔶 부분 매칭: " + ", ".join(project.coverage['partial_matches']))
        
        if project.coverage['missing']:
            st.error("❌ 누락된 키워드: " + ", ".join(project.coverage['missing']))
    
    # 가독성 분석
    st.subheader("📖 가독성 분석")
    readability = TextAnalyzer.analyze_readability(text_to_analyze)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("평균 문장 길이", f"{readability['avg_sentence_length']:.1f}자")
    with col2:
        st.metric("긴 문장 수", f"{readability['long_sentences']}개")
    with col3:
        st.metric("총 문장 수", f"{readability['total_sentences']}개")
    with col4:
        st.metric("가독성 점수", f"{readability['readability_score']:.1f}")
    
    # 클리셰 분석
    st.subheader("🎭 클리셰 분석")
    cliche_analysis = TextAnalyzer.detect_cliche_advanced(text_to_analyze)
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("클리셰 밀도", f"{cliche_analysis['cliche_density']:.2f}")
        st.caption("1000자당 클리셰 개수")
    with col2:
        st.metric("총 클리셰 수", f"{cliche_analysis['total_cliche_count']}개")
    
    # 클리셰 상세
    for category, items in cliche_analysis['categories'].items():
        if items:
            st.warning(f"**{category}**: {', '.join(items)}")

def render_export():
    """내보내기 기능"""
    st.subheader("💾 5) 내보내기")
    
    project = st.session_state.project
    export_text = project.refined or project.draft
    
    if not export_text:
        st.info("내보낼 텍스트가 없습니다.")
        return
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Markdown 다운로드
        md_content = f"""# 자기소개서

**지원 직무**: {project.job_title}
**작성일**: {datetime.fromtimestamp(project.timestamp).strftime('%Y-%m-%d %H:%M:%S') if project.timestamp else ''}

{export_text}

---
*AI 자기소개서 작성기로 생성됨*
"""
        st.download_button(
            "📄 Markdown 다운로드", 
            data=md_content.encode("utf-8"), 
            file_name=f"cover_letter_{int(time.time())}.md", 
            mime="text/markdown",
            use_container_width=True
        )
    
    with col2:
        # JSON 프로젝트 파일
        project_data = {
            "job_title": project.job_title,
            "jd_text": project.jd_text,
            "resume_text": project.resume_text,
            "questions": project.questions,
            "draft": project.draft,
            "refined": project.refined,
            "keywords": project.keywords,
            "coverage": project.coverage,
            "model": project.model,
            "temperature": project.temperature,
            "target_len": project.target_len,
            "tone": project.tone,
            "timestamp": project.timestamp,
            "version": "2.0"
        }
        
        st.download_button(
            "💾 프로젝트 저장", 
            data=json.dumps(project_data, ensure_ascii=False, indent=2),
            file_name=f"cover_letter_project_{int(time.time())}.json", 
            mime="application/json",
            use_container_width=True
        )
    
    with col3:
        # 텍스트 파일
        st.download_button(
            "📝 텍스트 다운로드", 
            data=export_text.encode("utf-8"), 
            file_name=f"cover_letter_{int(time.time())}.txt", 
            mime="text/plain",
            use_container_width=True
        )

def main():
    """메인 함수"""
    # 페이지 설정
    st.set_page_config(
        page_title="✍️ AI 자기소개서 작성기 Pro", 
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # 헤더
    st.title("✍️ AI 자기소개서 작성기 Pro")
    st.caption("📝 입력 → 🚀 초안 생성 → ✨ 길이/톤 보정 → 🔍 키워드 분석 → 📊 품질 평가 → 💾 내보내기")
    
    # 세션 상태 초기화
    initialize_session_state()
    
    # 사이드바 설정
    show_analysis, auto_save = setup_sidebar()
    
    # 메인 컨텐츠
    if render_input_form():
        # 생성 버튼
        generate_draft, refine_text, generate_all, analyze_keywords = render_generation_buttons()
        
        # 생성 프로세스
        process_generation(generate_draft, refine_text, generate_all, analyze_keywords)
        
        # 결과 표시
        render_results()
        
        # 분석 결과
        render_analysis(show_analysis)
        
        # 내보내기
        render_export()
    
    # 푸터
    st.markdown("---")
    st.caption("💡 **팁**: 구체적인 수치와 성과를 포함하면 더 좋은 자기소개서가 완성됩니다!")

if __name__ == "__main__":
    main()