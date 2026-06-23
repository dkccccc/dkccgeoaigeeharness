"""
datawa_study01 · 위성영상 뷰어 웹앱
사이드바에서 지역(위도·경도·반경)을 고르면, 그 지역의 구름 적은
가장 맑은 Sentinel-2 영상을 브라우저 지도에 보여주는 Streamlit 웹앱입니다.

0장(영상 한 장)을 키운 결과물입니다.
만든 순서: 프롬프트 1-1(뼈대) → 1-2(기능) → 1-3(점검)

실행:  streamlit run app.py   → 브라우저가 열립니다.
(처음 한 번은 터미널에서  earthengine authenticate  로 인증)
"""

import ee
import folium
import streamlit as st
from streamlit_folium import st_folium

# 1) Earth Engine 초기화
#    사전에 터미널에서 'earthengine authenticate' 를 한 번 해두면 됩니다.
try:
    ee.Initialize()
except Exception:
    ee.Authenticate()
    ee.Initialize()


# 2) GEE 이미지를 folium 지도에 올리는 헬퍼
#    ee 이미지를 '타일 URL'로 바꿔(getMapId) folium 타일 레이어로 추가한다.
def add_ee_layer(fmap, ee_image, vis, name):
    mapid = ee_image.getMapId(vis)
    folium.TileLayer(
        tiles=mapid["tile_fetcher"].url_format,
        attr="Google Earth Engine",
        name=name,
        overlay=True,
        control=True,
    ).add_to(fmap)


# 3) 웹앱 기본 설정
st.set_page_config(page_title="위성영상 뷰어", layout="wide")
st.title("🛰️ 위성영상 뷰어 웹앱")
st.caption("사이드바에서 지역을 고르면 그 지역의 맑은 위성영상을 보여줍니다")


# 4) 관심 지역(ROI) 만들기 — 점을 반경만큼 키워 사각형으로
def make_roi(lon, lat, radius_km):
    """중심 좌표(lon, lat)를 반경(km)만큼 buffer 후 사각형으로 만든 ROI."""
    point = ee.Geometry.Point([lon, lat])
    # buffer는 미터 단위 → km를 1000배. 그 원의 bounds(사각형)를 ROI로 쓴다.
    return point.buffer(radius_km * 1000).bounds()


# 5) ROI에 대해 구름 적은 가장 맑은 Sentinel-2 한 장 고르기
def s2_image(roi, start, end):
    """ROI를 덮는 영상 중 구름 20% 미만에서 가장 맑은 한 장을 골라 clip한다."""
    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(roi)                                   # ROI를 덮는 영상만
        .filterDate(start, end)                              # 기간 안에서
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))  # 구름 많은 건 걸러냄
        .sort("CLOUDY_PIXEL_PERCENTAGE")                     # 구름 적은 순
    )
    return collection.first().clip(roi)                      # 가장 맑은 한 장, ROI로 자름


# 6) 사이드바 — 학습자가 지역과 기간을 직접 고른다
st.sidebar.header("📍 지역 고르기")
lat = st.sidebar.number_input("중심 위도", value=37.5, format="%.4f")
lon = st.sidebar.number_input("중심 경도", value=127.0, format="%.4f")
radius_km = st.sidebar.slider("반경 (km)", min_value=1, max_value=30, value=5)

st.sidebar.header("📅 기간 (선택)")
start = st.sidebar.text_input("시작일", value="2024-01-01")
end = st.sidebar.text_input("종료일", value="2024-12-31")

run = st.sidebar.button("분석 / 보기", type="primary")

# 7) 버튼을 누르면 지도에 영상 표시
if run:
    roi = make_roi(lon, lat, radius_km)
    image = s2_image(roi, start, end)
    vis = {"bands": ["B4", "B3", "B2"], "min": 0, "max": 3000}  # 자연색(RGB)

    # 사이드바에서 고른 중심 좌표로 지도를 맞춘다 (lat, lon 순서)
    m = folium.Map(location=[lat, lon], zoom_start=12)
    add_ee_layer(m, image, vis, "Sentinel-2 (가장 맑은 한 장)")
    folium.LayerControl().add_to(m)
    st_folium(m, width=None, height=600, returned_objects=[])

    st.success(
        f"위도 {lat}, 경도 {lon} 반경 {radius_km}km 영역의 "
        f"{start}~{end} 중 가장 맑은 영상입니다."
    )
else:
    st.info("⬅️ 왼쪽 사이드바에서 지역을 고르고 [분석 / 보기]를 누르세요.")
