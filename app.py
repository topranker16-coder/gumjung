import io
import os
import time
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

        # 이미지를 바이트로 안전하게 변환
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_bytes = img_byte_arr.getvalue()

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

        # 503 과부하 대비 최대 3번까지 자동 재시도 로직 적용
        success = False
        extracted_text = ""
        for attempt in range(3):
          try:
            response = client.models.generate_content(
                model="gemini-2.5-flash", 
                contents=[
                    types.Part.from_bytes(
                        data=img_bytes,
                        mime_type='image/png',
                    ),
                    prompt
                ]
            )
            extracted_text = response.text
            success = True
            break
          except Exception as e:
            if attempt < 2:
              time.sleep(2 * (attempt + 1)) # 2초, 4초 대기 후 재시도
            else:
              st.error(f"{page_num}페이지 처리 중 오류 발생: {e}")

        if success:
          full_result.append(f"<!-- 페이지 {page_num} -->\n" + extracted_text)

        progress_bar.progress((idx + 1) / len(selected_pages))

      if full_result:
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
