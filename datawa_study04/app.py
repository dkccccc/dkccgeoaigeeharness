"""
datawa_study04 · 변화탐지 서비스 웹앱
3장(변화탐지)을 '쓸 만한 서비스'로 키운 누적 Streamlit 웹앱입니다.
사이드바에서 지역·이전/이후 기간·구름 임계값을 고르면, 두 시점의 NDVI를 빼서
'어디서 식생이 늘고 줄었는지'를 지도로 보여주고, 요약 통계를 카드로 띄우며,
영역을 격자로 나눈 셀별 평균 변화량을 GeoJSON/CSV 파일로 내려받게 합니다.

만든 순서: 프롬프트 4-1(구름 임계값+요약 통계 파라미터화)
        → 4-2(GeoJSON/CSV 다운로드 버튼) → 4-3(내려받은 파일 값 확인)

실행:  streamlit run app.py   → 브라우저가 열립니다.
(처음 한 번은 터미널에서  earthengine authenticate  로 인증)
"""

import csv
import io
import json

import ee
import geemap.foliumap as geemap
import pandas as pd
import streamlit as st

# 1) Earth Engine 초기화
#    사전에 터미널에서 'earthengine authenticate' 를 한 번 해두면 됩니다.
try:
    ee.Initialize()
except Exception:
    ee.Authenticate()
    ee.Initialize()

# 2) 웹앱 기본 설정
st.set_page_config(page_title="변화탐지 서비스", layout="wide")
st.title("🛰️ 변화탐지 서비스 웹앱")
st.caption("두 시점을 비교해 식생이 어디서 늘고 줄었는지 찾고, 결과를 파일로 내보냅니다")


# =====================================================================
# [1장에서 만든 것] 관심 지역(ROI) — 점을 반경만큼 키워 사각형으로
# =====================================================================
def make_roi(lon, lat, radius_km):
    """중심 좌표(lon, lat)를 반경(km)만큼 buffer 후 사각형으로 만든 ROI."""
    point = ee.Geometry.Point([lon, lat])
    # buffer는 미터 단위 → km를 1000배. 그 원의 bounds(사각형)를 ROI로 쓴다.
    return point.buffer(radius_km * 1000).bounds()


# =====================================================================
# [2장에서 만든 것] 그린 영역의 NDVI '이미지'를 계산해 반환
# =====================================================================
def ndvi_for_roi(roi, start, end, cloud_pct=20):
    """ROI의 NDVI 이미지를 계산해 반환한다. (2장 함수, 구름 임계값 추가)

    구름 적은 Sentinel-2(구름 cloud_pct% 미만, 가장 맑은 장면)에서 계산.
    반환값: 밴드 이름이 "NDVI" 인 ee.Image.
    """
    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(roi)
        .filterDate(start, end)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cloud_pct))  # 구름 임계값
        .sort("CLOUDY_PIXEL_PERCENTAGE")                              # 가장 맑은 순
    )
    image = collection.first().clip(roi)
    # NDVI = (근적외선 B8 - 빨강 B4) / (B8 + B4). 밴드 순서가 핵심.
    return image.normalizedDifference(["B8", "B4"]).rename("NDVI")


# 자연색(RGB)으로도 보여주기 위해 같은 조건의 원본 영상 한 장을 따로 골라 둔다
def s2_image(roi, start, end, cloud_pct=20):
    """ROI를 덮는 영상 중 구름 임계값 미만에서 가장 맑은 한 장을 골라 clip한다."""
    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(roi)
        .filterDate(start, end)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cloud_pct))
        .sort("CLOUDY_PIXEL_PERCENTAGE")
    )
    return collection.first().clip(roi)


# =====================================================================
# [3장에서 만든 것] 두 기간의 NDVI를 빼서 '변화 이미지'를 반환
# =====================================================================
def ndvi_change(roi, before, after, cloud_pct=20):
    """두 기간의 NDVI를 빼서 '변화 이미지'를 반환한다. (3장 함수)

    before, after: ("2023-01-01", "2023-12-31") 같은 (시작, 끝) 튜플.
    반환값: 밴드 이름이 "NDVI_change" 인 ee.Image.
            값이 + 면 식생 증가, - 면 식생 감소(개발·벌채 의심).
    """
    ndvi_before = ndvi_for_roi(roi, before[0], before[1], cloud_pct)
    ndvi_after = ndvi_for_roi(roi, after[0], after[1], cloud_pct)
    # after - before : 늘었으면 +, 줄었으면 -
    return ndvi_after.subtract(ndvi_before).rename("NDVI_change")


# =====================================================================
# [4-1] 변화탐지 서비스 — 변화 이미지 + 요약 통계를 dict로 반환
# 기간·지역·구름 임계값을 변수로 받아, 여러 곳에 반복해 쓸 수 있게 감쌌다.
# =====================================================================
def run_change_detection(roi, before, after, cloud_pct=20):
    """변화탐지 서비스 한 번 실행. 변화 이미지 + 요약 통계를 dict로 반환한다.

    반환값(dict):
      {
        "image":          ee.Image,   # 변화 이미지(밴드 "NDVI_change")
        "mean_change":    float,      # 영역 평균 변화량(+증가 / -감소)
        "decrease_ratio": float,      # 식생 감소(변화 < -0.1)한 면적 비율(%)
        "increase_ratio": float,      # 식생 증가(변화 > +0.1)한 면적 비율(%)
        "area_km2":       float,      # 분석 영역 넓이(km^2)
      }
    그 기간에 맑은 영상이 없으면 None 을 돌려준다.
    """
    # 1) 3장 변화 이미지 얻기
    change = ndvi_change(roi, before, after, cloud_pct)

    # 2) 요약 통계 — 영역 평균 변화량
    mean_stat = change.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=roi,
        scale=10,            # Sentinel-2 해상도 10m
        maxPixels=1e9,
    )
    mean_change = mean_stat.get("NDVI_change").getInfo()

    # 그 기간에 맑은 영상이 없으면 평균이 None 으로 온다 → 멈춘다
    if mean_change is None:
        return None

    # 3) 요약 통계 — 감소/증가 면적 비율
    #    변화가 -0.1 미만이면 '감소', +0.1 초과면 '증가'로 본다(노이즈 여유 0.1).
    THRESHOLD = 0.1
    pixel_area = ee.Image.pixelArea()              # 픽셀별 실제 면적(m^2)
    decreased = pixel_area.updateMask(change.lt(-THRESHOLD))
    increased = pixel_area.updateMask(change.gt(THRESHOLD))

    def area_m2(masked_area_image):
        stat = masked_area_image.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=roi,
            scale=10,
            maxPixels=1e9,
        )
        val = stat.get("area").getInfo()
        return float(val) if val is not None else 0.0

    total_m2 = roi.area(maxError=1).getInfo()       # 영역 전체 면적(m^2)
    decrease_ratio = area_m2(decreased) / total_m2 * 100 if total_m2 else 0.0
    increase_ratio = area_m2(increased) / total_m2 * 100 if total_m2 else 0.0

    return {
        "image": change,
        "mean_change": mean_change,
        "decrease_ratio": decrease_ratio,
        "increase_ratio": increase_ratio,
        "area_km2": total_m2 / 1e6,
    }


# =====================================================================
# [4-2] 결과를 격자(셀) 통계로 만들어 GeoJSON / CSV 문자열로 변환
# 영역을 grid_km 격자로 나눠 셀별 평균 변화량을 계산한다.
# (PRD의 '셀 단위 익스포트' — 한 덩어리 숫자가 아니라 칸칸이 남긴다.)
# =====================================================================
def build_grid_table(result, roi, grid_km=2):
    """영역을 grid_km 격자로 나눠 셀별 (중심좌표, 평균 변화량) 표를 만든다.

    반환값: [{"cell_id", "lon", "lat", "cell_change"}, ...] 리스트.
    """
    change = result["image"]

    # 영역을 정사각 격자(셀)로 자른다 — coveringGrid 가 셀 FeatureCollection 을 만든다
    cell_size_m = grid_km * 1000
    grid = roi.coveringGrid("EPSG:3857", cell_size_m).filterBounds(roi)

    # 각 셀의 평균 변화량을 'cell_change' 속성으로 붙인다
    cells = change.reduceRegions(
        collection=grid,
        reducer=ee.Reducer.mean().setOutputs(["cell_change"]),
        scale=10,
    )

    rows = []
    for i, feat in enumerate(cells.getInfo()["features"]):
        # 셀 중심 좌표(사각형 꼭짓점들의 평균)
        coords = feat["geometry"]["coordinates"][0]
        lon = sum(c[0] for c in coords[:-1]) / (len(coords) - 1)
        lat = sum(c[1] for c in coords[:-1]) / (len(coords) - 1)
        val = feat["properties"].get("cell_change")
        rows.append({
            "cell_id": i,
            "lon": round(lon, 5),
            "lat": round(lat, 5),
            "cell_change": round(val, 4) if val is not None else None,
        })
    return rows


def rows_to_csv(rows):
    """셀 표를 CSV 텍스트(엑셀로 바로 열림)로 만든다."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["cell_id", "lon", "lat", "cell_change"])
    writer.writeheader()
    for r in rows:
        writer.writerow(r)
    return buf.getvalue()


def rows_to_geojson(rows):
    """셀 표를 GeoJSON 텍스트(QGIS·지도 도구로 열림)로 만든다."""
    features = []
    for r in rows:
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [r["lon"], r["lat"]]},
            "properties": {"cell_id": r["cell_id"], "cell_change": r["cell_change"]},
        })
    return json.dumps({"type": "FeatureCollection", "features": features},
                      ensure_ascii=False, indent=2)


def filename_tag(before, after):
    """기간을 파일 이름에 넣어 헷갈리지 않게. 예: change_20230101_to_20240101"""
    return f"change_{before[0]}_to_{after[0]}".replace("-", "")


# =====================================================================
# 사이드바 — 학습자가 지역·기간·구름 임계값을 직접 고른다
# =====================================================================
st.sidebar.header("📍 지역 고르기")
lat = st.sidebar.number_input("중심 위도", value=37.5, format="%.4f")
lon = st.sidebar.number_input("중심 경도", value=127.0, format="%.4f")
radius_km = st.sidebar.slider("반경 (km)", min_value=1, max_value=30, value=5)

st.sidebar.header("📅 두 시점 기간")
before_start = st.sidebar.text_input("이전 시작일", value="2023-01-01")
before_end = st.sidebar.text_input("이전 종료일", value="2023-12-31")
after_start = st.sidebar.text_input("이후 시작일", value="2024-01-01")
after_end = st.sidebar.text_input("이후 종료일", value="2024-12-31")

st.sidebar.header("☁️ 구름 임계값")
cloud_pct = st.sidebar.slider("구름 % 미만만 사용", min_value=5, max_value=60, value=20,
                              help="낮추면 맑은 영상만, 영상이 없으면 올려보세요.")

st.sidebar.header("👁️ 보기 모드")
view_mode = st.sidebar.radio("지도에 무엇을 볼까요",
                             ["변화 (감소/증가)", "NDVI 식생지도", "자연색"])

st.sidebar.header("📦 내보내기")
grid_km = st.sidebar.slider("격자 크기 (km)", min_value=1, max_value=10, value=2,
                            help="작을수록 셀이 촘촘해집니다.")

run = st.sidebar.button("분석 / 보기", type="primary")


# =====================================================================
# 버튼을 누르면: 변화탐지 실행 → 지도 + 요약 카드 + 다운로드 버튼
# =====================================================================
if run:
    roi = make_roi(lon, lat, radius_km)
    before = (before_start, before_end)
    after = (after_start, after_end)

    with st.spinner("위성영상을 불러와 변화를 계산하는 중..."):
        result = run_change_detection(roi, before, after, cloud_pct)

    if result is None:
        st.error("그 기간에 맑은 영상이 없어요. 구름 임계값을 올리거나 기간을 넓혀보세요. ☁️")
        st.stop()

    # --- (4-1) 요약 통계를 st.metric 카드로 ---
    st.subheader("📊 요약")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("평균 변화량", f"{result['mean_change']:+.3f}", help="+ 증가 / - 감소")
    c2.metric("식생 감소 면적", f"{result['decrease_ratio']:.1f} %")
    c3.metric("식생 증가 면적", f"{result['increase_ratio']:.1f} %")
    c4.metric("분석 영역", f"{result['area_km2']:.1f} km²")

    # --- 보기 모드에 따라 지도에 다른 레이어를 올린다 ---
    m = geemap.Map()
    if view_mode == "변화 (감소/증가)":
        vis = {"min": -0.3, "max": 0.3,
               "palette": ["#d73027", "#ffffff", "#1a9850"]}  # 감소(빨강)→흰→증가(초록)
        m.add_layer(result["image"], vis, "NDVI 변화")
        m.add_colorbar(vis, label="NDVI 변화량 (- 감소 / + 증가)")
    elif view_mode == "NDVI 식생지도":
        ndvi = ndvi_for_roi(roi, after[0], after[1], cloud_pct)  # 이후 시점 NDVI
        vis = {"min": -0.2, "max": 0.8,
               "palette": ["#a52a2a", "#ffffff", "#228b22"]}  # 갈색→흰→초록
        m.add_layer(ndvi, vis, "NDVI 식생지도 (이후 시점)")
        m.add_colorbar(vis, label="NDVI (식생지수)")
    else:  # 자연색
        image = s2_image(roi, after[0], after[1], cloud_pct)
        m.add_layer(image, {"bands": ["B4", "B3", "B2"], "min": 0, "max": 3000},
                    "자연색 (이후 시점)")
    m.center_object(roi)
    m.to_streamlit(height=600)

    # --- (4-2) 격자 셀 통계 → GeoJSON/CSV 다운로드 버튼 ---
    st.subheader("📦 결과 내보내기 (셀 단위)")
    with st.spinner("영역을 격자로 나눠 셀별 통계를 만드는 중..."):
        rows = build_grid_table(result, roi, grid_km)

    if not rows:
        st.warning("격자 셀이 비었어요. 반경을 키우거나 격자 크기를 줄여보세요.")
    else:
        st.caption(f"영역을 {grid_km}km 격자로 나눠 셀 {len(rows)}개의 평균 변화량을 계산했습니다.")
        # 표로 미리 보기 (pandas)
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, height=240)

        tag = filename_tag(before, after)
        d1, d2 = st.columns(2)
        d1.download_button(
            "⬇️ CSV 내려받기 (엑셀)",
            data=rows_to_csv(rows).encode("utf-8-sig"),
            file_name=f"{tag}.csv",
            mime="text/csv",
        )
        d2.download_button(
            "⬇️ GeoJSON 내려받기 (QGIS)",
            data=rows_to_geojson(rows).encode("utf-8"),
            file_name=f"{tag}.geojson",
            mime="application/geo+json",
        )
        st.info("내려받은 파일을 엑셀·QGIS로 열어, 가장 많이 줄어든 셀 좌표가 "
                "실제 개발지·벌채지 근처인지 눈으로 대보세요.")
else:
    st.info("⬅️ 왼쪽 사이드바에서 지역·기간·구름 임계값을 고르고 [분석 / 보기]를 누르세요.")
