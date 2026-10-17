import io
import cv2
import numpy as np
from PIL import Image
import streamlit as st

st.set_page_config(
    page_title="전체 가이드 기준 대형 도면 복원기",
    page_icon="🗺️",
    layout="wide"
)

st.title("🗺️ 전체 가이드 기준 대형 도면/그림 완벽 복원기")
st.write("전체 모습이 담긴 가이드 사진 1장과 고화질 조각 사진들을 올려주시면, 위치를 자동으로 매칭하여 완벽한 고화질 도면으로 합성합니다!")

# 이미지 리사이즈 함수
def resize_image(img, max_dim=2000):
    h, w = img.shape[:2]
    if max(h, w) > max_dim:
        scale = max_dim / float(max(h, w))
        return cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    return img

col_up1, col_up2 = st.columns([1, 2])

with col_up1:
    st.subheader("1️⃣ 전체 기준 사진 (1장)")
    ref_file = st.file_uploader("전체가 흐릿하게나마 다 보이는 사진", type=['jpg', 'jpeg', 'png'], key="ref_uploader")

with col_up2:
    st.subheader("2️⃣ 고화질 조각 사진들 (N장)")
    slice_files = st.file_uploader("나누어 찍은 선명한 조각 사진들", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True, key="slice_uploader")

if ref_file and slice_files:
    st.divider()
    
    # 1. 전체 이미지 읽기
    ref_bytes = np.asarray(bytearray(ref_file.read()), dtype=np.uint8)
    ref_img = cv2.imdecode(ref_bytes, cv2.IMREAD_COLOR)
    
    # 2. 조각 이미지들 읽기
    slice_imgs = []
    slice_names = []
    for f in slice_files:
        b = np.asarray(bytearray(f.read()), dtype=np.uint8)
        img = cv2.imdecode(b, cv2.IMREAD_COLOR)
        if img is not None:
            slice_imgs.append(img)
            slice_names.append(f.name)
            
    st.subheader("⚙️ 자동 위치 매칭 및 합성 설정")
    match_sensitivity = st.slider("🔍 AI 특징점 감지 민감도 (기본 0.7)", 0.4, 0.9, 0.7, step=0.05)
    
    if st.button("🚀 전체 가이드 기반 고화질 복원 실행!", type="primary"):
        with st.spinner("전체 사진 속에서 각 고화질 조각의 위치를 AI가 정밀 검색 중입니다..."):
            try:
                # 작업용 캔버스 (전체 사진 크기에 맞춤)
                canvas = ref_img.copy()
                canvas_h, canvas_w = canvas.shape[:2]
                
                # SIFT 특징점 추출기 생성
                sift = cv2.SIFT_create()
                kp_ref, des_ref = sift.detectAndCompute(ref_img, None)
                
                matched_count = 0
                
                for idx, (s_img, s_name) in enumerate(zip(slice_imgs, slice_names)):
                    kp_s, des_s = sift.detectAndCompute(s_img, None)
                    
                    if des_s is None or des_ref is None:
                        continue
                        
                    # FLANN 매처로 특징점 비교
                    FLANN_INDEX_KDTREE = 1
                    index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
                    search_params = dict(checks=50)
                    flann = cv2.FlannBasedMatcher(index_params, search_params)
                    
                    matches = flann.knnMatch(des_s, des_ref, k=2)
                    
                    # 좋은 매칭점 골라내기
                    good_matches = []
                    for m, n in matches:
                        if m.distance < match_sensitivity * n.distance:
                            good_matches.append(m)
                            
                    if len(good_matches) >= 10:
                        src_pts = np.float32([kp_s[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
                        dst_pts = np.float32([kp_ref[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
                        
                        # 변환 행렬(Homography) 계산 (위치, 회전, 크기 변화 감지)
                        H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
                        
                        if H is not None:
                            # 조각 이미지를 전체 사진 좌표계로 변환하여 덮어씌우기
                            warped_slice = cv2.warpPerspective(s_img, H, (canvas_w, canvas_h))
                            
                            # 마스크 생성 (조각이 들어갈 부분만 덮어쓰기)
                            slice_gray = cv2.cvtColor(warped_slice, cv2.COLOR_BGR2GRAY)
                            _, mask_bin = cv2.threshold(slice_gray, 1, 255, cv2.THRESH_BINARY)
                            
                            # 캔버스에 합성
                            inv_mask = cv2.bitwise_not(mask_bin)
                            canvas_bg = cv2.bitwise_and(canvas, canvas, mask=inv_mask)
                            slice_fg = cv2.bitwise_and(warped_slice, warped_slice, mask=mask_bin)
                            canvas = cv2.add(canvas_bg, slice_fg)
                            
                            matched_count += 1
                            st.toast(f"✅ 조각 [{s_name}] 위치 매칭 성공!")
                    else:
                        st.warning(f"⚠️ [{s_name}] 조각은 전체 사진에서 특징점을 충분히 찾지 못했습니다.")

                st.success(f"✨ 총 {len(slice_imgs)}장 중 {matched_count}장의 고화질 조각이 전체 가이드 위치에 완벽 복원되었습니다!")
                
                final_rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(final_rgb)
                
                st.image(pil_img, caption="전체 가이드 기준 완성본", use_container_width=True)
                
                buf = io.BytesIO()
                pil_img.save(buf, format="JPEG", quality=98)
                st.download_button(
                    "📥 완성된 대형 도면 다운로드 (고화질)",
                    data=buf.getvalue(),
                    file_name="guide_matched_blueprint.jpg",
                    mime="image/jpeg"
                )
                
            except Exception as e:
                st.error(f"복원 중 오류가 발생했습니다: {e}")
