import streamlit as st
import cv2
import numpy as np
from PIL import Image

st.title("🧩 스마트 도면/조각 자동 스티칭기 (테두리 정제형)")
st.write("자유선으로 자른 조각의 검은 테두리 노이즈를 백색으로 정제하여 왜곡 없이 이어 붙입니다!")

uploaded_files = st.file_uploader("조각 사진들을 선택하세요 (여러 장)", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)

if uploaded_files:
    images = []
    for uploaded_file in uploaded_files:
        file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        
        # [핵심 전처리] 자유선 테두리의 검은색 여백을 흰색으로 깔끔하게 채우기
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 30, 255, cv2.THRESH_BINARY)
        
        # 검은 배경은 흰색으로 바꾸고 알맹이만 남김
        background_white = np.ones_like(img, dtype=np.uint8) * 255
        background_white[thresh > 0] = img[thresh > 0]
        
        images.append(background_white)
        st.image(uploaded_file, caption=uploaded_file.name, width=150)

    if len(images) >= 2:
        if st.button("🚀 테두리 정제 스티칭 실행!"):
            with st.spinner("조각들의 경계면을 정제하고 정밀 합성 중입니다..."):
                
                # OpenCV 도면 전용 스티처 실행
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
                    st.error(f"스티칭 실패 (오류 코드: {status}). 조각 간에 겹치는 영역이 충분한지 확인해 주세요.")
    else:
        st.warning("이어붙이려면 최소 2장 이상의 사진을 업로드해 주세요.")
