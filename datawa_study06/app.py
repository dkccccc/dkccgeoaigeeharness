"""
datawa_study06 · 배포 (Streamlit 웹앱)
====================================================================
지금까지 노트북에서 셀 단위로 돌리던 변화탐지를, '남이 클릭해서 쓰는 웹앱'으로 바꿉니다.
지역·기간·구름 임계값을 화면에서 입력 → [분석 실행] 버튼 → 변화 지도 + 요약 통계 표시.

만든 순서: 프롬프트 6-1(streamlit 웹앱) → 6-2(배포해 링크 공유) → 6-3(MCP 맛보기·확인)

[경계면 — 4장 service.py 를 그대로 재사용합니다]
핵심은 4장에서 만든 run_change_detection(roi, before, after, cloud_pct) 입니다.
이 파일은 그 함수를 'Streamlit 화면'으로 감쌌을 뿐입니다. 분석 로직은 4장 그대로입니다.

로컬 실행:
    pip install streamlit geemap earthengine-api
    streamlit run app.py
"""

import json

import ee
import geemap.foliumap as geemap   # streamlit 안에서는 folium 백엔드를 써야 지도가 뜸
import streamlit as st


# =====================================================================
# [0] Earth Engine 초기화
# 노트북과 달리 웹앱은 ee.Authenticate() 의 '브라우저 인증'을 띄울 수 없습니다.
# 그래서 로컬에서 미리 한 번 인증해 둔 토큰으로 조용히 초기화만 합니다.
#   (처음 한 번만, 터미널에서)  earthengine authenticate
# 배포(클라우드)에서는 README 의 '서비스 계정' 안내를 따르세요.
# =====================================================================

@st.cache_resource   # 초기화는 앱 수명 동안 한 번만
def init_ee():
    try:
        ee.Initialize()
    except Exception:
        # 토큰이 없으면(예: 클라우드 첫 실행) 인증을 시도해 본다.
        ee.Authenticate()
        ee.Initialize()


# =====================================================================
# [4장에서 만든 것] — service.py 의 핵심 3함수를 그대로 가져왔습니다.
# (이 한 파일만으로 배포되도록 여기에 다시 넣어 두었습니다. 로직은 4장과 동일.)
# =====================================================================

def ndvi_for_roi(roi, start, end, cloud_pct=20):
    """그린 영역(roi)의 NDVI 이미지를 계산해 반환한다. (2장 함수)"""
    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(roi)
        .filterDate(start, end)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cloud_pct))
        .sort("CLOUDY_PIXEL_PERCENTAGE")
    )
    image = collection.first().clip(roi)
    # NDVI = (근적외선 B8 - 빨강 B4) / (B8 + B4)
    return image.normalizedDifference(["B8", "B4"]).rename("NDVI")


def ndvi_change(roi, before, after, cloud_pct=20):
    """두 기간의 NDVI를 빼서 '변화 이미지'를 반환한다. (3장 함수)"""
    ndvi_before = ndvi_for_roi(roi, before[0], before[1], cloud_pct)
    ndvi_after = ndvi_for_roi(roi, after[0], after[1], cloud_pct)
    return ndvi_after.subtract(ndvi_before).rename("NDVI_change")


def run_change_detection(roi, before, after, cloud_pct=20):
    """변화탐지 서비스 한 번 실행. 변화 이미지 + 요약 통계를 dict로 반환한다. (4장 함수)"""
    if roi is None:
        return None

    change = ndvi_change(roi, before, after, cloud_pct)

    mean_stat = change.reduceRegion(
        reducer=ee.Reducer.mean(), geometry=roi, scale=10, maxPixels=1e9,
    )
    mean_change = mean_stat.get("NDVI_change").getInfo()

    THRESHOLD = 0.1
    pixel_area = ee.Image.pixelArea()
    decreased = pixel_area.updateMask(change.lt(-THRESHOLD))
    increased = pixel_area.updateMask(change.gt(THRESHOLD))

    def area_m2(masked_area_image):
        stat = masked_area_image.reduceRegion(
            reducer=ee.Reducer.sum(), geometry=roi, scale=10, maxPixels=1e9,
        )
        val = stat.get("area").getInfo()
        return float(val) if val is not None else 0.0

    total_m2 = roi.area(maxError=1).getInfo()
    decrease_m2 = area_m2(decreased)
    increase_m2 = area_m2(increased)
    decrease_ratio = decrease_m2 / total_m2 * 100 if total_m2 else 0.0
    increase_ratio = increase_m2 / total_m2 * 100 if total_m2 else 0.0

    return {
        "image": change,
        "roi": roi,
        "before": before,
        "after": after,
        "cloud_pct": cloud_pct,
        "mean_change": mean_change,
        "decrease_ratio": decrease_ratio,
        "increase_ratio": increase_ratio,
        "area_km2": total_m2 / 1e6,
    }


# =====================================================================
# [6-1] 뼈대 — 입력 화면 + 분석 버튼 + 결과(지도·통계) 표시
# Streamlit 은 위에서 아래로 코드를 읽으며 화면을 그립니다.
# st.xxx 한 줄이 화면의 한 요소(제목·입력칸·버튼·지도)가 됩니다.
# =====================================================================

# --- 페이지 기본 설정 (가장 위에 한 번) ---
st.set_page_config(page_title="변화탐지 웹앱", page_icon="🛰️", layout="wide")
init_ee()

st.title("🛰️ 위성영상 변화탐지 웹앱")
st.caption("지역과 두 기간을 정하면, 식생이 줄거나 는 곳을 지도로 보여줍니다. (NDVI 변화)")

# --- 왼쪽 사이드바: 입력값 (남이 바꿔 쓰는 부분) ---
with st.sidebar:
    st.header("① 분석 조건")

    # 지역: 중심 좌표 + 반경(km) 으로 네모 영역을 만든다.
    # (지도에 직접 그리게 할 수도 있지만, 웹앱은 '입력칸' 이 가장 쉽고 안 헷갈립니다.)
    st.subheader("지역")
    lat = st.number_input("중심 위도", value=37.50, format="%.4f")
    lon = st.number_input("중심 경도", value=127.00, format="%.4f")
    radius_km = st.slider("반경 (km)", min_value=1, max_value=15, value=3)

    st.subheader("기간")
    before = (
        str(st.date_input("이전 시작", value=None, key="b0",
                          format="YYYY-MM-DD") or "2023-01-01"),
        str(st.date_input("이전 끝", value=None, key="b1",
                          format="YYYY-MM-DD") or "2023-12-31"),
    )
    after = (
        str(st.date_input("이후 시작", value=None, key="a0",
                          format="YYYY-MM-DD") or "2024-01-01"),
        str(st.date_input("이후 끝", value=None, key="a1",
                          format="YYYY-MM-DD") or "2024-12-31"),
    )

    cloud_pct = st.slider("구름 임계값 (%)", min_value=5, max_value=60, value=20,
                          help="낮출수록 맑은 영상만. 결과가 비면 높여보세요.")

    run = st.button("② 분석 실행", type="primary", use_container_width=True)


# --- 변화 이미지를 지도에 칠하는 색 규칙 (4장 show_change 와 동일) ---
VIS = {
    "min": -0.3, "max": 0.3,
    "palette": ["#d73027", "#ffffff", "#1a9850"],  # 감소(빨강) → 흰 → 증가(초록), 3장과 동일
}


def make_roi(lon, lat, radius_km):
    """중심 좌표와 반경(km)으로 네모 영역(ee.Geometry)을 만든다."""
    point = ee.Geometry.Point([lon, lat])
    # buffer(미터) 로 원을 만든 뒤 그 외접 사각형(bounds)을 영역으로 쓴다.
    return point.buffer(radius_km * 1000).bounds()


# --- 버튼을 누르면 분석 → 결과 표시 ---
if run:
    with st.spinner("위성영상을 모아 변화를 계산하는 중... (10~40초)"):
        roi = make_roi(lon, lat, radius_km)
        result = run_change_detection(roi, before, after, cloud_pct)

    if result is None or result["mean_change"] is None:
        st.error("그 기간에 맑은 영상이 없어요. 구름 임계값을 올리거나 기간을 넓혀보세요.")
        st.stop()

    # (1) 요약 통계를 숫자 카드로 — st.metric 이 큰 숫자 카드를 그려줍니다.
    st.subheader("📊 요약")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("분석 면적", f"{result['area_km2']:.1f} km²")
    c2.metric("평균 변화량", f"{result['mean_change']:+.3f}", help="+ 증가 / - 감소")
    c3.metric("식생 감소", f"{result['decrease_ratio']:.1f} %", delta="-개발·벌채 의심",
              delta_color="inverse")
    c4.metric("식생 증가", f"{result['increase_ratio']:.1f} %", delta="+회복·생장")

    # (2) 변화 지도 — geemap.foliumap 으로 그려야 streamlit 안에 임베드됩니다.
    st.subheader("🗺️ 변화 지도  (빨강=감소 · 파랑=증가)")
    m = geemap.Map()
    m.add_layer(result["image"], VIS, "NDVI 변화")
    m.center_object(result["roi"])
    m.add_colorbar(VIS, label="NDVI 변화량 (- 감소 / + 증가)")
    m.to_streamlit(height=520)   # ← folium 지도를 streamlit 화면에 끼워 넣는 한 줄

    # (3) 결과를 JSON 으로 내려받기 (이미지는 빼고 통계만)
    stats = {k: v for k, v in result.items() if k not in ("image", "roi")}
    st.download_button(
        "결과 통계 내려받기 (JSON)",
        data=json.dumps(stats, ensure_ascii=False, indent=2),
        file_name="change_result.json",
        mime="application/json",
    )
else:
    # 버튼을 누르기 전 안내 화면
    st.info("왼쪽에서 지역·기간·구름값을 정하고 **[② 분석 실행]** 을 누르세요.")
