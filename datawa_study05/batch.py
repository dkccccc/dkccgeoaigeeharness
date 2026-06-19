"""
datawa_study05 · 여러 지역 자동 분석 (에이전트 팀)
4장에서 만든 변화탐지 '서비스'(run_change_detection)를, 한 지역이 아니라
'여러 관심지역(AOI)'에 한 번에 돌리고, 결과를 한 장의 보고서로 모읍니다.
주피터/코랩에서 셀 단위로 실행하세요.

만든 순서: 프롬프트 5-1(여러 AOI 반복) → 5-2(결과를 보고서로 모으기) → 5-3(점검·교차확인)

[경계면 — 4장 service.py 를 그대로 재사용합니다]
핵심은 4장의 run_change_detection(roi, before, after, cloud_pct) 입니다.
이 함수는 '한 지역'을 분석해 통계 dict 하나를 반환합니다.
5장은 그 함수를 '여러 지역'에 차례로 호출(batch_change_detection)하고,
모인 dict 들을 마크다운 표 보고서(build_report)로 묶습니다.
    results = batch_change_detection(aoi_list, before, after)
    build_report(results)

[혼자(loop) vs 팀(에이전트 팀) 두 길]
이 파일은 '혼자 차례로 도는' loop 방식입니다(가장 단순·확실).
같은 일을 'Claude Code 에게 여러 지역을 나눠 동시에 분석시키는' 에이전트 팀
방식으로도 할 수 있습니다 — 그 프롬프트는 실습 노트 lab-05 와 PROMPTS 5-1 참고.
"""

import csv
import json

import ee
import geemap

ee.Authenticate()   # 처음 한 번 (브라우저 인증)
ee.Initialize()


# =====================================================================
# [4장에서 만든 것] — 아래 함수들은 4장 service.py 산출물입니다.
# 5장은 그대로 가져다 씁니다. (이 스크립트만으로 돌아가도록 다시 넣어 두었습니다.)
# 자세한 주석은 datawa_study04/service.py 를 보세요.
# =====================================================================

def ndvi_for_roi(roi, start, end, cloud_pct=20):
    """그린 영역의 NDVI 이미지를 반환한다. (2장 함수)"""
    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(roi)
        .filterDate(start, end)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cloud_pct))
        .sort("CLOUDY_PIXEL_PERCENTAGE")
    )
    image = collection.first().clip(roi)
    return image.normalizedDifference(["B8", "B4"]).rename("NDVI")


def ndvi_change(roi, before, after, cloud_pct=20):
    """두 기간 NDVI 를 빼서 변화 이미지를 반환한다. (3장 함수)"""
    ndvi_before = ndvi_for_roi(roi, before[0], before[1], cloud_pct)
    ndvi_after = ndvi_for_roi(roi, after[0], after[1], cloud_pct)
    return ndvi_after.subtract(ndvi_before).rename("NDVI_change")


def run_change_detection(roi, before, after, cloud_pct=20):
    """한 지역 변화탐지 서비스. 통계 dict 를 반환한다. (4장 함수)

    반환 dict 의 키(5장이 이걸 그대로 받아 표로 만듭니다):
      mean_change, decrease_ratio, increase_ratio, area_km2,
      image, roi, before, after, cloud_pct
    """
    if roi is None:
        print("먼저 지역(roi)을 지정하세요. (roi 가 비어 있어요)")
        return None

    change = ndvi_change(roi, before, after, cloud_pct)

    mean_stat = change.reduceRegion(
        reducer=ee.Reducer.mean(), geometry=roi, scale=10, maxPixels=1e9,
    )
    mean_change = mean_stat.get("NDVI_change").getInfo()

    # 맑은 영상이 없으면 평균이 None → 이 지역은 건너뛰도록 멈춘다(배치가 계속 돌게)
    if mean_change is None:
        print("그 기간에 맑은 영상이 없어요. cloud_pct를 올리거나 기간을 넓혀보세요.")
        return None

    THRESHOLD = 0.1
    pixel_area = ee.Image.pixelArea()
    decreased = pixel_area.updateMask(change.lt(-THRESHOLD))
    increased = pixel_area.updateMask(change.gt(THRESHOLD))

    def area_m2(masked):
        stat = masked.reduceRegion(
            reducer=ee.Reducer.sum(), geometry=roi, scale=10, maxPixels=1e9,
        )
        val = stat.get("area").getInfo()
        return float(val) if val is not None else 0.0

    total_m2 = roi.area(maxError=1).getInfo()
    decrease_ratio = area_m2(decreased) / total_m2 * 100 if total_m2 else 0.0
    increase_ratio = area_m2(increased) / total_m2 * 100 if total_m2 else 0.0

    return {
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


# =====================================================================
# [도우미] 분석할 '여러 지역(AOI) 목록' 만들기
# 4장까지는 지도에서 사각형을 직접 그렸습니다(m.user_roi).
# 5장은 사람이 한 번씩 그리지 않고, '이름 + 좌표'로 지역 목록을 코드로 정합니다.
# =====================================================================

def aoi_from_point(name, lon, lat, half_km=5):
    """중심 좌표(lon, lat) 둘레로 사각형 AOI 하나를 만든다.

      name    : 지역 이름(보고서에 그대로 나옵니다). 예: "서울숲"
      lon,lat : 중심 경도/위도. 구글지도에서 우클릭하면 보입니다.
      half_km : 중심에서 사각형 변까지의 거리(km). 5 면 약 10km x 10km.

    반환값: {"name": 이름, "roi": ee.Geometry} 딕셔너리.
            batch_change_detection 이 이 형식의 목록(list)을 받습니다.
    """
    # 위도 1도 ~= 111km. 경도는 위도에 따라 줄어들어 cos 로 보정.
    import math
    dlat = half_km / 111.0
    dlon = half_km / (111.0 * math.cos(math.radians(lat)))
    roi = ee.Geometry.Rectangle([lon - dlon, lat - dlat, lon + dlon, lat + dlat])
    return {"name": name, "roi": roi}


# =====================================================================
# [5-1] 뼈대 — 여러 지역(AOI) 목록을 차례로 분석한다 (loop 방식)
# 4장 run_change_detection 을 지역마다 한 번씩 호출하고, 결과를 모읍니다.
# "혼자 차례로" 도는 가장 단순하고 확실한 방법입니다.
# =====================================================================

def batch_change_detection(aoi_list, before, after, cloud_pct=20):
    """여러 지역을 차례로 분석해, 지역별 통계 dict 의 목록을 반환한다.

    매개변수:
      aoi_list : 분석할 지역 목록. [{"name": str, "roi": ee.Geometry}, ...]
                 aoi_from_point 로 만들거나, 직접 사각형을 넣어도 됩니다.
      before   : 이전 기간 (시작, 끝) 튜플.
      after    : 이후 기간 (시작, 끝) 튜플.
      cloud_pct: 구름 임계값(%). 모든 지역에 같은 값을 씁니다.

    반환값(list[dict]) — build_report 가 이 목록을 그대로 받아 표로 만듭니다:
      각 dict 는 run_change_detection 의 통계에 "name" 을 더한 것.
      분석에 실패한 지역(맑은 영상 없음 등)은 "error" 키를 담아 표시합니다.
    """
    results = []
    total = len(aoi_list)
    print(f"[배치 분석 시작] 지역 {total} 곳을 차례로 분석합니다.\n")

    for i, aoi in enumerate(aoi_list, start=1):
        name = aoi["name"]
        roi = aoi["roi"]
        print(f"  ({i}/{total}) {name} 분석 중 ...", end=" ")
        try:
            stat = run_change_detection(roi, before, after, cloud_pct)
            if stat is None:
                raise ValueError("roi 가 비었습니다")
            # 무거운 ee 객체(image/roi)는 보고서에 필요 없어 빼고, 이름을 붙인다.
            row = {
                "name": name,
                "mean_change": stat["mean_change"],
                "decrease_ratio": stat["decrease_ratio"],
                "increase_ratio": stat["increase_ratio"],
                "area_km2": stat["area_km2"],
            }
            results.append(row)
            print(f"완료 (평균 {row['mean_change']:+.3f})")
        except Exception as e:
            # 한 지역이 실패해도 멈추지 않고 다음 지역으로 넘어갑니다.
            results.append({"name": name, "error": str(e)})
            print(f"건너뜀 ({e})")

    ok = sum(1 for r in results if "error" not in r)
    print(f"\n[배치 분석 끝] {ok}/{total} 곳 성공.")
    return results


# =====================================================================
# [5-2] 기능 — 모인 결과를 한 장의 마크다운 표 보고서로 묶는다
# 지역명·평균변화·감소%·증가% 를 표로 만들고 파일로 저장합니다.
# =====================================================================

def build_report(results, out_path="change_report.md", title="변화탐지 배치 보고서"):
    """배치 결과(list[dict])를 마크다운 표 보고서로 만들어 파일로 저장한다.

      results : batch_change_detection 이 돌려준 목록.
      out_path: 저장할 파일 경로. 기본 "change_report.md".
      title   : 보고서 제목.

    반환값: 보고서 문자열(str). 같은 내용을 파일로도 저장합니다.
            노트북에서 print(build_report(results)) 하면 화면에서도 볼 수 있어요.
    """
    lines = []
    lines.append(f"# {title}")
    lines.append("")

    # 성공/실패 지역을 나눈다
    ok_rows = [r for r in results if "error" not in r]
    bad_rows = [r for r in results if "error" in r]

    lines.append(f"- 분석 지역: {len(results)} 곳 (성공 {len(ok_rows)} · 실패 {len(bad_rows)})")
    lines.append("")

    # 본 표 — 지역명 · 평균변화 · 감소% · 증가% · 면적
    lines.append("| 지역 | 평균 변화량 | 식생 감소 % | 식생 증가 % | 면적 km^2 |")
    lines.append("|------|------------:|------------:|------------:|----------:|")
    # 평균 변화량이 가장 많이 '감소'한 순으로 정렬(개발·벌채 의심 지역이 위로)
    for r in sorted(ok_rows, key=lambda x: x["mean_change"]):
        lines.append(
            f"| {r['name']} "
            f"| {r['mean_change']:+.3f} "
            f"| {r['decrease_ratio']:.1f} "
            f"| {r['increase_ratio']:.1f} "
            f"| {r['area_km2']:.1f} |"
        )
    lines.append("")

    # 한눈 요약 — 가장 많이 감소한 지역(주의해서 볼 곳)
    if ok_rows:
        worst = min(ok_rows, key=lambda x: x["mean_change"])
        lines.append(
            f"> 가장 많이 식생이 줄어든 곳: **{worst['name']}** "
            f"(평균 {worst['mean_change']:+.3f}). 개발·벌채를 의심해 우선 살펴보세요."
        )
        lines.append("")

    # 실패한 지역도 숨기지 않고 남긴다(왜 빠졌는지 알 수 있게)
    if bad_rows:
        lines.append("## 분석하지 못한 지역")
        for r in bad_rows:
            lines.append(f"- {r['name']} — {r['error']} (구름 임계값을 올리거나 기간을 넓혀 다시 시도)")
        lines.append("")

    report = "\n".join(lines)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"보고서를 저장했어요 → {out_path}  ({len(ok_rows)} 개 지역 표 포함)")
    return report


# =====================================================================
# [5-3] 점검 — 보고서 값이 상식과 맞는지 교차 확인한다
# (할루시네이션 검증: 표의 숫자를 그대로 믿지 않습니다.)
# =====================================================================

def check_report(results):
    """배치 결과의 값들이 상식 범위인지 교차 확인한다.

    - 평균 변화량은 보통 -0.5 ~ +0.5. 1을 넘으면 구름·계절 노이즈 의심.
    - 감소% + 증가% 가 100%를 넘으면 계산이 이상한 것.
    - 실패한 지역이 있으면 알려준다.
    """
    ok_rows = [r for r in results if "error" not in r]
    bad_rows = [r for r in results if "error" in r]

    print(f"보고서 점검 → 지역 {len(results)} 곳 (성공 {len(ok_rows)} · 실패 {len(bad_rows)})")

    flagged = 0
    for r in ok_rows:
        warnings = []
        if abs(r["mean_change"]) > 1.0:
            warnings.append(f"평균 변화량 {r['mean_change']:+.3f} 이 ±1 을 넘음(구름·계절 의심)")
        if r["decrease_ratio"] + r["increase_ratio"] > 100.0:
            warnings.append("감소%+증가% 가 100 을 넘음(계산 확인 필요)")
        if warnings:
            flagged += 1
            print(f"  [의심] {r['name']}: " + " / ".join(warnings))

    if flagged == 0:
        print("  모든 지역 값이 상식 범위(평균 -0.5~+0.5)입니다. 정상으로 보입니다.")
    for r in bad_rows:
        print(f"  [실패] {r['name']}: {r['error']}")
    print("  → 가장 많이 감소한 지역의 좌표를 지도에서 직접 보고, 실제 개발·벌채인지 눈으로 대보세요.")


# =====================================================================
# 사용법 (이 부분만 바꾸면 다른 지역들·기간으로 돌릴 수 있어요)
# =====================================================================
#
#   # 1) 분석할 지역 목록 — 이름과 중심 좌표만 적으면 됩니다(구글지도 우클릭으로 좌표 확인)
#   aoi_list = [
#       aoi_from_point("서울숲",   127.0375, 37.5444),
#       aoi_from_point("세종신도시", 127.2890, 36.4800),
#       aoi_from_point("송도",     126.6490, 37.3830),
#   ]
#
#   # 2) 두 기간(이전/이후) — 모든 지역에 같은 기간을 씁니다
#   before = ("2023-01-01", "2023-12-31")
#   after  = ("2024-01-01", "2024-12-31")
#
#   # 3) 배치 분석 (여러 지역을 차례로)
#   results = batch_change_detection(aoi_list, before, after, cloud_pct=20)
#
#   # 4) 보고서로 모으기 (마크다운 표 + 파일 저장)
#   print(build_report(results))
#
#   # 5) 보고서 값 점검
#   check_report(results)
