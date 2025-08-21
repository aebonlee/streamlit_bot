import os
import streamlit as st
import openai
from duckduckgo_search import DDGS  # pip install duckduckgo-search
import json # Not strictly needed for this version, but useful for structured data handling

# ==================== 설정 방법 ====================
# 1) 환경변수 사용 시:
#    터미널에서:
#      export OPENAI_API_KEY="YOUR_OPENAI_API_KEY"  # Windows: set OPENAI_API_KEY="YOUR_OPENAI_API_KEY"
#    아래 주석 해제:
# openai.api_key = os.getenv("OPENAI_API_KEY")

# 2) 직접 키값 입력 시 (VS Code에서 사용):
# 실제 API 키로 변경하세요. 보안을 위해 환경변수 사용을 권장합니다.
openai.api_key = "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" # YOUR_OPENAI_API_KEY 대신 실제 키를 입력하세요.
# ===================================================

st.set_page_config(page_title="AI 자기소개서 + 이력서 통합 생성 및 평판 조회기", layout="centered")
st.title("✍️ AI 기반 자기소개서 & 이력서 통합 생성기")
st.write("이력서 상세 정보를 입력하면 이력서와 자기소개서를 생성하고, 인터넷 평판과 출처를 자동으로 조회해 보여줍니다.")

# --- 이력서 정보 입력 폼 ---
st.header("📄 이력서 정보 입력")
with st.form(key="detailed_resume_form"):
    st.subheader("개인 정보")
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("이름", key="name_input", help="예: 홍길동")
    with col2:
        cellphone = st.text_input("전화번호", help="예: 010-1234-5678", key="phone_input")
    email = st.text_input("이메일", help="예: example@email.com", key="email_input")
    address = st.text_input("주소 (선택 사항)", key="address_input", help="예: 서울특별시 강남구")

    st.subheader("학력")
    st.info("학교명, 전공, 학점 (선택), 재학/졸업 기간을 상세하게 입력해주세요. (예: 2015.03 - 2019.02, OO대학교, 컴퓨터공학 학사, 3.8/4.5)")
    education = st.text_area("학력", height=100, key="education_input")

    st.subheader("경력")
    st.info("회사명, 직책, 재직 기간, 그리고 **주요 업무와 성과를 구체적인 수치로** 작성해주세요. (예: 2020.03 - 2023.08, ABC 주식회사, 소프트웨어 엔지니어, 웹 서비스 성능 20% 개선)")
    experience = st.text_area("경력", height=150, key="experience_input")

    st.subheader("기술 및 역량")
    st.info("프로그래밍 언어, 개발 도구, 프레임워크, 라이브러리, 자격증 등을 작성해주세요. (예: Python, Java, React, Docker, AWS, 정보처리기사)")
    skills = st.text_area("기술 및 역량", height=100, key="skills_input")

    with st.expander("💼 선택 사항: 추가 이력서 정보"):
        st.subheader("자격증 (선택 사항)")
        certification = st.text_area("보유 자격증 (취득 기관, 취득일 포함)", key="certification_input", help="예: 정보처리기사 (한국산업인력공단, 2020.05)")

        st.subheader("어학 능력 (선택 사항)")
        language = st.text_area("어학 시험 점수 또는 숙련도 (예: 토익 900점, 영어 상)", key="language_input")

        st.subheader("수상 경력 (선택 사항)")
        awards = st.text_area("수상 내역 (수상 기관, 수상일 포함)", key="awards_input", help="예: 2022년 교내 코딩 경진대회 최우수상 (OO대학교)")

        st.subheader("대외 활동 (선택 사항)")
        activities = st.text_area("참여했던 대외 활동 (활동 기간, 역할, 주요 내용)", key="activities_input", help="예: 2018.03 - 2018.12, OO봉사단, 팀원, 지역 아동센터 교육 봉사")

        st.subheader("포트폴리오 (선택 사항)")
        portfolio_link = st.text_input("포트폴리오 링크", help="온라인 포트폴리오가 있다면 URL을 입력해주세요.", key="portfolio_input")

    submitted = st.form_submit_button("이력서 및 자기소개서 생성 & 평판 조회")

# 인터넷 평판 조회 함수
def fetch_reputation(name: str, max_results: int = 5):
    """DuckDuckGo Search를 사용하여 특정 이름의 평판을 조회합니다."""
    if not name:
        return []
    # 평판 조회 쿼리 강화: 긍정적/부정적 키워드 포함
    query = f'"{name}" 평판 후기 OR 리뷰 OR "문제" OR "논란" OR "성과" OR "논문"'
    reputations = []
    try:
        with DDGS() as ddgs:
            # timelimit을 사용하면 너무 최근 결과만 나올 수 있어, 없애거나 필요에 따라 조정
            results = ddgs.text(query, region='wt-wt', safesearch='Off', max_results=max_results)
            for i, r in enumerate(results):
                if i >= max_results:
                    break
                snippet = r.get('body', '')
                url = r.get('href', '')
                reputations.append({'snippet': snippet, 'url': url})
        return reputations
    except Exception as e:
        st.error(f"평판 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요. 오류: {e}")
        return []

# 이력서 텍스트 생성 함수 (GPT를 사용하지 않고 직접 포맷팅)
def generate_resume_text(data):
    """입력된 이력서 데이터를 Markdown 형식의 텍스트로 변환합니다."""
    resume_parts = []

    resume_parts.append("## 📄 이 력 서\n")
    resume_parts.append("### 👤 개인 정보\n")
    resume_parts.append(f"- **이름**: {data['name']}")
    resume_parts.append(f"- **전화번호**: {data['cellphone']}")
    resume_parts.append(f"- **이메일**: {data['email']}")
    if data['address']:
        resume_parts.append(f"- **주소**: {data['address']}")
    resume_parts.append("\n")

    if data['education']:
        resume_parts.append("### 🎓 학력\n")
        # 학력은 사용자가 입력한 그대로 표시
        resume_parts.append(data['education'] + "\n")
        resume_parts.append("\n")

    if data['experience']:
        resume_parts.append("### 🏢 경력\n")
        # 경력은 사용자가 입력한 그대로 표시
        resume_parts.append(data['experience'] + "\n")
        resume_parts.append("\n")

    if data['skills']:
        resume_parts.append("### 💡 기술 및 역량\n")
        # 기술 및 역량은 사용자가 입력한 그대로 표시
        resume_parts.append(data['skills'] + "\n")
        resume_parts.append("\n")

    if data['certification']:
        resume_parts.append("### 📜 자격증\n")
        resume_parts.append(data['certification'] + "\n")
        resume_parts.append("\n")

    if data['language']:
        resume_parts.append("### 🗣️ 어학 능력\n")
        resume_parts.append(data['language'] + "\n")
        resume_parts.append("\n")

    if data['awards']:
        resume_parts.append("### 🏆 수상 경력\n")
        resume_parts.append(data['awards'] + "\n")
        resume_parts.append("\n")

    if data['activities']:
        resume_parts.append("### 🌍 대외 활동\n")
        resume_parts.append(data['activities'] + "\n")
        resume_parts.append("\n")

    if data['portfolio_link']:
        resume_parts.append("### 🔗 포트폴리오\n")
        resume_parts.append(f"- [포트폴리오 링크]({data['portfolio_link']})\n")
        resume_parts.append("\n")

    return "\n".join(resume_parts)


if submitted:
    # OpenAI API 키 유효성 검사
    if not openai.api_key or openai.api_key == "YOUR_OPENAI_API_KEY" or openai.api_key == "":
        st.error("OpenAI API 키가 설정되지 않았습니다. 환경변수나 소스코드에 API 키를 설정해주세요.")
    else:
        # 이력서 정보를 딕셔너리로 저장
        resume_data = {
            "name": name,
            "cellphone": cellphone,
            "email": email,
            "address": address,
            "education": education,
            "experience": experience,
            "skills": skills,
            "certification": certification,
            "language": language,
            "awards": awards,
            "activities": activities,
            "portfolio_link": portfolio_link
        }

        # 1. 이력서 텍스트 생성 (GPT 미사용)
        generated_resume_text = generate_resume_text(resume_data)
        st.subheader("📄 생성된 이력서")
        # Markdown으로 렌더링하여 깔끔하게 표시
        st.markdown(generated_resume_text) 

        # 2. 자기소개서 생성 프롬프트
        # 이력서 전체 정보를 포함하여 자기소개서 생성 요청
        prompt_for_cover_letter = (
            f"다음 이력서 정보를 바탕으로 한국어로 자기소개서를 작성해줘. "
            f"자기소개서는 3~4문단으로 구성하고, 지원 동기와 강점(특히 경력과 기술/역량에 기반한)을 부각시켜 작성해줘. "
            f"또한, {name}님의 개인적인 성장 경험과 지원하는 회사(가상의 회사라고 가정해도 됨)에 기여할 수 있는 역량을 연결하여 작성해줘.\n\n"
            f"--- 이력서 정보 ---\n"
            f"{generated_resume_text}\n" # 생성된 이력서 텍스트를 프롬프트에 포함
            f"-------------------\n"
            f"자기소개서 시작:"
        )

        with st.spinner("자기소개서를 생성 중입니다..."):
            try:
                response = openai.chat.completions.create(
                    model="gpt-4o-mini", # 더 강력한 모델 사용 (필요에 따라 gpt-3.5-turbo 또는 gpt-4 사용)
                    messages=[
                        {"role": "system", "content": "친절하고 전문적인 이력서 및 자기소개서 작성 도우미입니다. 사용자에게 최적화된 문서를 생성합니다."},
                        {"role": "user", "content": prompt_for_cover_letter},
                    ],
                    temperature=0.7,
                    max_tokens=1200, # 자기소개서가 길어질 수 있으므로 토큰 증가
                )
                cover_letter = response.choices[0].message.content.strip()
                st.subheader("📝 생성된 자기소개서")
                st.write(cover_letter)
            except openai.APIError as e:
                st.error(f"OpenAI API 호출 중 오류가 발생했습니다: {e.status_code} - {e.response.text}")
                st.warning("API 키가 유효한지, 또는 사용량 한도를 초과하지 않았는지 확인해주세요.")
            except Exception as e:
                st.error(f"자기소개서 생성 중 예측하지 못한 오류가 발생했습니다: {e}")

        # 3. 인터넷 평판 조회 및 출력
        if name: # 이름이 입력되었을 때만 평판 조회
            reputations = fetch_reputation(name)
            st.subheader(f"🌐 인터넷 평판 조회 결과 ({len(reputations)}건)")
            if reputations:
                for idx, rep in enumerate(reputations, 1):
                    snippet = rep.get('snippet', '')
                    url = rep.get('url', '')
                    if url:
                        st.markdown(f"**{idx}.** {snippet} [출처]({url})")
                    else:
                        st.markdown(f"**{idx}.** {snippet}")
            else:
                st.write("관련 평판 정보를 찾을 수 없습니다. (이름이 불분명하거나 공개된 정보가 적을 수 있습니다)")
        else:
            st.info("평판 조회를 위해 이름을 입력해주세요.")

        st.success("이력서, 자기소개서 생성 및 평판 조회가 완료되었습니다.")
        st.balloons()
