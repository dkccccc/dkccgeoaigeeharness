"""
datawa_study04 · 변화탐지 서비스
3장에서 만든 변화탐지를, 기간·지역·구름 임계값을 마음대로 바꿀 수 있는
'서비스'로 감쌌습니다. 그리고 결과를 GeoJSON/CSV 파일로 내보냅니다.
주피터/코랩에서 셀 단위로 실행하세요.

만든 순서: 프롬프트 4-1(파라미터화 서비스) → 4-2(GeoJSON/CSV 내보내기) → 4-3(점검·파일 값 확인)

[경계면 — 5장이 이 파일을 재사용합니다]
핵심은 아래 `run_change_detection(roi, before, after, cloud_pct)` 함수입니다.
이 함수는 변화 이미지 + 요약 통계를 담은 '딕셔너리(dict)' 하나를 반환합니다.
5장 에이전트 팀은 이 함수를 '여러 지역(AOI)'에 반복해서 호출합니다.
    for aoi in 여러_지역:
        result = run_change_detection(aoi, before, after, cloud_pct=20)
        export_result(result, aoi, fmt="csv")
그래서 이 함수는 지도에 그리는 일과 분리해, 'dict만' 깔끔히 반환합니다.
"""

import csv
import json

import ee
import geemap

ee.Authenticate()   # 처음 한 번 (브라우저 인증)
ee.Initialize()


# =====================================================================
# [3장에서 만든 것] — 이 두 함수는 3장 산출물입니다. 4장은 그대로 가져다 씁니다.
# (이 스크립트만으로 돌아가도록 여기에 다시 넣어 두었습니다.)
# =====================================================================

def ndvi_for_roi(roi, start, end, cloud_pct=20):
    """그린 영역(roi)의 NDVI 이미지를 계산해 반환한다. (2장 함수)

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
# [4-1] 뼈대 — 3장 변화탐지를 '파라미터화된 서비스'로 감싼다
# 기간·지역·구름 임계값을 변수로 받아, 변화 이미지 + 요약 통계를 dict로 반환.
# =====================================================================

def run_change_detection(roi, before, after, cloud_pct=20):
    """변화탐지 서비스 한 번 실행. 변화 이미지 + 요약 통계를 dict로 반환한다.

    매개변수(여기만 바꾸면 됩니다):
      roi       : 분석할 지역 (ee.Geometry). 지도에서 그린 m.user_roi 등.
      before    : 이전 기간 (시작, 끝) 튜플. 예: ("2023-01-01", "2023-12-31")
      after     : 이후 기간 (시작, 끝) 튜플. 예: ("2024-01-01", "2024-12-31")
      cloud_pct : 구름 임계값(%). 낮출수록 맑은 영상만, 높이면 영상이 없을 때 도움.

    반환값(dict) — 5장이 이 dict를 그대로 받아 씁니다:
      {
        "image":          ee.Image,   # 변화 이미지(밴드 "NDVI_change"), 지도에 올릴 때 사용
        "roi":            ee.Geometry,# 그대로 되돌려줌(내보내기에서 다시 씀)
        "before":         (s, e),     # 입력 기간을 기록
        "after":          (s, e),
        "cloud_pct":      int,
        "mean_change":    float,      # 영역 평균 변화량(+증가 / -감소)
        "decrease_ratio": float,      # 식생 감소(변화 < -0.1)한 면적 비율(%)
        "increase_ratio": float,      # 식생 증가(변화 > +0.1)한 면적 비율(%)
        "area_km2":       float,      # 분석 영역 넓이(km^2)
      }
    """
    if roi is None:
        print("먼저 지도에서 영역을 그린 뒤 다시 실행하세요. (roi 가 비어 있어요)")
        return None

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

    # 그 기간에 맑은 영상이 없으면 평균이 None 으로 온다 → 친절히 안내하고 멈춘다
    if mean_change is None:
        print("그 기간에 맑은 영상이 없어요. cloud_pct를 올리거나 기간을 넓혀보세요.")
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
        # 마스크가 전부 비면 None 이 올 수 있어 0 으로 처리
        val = stat.get("area").getInfo()
        return float(val) if val is not None else 0.0

    total_m2 = roi.area(maxError=1).getInfo()       # 영역 전체 면적(m^2)
    decrease_m2 = area_m2(decreased)
    increase_m2 = area_m2(increased)

    decrease_ratio = decrease_m2 / total_m2 * 100 if total_m2 else 0.0
    increase_ratio = increase_m2 / total_m2 * 100 if total_m2 else 0.0

    result = {
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

    # 사람이 바로 읽을 수 있게 한 줄 요약을 출력
    print(f"[변화탐지 완료] 영역 {result['area_km2']:.1f} km^2")
    print(f"  평균 변화량 : {mean_change:+.3f}  (+증가 / -감소)")
    print(f"  식생 감소 면적 : {decrease_ratio:.1f} %")
    print(f"  식생 증가 면적 : {increase_ratio:.1f} %")
    return result


# --- (보너스) 변화 이미지를 지도에 히트맵으로 올려 눈으로도 확인 ---
def show_change(result):
    """run_change_detection 의 결과를 빨강(감소)~흰~초록(증가) 히트맵으로 올린다."""
    if result is None:
        return
    m = geemap.Map()
    vis = {
        "min": -0.3,
        "max": 0.3,
        "palette": ["#d73027", "#ffffff", "#1a9850"],  # 감소(빨강) → 흰 → 증가(초록), 3장과 동일
    }
    m.add_layer(result["image"], vis, "NDVI 변화")
    m.center_object(result["roi"])
    m.add_colorbar(vis, label="NDVI 변화량 (- 감소 / + 증가)")
    return m


# =====================================================================
# [4-2] 기능 — 결과를 GeoJSON / CSV 파일로 내보낸다
# 초급자가 다운로드해서 엑셀·QGIS로 열 수 있도록 '셀 통계 → 파일'.
# =====================================================================

def export_result(result, roi=None, fmt="geojson", out_path=None, grid_km=2):
    """변화탐지 결과를 파일로 내보낸다.

      result  : run_change_detection 이 돌려준 dict.
      roi     : 영역(없으면 result["roi"] 사용).
      fmt     : "geojson" 또는 "csv".
      out_path: 저장 경로(없으면 자동 이름). 예: "change_seoul.geojson"
      grid_km : 영역을 몇 km 격자(셀)로 나눠 통계를 낼지. 작을수록 촘촘.

    동작: 영역을 grid_km 격자로 나누고, 각 셀의 평균 변화량을 계산해
          'cell_change' 속성으로 담은 벡터를 내보낸다(= PRD의 셀 단위 익스포트).
    반환값: 저장한 파일 경로(str).
    """
    if result is None:
        print("내보낼 결과가 없어요. 먼저 run_change_detection 을 실행하세요.")
        return None

    roi = roi if roi is not None else result["roi"]
    change = result["image"]

    # 1) 영역을 정사각 격자(셀)로 자른다 — coveringGrid 가 셀 FeatureCollection 을 만든다
    cell_size_m = grid_km * 1000
    grid = roi.coveringGrid("EPSG:3857", cell_size_m).filterBounds(roi)

    # 2) 각 셀의 평균 변화량을 계산해 'cell_change' 속성으로 붙인다
    cells = change.reduceRegions(
        collection=grid,
        reducer=ee.Reducer.mean().setOutputs(["cell_change"]),
        scale=10,
    )

    # 3) 파일 이름 자동 생성(기간을 이름에 넣어 헷갈리지 않게)
    if out_path is None:
        tag = f"{result['before'][0]}_to_{result['after'][0]}".replace("-", "")
        out_path = f"change_{tag}.{ 'csv' if fmt == 'csv' else 'geojson' }"

    # 4) 형식별로 저장
    if fmt == "geojson":
        # geemap 으로 EE FeatureCollection 을 GeoJSON 파일로 바로 내려받는다
        geemap.ee_to_geojson(cells, filename=out_path)
        print(f"GeoJSON 으로 저장했어요 → {out_path}  (QGIS·지도 도구로 열 수 있어요)")

    elif fmt == "csv":
        # 셀별 (중심좌표, 평균 변화량) 표를 CSV 로 저장 — 엑셀로 바로 열림
        features = cells.getInfo()["features"]
        with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["cell_id", "lon", "lat", "cell_change"])
            for i, feat in enumerate(features):
                # 셀 중심 좌표를 구한다(사각형 꼭짓점들의 평균)
                coords = feat["geometry"]["coordinates"][0]
                lon = sum(c[0] for c in coords[:-1]) / (len(coords) - 1)
                lat = sum(c[1] for c in coords[:-1]) / (len(coords) - 1)
                change_val = feat["properties"].get("cell_change")
                writer.writerow([i, round(lon, 5), round(lat, 5),
                                 round(change_val, 4) if change_val is not None else ""])
        print(f"CSV 로 저장했어요 → {out_path}  (엑셀로 바로 열 수 있어요)")

    else:
        print(f"모르는 형식이에요: {fmt}. 'geojson' 또는 'csv' 중에 고르세요.")
        return None

    return out_path


# =====================================================================
# [4-3] 점검 — 내보낸 파일을 열어 값이 상식과 맞는지 확인한다
# (할루시네이션 검증: 코드가 만든 숫자를 그대로 믿지 않는다.)
# =====================================================================

def check_export(out_path):
    """내보낸 파일을 다시 열어 셀 개수와 변화량 범위를 사람 눈으로 확인한다."""
    if out_path.endswith(".csv"):
        with open(out_path, encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        values = [float(r["cell_change"]) for r in rows if r["cell_change"] != ""]
    elif out_path.endswith(".geojson"):
        with open(out_path, encoding="utf-8") as f:
            data = json.load(f)
        values = [
            feat["properties"]["cell_change"]
            for feat in data["features"]
            if feat["properties"].get("cell_change") is not None
        ]
    else:
        print("csv 또는 geojson 파일만 확인할 수 있어요.")
        return

    if not values:
        print("셀 값이 비어 있어요. 기간에 맑은 영상이 없거나 격자가 영역 밖일 수 있어요.")
        return

    print(f"파일 확인 → {out_path}")
    print(f"  셀 개수      : {len(values)} 개")
    print(f"  변화량 최소  : {min(values):+.3f}  (가장 많이 감소한 셀)")
    print(f"  변화량 최대  : {max(values):+.3f}  (가장 많이 증가한 셀)")
    print(f"  변화량 평균  : {sum(values) / len(values):+.3f}")
    print("  → 값이 보통 -0.5 ~ +0.5 사이면 정상입니다. 1을 넘으면 구름·계절 노이즈를 의심하세요.")


# =====================================================================
# 사용법 (이 네 줄만 바꾸면 다른 지역·기간·구름값으로 돌릴 수 있어요)
# =====================================================================
#
#   # 지도를 띄우고 영역을 그린 뒤:
#   m = geemap.Map(center=[37.5, 127.0], zoom=10); m
#
#   # 바꿔보는 변수 — 지역(roi)·기간(before/after)·구름 임계값(cloud_pct)
#   roi    = m.user_roi
#   before = ("2023-01-01", "2023-12-31")   # 이전 기간
#   after  = ("2024-01-01", "2024-12-31")   # 이후 기간
#
#   # 1) 서비스 실행 → 통계 dict 반환
#   result = run_change_detection(roi, before, after, cloud_pct=20)
#
#   # 2) 파일로 내보내기 (csv 또는 geojson)
#   path = export_result(result, fmt="csv")
#
#   # 3) 내보낸 파일 점검
#   check_export(path)
#
#   # (보너스) 지도에서 히트맵으로 눈 확인
#   show_change(result)
