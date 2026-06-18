"""
datawa_study01 · 위성영상 뷰어
지도에서 영역을 그리면, 그 영역의 구름 적은 최근 Sentinel-2 영상을 보여줍니다.
주피터/코랩에서 셀 단위로 실행하세요.

만든 순서: 프롬프트 1-1(뼈대) → 1-2(기능) → 1-3(점검)
"""

import ee
import geemap

ee.Authenticate()   # 처음 한 번
ee.Initialize()

# --- 뼈대: 지도를 띄우고, 영역을 그릴 수 있게 한다 (프롬프트 1-1) ---
m = geemap.Map(center=[37.5, 127.0], zoom=10)
m  # 노트북에서 이 줄이 지도를 보여줍니다. 왼쪽 도구로 사각형을 그리세요.


# --- 기능: 그린 영역의 구름 적은 최근 영상 보여주기 (프롬프트 1-2) ---
def show_for_roi(roi, start="2024-01-01", end="2024-12-31"):
    """그린 영역(roi)에 대해 구름 적은 최근 Sentinel-2 영상을 지도에 올린다."""
    if roi is None:
        print("먼저 지도에서 영역을 그린 뒤 다시 실행하세요. (m.user_roi 가 비어 있어요)")
        return

    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(roi)
        .filterDate(start, end)
        # 구름 많은 영상은 걸러낸다: 구름 픽셀 20% 미만만
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))
        .sort("CLOUDY_PIXEL_PERCENTAGE")
    )

    image = collection.first().clip(roi)   # 영역 밖은 잘라낸다
    vis = {"bands": ["B4", "B3", "B2"], "min": 0, "max": 3000}

    m.add_layer(image, vis, "내 영역의 위성영상")
    m.center_object(roi)
    print("영상을 올렸어요. 지도를 확인하세요.")


# 사용법: 위 지도에서 영역을 그린 뒤, 새 셀에서 실행
#   show_for_roi(m.user_roi)


# --- 점검: 구름 필터가 정말 동작하나? (프롬프트 1-3) ---
def compare_cloud_filter(roi, start="2024-01-01", end="2024-12-31"):
    """필터 적용 전(가장 흐린 영상) vs 후(가장 맑은 영상)를 비교해 본다."""
    if roi is None:
        print("먼저 영역을 그리세요.")
        return
    base = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(roi)
        .filterDate(start, end)
    )
    vis = {"bands": ["B4", "B3", "B2"], "min": 0, "max": 3000}
    cloudy = base.sort("CLOUDY_PIXEL_PERCENTAGE", False).first().clip(roi)  # 가장 흐림
    clear = base.sort("CLOUDY_PIXEL_PERCENTAGE").first().clip(roi)          # 가장 맑음
    m.add_layer(cloudy, vis, "필터 전: 가장 흐린 영상")
    m.add_layer(clear, vis, "필터 후: 가장 맑은 영상")
    print("두 레이어를 켜고 끄며 비교하세요. 필터가 맑은 영상을 고르는지 눈으로 확인합니다.")
