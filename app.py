import streamlit as st
import cv2
import numpy as np
import os
from PIL import Image

st.title("🧩 스마트 도면/사진 자동 이어붙이기 (Stitcher)")
st.write("여러 장의 분할 사진을 업로드하면, 찌그러짐 없이 나란히 이어 붙여줍니다!")

# 파일 업로드 기능 (여러 장 선택 가능)
uploaded_files = st.file_uploader("도면 사진들을 선택하세요 (여러 장 선택 가능)", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)

if uploaded_files:
    st.write(f"총 {len(uploaded_files)}개의 파일이 업로드되었습니다.")
    
    images = []
    for uploaded_file in uploaded_files:
        # 업로드된 파일을 OpenCV 이미지 형식으로 변환
        file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        images.append(img)
        
        # 화면에 업로드된 사진 미리보기 표시
        st.image(uploaded_file, caption=uploaded_file.name, width=300)

    if len(images) >= 2:
        if st.button("🚀 도면 이어붙이기 실행!"):
            with st.spinner("이미지를 나란히 이어 붙이는 중입니다..."):
                # 기준 이미지 높이 맞추기 후 가로로 결합
                h_base, w_base = images[0].shape[:2]
                resized_images = []
                for img in images:
                    h, w = img.shape[:2]
                    if h != h_base:
                        new_w = int(w * (h_base / h))
                        img = cv2.resize(img, (new_w, h_base))
                    resized_images.append(img)
                
                result_img = np.hstack(resized_images)
                
                # OpenCV 형식을 스트림릿이 보여줄 수 있는 RGB 이미지로 변환
                result_rgb = cv2.cvtColor(result_img, cv2.COLOR_BGR2RGB)
                final_pil_img = Image.fromarray(result_rgb)
                
                st.success("✨ 이어붙이기 완료!")
                st.image(final_pil_img, caption="완성된 대형 도면", use_column_width=True)
                
                # 다운로드 버튼 제공
                # 임시 저장 후 다운로드 링크 생성
                cv2.imwrite("complete_drawing.jpg", result_img)
                with open("complete_drawing.jpg", "rb") as file:
                    st.download_button(
                        label="📥 완성된 도면 다운로드하기",
                        data=file,
                        file_name="complete_drawing.jpg",
                        mime="image/jpeg"
                    )
    else:
        st.warning("이어붙이려면 최소 2장 이상의 사진을 업로드해 주세요.")