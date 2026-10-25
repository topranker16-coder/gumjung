import io
import os
from google import genai
from google.genai import types
import pdf2image
from PIL import Image
import streamlit as st

st.set_page_config(
    page_title="PDF ➡️ LaTeX 수학 시험지 변환기", page_icon="📐", layout="wide"
)

st.title("📐 PDF ➡️ LaTeX 수학 시험지 추출기")
st.write(
    "PDF 시험지에서 폰트 깨짐(네모 박스 □□□) 없이 완벽한 한글과 LaTeX 수식을"
    " 추출합니다."
)

# 사이드바: Gemini API 키 입력
st.sidebar.header("🔑 API 설정")
api_key = st.sidebar.text_input(
    "Gemini API Key를 입력하세요:",
    type="password",
    help="Google AI Studio에서 발급받은 API 키를 입력해 주세요.",
)

if not api_key:
  if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
  else:
    st.info("👈 사이드바에 Gemini API Key를 입력하거나 secrets를 설정해 주세요.")

uploaded_file = st.file_uploader("수학 시험지 PDF 파일을 업로드하세요", type=["pdf"])

if uploaded_file and api_key:
  # Client 생성
  client = genai.Client(api_key=api_key)

  with st.spinner("PDF 페이지를 이미지로 변환 중입니다..."):
    try:
      pdf_bytes = uploaded_file.read()
      images = pdf2image.convert_from_bytes(pdf_bytes, dpi=200)
      st.success(f"총 {len(images)}페이지를 성공적으로 불러왔습니다.")
    except Exception as e:
      st.error(
          f"PDF 변환 오류: {e}\n(poppler-utils 가 설치되어 있는지 확인해"
          " 주세요.)"
      )
      images = []

  if images:
    selected_pages = st.multiselect(
        "변환할 페이지를 선택하세요:",
        options=list(range(1, len(images) + 1)),
        default=list(range(1, len(images) + 1)),
    )

    if st.button("🚀 선택한 페이지 LaTeX 추출 시작", type="primary"):
      full_result = []

      progress_bar = st.progress(0)
      for idx, page_num in enumerate(selected_pages):
        st.write(f"⏳ {page_num}페이지 분석 중...")
        img = images[page_num - 1]

        # 영문 프롬프트와 명확한 지침을 사용하여 인코딩 충돌 원천 차단
        prompt = (
            "You are an expert Korean high school math exam LaTeX converter. "
            "Extract all text, math formulas, question numbers, sub-items "
            "(ㄱ, ㄴ, ㄷ), and options (①, ②, ③, ④, ⑤) from this exam page image accurately. "
            "Rules:\n"
            "1. Keep all original Korean text intact.\n"
            "2. Wrap inline math in $...$ and block math in $$...$$ without errors.\n"
            "3. Format question boxes or condition blocks using markdown blockquotes (>).\n"
            "4. Output ONLY the clean markdown and LaTeX source code without extra conversation.\n"
            "5. Ensure backslashes like \\frac, \\theta, \\sum are correctly written."
        )

        try:
          response = client.models.generate_content(
              model="gemini-3.8-flash", contents=[img, prompt]
          )
          extracted_text = response.text
          full_result.append(f"<!-- 페이지 {page_num} -->\n" + extracted_text)
        except Exception as e:
          st.error(f"{page_num}페이지 처리 중 오류 발생: {e}")

        progress_bar.progress((idx + 1) / len(selected_pages))

      final_output = "\n\n---\n\n".join(full_result)

      st.success("🎉 추출이 완료되었습니다!")
      st.text_area(
          "📄 추출된 LaTeX / Markdown 소스:",
          value=final_output,
          height=400,
      )

      st.download_button(
          label="📥 .md 파일로 다운로드",
          data=final_output,
          file_name="extracted_math_paper.md",
          mime="text/markdown",
      )
