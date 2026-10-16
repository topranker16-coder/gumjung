import streamlit as st
import cv2
import numpy as np
from PIL import Image

st.title("🧩 스마트 도면/조각 캔버스 정밀 조립기 (크기 자동 맞춤형)")
st.write("조각들의 크기가 조금씩 달라도 알아서 픽셀을 맞춰 2x2 격자로 완벽하게 조립합니다!")

uploaded_files = st.file_uploader("조각 사진들을 선택하세요 (4장 권장)", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)

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
        if st.button("🚀 캔버스 정밀 조립 실행!"):
            with st.spinner("이미지 크기를 맞추고 캔버스에 조립 중입니다..."):
                
                try:
                    # 4장이 업로드된 경우 2x2 그리드로 직접 조립 (크기 불일치 에러 원천 차단)
                    if len(images) >= 4:
                        img0, img1, img2, img3 = images[0], images[1], images[2], images[3]
                        
                        # 1단계: 윗줄 (img0, img1) 가로 결합을 위해 높이(Height) 맞추기
                        h0, w0 = img0.shape[:2]
                        h1, w1 = img1.shape[:2]
                        target_h_top = max(h0, h1)
                        
                        if h0 != target_h_top:
                            img0 = cv2.resize(img0, (int(w0 * target_h_top / h0), target_h_top))
                        if h1 != target_h_top:
                            img1 = cv2.resize(img1, (int(w1 * target_h_top / h1), target_h_top))
                            
                        top_row = np.hstack((img0, img1))
                        
                        # 2단계: 아랫줄 (img2, img3) 가로 결합을 위해 높이 맞추기
                        h2, w2 = img2.shape[:2]
                        h3, w3 = img3.shape[:2]
                        target_h_bot = max(h2, h3)
                        
                        if h2 != target_h_bot:
                            img2 = cv2.resize(img2, (int(w2 * target_h_bot / h2), target_h_bot))
                        if h3 != target_h_bot:
                            img3 = cv2.resize(img3, (int(w3 * target_h_bot / h3), target_h_bot))
                            
                        bot_row = np.hstack((img2, img3))
                        
                        # 3단계: 윗줄과 아랫줄의 너비(Width) 맞추기
                        w_top = top_row.shape[1]
                        w_bot = bot_row.shape[1]
                        max_w = max(w_top, w_bot)
                        
                        if w_top < max_w:
                            pad = np.ones((top_row.shape[0], max_w - w_top, 3), dtype=np.uint8) * 255
                            top_row = np.hstack((top_row, pad))
                        if w_bot < max_w:
                            pad = np.ones((bot_row.shape[0], max_w - w_bot, 3), dtype=np.uint8) * 255
                            bot_row = np.hstack((bot_row, pad))
                            
                        # 최종 세로 결합
                        stitched_img = np.vstack((top_row, bot_row))
                    else:
                        # 2장인 경우 가로로 단순 결합 (높이 맞춤)
                        h0, w0 = images[0].shape[:2]
                        h1, w1 = images[1].shape[:2]
                        target_h = max(h0, h1)
                        if h0 != target_h:
                            images[0] = cv2.resize(images[0], (int(w0 * target_h / h0), target_h))
                        if h1 != target_h:
                            images[1] = cv2.resize(images[1], (int(w1 * target_h / h1), target_h))
                        stitched_img = np.hstack((images[0], images[1]))

                    st.success("✨ 캔버스 조립 완벽 성공!")
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
                    st.error(f"조립 중 오류가 발생했습니다: {e}")
    else:
        st.warning("이어붙이려면 최소 2장 이상의 사진을 업로드해 주세요.")
