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

st.title("🎬 영화 속 딥 줌(Deep Zoom) 부분 화질 업그레이드기")
st.write("저화질 전체 사진 위에 고화질 부분 조각을 합성하여, 특정 구역의 선명도를 첩보 영화처럼 극적으로 올려줍니다!")

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
    upscale_factor = st.select_slider("🚀 전체 캔버스 확대 배율 (기본 2배 확대)", options=[1, 2, 3, 4], value=2)
    
    if st.button("🚀 딥 줌 화질 복원 실행!", type="primary"):
        with st.spinner("저화질 캔버스를 확대하고 고화질 조각을 정밀 합성 중입니다..."):
            try:
                # 1. 저화질 원본을 고해상도 캔버스로 확대 (LANCZOS4 보정)
                orig_h, orig_w = ref_img.shape[:2]
                target_w = orig_w * upscale_factor
                target_h = orig_h * upscale_factor
                
                high_res_canvas = cv2.resize(ref_img, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)
                
                # 2. SIFT 특징점 매칭으로 고화질 조각 위치 정밀 합성
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
                        # 원래 저화질 좌표 찾기
                        src_pts = np.float32([kp_s[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
                        dst_pts = np.float32([kp_ref[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
                        
                        # 확대된 캔버스 좌표계로 스케일 변환
                        dst_pts_scaled = dst_pts * upscale_factor
                        
                        H, mask = cv2.findHomography(src_pts, dst_pts_scaled, cv2.RANSAC, 5.0)
                        
                        if H is not None:
                            # 고화질 조각을 확대 캔버스 위치에 와핑하여 정밀 덮어쓰기
                            warped = cv2.warpPerspective(s_img, H, (target_w, target_h), flags=cv2.INTER_LANCZOS4)
                            
                            gray_warped = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
                            _, mask_bin = cv2.threshold(gray_warped, 1, 255, cv2.THRESH_BINARY)
                            
                            inv_mask = cv2.bitwise_not(mask_bin)
                            bg = cv2.bitwise_and(high_res_canvas, high_res_canvas, mask=inv_mask)
                            fg = cv2.bitwise_and(warped, warped, mask=mask_bin)
                            
                            high_res_canvas = cv2.add(bg, fg)
                            success_count += 1
                            st.toast(f"✅ [{s_name}] 구역 화질 업그레이드 완료!")

                st.success(f"✨ 총 {success_count}개 구역의 고화질 복원이 완료되었습니다!")
                
                final_rgb = cv2.cvtColor(high_res_canvas, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(final_rgb)
                
                st.image(pil_img, caption=f"화질 개선 완료본 ({target_w}x{target_h}px)", use_container_width=True)
                
                buf = io.BytesIO()
                pil_img.save(buf, format="JPEG", quality=98)
                st.download_button(
                    "📥 초고화질 완성본 다운로드",
                    data=buf.getvalue(),
                    file_name="deepzoom_enhanced_image.jpg",
                    mime="image/jpeg"
                )
                
            except Exception as e:
                st.error(f"처리 중 오류가 발생했습니다: {e}")
