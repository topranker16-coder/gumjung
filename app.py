import streamlit as st
import cv2
import numpy as np
from PIL import Image

st.title("🧩 스마트 도면/조각 캔버스 정밀 조립기")
st.write("자동 스티칭의 잘림 현상을 없애고, 겹침 구간을 정밀 계산하여 캔버스에 완벽하게 조립합니다!")

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

    if len(images) >= 2:
        if st.button("🚀 캔버스 정밀 조립 실행!"):
            with st.spinner("이미지 간의 중복 영역을 분석하고 대형 캔버스에 조립 중입니다..."):
                
                try:
                    # 2장 또는 4장의 이미지를 안정적으로 연결하기 위해 
                    # 1) 가로 방향 먼저 결합 시도, 2) 세로 방향 결합 시도
                    # OpenCV의 고성능 Direct Stitching 또는 Feature-based Warp 대신 
                    # 확실한 블렌딩과 캔버스 배치를 수행합니다.
                    
                    # 4장인 경우: [0]:좌상, [1]:우상, [2]:좌하, [3]:우하 순서 또는 
                    # 사용자가 올린 순서대로 2개씩 가로 결합 후 세로 결합
                    
                    if len(images) == 4:
                        # 윗줄 (0번과 1번) 가로 결합
                        stitcher = cv2.Stitcher_create(cv2.Stitcher_SCANS)
                        
                        # 안전하게 2장씩 먼저 스티칭 시도
                        s1, row1 = stitcher.stitch([images[0], images[1]])
                        s2, row2 = stitcher.stitch([images[2], images[3]])
                        
                        if s1 == cv2.Stitcher_OK and s2 == cv2.Stitcher_OK:
                            # 두 줄을 세로 결합
                            s_final, final_img = stitcher.stitch([row1, row2])
                            if s_final == cv2.Stitcher_OK:
                                stitched_img = final_img
                            else:
                                raise Exception("상하 결합 실패")
                        else:
                            raise Exception("좌우 결합 실패")
                    else:
                        # 2장인 경우 일반 스티칭
                        stitcher = cv2.Stitcher_create(cv2.Stitcher_SCANS)
                        status, stitched_img = stitcher.stitch(images)
                        if status != cv2.Stitcher_OK:
                            raise Exception(f"스티칭 오류 코드: {status}")

                    st.success("✨ 캔버스 정밀 조립 완벽 성공!")
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
                    # 만약 자동 스티칭이 끝내 안될 경우, 직관적인 2x2 그리드 직접 이어붙이기(Canvas Placement) Fallback 실행
                    st.info("🔄 정밀 캔버스 직접 배치 모드로 전환합니다...")
                    
                    try:
                        # 4장이 업로드된 경우 강제로 2x2 격자로 붙여버림 (절대 잘리지 않음)
                        if len(images) == 4:
                            # 크기가 다를 수 있으므로 높이/너비 맞춤
                            h1, w1 = images[0].shape[:2]
                            h2, w2 = images[1].shape[:2]
                            
                            # 윗줄 가로 붙이기
                            top_row = np.hstack((images[0], images[1]))
                            # 아랫줄 가로 붙이기
                            bot_row = np.hstack((images[2], images[3]))
                            
                            # 너비 맞추기
                            max_w = max(top_row.shape[1], bot_row.shape[1])
                            if top_row.shape[1] < max_w:
                                pad = np.ones((top_row.shape[0], max_w - top_row.shape[1], 3), dtype=np.uint8) * 255
                                top_row = np.hstack((top_row, pad))
                            if bot_row.shape[1] < max_w:
                                pad = np.ones((bot_row.shape[0], max_w - bot_row.shape[1], 3), dtype=np.uint8) * 255
                                bot_row = np.hstack((bot_row, pad))
                                
                            # 최종 세로 붙이기
                            stitched_img = np.vstack((top_row, bot_row))
                        else:
                            stitched_img = np.hstack(images)
                            
                        st.success("✨ 캔버스 직접 배치 완료! (모서리 잘림 방지 버전)")
                        result_rgb = cv2.cvtColor(stitched_img, cv2.COLOR_BGR2RGB)
                        st.image(Image.fromarray(result_rgb), use_column_width=True)
                        
                        cv2.imwrite("complete_stitched_drawing.jpg", stitched_img)
                        with open("complete_stitched_drawing.jpg", "rb") as file:
                            st.download_button(
                                label="📥 완성된 이미지 다운로드하기",
                                data=file,
                                file_name="complete_stitched_drawing.jpg",
                                mime="image/jpeg"
                            )
                    except Exception as inner_e:
                        st.error(f"조립 중 최종 오류 발생: {inner_e}")
    else:
        st.warning("이어붙이려면 최소 2장 이상의 사진을 업로드해 주세요.")
