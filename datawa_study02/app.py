"""
datawa_study02 · NDVI 식생지도 웹앱
1장 뷰어(사이드바로 지역 골라 영상 보기)에 'NDVI 식생지도'를 더한 누적 앱입니다.
보기 모드를 고르면 자연색(RGB) 또는 NDVI 색지도로 같은 영역을 볼 수 있습니다.

실행:  streamlit run app.py   → 브라우저가 열립니다.
(처음 한 번은 터미널에서  earthengine authenticate  로 인증)

[경계면 — 3장이 이 파일의 ndvi_for_roi 를 재사용합니다]
핵심은 아래 ndvi_for_roi(roi, start, end) 함수입니다.
이 함수는 NDVI '이미지'(ee.Image, 밴드 이름 "NDVI") 하나를 깔끔히 '반환'합니다.
3장 변화탐지는 이 함수를 두 시점에 각각 호출해
    before = ndvi_for_roi(roi, "2023-01-01", "2023-12-31")
    after  = ndvi_for_roi(roi, "2024-01-01", "2024-12-31")
    change = after.subtract(before)   # 두 NDVI를 빼서 변화량을 구함
처럼 쓸 것입니다.
"""

import branca.colormap as bcm
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


# GEE 이미지를 folium 지도에 올리는 헬퍼
# ee 이미지를 '타일 URL'로 바꿔(getMapId) folium 타일 레이어로 추가한다.
def add_ee_layer(fmap, ee_image, vis, name):
    mapid = ee_image.getMapId(vis)
    folium.TileLayer(
        tiles=mapid["tile_fetcher"].url_format,
        attr="Google Earth Engine",
        name=name,
        overlay=True,
        control=True,
    ).add_to(fmap)


# 2) 웹앱 기본 설정
st.set_page_config(page_title="NDVI 식생지도", layout="wide")
st.title("🌳 NDVI 식생지도 웹앱")
st.caption("1장 뷰어에 식생지도(NDVI)를 더한 누적 앱")


# 3) 누적: 사이드바로 지역을 고른다 (1장 뷰어에서 이어짐)
with st.sidebar:
    st.header("관심 지역 고르기")
    lon = st.number_input("경도(longitude)", value=127.0, format="%.4f")
    lat = st.number_input("위도(latitude)", value=37.5, format="%.4f")
    radius_km = st.slider("반경(km)", min_value=1, max_value=30, value=10)
    start = st.text_input("시작일", value="2024-01-01")
    end = st.text_input("종료일", value="2024-12-31")

    st.divider()
    # 추가: 보기 모드 (1장은 자연색만, 2장에서 NDVI를 더한다)
    mode = st.radio("보기 모드", ["자연색", "NDVI"])


# 4) 누적: 사이드바 좌표/반경으로 관심 영역(ROI)을 만든다
def make_roi(lon, lat, radius_km):
    """중심 좌표(lon, lat)에서 반경 radius_km 인 사각형 영역을 만든다."""
    point = ee.Geometry.Point([lon, lat])
    # 미터 단위로 버퍼를 준 뒤 사각형(bounds)으로 — 보기 좋게 네모난 영역이 된다
    return point.buffer(radius_km * 1000).bounds()


# 5) 누적: 영역의 구름 적은(20% 미만) 가장 맑은 S2 한 장을 고른다 (1장 뷰어)
def clearest_s2(roi, start, end):
    """영역(roi)에서 구름 20% 미만, 그중 가장 맑은 Sentinel-2 한 장을 반환한다."""
    return (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(roi)
        .filterDate(start, end)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))  # 구름 20% 미만만
        .sort("CLOUDY_PIXEL_PERCENTAGE")                       # 가장 맑은 순
        .first()
        .clip(roi)                                            # 영역 밖은 잘라낸다
    )


# 6) 추가: 영역의 NDVI '이미지'를 계산해 반환한다 (프롬프트 2-1)
def ndvi_for_roi(roi, start, end):
    """영역(roi)의 NDVI 이미지를 계산해 '반환'한다.

    구름 적은 Sentinel-2(가장 맑은 한 장)에서 계산한다.
    반환값: 밴드 이름이 "NDVI" 인 ee.Image (지도에 그리지는 않음).

    NDVI = (근적외선 - 빨강) / (근적외선 + 빨강)
    Sentinel-2: B8 = 근적외선(NIR), B4 = 빨강(Red). 순서가 핵심.

    [3장 재사용] 3장은 이 함수를 두 시점에 호출해 NDVI를 빼서 변화를 구한다.
    """
    image = clearest_s2(roi, start, end)
    ndvi = image.normalizedDifference(["B8", "B4"]).rename("NDVI")
    return ndvi   # 이미지만 반환 — 그리는 일은 지도 쪽에서 한다


# 7) 지도 웹앱에 띄우기
center = [lat, lon]            # folium 은 [위도, 경도] 순서
roi = make_roi(lon, lat, radius_km)
m = folium.Map(location=center, zoom_start=11)

if mode == "자연색":
    # 1장과 동일: 구름 적은 가장 맑은 한 장을 자연색(RGB)으로
    image = clearest_s2(roi, start, end)
    vis = {"bands": ["B4", "B3", "B2"], "min": 0, "max": 3000}  # 자연색(RGB)
    add_ee_layer(m, image, vis, "Sentinel-2 자연색")
else:
    # 추가: NDVI 색지도 — 낮음(갈색) → 중간(흰) → 높음(초록)
    ndvi = ndvi_for_roi(roi, start, end)
    vis = {
        "min": -0.2,
        "max": 0.8,
        "palette": ["#a52a2a", "#ffffff", "#228b22"],  # 갈색 → 흰 → 초록
    }
    add_ee_layer(m, ndvi, vis, "NDVI 식생지도")
    # 범례(colorbar): 색이 무슨 값을 뜻하는지 보여준다 — 이 장의 핵심
    bcm.LinearColormap(
        colors=vis["palette"],
        vmin=vis["min"],
        vmax=vis["max"],
        caption="NDVI (식생지수)",
    ).add_to(m)

folium.LayerControl().add_to(m)
st_folium(m, width=None, height=600, returned_objects=[])

if mode == "자연색":
    st.info("구름 적은 가장 맑은 한 장을 자연색으로 보고 있어요. 사이드바에서 보기 모드를 'NDVI'로 바꿔보세요.")
else:
    st.info("초록일수록 식생이 무성한 곳입니다. 물·도심·맨땅은 갈색~흰색으로 나옵니다.")
