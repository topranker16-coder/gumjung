import io
import cv2
import numpy as np
from PIL import Image
import streamlit as st

# 웹 페이지 기본 설정
st.set_page_config(
    page_title="스마트 도면/조각 캔버스 정밀 조립기",
    page_icon="🧩",
    layout="wide"
)

st.title("🧩 스마트 도면/조각 캔버스 정밀 조립기 (자동 크기 맞춤형)")
st.write("크기가 서로 다른 조각 사진들의 높이와 너비를 자동으로 계산하여 깔끔하게 조립해 드립니다!")

uploaded_files = st.file_uploader(
    "조각 사진들을 선택하세요 (2장 이상 권장)",
    type=['jpg', 'jpeg', 'png'],
    accept_multiple_files=True
)

if uploaded_files:
    images = []
    st.subheader("🖼️ 업로드된 조각 목록")
    cols = st.columns(min(len(uploaded_files), 4))
    
    for idx, uploaded_file in enumerate(uploaded_files):
        file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        if img is not None:
            images.append(img)
            with cols[idx % 4]:
                st.image(uploaded_file, caption=f"조각 {idx+1}: {uploaded_file.name}", use_container_width=True)

    if len(images) >= 2:
        st.divider()
        if st.button("🚀 캔버스 정밀 조립 실행!", type="primary"):
            with st.spinner("조각들의 크기를 정밀 계산하여 조립 중입니다..."):
                try:
                    # 2장인 경우: 가로 배치
                    if len(images) == 2:
                        h0, w0 = images[0].shape[:2]
                        h1, w1 = images[1].shape[:2]
                        target_h = max(h0, h1)
                        
                        img0 = cv2.resize(images[0], (int(w0 * target_h / h0), target_h)) if h0 != target_h else images[0]
                        img1 = cv2.resize(images[1], (int(w1 * target_h / h1), target_h)) if h1 != target_h else images[1]
                        
                        stitched_img = np.hstack((img0, img1))

                    # 3장 이상인 경우: 2개씩 짝지어 2x2 이상 격자(Grid) 자동 배치
                    else:
                        rows = []
                        for i in range(0, len(images), 2):
                            pair = images[i:i+2]
                            if len(pair) == 2:
                                h0, w0 = pair[0].shape[:2]
                                h1, w1 = pair[1].shape[:2]
                                target_h = max(h0, h1)
                                
                                p0 = cv2.resize(pair[0], (int(w0 * target_h / h0), target_h)) if h0 != target_h else pair[0]
                                p1 = cv2.resize(pair[1], (int(w1 * target_h / h1), target_h)) if h1 != target_h else pair[1]
                                row_img = np.hstack((p0, p1))
                            else:
                                row_img = pair[0]
                            rows.append(row_img)
                        
                        # 행 간 너비(Width) 통일 후 세로 결합
                        max_w = max(r.shape[1] for r in rows)
                        padded_rows = []
                        for r in rows:
                            curr_h, curr_w = r.shape[:2]
                            if curr_w < max_w:
                                pad = np.ones((curr_h, max_w - curr_w, 3), dtype=np.uint8) * 255
                                r_padded = np.hstack((r, pad))
                            else:
                                r_padded = r
                            padded_rows.append(r_padded)
                            
                        stitched_img = np.vstack(padded_rows)

                    st.success("✨ 캔버스 조립이 완벽하게 완료되었습니다!")
                    
                    # BGR -> RGB 변환 및 PIL 이미지 생성
                    result_rgb = cv2.cvtColor(stitched_img, cv2.COLOR_BGR2RGB)
                    final_pil_img = Image.fromarray(result_rgb)
                    
                    st.image(final_pil_img, caption="완성된 통합 도면/이미지", use_container_width=True)
                    
                    # 메모리 버퍼를 통한 안전한 다운로드
                    buf = io.BytesIO()
                    final_pil_img.save(buf, format="JPEG", quality=95)
                    byte_im = buf.getvalue()
                    
                    st.download_button(
                        label="📥 완성된 통합 이미지 다운로드하기",
                        data=byte_im,
                        file_name="complete_stitched_drawing.jpg",
                        mime="image/jpeg"
                    )
                except Exception as e:
                    st.error(f"조립 중 오류가 발생했습니다: {e}")
    else:
        st.warning("조립을 시작하려면 최소 2장 이상의 이미지 파일을 업로드해 주세요.")
