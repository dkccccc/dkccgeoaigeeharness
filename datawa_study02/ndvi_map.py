"""
datawa_study02 · NDVI 식생지도 앱
그린 영역의 식생 상태(NDVI)를 갈색~초록 색지도로 보여줍니다.
주피터/코랩에서 셀 단위로 실행하세요.

만든 순서: 프롬프트 2-1(뼈대·NDVI 계산) → 2-2(색지도+범례) → 2-3(점검·물 vs 숲)

[경계면 — 3장이 이 파일을 재사용합니다]
핵심은 아래 `ndvi_for_roi(roi, start, end)` 함수입니다.
이 함수는 NDVI '이미지'(ee.Image, 밴드 이름 "NDVI") 하나를 깔끔히 '반환'합니다.
3장 변화탐지는 이 함수를 두 시점에 각각 호출해
    before = ndvi_for_roi(roi, "2023-01-01", "2023-12-31")
    after  = ndvi_for_roi(roi, "2024-01-01", "2024-12-31")
    change = after.subtract(before)   # 두 NDVI를 빼서 변화량을 구함
처럼 쓸 것입니다. 그래서 이 함수는 지도에 그리지 않고 '이미지만' 반환합니다.
"""

import ee
import geemap

ee.Authenticate()   # 처음 한 번 (브라우저 인증)
ee.Initialize()

# 1장과 동일하게 지도를 띄웁니다. 왼쪽 도구로 사각형을 그리세요.
m = geemap.Map(center=[37.5, 127.0], zoom=10)
m  # 노트북에서 이 줄이 지도를 보여줍니다.


# --- 뼈대: 그린 영역의 NDVI '이미지'를 계산해 반환한다 (프롬프트 2-1) ---
def ndvi_for_roi(roi, start="2024-01-01", end="2024-12-31"):
    """그린 영역(roi)의 NDVI 이미지를 계산해 '반환'한다.

    구름 적은 Sentinel-2(구름 20% 미만, 가장 맑은 장면)에서 계산한다.
    반환값: 밴드 이름이 "NDVI" 인 ee.Image (지도에 그리지는 않음).

    [3장 재사용] 3장은 이 함수를 두 시점에 호출해 NDVI를 빼서 변화를 구한다.
    """
    if roi is None:
        print("먼저 지도에서 영역을 그린 뒤 다시 실행하세요. (m.user_roi 가 비어 있어요)")
        return None

    # 1장과 같은 구름 필터: 구름 적은 가장 맑은 한 장면을 고른다
    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(roi)
        .filterDate(start, end)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))  # 구름 20% 미만만
        .sort("CLOUDY_PIXEL_PERCENTAGE")                       # 가장 맑은 순
    )

    image = collection.first().clip(roi)   # 영역 밖은 잘라낸다

    # NDVI = (근적외선 - 빨강) / (근적외선 + 빨강)
    # Sentinel-2: B8 = 근적외선(NIR), B4 = 빨강(Red). 순서가 핵심.
    ndvi = image.normalizedDifference(["B8", "B4"]).rename("NDVI")
    return ndvi   # 이미지만 반환 — 그리는 일은 show_ndvi 가 한다


# --- 기능: 반환된 NDVI를 색지도+범례로 지도에 올린다 (프롬프트 2-2) ---
def show_ndvi(roi, start="2024-01-01", end="2024-12-31"):
    """ndvi_for_roi 로 NDVI를 구해 갈색~흰~초록 색지도로 지도에 올린다."""
    ndvi = ndvi_for_roi(roi, start, end)
    if ndvi is None:
        return

    # 색지도 설정: 낮음(갈색) → 중간(흰) → 높음(초록)
    vis = {
        "min": -0.2,
        "max": 0.8,
        "palette": ["#a52a2a", "#ffffff", "#228b22"],  # 갈색 → 흰 → 초록
    }

    m.add_layer(ndvi, vis, "NDVI 식생지도")
    m.center_object(roi)

    # 범례(colorbar): 색이 무슨 값을 뜻하는지 보여준다
    m.add_colorbar(vis, label="NDVI (식생지수)", layer_name="NDVI 식생지도")
    print("NDVI 색지도를 올렸어요. 초록일수록 식생이 많은 곳입니다.")


# 사용법: 위 지도에서 영역을 그린 뒤, 새 셀에서 실행
#   show_ndvi(m.user_roi)


# --- 점검: 값이 상식과 맞나? 물(낮음) vs 숲(높음) 비교 (프롬프트 2-3) ---
def compare_ndvi(roi, water_point, forest_point, start="2024-01-01", end="2024-12-31"):
    """물 지점과 숲 지점의 NDVI 평균을 뽑아 비교한다.

    water_point, forest_point: ee.Geometry.Point(경도, 위도).
    물은 낮게(0 근처/음수), 숲은 높게(0.6~0.9) 나오면 NDVI가 올바른 것.
    """
    ndvi = ndvi_for_roi(roi, start, end)
    if ndvi is None:
        return

    def mean_at(point):
        # 한 지점에서의 NDVI 평균값을 숫자로 뽑는다
        stat = ndvi.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=point,
            scale=10,            # Sentinel-2 해상도 10m
        )
        return stat.get("NDVI").getInfo()

    water = mean_at(water_point)
    forest = mean_at(forest_point)

    # 값이 안 잡히면(None) 영역 밖이거나 해당 지점에 영상이 없는 것
    if water is None or forest is None:
        print("지점에서 NDVI 값을 못 읽었어요. 좌표가 그린 영역(roi) '안'에 있는지 확인하세요.")
        return

    print(f"물 지점 NDVI  ≈ {water:.3f}  (낮을수록 정상: 0 근처/음수)")
    print(f"숲 지점 NDVI  ≈ {forest:.3f}  (높을수록 정상: 0.6~0.9)")
    if forest > water:
        print("정상입니다 — 숲이 물보다 NDVI가 높습니다.")
    else:
        print("이상해요 — 밴드 순서를 확인하세요. normalizedDifference(['B8','B4']) 가 맞습니다.")


# 사용법 예 (좌표는 여러분 영역 안의 강/호수, 숲으로 바꾸세요):
#   water  = ee.Geometry.Point(127.05, 37.52)   # 강 위의 한 점
#   forest = ee.Geometry.Point(127.10, 37.45)   # 숲 위의 한 점
#   compare_ndvi(m.user_roi, water, forest)
