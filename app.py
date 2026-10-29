import streamlit as st
import json
import time
from google import genai
from google.genai import types

# Streamlit 페이지 기본 설정
st.set_page_config(page_title="초순수 문제 자동 검증기", page_icon="💧", layout="wide")

st.title("💧 초순수(Ultrapure) 기출변형 자동 검증 파이프라인")
st.caption("파일을 업로드하거나 텍스트를 입력하면, 백그라운드에서 악랄한 이의제기 공격을 거쳐 무결점 문제만 추출합니다.")

# 1. API 키 설정 (스트림릿 시크릿 또는 사이드바 입력)
api_key = st.sidebar.text_input("Gemini API Key", type="password")
if not api_key:
    st.info("👈 왼쪽 사이드바에 Gemini API Key를 입력해주세요.")
    st.stop()

client = genai.Client(api_key=api_key)

# ---------------------------------------------------------
# Prompt Templates (역할 분담 에이전트)
# ---------------------------------------------------------

GENERATOR_PROMPT = """
당신은 한국 수능 및 평가원 최고 수준의 출제위원입니다.
아래 제공된 [기출 원본 / 지문 / 개념]을 바탕으로, 평가원 스타일의 완벽한 문항 1개를 작성하세요.

[지시사항]
- 발문, 지문/제시문, 보기(①~⑤), 정답, 그리고 상세 해설을 포함하세요.
- 마크다운(Markdown) 포맷으로 출력하세요.

[제공 소스]:
{source_text}
"""

ATTACKER_PROMPT = """
당신은 수능 시험 직후 '이의제기'를 신청하려는 가장 깐깐하고 악랄한 최상위권 수험생이자 학원 강사입니다.
제시된 [초안 문제]를 샅샅이 뜯어보고 다음 항목을 철저히 공격하세요.

[검증 항목]
1. 복수정답 가능성: 정답 이외의 오답 선지 중 정답이 될 여지가 단 1%라도 있는가?
2. 논리적 비약/오류: 지문/제시문과 정답 간의 논리적 모순이나 단어 해석의 왜곡이 있는가?
3. 수학/표분석 수치 오류: 조건과 해 사이의 수치적 모순이나 계산 오류가 있는가?
4. 평가원 학자 입장 왜곡 (사탐): 생윤/사문 학자의 어조나 특정 조건(~만, 모두 등)이 오개념을 유발하는가?

[초안 문제]:
{problem_draft}

지적할 오류나 허점이 있다면 명확히 짚어내고, 이상이 전혀 없다면 "오류 없음"이라고 단호하게 말하세요.
"""

JUDGE_PROMPT = """
당신은 수능 출제위원장입니다.
[이의제기 공격 내용]을 검토하여 이 문제가 진짜로 '불순물(오류/복수정답 여지)'이 섞인 불량 문제인지 판정하세요.

[이의제기 공격 내용]:
{attack_report}

[응답 형식 (반드시 JSON 형식으로 응답할 것)]:
{{
  "is_clean": true 또는 false,
  "reason": "PASS 사유 또는 REJECT 사유 요약"
}}
is_clean이 true인 경우는 단 0.001%의 허점도 없이 완전히 깨끗할 때만 해당합니다.
"""

# ---------------------------------------------------------
# Core API Functions
# ---------------------------------------------------------

def generate_problem(source_text: str) -> str:
    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=GENERATOR_PROMPT.format(source_text=source_text)
    )
    return response.text

def attack_problem(problem_draft: str) -> str:
    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=ATTACKER_PROMPT.format(problem_draft=problem_draft)
    )
    return response.text

def judge_problem(attack_report: str) -> dict:
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=JUDGE_PROMPT.format(attack_report=attack_report),
        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        )
    )
    return json.loads(response.text)

# ---------------------------------------------------------
# UI Layout & User Input
# ---------------------------------------------------------

col1, col2 = st.columns([1, 1])

with col1:
    subject = st.selectbox("과목 선택", ["ENGLISH", "MATH", "SOCIOLOGY", "ETHICS"])
    loop_count = st.slider("검증 크로스체크 횟수 (N회 반복)", min_value=1, max_value=5, value=3)
    
    # [추가된 파일 업로더 기능]
    uploaded_file = st.file_uploader("📁 기출 원본 파일 업로드 (.txt 또는 .md)", type=["txt", "md"])
    
    source_input_text = ""
    if uploaded_file is not None:
        # 업로드된 파일 내용을 텍스트로 읽어옴
        source_input_text = uploaded_file.getvalue().decode("utf-8")
        st.success(f"파일 업로드 완료: {uploaded_file.name}")
        with st.expander("업로드된 원본 내용 미리보기"):
            st.text(source_input_text[:500] + ("..." if len(source_input_text) > 500 else ""))
    
    # 직접 입력도 병행 가능
    source_input = st.text_area("또는 기출 원본 지문 / 문제 조건 / 개념 직접 입력", value=source_input_text, height=200)
    
    run_btn = st.button("🚀 초순수 문제 생성 및 자동 검증 시작", use_container_width=True)

with col2:
    st.subheader("📋 실시간 검증 로그 & 결과")
    status_area = st.empty()
    result_area = st.empty()

if run_btn:
    if not source_input.strip():
        st.warning("파일을 업로드하거나 원수(기출 소스) 데이터를 입력해 주세요.")
        st.stop()
        
    status_area.info("1단계: 문제 초안을 생성하는 중입니다...")
    try:
        draft = generate_problem(source_input)
        
        is_passed = True
        for i in range(1, loop_count + 1):
            status_area.info(f"2단계-{i}회차 Filter: 악랄한 이의제기 공격 및 판정 중...")
            
            attack = attack_problem(draft)
            judgment = judge_problem(attack)
            
            if not judgment.get("is_clean", False):
                is_passed = False
                status_area.error(f"❌ [{i}회차 검증 실패] 불순물(오류) 발견으로 자진 폐기되었습니다.\n사유: {judgment.get('reason')}")
                break
            time.sleep(0.5)
            
        if is_passed:
            status_area.success(f"✨ [{loop_count}회 연속 검증 통과] 순도 100% 초순수 문제 완성!")
            result_area.markdown(draft)
            
            st.download_button(
                label="📥 검증된 마크다운(.md) 파일 다운로드",
                data=draft,
                file_name=f"{subject}_clean_problem.md",
                mime="text/markdown"
            )
    except Exception as e:
        status_area.error(f"실행 중 오류가 발생했습니다: {e}")
