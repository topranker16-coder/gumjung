import io
import cv2
import numpy as np
from PIL import Image
import streamlit as st

st.set_page_config(
    page_title="대형 도면/그림 정밀 복원기",
    page_icon="🎨",
    layout="wide"
)

st.title("🎨 대형 도면/그림 비율 보존 정밀 복원기")
st.write("조각 사진들의 원본 비율을 100% 유지하고, 테두리를 정밀 조절하여 원래 그림 그대로 복원합니다!")

# 비율 유지 리사이즈 함수
def resize_keep_aspect(img, target_w=None, target_h=None):
    h, w = img.shape[:2]
    if target_w is not None and w != target_w:
        scale = target_w / float(w)
        new_h = int(h * scale)
        return cv2.resize(img, (target_w, new_h), interpolation=cv2.INTER_LANCZOS4)
    elif target_h is not None and h != target_h:
        scale = target_h / float(h)
        new_w = int(w * scale)
        return cv2.resize(img, (new_w, target_h), interpolation=cv2.INTER_LANCZOS4)
    return img

uploaded_files = st.file_uploader(
    "나누어 찍은 그림/도면 조각 사진들을 선택하세요 (4장 권장)",
    type=['jpg', 'jpeg', 'png'],
    accept_multiple_files=True
)

if uploaded_files:
    st.divider()
    raw_images = []
    image_names = []
    
    st.subheader(f"🖼️ 업로드된 조각 ({len(uploaded_files)}장)")
    cols = st.columns(min(len(uploaded_files), 4))
    for idx, f in enumerate(uploaded_files):
        file_bytes = np.asarray(bytearray(f.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        if img is not None:
            raw_images.append(img)
            image_names.append(f.name)
            with cols[idx % 4]:
                st.image(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), caption=f"[{idx+1}번] {f.name}", use_container_width=True)

    st.divider()
    st.subheader("⚙️ 미세 정렬 및 테두리 자르기 옵션")
    
    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        num_cols = st.number_input("가로 열(Column) 개수:", min_value=1, max_value=10, value=2, step=1)
        crop_tb = st.slider("✂️ 상/하 테두리 자르기 (픽셀):", 0, 100, 0, step=2)
    with col_opt2:
        crop_lr = st.slider("✂️ 좌/우 테두리 자르기 (픽셀):", 0, 100, 0, step=2)

    # 테두리 자르기 적용
    processed_images = []
    for img in raw_images:
        h, w = img.shape[:2]
        top = crop_tb if crop_tb < h // 2 else 0
        bottom = h - crop_tb if crop_tb < h // 2 else h
        left = crop_lr if crop_lr < w // 2 else 0
        right = w - crop_lr if crop_lr < w // 2 else w
        cropped = img[top:bottom, left:right]
        processed_images.append(cropped)

    st.write("##### 🔄 각 위치별 조각 지정")
    ordered_indices = []
    grid_cols = st.columns(num_cols)
    for i in range(len(processed_images)):
        col_i = i % num_cols
        row_i = i // num_cols
        with grid_cols[col_i]:
            idx_sel = st.selectbox(
                f"[{row_i+1}행 {col_i+1}열]",
                options=list(range(len(processed_images))),
                format_func=lambda x: f"조각 {x+1}: {image_names[x]}",
                index=i,
                key=f"grid_sel_{i}"
            )
            ordered_indices.append(idx_sel)

    if st.button("🚀 원본 비율 보존 복원 실행!", type="primary"):
        with st.spinner("비율을 유지하며 정밀 복원 중입니다..."):
            try:
                ordered_imgs = [processed_images[i] for i in ordered_indices]
                
                # 1단계: 각 행(Row)별로 높이를 표준화하되 비율 유지
                rows = []
                for r in range(0, len(ordered_imgs), num_cols):
                    row_group = ordered_imgs[r:r+num_cols]
                    if not row_group:
                        continue
                    
                    # 기준 높이
                    ref_h = row_group[0].shape[0]
                    resized_row = [resize_keep_aspect(img, target_h=ref_h) for img in row_group]
                    
                    # 가로 결합
                    row_img = np.hstack(resized_row)
                    rows.append(row_img)

                # 2단계: 행 간 가로 너비 표준화 (비율 유지)
                ref_w = rows[0].shape[1]
                final_rows = [resize_keep_aspect(r, target_w=ref_w) for r in rows]

                # 세로 결합
                final_image = np.vstack(final_rows)

                st.success("✨ 원본 비율 보존 복원 성공!")
                final_rgb = cv2.cvtColor(final_image, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(final_rgb)

                st.image(pil_img, caption="복원된 결과물", use_container_width=True)

                buf = io.BytesIO()
                pil_img.save(buf, format="JPEG", quality=98)
                st.download_button(
                    "📥 고화질 완성본 다운로드",
                    data=buf.getvalue(),
                    file_name="restored_image.jpg",
                    mime="image/jpeg"
                )
            except Exception as e:
                st.error(f"복원 중 오류가 발생했습니다: {e}")
