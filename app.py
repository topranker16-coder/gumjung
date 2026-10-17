import io
import cv2
import numpy as np
from PIL import Image
import streamlit as st

st.set_page_config(
    page_title="영화 속 딥줌(Deep Zoom) 화질 업그레이드기",
    page_icon="🔍",
    layout="wide"
)

st.title("🎬 영화 속 딥 줌(Deep Zoom) 화질 업그레이드기 + 인터랙티브 뷰어")
st.write("저화질 전체 사진 위에 고화질 조각을 정밀 합성하고, 원하는 구역을 실시간으로 돋보기 확대(Deep Zoom)하여 원본과 고화질 결과를 비교해보세요!")

col1, col2 = st.columns(2)

with col1:
    st.subheader("1️⃣ 저화질 전체 원본 사진 (가이드)")
    ref_file = st.file_uploader("전체 모습을 담은 저화질/축소 사진 1장", type=['jpg', 'jpeg', 'png'], key="ref_base")

with col2:
    st.subheader("2️⃣ 고화질 부분 확대 조각 사진들")
    slice_files = st.file_uploader("선명하게 업그레이드할 고화질 조각 사진들", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True, key="slices_high")

if ref_file and slice_files:
    st.divider()
    
    # 저화질 전체 사진 읽기
    ref_bytes = np.asarray(bytearray(ref_file.read()), dtype=np.uint8)
    ref_img = cv2.imdecode(ref_bytes, cv2.IMREAD_COLOR)
    
    # 조각 사진들 읽기
    slice_imgs = []
    slice_names = []
    for f in slice_files:
        b = np.asarray(bytearray(f.read()), dtype=np.uint8)
        img = cv2.imdecode(b, cv2.IMREAD_COLOR)
        if img is not None:
            slice_imgs.append(img)
            slice_names.append(f.name)

    st.subheader("⚙️ 고해상도 캔버스 및 합성 설정")
    upscale_factor = st.select_slider("🚀 전체 캔버스 확대 배율 (기본 2배 확대)", options=[2, 3, 4], value=2)
    
    if st.button("🚀 딥 줌 화질 복원 실행!", type="primary"):
        with st.spinner("저화질 캔버스를 확대하고 고화질 조각을 정밀 합성 중입니다..."):
            try:
                orig_h, orig_w = ref_img.shape[:2]
                target_w = orig_w * upscale_factor
                target_h = orig_h * upscale_factor
                
                # 1. 저화질 캔버스 확대
                low_res_canvas = cv2.resize(ref_img, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)
                high_res_canvas = low_res_canvas.copy()
                
                # 2. SIFT 특징점 매칭
                sift = cv2.SIFT_create()
                kp_ref, des_ref = sift.detectAndCompute(ref_img, None)
                
                success_count = 0
                for s_img, s_name in zip(slice_imgs, slice_names):
                    kp_s, des_s = sift.detectAndCompute(s_img, None)
                    if des_s is None or des_ref is None:
                        continue
                        
                    FLANN_INDEX_KDTREE = 1
                    flann = cv2.FlannBasedMatcher(dict(algorithm=FLANN_INDEX_KDTREE, trees=5), dict(checks=50))
                    matches = flann.knnMatch(des_s, des_ref, k=2)
                    
                    good_matches = [m for m, n in matches if m.distance < 0.7 * n.distance]
                    
                    if len(good_matches) >= 10:
                        src_pts = np.float32([kp_s[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
                        dst_pts = np.float32([kp_ref[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
                        dst_pts_scaled = dst_pts * upscale_factor
                        
                        H, mask = cv2.findHomography(src_pts, dst_pts_scaled, cv2.RANSAC, 5.0)
                        
                        if H is not None:
                            warped = cv2.warpPerspective(s_img, H, (target_w, target_h), flags=cv2.INTER_LANCZOS4)
                            gray_warped = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
                            _, mask_bin = cv2.threshold(gray_warped, 1, 255, cv2.THRESH_BINARY)
                            
                            inv_mask = cv2.bitwise_not(mask_bin)
                            bg = cv2.bitwise_and(high_res_canvas, high_res_canvas, mask=inv_mask)
                            fg = cv2.bitwise_and(warped, warped, mask=mask_bin)
                            
                            high_res_canvas = cv2.add(bg, fg)
                            success_count += 1
                            st.toast(f"✅ [{s_name}] 구역 화질 업그레이드 완료!")

                # 세션 상태 저장 (뷰어용)
                st.session_state["low_res"] = low_res_canvas
                st.session_state["high_res"] = high_res_canvas
                st.session_state["target_w"] = target_w
                st.session_state["target_h"] = target_h
                st.success(f"✨ 총 {success_count}개 구역의 고화질 복원이 완료되었습니다!")
                
            except Exception as e:
                st.error(f"처리 중 오류가 발생했습니다: {e}")

# --- 인터랙티브 돋보기 뷰어 영역 ---
if "high_res" in st.session_state:
    st.divider()
    st.subheader("🔎 인터랙티브 돋보기 (Deep Zoom) 비교 뷰어")
    
    low_canvas = st.session_state["low_res"]
    high_canvas = st.session_state["high_res"]
    tw = st.session_state["target_w"]
    th = st.session_state["target_h"]
    
    st.write("슬라이더로 확대를 원하는 중심 위치(X, Y)와 돋보기 비율을 조절해 보세요!")
    
    col_v1, col_v2, col_v3 = st.columns(3)
    with col_v1:
        center_x = st.slider("📍 가로 위치 (X%):", 0, 100, 50, step=1)
    with col_v2:
        center_y = st.slider("📍 세로 위치 (Y%):", 0, 100, 50, step=1)
    with col_v3:
        zoom_level = st.slider("🔍 돋보기 확대율:", 2, 10, 4, step=1)

    # 중심 좌표 및 영역 Crop 계산
    cx = int(tw * (center_x / 100.0))
    cy = int(th * (center_y / 100.0))
    
    crop_w = max(50, int(tw / zoom_level))
    crop_h = max(50, int(th / zoom_level))
    
    x1 = max(0, min(tw - crop_w, cx - crop_w // 2))
    y1 = max(0, min(th - crop_h, cy - crop_h // 2))
    x2 = x1 + crop_w
    y2 = y1 + crop_h
    
    # 영역 자르기
    crop_low = low_canvas[y1:y2, x1:x2]
    crop_high = high_canvas[y1:y2, x1:x2]
    
    st.write("##### 🔬 돋보기 확대 비교 (Before vs After)")
    col_comp1, col_comp2 = st.columns(2)
    
    with col_comp1:
        st.write("🔻 **기존 저화질 확대 영역**")
        st.image(cv2.cvtColor(crop_low, cv2.COLOR_BGR2RGB), use_container_width=True)
        
    with col_comp2:
        st.write("✨ **딥 줌 고화질 복원 영역**")
        st.image(cv2.cvtColor(crop_high, cv2.COLOR_BGR2RGB), use_container_width=True)
        
    st.divider()
    st.write("##### 🖼️ 전체 완성본")
    st.image(cv2.cvtColor(high_canvas, cv2.COLOR_BGR2RGB), caption=f"최종 딥 줌 이미지 ({tw}x{th}px)", use_container_width=True)
    
    buf = io.BytesIO()
    final_pil = Image.fromarray(cv2.cvtColor(high_canvas, cv2.COLOR_BGR2RGB))
    final_pil.save(buf, format="JPEG", quality=98)
    st.download_button(
        "📥 초고화질 완성본 다운로드",
        data=buf.getvalue(),
        file_name="deepzoom_enhanced_image.jpg",
        mime="image/jpeg"
    )
