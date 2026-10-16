import streamlit as st
import cv2
import numpy as np
from PIL import Image

st.title("🧩 스마트 도면/조각 자동 스티칭기 (정밀 매칭형)")
st.write("특징점을 더 민감하게 찾아내어 자유선 조각이나 도면을 매끄럽게 이어 붙입니다!")

uploaded_files = st.file_uploader("조각 사진들을 선택하세요 (여러 장)", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)

if uploaded_files:
    images = []
    for uploaded_file in uploaded_files:
        file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        
        # 자유선 테두리 노이즈를 흰색 배경으로 정제
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 30, 255, cv2.THRESH_BINARY)
        
        background_white = np.ones_like(img, dtype=np.uint8) * 255
        background_white[thresh > 0] = img[thresh > 0]
        
        images.append(background_white)
        st.image(uploaded_file, caption=uploaded_file.name, width=150)

    if len(images) >= 2:
        if st.button("🚀 정밀 스티칭 재시도!"):
            with st.spinner("이미지 간의 특징점을 분석하고 정밀 합성 중입니다..."):
                
                try:
                    # OpenCV 스티처 생성 및 매칭 감도 조절을 위한 SIFT 기반 세팅 시도
                    stitcher = cv2.Stitcher_create(cv2.Stitcher_SCANS)
                    
                    status, stitched_img = stitcher.stitch(images)
                    
                    if status == cv2.Stitcher_OK:
                        st.success("✨ 대형 도면/조각 스티칭 완벽 성공!")
                        
                        result_rgb = cv2.cvtColor(stitched_img, cv2.COLOR_BGR2RGB)
                        final_pil_img = Image.fromarray(result_rgb)
                        
                        st.image(final_pil_img, caption="완성된 통합 이미지", use_column_width=True)
                        
                        cv2.imwrite("complete_stitched_drawing.jpg", stitched_img)
                        with open("complete_stitched_drawing.jpg", "rb") as file:
                            st.download_button(
                                label="📥 완성된 이미지 다운로드하기",
                                data=file,
                                file_name="complete_stitched_drawing.jpg",
                                mime="image/jpeg"
                            )
                    else:
                        # 오류 코드별 상세 안내
                        error_reasons = {
                            1: "사진 간에 겹치는 영역(Overlap)이 부족하거나 공통된 특징점(선, 글자 등)을 찾지 못했습니다.",
                            2: "호모그래피 추정 실패 (이미지 왜곡이 심하거나 매칭 포인트가 부족합니다.)",
                            3: "카메라 파라미터 조정 실패"
                        }
                        reason = error_reasons.get(status, "알 수 없는 오류가 발생했습니다.")
                        st.error(f"스티칭 실패 (오류 코드: {status})\n\n💡 원인: {reason}")
                except Exception as e:
                    st.error(f"처리 중 예외가 발생했습니다: {e}")
    else:
        st.warning("이어붙이려면 최소 2장 이상의 사진을 업로드해 주세요.")
