import streamlit as st
import cv2
import numpy as np
import os
from PIL import Image

st.title("🧩 스마트 도면/조각 자동 스티칭기 (고급형)")
st.write("자유선으로 자른 조각이나 검은 테두리가 있는 사진도 알아서 테두리를 정리하고 깔끔하게 이어 붙여줍니다!")

uploaded_files = st.file_uploader("도면 및 조각 사진들을 선택하세요 (여러 장 선택 가능)", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)

if uploaded_files:
    st.write(f"총 {len(uploaded_files)}개의 파일이 업로드되었습니다.")
    
    images = []
    for uploaded_file in uploaded_files:
        file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        
        # [핵심 전처리] 자유선 자르기로 생긴 주변의 검은 테두리(배경)를 흰색/투명으로 깔끔하게 마스킹 처리
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 10, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            # 가장 큰 영역(실제 도면/그림 본체)만 남기고 주변 검은 여백을 잘라내기
            c = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(c)
            img_cropped = img[y:y+h, x:x+w]
            images.append(img_cropped)
        else:
            images.append(img)
            
        st.image(uploaded_file, caption=uploaded_file.name, width=200)

    if len(images) >= 2:
        if st.button("🚀 고급 자동 스티칭 실행!"):
            with st.spinner("테두리를 다듬고 정밀하게 이어 붙이는 중입니다..."):
                
                # OpenCV 도면 전용 스티처 실행
                stitcher = cv2.Stitcher_create(cv2.Stitcher_SCANS)
                status, stitched_img = stitcher.stitch(images)
                
                if status == cv2.Stitcher_OK:
                    st.success("✨ 대형 도면 스티칭 완벽 성공!")
                    
                    result_rgb = cv2.cvtColor(stitched_img, cv2.COLOR_BGR2RGB)
                    final_pil_img = Image.fromarray(result_rgb)
                    
                    st.image(final_pil_img, caption="완성된 통합 도면", use_column_width=True)
                    
                    cv2.imwrite("complete_stitched_drawing.jpg", stitched_img)
                    with open("complete_stitched_drawing.jpg", "rb") as file:
                        st.download_button(
                            label="📥 완성된 도면 다운로드하기",
                            data=file,
                            file_name="complete_stitched_drawing.jpg",
                            mime="image/jpeg"
                        )
                else:
                    st.error(f"스티칭 실패 (오류 코드: {status}). 사진 간에 겹치는 영역이 충분한지 확인해 주세요.")
    else:
        st.warning("이어붙이려면 최소 2장 이상의 사진을 업로드해 주세요.")
