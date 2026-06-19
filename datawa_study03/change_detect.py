"""
datawa_study03 · 미니 변화탐지 앱
두 시점(작년 vs 올해)의 NDVI를 빼서, 식생이 어디서 늘고 줄었는지를
빨강(감소)~흰색(변화없음)~초록(증가) 발산형 색지도로 보여줍니다.
주피터/코랩에서 셀 단위로 실행하세요.

만든 순서: 프롬프트 3-1(뼈대·두 시점 NDVI 차분) → 3-2(변화 히트맵+범례) → 3-3(점검·임계값/통계)

[경계면 — 2장에서 이어받고, 4장이 이 파일을 재사용합니다]
- 2장(datawa_study02)이 만든 `ndvi_for_roi(roi, start, end)` 를 '두 번' 호출해 차분합니다.
- 핵심 함수는 아래 `ndvi_change(roi, before, after)` 입니다.
  반환값은 밴드 이름이 "NDVI_change" 인 ee.Image (지도에 그리지 않고 '이미지만' 반환).
  4장 서비스는 이 함수를 사용자가 고른 기간/지역으로 호출하고, 결과를 내보냅니다.
"""

import ee
import geemap

ee.Authenticate()   # 처음 한 번 (브라우저 인증). 이미 했으면 건너뛰어도 됩니다.
ee.Initialize()

# 1·2장과 동일하게 지도를 띄웁니다. 왼쪽 도구로 사각형을 그리세요.
m = geemap.Map(center=[37.5, 127.0], zoom=10)
m  # 노트북에서 이 줄이 지도를 보여줍니다.


# ============================================================
# 2장과 동일한 함수 — 그린 영역의 NDVI '이미지'를 반환한다.
# (datawa_study02/ndvi_map.py 의 ndvi_for_roi 와 같은 함수입니다.
#  3장이 자체 포함 스크립트라 여기에 그대로 다시 넣었습니다.)
# ============================================================
def ndvi_for_roi(roi, start="2024-01-01", end="2024-12-31"):
    """그린 영역(roi)의 NDVI 이미지를 계산해 '반환'한다. (2장과 동일)

    구름 적은 Sentinel-2(구름 20% 미만, 가장 맑은 장면)에서 계산한다.
    반환값: 밴드 이름이 "NDVI" 인 ee.Image (지도에 그리지는 않음).
    """
    if roi is None:
        print("먼저 지도에서 영역을 그린 뒤 다시 실행하세요. (m.user_roi 가 비어 있어요)")
        return None

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
    return ndvi


# ============================================================
# 3-1 뼈대: 두 시점 NDVI를 빼서 '변화량 이미지'를 반환한다
# ============================================================
def ndvi_change(roi, before=("2023-01-01", "2023-12-31"),
                after=("2024-01-01", "2024-12-31")):
    """두 시점의 NDVI를 빼서 변화량 이미지를 '반환'한다.

    before, after: (start, end) 날짜 튜플. 기본값은 작년(2023) vs 올해(2024).
                   가짜 변화를 줄이려면 두 기간을 '같은 계절'로 맞추는 게 좋습니다.
    반환값: 밴드 이름이 "NDVI_change" 인 ee.Image.
        값 = after의 NDVI − before의 NDVI
        +  (양수, 초록) = 식생 증가     예) 농사 시작, 숲 회복
        0  (흰색)       = 변화 없음
        −  (음수, 빨강) = 식생 감소     예) 개발, 벌채, 산불

    [4장 재사용] 4장 서비스는 사용자가 고른 기간/지역으로 이 함수를 호출한다.
    """
    if roi is None:
        print("먼저 지도에서 영역을 그린 뒤 다시 실행하세요. (m.user_roi 가 비어 있어요)")
        return None

    # 2장 함수를 '두 번' 호출 — 핵심은 이 두 줄입니다.
    before_ndvi = ndvi_for_roi(roi, before[0], before[1])
    after_ndvi = ndvi_for_roi(roi, after[0], after[1])
    if before_ndvi is None or after_ndvi is None:
        return None

    # 두 NDVI를 뺀다. 이게 변화탐지의 가장 직관적인 방법.
    change = after_ndvi.subtract(before_ndvi).rename("NDVI_change")
    return change   # 이미지만 반환 — 그리는 일은 show_change 가 한다


# ============================================================
# 3-2 기능: 변화량 이미지를 '발산형 색지도'로 지도에 올린다
# ============================================================
def show_change(roi, before=("2023-01-01", "2023-12-31"),
                after=("2024-01-01", "2024-12-31"), vmax=0.3):
    """ndvi_change 로 변화량을 구해, 빨강~흰~초록 발산형 색지도로 지도에 올린다.

    vmax: 색지도의 끝 값(기본 0.3). 변화량은 보통 −0.3~+0.3 사이에 몰려 있다.
          전부 흰색에 가깝게 나오면 vmax 를 0.2 처럼 줄여 대비를 키우세요.
    """
    change = ndvi_change(roi, before, after)
    if change is None:
        return

    # 발산형(diverging) 색지도: 가운데(0=변화없음)가 흰색, 양끝이 빨강/초록.
    #   min(감소 끝) = 빨강,  0 = 흰색,  max(증가 끝) = 초록
    # min/max 를 0 기준으로 '대칭'(-vmax ~ +vmax)으로 두는 것이 발산형의 핵심입니다.
    vis = {
        "min": -vmax,
        "max": vmax,
        "palette": ["#d73027", "#ffffff", "#1a9850"],  # 빨강 → 흰 → 초록
    }

    m.add_layer(change, vis, "NDVI 변화 (after − before)")
    m.center_object(roi)

    # 범례(colorbar): 빨강=감소, 흰=변화없음, 초록=증가
    m.add_colorbar(vis, label="NDVI 변화량 (− 감소 / + 증가)",
                   layer_name="NDVI 변화 (after − before)")
    print("변화 히트맵을 올렸어요. 빨강=식생 감소(개발·벌채), 초록=식생 증가입니다.")


# 사용법: 위 지도에서 영역을 그린 뒤, 새 셀에서 실행
#   show_change(m.user_roi)
#   show_change(m.user_roi, before=("2020-06-01","2020-09-30"),
#                           after=("2024-06-01","2024-09-30"))   # 같은 계절끼리 비교


# ============================================================
# 3-3 점검: 변화가 '얼마나' 일어났나 — 임계값 마스크 + 통계
# ============================================================
def change_stats(roi, before=("2023-01-01", "2023-12-31"),
                 after=("2024-01-01", "2024-12-31"), threshold=0.2):
    """큰 감소/증가가 일어난 면적 비율을 숫자로 뽑아 결과를 검증한다.

    threshold: '큰 변화'로 칠 기준(기본 0.2). |변화량| 이 이보다 크면 큰 변화로 본다.
    출력: 영역 중 큰 감소(빨강)·큰 증가(초록) 픽셀이 각각 몇 %인지.
          아는 변화지역(개발지·벌채지)을 그렸다면 '감소' 비율이 높게 나와야 정상.
    """
    change = ndvi_change(roi, before, after)
    if change is None:
        return

    # 큰 감소 / 큰 증가 마스크 (각각 1=해당, 0=아님)
    big_loss = change.lt(-threshold).rename("loss")   # 임계값보다 많이 줄어든 곳
    big_gain = change.gt(threshold).rename("gain")    # 임계값보다 많이 늘어난 곳

    # 영역 전체에서 마스크의 평균 = 해당 픽셀의 '비율'(0~1).
    stat = big_loss.addBands(big_gain).reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=roi,
        scale=10,            # Sentinel-2 해상도 10m
        maxPixels=1e9,
    )
    loss = stat.get("loss").getInfo()
    gain = stat.get("gain").getInfo()

    if loss is None or gain is None:
        print("값을 못 읽었어요. 그린 영역에 맑은 영상이 있는지(기간을 넓혀) 확인하세요.")
        return

    print(f"임계값 |{threshold}| 기준 — 영역 안에서")
    print(f"  식생 큰 감소(빨강) ≈ {loss * 100:.1f}%")
    print(f"  식생 큰 증가(초록) ≈ {gain * 100:.1f}%")
    if loss > gain:
        print("감소가 더 많네요 — 개발·벌채·재해 지역이라면 상식과 맞습니다.")
    elif gain > loss:
        print("증가가 더 많네요 — 농사 시작·식생 회복 지역이라면 상식과 맞습니다.")
    else:
        print("감소·증가가 비슷합니다 — 변화가 적거나 계절/구름 노이즈일 수 있어요.")


# 사용법 예 (아는 변화지역을 그린 뒤 실행):
#   change_stats(m.user_roi)
#   change_stats(m.user_roi, threshold=0.15)   # 기준을 낮추면 더 작은 변화도 잡힘
