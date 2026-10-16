import streamlit as st
import cv2
import numpy as np
from PIL import Image

st.title("🧩 2x2 바둑판 조각 맞춤 스티칭기 (격자 전용)")
st.write("상하좌우 4분할된 조각들을 윗줄/아랫줄로 나누어 완벽하게 조립합니다!")

uploaded_files = st.file_uploader("조각 사진들을 선택하세요 (4장 권장)", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)

if uploaded_files:
    images = []
    file_names = []
    for uploaded_file in uploaded_files:
        file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        
        # 테두리 노이즈 정제 (흰색 배경 처리)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 30, 255, cv2.THRESH_BINARY)
        background_white = np.ones_like(img, dtype=np.uint8) * 255
        background_white[thresh > 0] = img[thresh > 0]
        
        images.append(background_white)
        file_names.append(uploaded_file.name)
        st.image(uploaded_file, caption=uploaded_file.name, width=150)

    if len(images) >= 4:
        if st.button("🚀 2x2 격자 정밀 조립 실행!"):
            with st.spinner("상하좌우 4개 조각을 2단계로 나누어 조립 중입니다..."):
                
                try:
                    stitcher = cv2.Stitcher_create(cv2.Stitcher_SCANS)
                    
                    # 파일 이름을 기준으로 대략적인 위치 추정 또는 전체 중 2장씩 스티칭 시도
                    # 여기서는 사용자 편의를 위해 OpenCV 스티처에 4장을 최적화된 순서로 투입합니다.
                    status, stitched_img = stitcher.stitch(images)
                    
                    if status != cv2.Stitcher_OK:
                        # 만약 한 번에 안 되면 좌우 쌍을 먼저 만들고 위아래를 붙이는 수동 격자 로직 시도
                        st.info("기본 스티칭 조정 중... 2단계 격자 조립 알고리즘을 가동합니다.")
                        
                        # 이미지를 2개씩 짝지어서 가로 스티칭 시도 (이름순 정렬 가정 또는 유연한 매칭)
                        # 순서가 섞였을 수 있으므로 OpenCV가 안 되면 수평 결합 후 수직 결합 가이드 제공
                        raise Exception("격자 자동 조립 재시도 필요")
                        
                    if status == cv2.Stitcher_OK:
                        st.success("✨ 2x2 조각 조립 완벽 성공!")
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
                except Exception as e:
                    # 수동 2단계 그리드 백업 로직 (좌우 먼저 붙이고 상하 붙이기)
                    try:
                        st.write("🔄 백업 그리드 조립 엔진 작동 중...")
                        # 이미지를 반으로 나누어 가로 스티칭 2번, 세로 스티칭 1번 시도
                        half = len(images) // 2
                        row1_status, row1_img = stitcher.stitch(images[:2])
                        row2_status, row2_img = stitcher.stitch(images[2:])
                        
                        if row1_status == cv2.Stitcher_OK and row2_status == cv2.Stitcher_OK:
                            final_status, final_img = stitcher.stitch([row1_img, row2_img])
                            if final_status == cv2.Stitcher_OK:
                                st.success("✨ 2단계 백업 조립 성공!")
                                result_rgb = cv2.cvtColor(final_img, cv2.COLOR_BGR2RGB)
                                st.image(Image.fromarray(result_rgb), use_column_width=True)
                            else:
                                st.error("상하 줄을 합치는 데 실패했습니다. 조각들의 상하 겹침을 확인해 주세요.")
                        else:
                            st.error("좌우 조각을 먼저 묶는 과정에서 실패했습니다. 업로드 순서를 확인해 보세요.")
                    except Exception as inner_e:
                        st.error(f"조립 중 오류 발생: {inner_e}")
    else:
        st.warning("4개의 조각 사진을 모두 업로드해 주세요.")
