"""
datawa_study00 · 위성영상 한 장 띄우는 웹앱
원격탐사 연구자의 '첫 바이브 코딩' 결과물.
Claude Code에게 일상 언어로 시켜서 만든 가장 작은 Streamlit 웹앱입니다.

지도는 folium(Leaflet)으로 그립니다 — Earth Engine 이미지를 ee.getMapId()로
타일 URL로 바꿔 folium 지도에 올립니다. (무거운 geemap 없이 가볍게)

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
st.set_page_config(page_title="위성영상 한 장", layout="wide")
st.title("🛰️ 위성영상 한 장 띄우기")
st.caption("Claude Code에게 말해서 만든 첫 웹앱")

# 4) 관심 지역(AOI): 서울 부근
center = [37.5, 127.0]  # [위도, 경도]
seoul = ee.Geometry.Point([center[1], center[0]])

# 5) 구름 적은 최근 Sentinel-2 한 장 고르기
image = (
    ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
    .filterBounds(seoul)                       # 서울을 덮는 영상만
    .filterDate("2024-01-01", "2024-12-31")    # 2024년 안에서
    .sort("CLOUDY_PIXEL_PERCENTAGE")           # 구름 적은 순
    .first()                                   # 가장 맑은 한 장
)
vis = {"bands": ["B4", "B3", "B2"], "min": 0, "max": 3000}  # 자연색(RGB)

# 6) folium 지도에 올려 브라우저에 표시
m = folium.Map(location=center, zoom_start=11)
add_ee_layer(m, image, vis, "Sentinel-2 (가장 맑은 한 장)")
folium.LayerControl().add_to(m)
st_folium(m, width=None, height=600)

st.info("서울 부근의 2024년 가장 맑은 위성영상입니다. 이 한 장이 모든 실습의 출발점이에요.")
