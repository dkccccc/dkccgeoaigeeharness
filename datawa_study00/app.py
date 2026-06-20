"""
datawa_study00 · 위성영상 한 장 띄우는 웹앱
원격탐사 연구자의 '첫 바이브 코딩' 결과물.
Claude Code에게 일상 언어로 시켜서 만든 가장 작은 Streamlit 웹앱입니다.

실행:  streamlit run app.py   → 브라우저가 열립니다.
(처음 한 번은 터미널에서  earthengine authenticate  로 인증)
"""

import ee
import geemap.foliumap as geemap
import streamlit as st

# 1) Earth Engine 초기화
#    사전에 터미널에서 'earthengine authenticate' 를 한 번 해두면 됩니다.
try:
    ee.Initialize()
except Exception:
    ee.Authenticate()
    ee.Initialize()

# 2) 웹앱 기본 설정
st.set_page_config(page_title="위성영상 한 장", layout="wide")
st.title("🛰️ 위성영상 한 장 띄우기")
st.caption("Claude Code에게 말해서 만든 첫 웹앱")

# 3) 관심 지역(AOI): 서울 부근
center = [37.5, 127.0]  # [위도, 경도]
seoul = ee.Geometry.Point([center[1], center[0]])

# 4) 구름 적은 최근 Sentinel-2 한 장 고르기
image = (
    ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
    .filterBounds(seoul)                       # 서울을 덮는 영상만
    .filterDate("2024-01-01", "2024-12-31")    # 2024년 안에서
    .sort("CLOUDY_PIXEL_PERCENTAGE")           # 구름 적은 순
    .first()                                   # 가장 맑은 한 장
)
vis = {"bands": ["B4", "B3", "B2"], "min": 0, "max": 3000}  # 자연색(RGB)

# 5) 지도 웹앱에 띄우기 — 브라우저에 바로 보입니다
m = geemap.Map(center=center, zoom=11)
m.add_layer(image, vis, "Sentinel-2 (가장 맑은 한 장)")
m.to_streamlit(height=600)

st.info("서울 부근의 2024년 가장 맑은 위성영상입니다. 이 한 장이 모든 실습의 출발점이에요.")
