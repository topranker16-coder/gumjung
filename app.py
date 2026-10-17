import io
import cv2
import numpy as np
from PIL import Image
import streamlit as st

# 웹 페이지 기본 설정
st.set_page_config(
    page_title="대형 도면 복원 정밀 조립기",
    page_icon="📐",
    layout="wide"
)

st.title("📐 대형 도면/그림 조각 사진 자동 복원기")
st.write("커다란 도면을 나누어 찍은 조각 사진들(4장, 5장, N장)을 원래의 대형 도면 하나로 완벽하게 복원합니다!")

# 이미지 밝기/조명 균일화 보정 함수
def equalize_lighting(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (0, 0), sigmaX=15, sigmaY=15)
    num = cv2.divide(gray, blur, scale=255)
    res = cv2.cvtColor(num, cv2.COLOR_GRAY2BGR)
    return res

uploaded_files = st.file_uploader(
    "나누어 찍은 도면 조각 사진들을 선택하세요 (4장, 5장, 6장 등 제한 없음)",
    type=['jpg', 'jpeg', 'png'],
    accept_multiple_files=True
)

if uploaded_files:
    st.divider()
    st.subheader(f"🖼️ 업로드된 조각 목록 (총 {len(uploaded_files)}장)")
    
    raw_images = []
    image_names = []
    
    cols = st.columns(min(len(uploaded_files), 5))
    for idx, f in enumerate(uploaded_files):
        file_bytes = np.asarray(bytearray(f.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        if img is not None:
            raw_images.append(img)
            image_names.append(f.name)
            with cols[idx % min(len(uploaded_files), 5)]:
                st.image(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), caption=f"[{idx+1}번] {f.name}", use_container_width=True)

    st.divider()
    
    # 조작 모드 선택
    mode = st.radio(
        "⚙️ 복원 방식을 선택하세요:",
        ["🧩 1. 격자 지정 복원 (구역별 조각 사진 배치)", "🤖 2. AI 자동 스티칭 복원 (사진 간 겹치는 부위 자동 감지)"],
        index=0
    )
    
    apply_enhance = st.checkbox("💡 카메라 조명/밝기 차이 균일화 보정 적용", value=False)
    
    processed_images = [equalize_lighting(img) if apply_enhance else img for img in raw_images]

    # --- 모드 1: 격자 지정 복원 ---
    if mode == "🧩 1. 격자 지정 복원 (구역별 조각 사진 배치)":
        st.write("##### 📐 도면 배치 설정")
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            num_cols = st.number_input("가로 열(Column) 개수:", min_value=1, max_value=10, value=2, step=1)
        
        # 순서 재배치 UI
        st.write("##### 🔄 각 위치에 들어갈 조각 선택 (1행 1열부터 순서대로)")
        ordered_indices = []
        grid_cols = st.columns(num_cols)
        
        for i in range(len(processed_images)):
            col_idx = i % num_cols
            row_idx = i // num_cols
            with grid_cols[col_idx]:
                selected = st.selectbox(
                    f"[{row_idx+1}행 {col_idx+1}열]",
                    options=list(range(len(processed_images))),
                    format_func=lambda x: f"조각 {x+1}: {image_names[x]}",
                    index=i,
                    key=f"select_{i}"
                )
                ordered_indices.append(selected)
                
        if st.button("🚀 대형 도면 복원 실행!", type="primary"):
            with st.spinner("조각들을 정밀 연결하여 대형 도면을 만드는 중입니다..."):
                try:
                    ordered_imgs = [processed_images[i] for i in ordered_indices]
                    
                    # 1단계: 행 단위 가로 결합 (높이 맞춤)
                    rows = []
                    for r in range(0, len(ordered_imgs), num_cols):
                        row_group = ordered_imgs[r:r+num_cols]
                        if not row_group:
                            continue
                        
                        target_h = max(img.shape[0] for img in row_group)
                        resized_row = []
                        for img in row_group:
                            h, w = img.shape[:2]
                            if h != target_h:
                                new_w = int(w * target_h / h)
                                img_r = cv2.resize(img, (new_w, target_h), interpolation=cv2.INTER_LANCZOS4)
                            else:
                                img_r = img
                            resized_row.append(img_r)
                        
                        row_stitched = np.hstack(resized_row)
                        rows.append(row_stitched)
                        
                    # 2단계: 행 간 세로 결합 (너비 맞춤)
                    max_w = max(r.shape[1] for r in rows)
                    final_rows = []
                    for r in rows:
                        h, w = r.shape[:2]
                        if w < max_w:
                            pad = np.ones((h, max_w - w, 3), dtype=np.uint8) * 255
                            r_padded = np.hstack((r, pad))
                        else:
                            r_padded = r
                        final_rows.append(r_padded)
                        
                    final_image = np.vstack(final_rows)
                    
                    st.success("✨ 대형 도면 복원 완료!")
                    final_rgb = cv2.cvtColor(final_image, cv2.COLOR_BGR2RGB)
                    pil_img = Image.fromarray(final_rgb)
                    
                    st.image(pil_img, caption="복원된 대형 도면", use_container_width=True)
                    
                    buf = io.BytesIO()
                    pil_img.save(buf, format="JPEG", quality=98)
                    st.download_button(
                        "📥 복원된 대형 도면 다운로드 (고화질)",
                        data=buf.getvalue(),
                        file_name="reconstructed_blueprint.jpg",
                        mime="image/jpeg"
                    )
                    
                except Exception as e:
                    st.error(f"도면 복원 중 오류가 발생했습니다: {e}")

    # --- 모드 2: AI 자동 스티칭 ---
    else:
        st.write("##### 🤖 AI 특징점 감지 자동 스티칭")
        st.caption("도면 조각들의 경계선에 겹치는 부분이 포함되어 있을 때, 선과 도면 기호를 감지하여 자동으로 붙여줍니다.")
        
        if st.button("🚀 AI 자동 스티칭 시작!", type="primary"):
            with st.spinner("도면의 선과 특징점을 분석하여 복원하는 중입니다..."):
                try:
                    if hasattr(cv2, 'Stitcher_SCANS'):
                        stitcher = cv2.Stitcher_create(cv2.Stitcher_SCANS)
                    else:
                        stitcher = cv2.Stitcher_create()
                        
                    status, stitched = stitcher.stitch(processed_images)
                    
                    if status == cv2.Stitcher_OK:
                        st.success("✨ AI 특징점 자동 도면 복원 성공!")
                        final_rgb = cv2.cvtColor(stitched, cv2.COLOR_BGR2RGB)
                        pil_img = Image.fromarray(final_rgb)
                        
                        st.image(pil_img, caption="AI 복원된 대형 도면", use_container_width=True)
                        
                        buf = io.BytesIO()
                        pil_img.save(buf, format="JPEG", quality=98)
                        st.download_button(
                            "📥 AI 복원 대형 도면 다운로드 (고화질)",
                            data=buf.getvalue(),
                            file_name="ai_stitched_blueprint.jpg",
                            mime="image/jpeg"
                        )
                    else:
                        st.error("AI가 사진 간의 겹치는 특징점을 찾지 못했습니다. 상단 '1. 격자 지정 복원' 모드를 사용하여 조립해 보세요!")
                except Exception as e:
                    st.error(f"자동 스티칭 중 오류가 발생했습니다: {e}")
