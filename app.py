import streamlit as st
import cv2
import numpy as np
import os
from PIL import Image

st.title("🧩 스마트 도면 자동 스티칭 & 병합기")
st.write("현장에서 여러 장으로 나눠 찍은 도면 사진을 올리면, 겹치는 부분을 자동 분석하여 하나의 완벽한 대형 도면으로 합쳐줍니다!")

uploaded_files = st.file_uploader("도면 사진들을 선택하세요 (여러 장 선택 가능)", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)

if uploaded_files:
    st.write(f"총 {len(uploaded_files)}개의 파일이 업로드되었습니다.")
    
    images = []
    for uploaded_file in uploaded_files:
        file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        images.append(img)
        st.image(uploaded_file, caption=uploaded_file.name, width=200)

    if len(images) >= 2:
        if st.button("🚀 정밀 자동 스티칭 실행!"):
            with st.spinner("AI가 겹치는 영역을 분석하고 하나의 대형 도면으로 합성 중입니다... (사진 장수에 따라 잠시 꿀렁거릴 수 있습니다)"):
                
                # OpenCV 도면/문서 최적화 자동 스티처 생성
                stitcher = cv2.Stitcher_create(cv2.Stitcher_SCANS)
                status, stitched_img = stitcher.stitch(images)
                
                if status == cv2.Stitcher_OK:
                    st.success("✨ 대형 도면 스티칭 완벽 성공!")
                    
                    # BGR을 RGB로 변환하여 화면에 표시
                    result_rgb = cv2.cvtColor(stitched_img, cv2.COLOR_BGR2RGB)
                    final_pil_img = Image.fromarray(result_rgb)
                    
                    st.image(final_pil_img, caption="완성된 통합 대형 도면", use_column_width=True)
                    
                    # 파일 다운로드 버튼 제공
                    cv2.imwrite("complete_stitched_drawing.jpg", stitched_img)
                    with open("complete_stitched_drawing.jpg", "rb") as file:
                        st.download_button(
                            label="📥 완성된 대형 도면 다운로드하기",
                            data=file,
                            file_name="complete_stitched_drawing.jpg",
                            mime="image/jpeg"
                        )
                else:
                    st.error(f"스티칭 실패 (오류 코드: {status}). 사진 간의 겹치는 영역(Overlap)이 충분한지, 혹은 특징점이 너무 적지 않은지 확인해 주세요.")
    else:
        st.warning("이어붙이려면 최소 2장 이상의 사진을 업로드해 주세요.")
