import streamlit as st
import cv2
import numpy as np
from PIL import Image

st.title("🧩 2차원 스마트 도면/조각 자동 스티칭기 (바둑판식)")
st.write("상하좌우로 나뉜 조각 사진들을 업로드하면 2차원으로 자동 조합하여 완성해 줍니다!")

uploaded_files = st.file_uploader("조각 사진들을 선택하세요 (4장 이상)", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)

if uploaded_files:
    images = []
    for uploaded_file in uploaded_files:
        file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        
        # 테두리 노이즈 정제 (흰색 배경 처리)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 30, 255, cv2.THRESH_BINARY)
        background_white = np.ones_like(img, dtype=np.uint8) * 255
        background_white[thresh > 0] = img[thresh > 0]
        
        images.append(background_white)
        st.image(uploaded_file, caption=uploaded_file.name, width=150)

    if len(images) >= 2:
        if st.button("🚀 2차원 정밀 스티칭 실행!"):
            with st.spinner("상하좌우 조각들을 분석하여 퍼즐 맞추듯 조립 중입니다..."):
                
                try:
                    # OpenCV 스티처 생성 (SCANS 모드는 파노라마뿐만 아니라 다방면 오버랩도 처리)
                    stitcher = cv2.Stitcher_create(cv2.Stitcher_SCANS)
                    status, stitched_img = stitcher.stitch(images)
                    
                    if status == cv2.Stitcher_OK:
                        st.success("✨ 2차원 조각 합성 완벽 성공!")
                        
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
                        st.error(f"스티칭 실패 (오류 코드: {status}). 조각들 간에 상하 또는 좌우로 겹치는 영역(Overlap)이 충분한지 확인해 주세요.")
                except Exception as e:
                    st.error(f"처리 중 오류 발생: {e}")
    else:
        st.warning("이어붙이려면 최소 2장 이상의 사진을 업로드해 주세요.")
