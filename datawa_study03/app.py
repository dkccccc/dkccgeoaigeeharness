"""
datawa_study03 · 미니 변화탐지 웹앱 (누적 앱 전체)
====================================================================
2장(자연색 / NDVI 보기) 위에 '두 시점 변화탐지' 를 더한 누적 Streamlit 웹앱.
사이드바에서 지역·기간을 정하고, 보기 모드(자연색 / NDVI / 변화)를 고르면
브라우저 지도에 바로 그려집니다.

만든 순서: 프롬프트 3-1(두 시점 NDVI 차분) → 3-2(변화 히트맵+범례) → 3-3(아는 변화지역 검증)

[경계면 — 2장에서 이어받고, 4장이 이 파일을 재사용합니다]
- 2장이 만든 make_roi / ndvi_for_roi(roi, start, end) 를 그대로 누적해 씁니다.
- 이 장의 심장은 아래 ndvi_change(roi, before, after) 입니다.
  반환값은 밴드 이름이 "NDVI_change" 인 ee.Image (= 이후 NDVI − 이전 NDVI).
  4장 서비스는 이 함수를 사용자가 고른 기간/지역으로 호출해 결과를 내보냅니다.

로컬 실행:
    pip install -r requirements.txt
    earthengine authenticate     # 처음 한 번만 (브라우저 로그인)
    streamlit run app.py
"""

import branca.colormap as bcm
import ee
import folium
import streamlit as st
from streamlit_folium import st_folium


# =====================================================================
# [0] Earth Engine 초기화
# 웹앱은 노트북처럼 브라우저 인증창을 띄울 수 없습니다. 그래서 미리 한 번
#   (터미널)  earthengine authenticate
# 로 인증해 둔 토큰으로 조용히 초기화만 합니다. 토큰이 없으면 인증을 시도합니다.
# =====================================================================

@st.cache_resource   # 초기화는 앱 수명 동안 한 번만
def init_ee():
    try:
        ee.Initialize()
    except Exception:
        ee.Authenticate()
        ee.Initialize()


# GEE 이미지를 folium 지도에 올리는 헬퍼 (0장과 동일)
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


# =====================================================================
# [2장에서 누적] 지역(ROI) 만들기 + 한 시점 NDVI 이미지 반환
# (2장 datawa_study02/app.py 와 같은 함수입니다. 한 파일로 돌도록 그대로 가져왔습니다.)
# =====================================================================

def make_roi(lon, lat, radius_km):
    """중심 좌표와 반경(km)으로 네모 영역(ee.Geometry)을 만든다. (2장과 동일)"""
    point = ee.Geometry.Point([lon, lat])
    # buffer(미터)로 원을 만든 뒤 그 외접 사각형(bounds)을 영역으로 쓴다.
    return point.buffer(radius_km * 1000).bounds()


def natural_color(roi, start, end, cloud_pct=20):
    """구름 적은 가장 맑은 Sentinel-2 한 장면의 자연색(RGB) 이미지를 반환한다. (2장과 동일)"""
    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(roi)
        .filterDate(start, end)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cloud_pct))  # 구름 적은 것만
        .sort("CLOUDY_PIXEL_PERCENTAGE")                             # 가장 맑은 순
    )
    return collection.first().clip(roi)   # 영역 밖은 잘라낸다


def ndvi_for_roi(roi, start, end, cloud_pct=20):
    """그린 영역(roi)의 NDVI 이미지를 계산해 '반환'한다. (2장 함수)

    구름 적은 가장 맑은 Sentinel-2 한 장면에서 계산한다.
    반환값: 밴드 이름이 "NDVI" 인 ee.Image (지도에 그리지는 않음).

    [3장 재사용] 3장 변화탐지는 이 함수를 '두 시점'에 각각 호출해 NDVI를 뺀다.
    """
    image = natural_color(roi, start, end, cloud_pct)
    # NDVI = (근적외선 B8 − 빨강 B4) / (B8 + B4). 밴드 순서가 핵심.
    return image.normalizedDifference(["B8", "B4"]).rename("NDVI")


# =====================================================================
# [3-1] 이 장의 심장 — 두 시점 NDVI를 빼서 '변화량 이미지'를 반환한다
# 새 영상을 다시 받지 않고, 2장 ndvi_for_roi 를 '두 번' 호출하는 게 핵심입니다.
# =====================================================================

def ndvi_change(roi, before, after, cloud_pct=20):
    """두 시점의 NDVI를 빼서 변화량 이미지를 '반환'한다.

    before, after: (시작일, 종료일) 날짜 튜플.
                   가짜 변화를 줄이려면 두 기간을 '같은 계절'로 맞추는 게 좋습니다.
    반환값: 밴드 이름이 "NDVI_change" 인 ee.Image.
        값 = 이후(after) NDVI − 이전(before) NDVI
        +  (양수, 초록) = 식생 증가     예) 농사 시작, 숲 회복
        0  (흰색)       = 변화 없음
        −  (음수, 빨강) = 식생 감소     예) 개발, 벌채, 산불

    [4장 재사용] 4장 서비스가 사용자 입력 기간/지역으로 이 함수를 호출한다.
    """
    before_ndvi = ndvi_for_roi(roi, before[0], before[1], cloud_pct)
    after_ndvi = ndvi_for_roi(roi, after[0], after[1], cloud_pct)
    # 두 NDVI를 뺀다 — 변화탐지의 가장 직관적인 방법.
    return after_ndvi.subtract(before_ndvi).rename("NDVI_change")


# =====================================================================
# [3-2] 변화량을 칠하는 발산형(diverging) 색 규칙
# 가운데(0=변화없음)가 흰색, 양끝이 빨강(감소)/초록(증가).
# min/max 를 0 기준 '대칭'(-0.3 ~ +0.3)으로 두는 것이 발산형의 핵심입니다.
# =====================================================================

NATURAL_VIS = {"bands": ["B4", "B3", "B2"], "min": 0, "max": 3000}   # 자연색(RGB)
NDVI_VIS = {"min": -0.2, "max": 0.8, "palette": ["#a52a2a", "#ffffff", "#228b22"]}  # 갈→흰→초록
CHANGE_VIS = {
    "min": -0.3, "max": 0.3,
    "palette": ["#d73027", "#ffffff", "#1a9850"],  # 감소(빨강) → 흰 → 증가(초록)
}


# =====================================================================
# 화면 — 사이드바 입력 + 보기 모드별 지도
# Streamlit 은 위에서 아래로 코드를 읽으며 화면을 그립니다.
# =====================================================================

st.set_page_config(page_title="미니 변화탐지", page_icon="🛰️", layout="wide")
init_ee()

st.title("🛰️ 미니 변화탐지 웹앱")
st.caption("지역과 두 기간을 정하고 보기 모드를 고르면, 식생이 줄거나 는 곳을 지도로 보여줍니다.")

# --- 왼쪽 사이드바: 입력값 (남이 바꿔 쓰는 부분) ---
with st.sidebar:
    st.header("① 지역")
    lat = st.number_input("중심 위도", value=37.50, format="%.4f")
    lon = st.number_input("중심 경도", value=127.00, format="%.4f")
    radius_km = st.slider("반경 (km)", min_value=1, max_value=15, value=3)

    st.header("② 기간 (두 시점)")
    st.caption("같은 계절끼리 비교하면 가짜 변화가 줄어요.")
    st.subheader("이전 기간")
    before = (
        str(st.date_input("이전 시작", value=None, key="b0",
                          format="YYYY-MM-DD") or "2023-01-01"),
        str(st.date_input("이전 끝", value=None, key="b1",
                          format="YYYY-MM-DD") or "2023-12-31"),
    )
    st.subheader("이후 기간")
    after = (
        str(st.date_input("이후 시작", value=None, key="a0",
                          format="YYYY-MM-DD") or "2024-01-01"),
        str(st.date_input("이후 끝", value=None, key="a1",
                          format="YYYY-MM-DD") or "2024-12-31"),
    )

    cloud_pct = st.slider("구름 임계값 (%)", min_value=5, max_value=60, value=20,
                          help="낮출수록 맑은 영상만. 결과가 비면 높여보세요.")

    st.header("③ 보기 모드")
    # 2장(자연색·NDVI)에 3장 '변화' 를 더했습니다.
    mode = st.radio("무엇을 볼까요?", ["자연색", "NDVI", "변화"], index=2)


roi = make_roi(lon, lat, radius_km)

# --- 보기 모드에 따라 다른 이미지를 그립니다 ---
try:
    # 사이드바 중심좌표로 지도 중심을 잡는다 (geemap center_object 대체)
    m = folium.Map(location=[lat, lon], zoom_start=12)

    if mode == "자연색":
        # 이후 기간의 자연색 영상 한 장 (눈으로 지형 확인용)
        image = natural_color(roi, after[0], after[1], cloud_pct)
        add_ee_layer(m, image, NATURAL_VIS, "자연색 (이후 기간)")
        st.subheader("🌍 자연색  (이후 기간의 가장 맑은 한 장)")

    elif mode == "NDVI":
        # 이후 기간의 NDVI 색지도 (식생 분포)
        ndvi = ndvi_for_roi(roi, after[0], after[1], cloud_pct)
        add_ee_layer(m, ndvi, NDVI_VIS, "NDVI (이후 기간)")
        bcm.LinearColormap(
            colors=NDVI_VIS["palette"], vmin=NDVI_VIS["min"], vmax=NDVI_VIS["max"],
            caption="NDVI (식생지수)",
        ).add_to(m)
        st.subheader("🌱 NDVI 식생지도  (초록일수록 식생 많음)")

    else:  # "변화" — 이 장의 핵심
        # 두 시점 NDVI 차분 → 발산형 히트맵
        change = ndvi_change(roi, before, after, cloud_pct)
        add_ee_layer(m, change, CHANGE_VIS, "NDVI 변화 (이후 − 이전)")
        # 발산형 변화 히트맵 범례 (감소=빨강 / 0=흰 / 증가=초록)
        bcm.LinearColormap(
            colors=CHANGE_VIS["palette"], vmin=CHANGE_VIS["min"], vmax=CHANGE_VIS["max"],
            caption="NDVI 변화량 (− 감소 / + 증가)",
        ).add_to(m)
        st.subheader("🔥 변화 히트맵  (빨강=식생 감소 · 초록=식생 증가)")
        st.caption("개발·벌채는 빨강, 농사 시작·숲 회복은 초록, 변화 없는 곳은 흰색에 가깝습니다.")

    folium.LayerControl().add_to(m)
    st_folium(m, width=None, height=560, returned_objects=[])   # ← folium 지도를 streamlit 화면에 끼워 넣는다

except Exception as e:
    st.error("그 기간에 맑은 영상이 없거나 영역이 너무 작을 수 있어요. "
             "구름 임계값을 올리거나 기간을 넓혀 보세요.")
    st.exception(e)
