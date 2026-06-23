"""
datawa_study05 · 여러 지역 자동 분석 웹앱
====================================================================
4장 변화탐지 서비스 웹앱(한 지역)에 '여러 지역 일괄 분석' 모드를 더했습니다.
앱 상단에서 모드를 고릅니다.
  - "한 지역"   : 4장 그대로 — 사이드바로 한 곳을 정해 변화 지도·통계를 봅니다.
  - "여러 지역" : 이름,위도,경도 목록을 붙여넣으면 전부 자동 분석해 한 표로 모읍니다.

만든 순서: 프롬프트 5-1(여러 지역 반복) → 5-2(결과 표·보고서) → 5-3(표 값 교차확인)

[경계면 — 4장 run_change_detection 을 그대로 재사용합니다]
핵심은 4장에서 만든 run_change_detection(roi, before, after, cloud_pct) 입니다.
이 함수는 '한 지역'을 분석해 통계 dict 하나를 반환합니다.
5장은 그 함수를 '여러 지역'에 차례로 호출(batch_change_detection)하고,
모인 dict 들을 결과 표(build_report)로 묶습니다. 분석 로직은 4장 그대로입니다.

[혼자(loop) vs 팀(에이전트 팀)]
batch_change_detection 은 '혼자 차례로' 도는 loop 방식입니다(가장 단순·확실).
같은 일을 Claude Code 에게 '여러 지역을 나눠 동시에 맡는 작은 팀처럼' 시킬 수도
있습니다. 사실 이 교재 자체가 5인 에이전트 팀이 나눠 만든 결과물입니다(저장소 .claude/).

로컬 실행:
    pip install -r requirements.txt
    earthengine authenticate     # 처음 한 번 (브라우저 로그인)
    streamlit run app.py
"""

import json

import branca.colormap as bcm
import ee
import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium


# =====================================================================
# [0] Earth Engine 초기화
# 웹앱은 ee.Authenticate() 의 '브라우저 인증'을 띄울 수 없습니다.
# 그래서 로컬에서 미리 한 번 인증해 둔 토큰으로 조용히 초기화만 합니다.
#   (처음 한 번만, 터미널에서)  earthengine authenticate
# 배포(클라우드)에서는 README 의 '서비스 계정' 안내를 따르세요.
# =====================================================================

@st.cache_resource   # 초기화는 앱 수명 동안 한 번만
def init_ee():
    try:
        ee.Initialize()
    except Exception:
        # 토큰이 없으면(예: 클라우드 첫 실행) 인증을 시도해 본다.
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
# [4장에서 만든 것] — service.py 의 핵심 3함수를 그대로 가져왔습니다.
# (이 한 파일만으로 돌아가도록 다시 넣어 두었습니다. 로직은 4장과 동일.)
# 자세한 주석은 datawa_study04/service.py 를 보세요.
# =====================================================================

def ndvi_for_roi(roi, start, end, cloud_pct=20):
    """그린 영역(roi)의 NDVI 이미지를 계산해 반환한다. (2장 함수)"""
    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(roi)
        .filterDate(start, end)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cloud_pct))
        .sort("CLOUDY_PIXEL_PERCENTAGE")
    )
    image = collection.first().clip(roi)
    # NDVI = (근적외선 B8 - 빨강 B4) / (B8 + B4)
    return image.normalizedDifference(["B8", "B4"]).rename("NDVI")


def ndvi_change(roi, before, after, cloud_pct=20):
    """두 기간의 NDVI를 빼서 '변화 이미지'를 반환한다. (3장 함수)"""
    ndvi_before = ndvi_for_roi(roi, before[0], before[1], cloud_pct)
    ndvi_after = ndvi_for_roi(roi, after[0], after[1], cloud_pct)
    return ndvi_after.subtract(ndvi_before).rename("NDVI_change")


def run_change_detection(roi, before, after, cloud_pct=20):
    """한 지역 변화탐지 서비스. 변화 이미지 + 요약 통계를 dict로 반환한다. (4장 함수)

    반환 dict 의 키 — 5장이 이걸 그대로 받아 표로 만듭니다:
      image, roi, before, after, cloud_pct,
      mean_change(평균 변화량), decrease_ratio(감소%), increase_ratio(증가%), area_km2
    맑은 영상이 없으면 None 을 반환합니다(배치에서 이 지역만 건너뛰게).
    """
    if roi is None:
        return None

    change = ndvi_change(roi, before, after, cloud_pct)

    mean_stat = change.reduceRegion(
        reducer=ee.Reducer.mean(), geometry=roi, scale=10, maxPixels=1e9,
    )
    mean_change = mean_stat.get("NDVI_change").getInfo()

    # 그 기간에 맑은 영상이 없으면 평균이 None → 이 지역은 분석 불가
    if mean_change is None:
        return None

    THRESHOLD = 0.1
    pixel_area = ee.Image.pixelArea()
    decreased = pixel_area.updateMask(change.lt(-THRESHOLD))
    increased = pixel_area.updateMask(change.gt(THRESHOLD))

    def area_m2(masked_area_image):
        stat = masked_area_image.reduceRegion(
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


# --- 지역 만들기 도우미 (중심 좌표 → 네모 영역) ---
def make_roi(lon, lat, radius_km):
    """중심 좌표(lon, lat)와 반경(km)으로 네모 영역(ee.Geometry)을 만든다. (4장 함수)"""
    point = ee.Geometry.Point([lon, lat])
    # buffer(미터) 로 원을 만든 뒤 그 외접 사각형(bounds)을 영역으로 쓴다.
    return point.buffer(radius_km * 1000).bounds()


# --- 변화 이미지를 지도에 칠하는 색 규칙 (4장과 동일) ---
VIS = {
    "min": -0.3, "max": 0.3,
    "palette": ["#d73027", "#ffffff", "#1a9850"],  # 감소(빨강) → 흰 → 증가(초록)
}


# =====================================================================
# [5-1] 뼈대 — 여러 지역(AOI) 목록을 차례로 분석한다 (loop 방식)
# 4장 run_change_detection 을 지역마다 한 번씩 호출하고, 결과를 모읍니다.
# "혼자 차례로" 도는 가장 단순하고 확실한 방법입니다.
# 한 지역이 실패해도 멈추지 않고 다음 지역으로 넘어갑니다(실패 격리).
# =====================================================================

def batch_change_detection(aoi_list, before, after, cloud_pct=20, radius_km=3,
                           progress=None):
    """여러 지역을 차례로 분석해, 지역별 통계 dict 의 목록을 반환한다.

    매개변수:
      aoi_list : 분석할 지역 목록. [{"name": str, "lon": float, "lat": float}, ...]
      before   : 이전 기간 (시작, 끝) 튜플.
      after    : 이후 기간 (시작, 끝) 튜플.
      cloud_pct: 구름 임계값(%). 모든 지역에 같은 값을 씁니다.
      radius_km: 각 중심 좌표 둘레로 만들 네모 영역의 반경(km).
      progress : 진행 한 줄을 받을 콜백(웹 화면에 찍을 때 씀). 없으면 무시.

    반환값(list[dict]) — build_report 가 이 목록을 그대로 받아 표로 만듭니다:
      각 dict 는 run_change_detection 의 통계에 "name" 을 더한 것.
      분석에 실패한 지역(맑은 영상 없음 등)은 "error" 키를 담아 표시합니다.
    """
    results = []
    total = len(aoi_list)

    for i, aoi in enumerate(aoi_list, start=1):
        name = aoi["name"]
        if progress:
            progress(f"({i}/{total}) {name} 분석 중 ...")
        try:
            roi = make_roi(aoi["lon"], aoi["lat"], radius_km)
            stat = run_change_detection(roi, before, after, cloud_pct)
            if stat is None:
                # 맑은 영상이 없는 경우 — 이 지역만 건너뛴다(전체는 계속)
                raise ValueError("그 기간에 맑은 영상 없음")
            # 무거운 ee 객체(image/roi)는 표에 필요 없어 빼고, 이름을 붙인다.
            results.append({
                "name": name,
                "mean_change": stat["mean_change"],
                "decrease_ratio": stat["decrease_ratio"],
                "increase_ratio": stat["increase_ratio"],
                "area_km2": stat["area_km2"],
            })
        except Exception as e:
            # 한 지역이 실패해도 멈추지 않고 다음 지역으로 넘어갑니다.
            results.append({"name": name, "error": str(e)})

    return results


def parse_aoi_text(text):
    """텍스트 영역의 '이름,위도,경도' 줄들을 지역 목록으로 바꾼다.

    한 줄 = 한 지역. 예:  서울숲,37.5444,127.0375
    빈 줄·형식이 틀린 줄은 조용히 건너뜁니다(웹에서 사람이 붙여넣으므로 관대하게).
    반환값: [{"name": str, "lon": float, "lat": float}, ...]
    """
    aoi_list = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 3:
            continue
        name = parts[0]
        try:
            lat = float(parts[1])
            lon = float(parts[2])
        except ValueError:
            continue   # 숫자가 아니면 건너뜀
        aoi_list.append({"name": name, "lon": lon, "lat": lat})
    return aoi_list


# =====================================================================
# [5-2] 기능 — 모인 결과를 한 표(DataFrame)로 묶고 보고서를 만든다
# 지역명·평균변화·감소%·증가% 표 + "가장 주의해서 볼 지역" 한 줄 요약.
# =====================================================================

def build_report(results):
    """배치 결과(list[dict])를 표(DataFrame) + 요약 문장으로 묶는다.

      results : batch_change_detection 이 돌려준 목록.

    반환값(dict):
      {
        "table":   pandas.DataFrame,  # 성공 지역 표(감소순 정렬). st.dataframe 으로 표시.
        "summary": str,               # "가장 주의해서 볼 지역" 한 줄 요약.
        "ok":      int,               # 성공 지역 수
        "failed":  list[dict],        # 실패 지역(이름·이유)
      }
    """
    ok_rows = [r for r in results if "error" not in r]
    bad_rows = [r for r in results if "error" in r]

    # 평균 변화량이 가장 많이 '감소'한 순으로 정렬(개발·벌채 의심 지역이 위로)
    ok_sorted = sorted(ok_rows, key=lambda x: x["mean_change"])

    table = pd.DataFrame([
        {
            "지역": r["name"],
            "평균 변화량": round(r["mean_change"], 3),
            "식생 감소 %": round(r["decrease_ratio"], 1),
            "식생 증가 %": round(r["increase_ratio"], 1),
            "면적 km²": round(r["area_km2"], 1),
        }
        for r in ok_sorted
    ])

    if ok_sorted:
        worst = ok_sorted[0]   # 정렬했으므로 맨 위가 가장 많이 감소한 곳
        summary = (
            f"가장 주의해서 볼 지역: **{worst['name']}** "
            f"(평균 변화량 {worst['mean_change']:+.3f}). 개발·벌채를 의심해 우선 살펴보세요."
        )
    else:
        summary = "성공한 지역이 없습니다. 구름 임계값을 올리거나 기간을 넓혀 다시 시도하세요."

    return {
        "table": table,
        "summary": summary,
        "ok": len(ok_rows),
        "failed": bad_rows,
    }


# =====================================================================
# 화면 그리기 — Streamlit 은 위에서 아래로 코드를 읽으며 화면을 그립니다.
# =====================================================================

st.set_page_config(page_title="여러 지역 자동 분석", page_icon="🛰️", layout="wide")
init_ee()

st.title("🛰️ 위성영상 변화탐지 — 여러 지역 자동 분석")
st.caption("한 지역을 손으로 → 여러 지역을 자동으로. 지역 목록만 주면 전부 분석해 한 표로 모읍니다.")

# --- 앱 상단: 모드 선택 (이 장에서 새로 더한 부분) ---
mode = st.radio(
    "분석 모드",
    ["한 지역", "여러 지역"],
    horizontal=True,
    help="‘한 지역’은 4장 그대로. ‘여러 지역’은 목록을 한 번에 자동 분석합니다.",
)


# ---------------------------------------------------------------------
# 모드 A) 한 지역 — 4장 서비스 웹앱 그대로 (사이드바·지도·통계)
# ---------------------------------------------------------------------
if mode == "한 지역":
    with st.sidebar:
        st.header("① 분석 조건")

        st.subheader("지역")
        lat = st.number_input("중심 위도", value=37.5444, format="%.4f")
        lon = st.number_input("중심 경도", value=127.0375, format="%.4f")
        radius_km = st.slider("반경 (km)", min_value=1, max_value=15, value=3)

        st.subheader("기간")
        before = (
            str(st.date_input("이전 시작", value=None, key="b0",
                              format="YYYY-MM-DD") or "2023-01-01"),
            str(st.date_input("이전 끝", value=None, key="b1",
                              format="YYYY-MM-DD") or "2023-12-31"),
        )
        after = (
            str(st.date_input("이후 시작", value=None, key="a0",
                              format="YYYY-MM-DD") or "2024-01-01"),
            str(st.date_input("이후 끝", value=None, key="a1",
                              format="YYYY-MM-DD") or "2024-12-31"),
        )

        cloud_pct = st.slider("구름 임계값 (%)", min_value=5, max_value=60, value=20,
                              help="낮출수록 맑은 영상만. 결과가 비면 높여보세요.")

        run = st.button("② 분석 실행", type="primary", use_container_width=True)

    if run:
        with st.spinner("위성영상을 모아 변화를 계산하는 중... (10~40초)"):
            roi = make_roi(lon, lat, radius_km)
            result = run_change_detection(roi, before, after, cloud_pct)

        if result is None:
            st.error("그 기간에 맑은 영상이 없어요. 구름 임계값을 올리거나 기간을 넓혀보세요.")
            st.stop()

        # (1) 요약 통계 카드
        st.subheader("📊 요약")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("분석 면적", f"{result['area_km2']:.1f} km²")
        c2.metric("평균 변화량", f"{result['mean_change']:+.3f}", help="+ 증가 / - 감소")
        c3.metric("식생 감소", f"{result['decrease_ratio']:.1f} %", delta="-개발·벌채 의심",
                  delta_color="inverse")
        c4.metric("식생 증가", f"{result['increase_ratio']:.1f} %", delta="+회복·생장")

        # (2) 변화 지도 — folium(Leaflet) 으로 그려 streamlit 안에 임베드합니다.
        st.subheader("🗺️ 변화 지도  (빨강=감소 · 초록=증가)")
        m = folium.Map(location=[lat, lon], zoom_start=12)
        add_ee_layer(m, result["image"], VIS, "NDVI 변화")
        bcm.LinearColormap(
            colors=VIS["palette"], vmin=VIS["min"], vmax=VIS["max"],
            caption="NDVI 변화량 (- 감소 / + 증가)",
        ).add_to(m)
        folium.LayerControl().add_to(m)
        st_folium(m, width=None, height=520, returned_objects=[])

        # (3) 통계 내려받기
        stats = {k: v for k, v in result.items() if k not in ("image", "roi")}
        st.download_button(
            "결과 통계 내려받기 (JSON)",
            data=json.dumps(stats, ensure_ascii=False, indent=2),
            file_name="change_result.json",
            mime="application/json",
        )
    else:
        st.info("왼쪽에서 지역·기간·구름값을 정하고 **[② 분석 실행]** 을 누르세요.")


# ---------------------------------------------------------------------
# 모드 B) 여러 지역 — 목록을 붙여넣으면 전부 자동 분석해 한 표로 (이 장의 핵심)
# ---------------------------------------------------------------------
else:
    with st.sidebar:
        st.header("① 공통 조건 (모든 지역에 같이 적용)")

        radius_km = st.slider("각 지역 반경 (km)", min_value=1, max_value=10, value=3,
                              help="중심 좌표 둘레로 만들 네모의 반경. 크면 느려집니다.")

        st.subheader("기간")
        before = (
            str(st.date_input("이전 시작", value=None, key="bb0",
                              format="YYYY-MM-DD") or "2023-01-01"),
            str(st.date_input("이전 끝", value=None, key="bb1",
                              format="YYYY-MM-DD") or "2023-12-31"),
        )
        after = (
            str(st.date_input("이후 시작", value=None, key="aa0",
                              format="YYYY-MM-DD") or "2024-01-01"),
            str(st.date_input("이후 끝", value=None, key="aa1",
                              format="YYYY-MM-DD") or "2024-12-31"),
        )

        cloud_pct = st.slider("구름 임계값 (%)", min_value=5, max_value=60, value=20,
                              key="cloud_batch",
                              help="낮출수록 맑은 영상만. 건너뛴 지역이 많으면 올려보세요.")

    st.subheader("① 분석할 지역 목록")
    st.caption("`이름,위도,경도` 를 한 줄에 하나씩. (구글지도에서 우클릭하면 `위도, 경도` 가 보입니다.)")
    default_aoi = (
        "서울숲,37.5444,127.0375\n"
        "세종신도시,36.4800,127.2890\n"
        "송도,37.3830,126.6490"
    )
    aoi_text = st.text_area("지역 목록", value=default_aoi, height=160,
                            label_visibility="collapsed")

    run_batch = st.button("② 여러 지역 자동 분석", type="primary")

    if run_batch:
        aoi_list = parse_aoi_text(aoi_text)
        if not aoi_list:
            st.error("지역 목록이 비었어요. `이름,위도,경도` 형식으로 한 줄에 하나씩 적어주세요.")
            st.stop()

        # 진행 상황을 화면에 한 줄씩 보여준다(어디까지 돌았는지 보이게).
        status = st.empty()
        bar = st.progress(0)
        log = []

        def progress(msg):
            log.append(msg)
            status.write("  ·  ".join(log[-1:]))   # 가장 최근 한 줄
            bar.progress(min(len(log) / len(aoi_list), 1.0))

        with st.spinner(f"지역 {len(aoi_list)} 곳을 차례로 분석하는 중..."):
            results = batch_change_detection(
                aoi_list, before, after, cloud_pct, radius_km, progress=progress
            )
        bar.empty()
        status.empty()

        report = build_report(results)

        # (1) 한눈 카드 — 성공/실패 개수
        st.subheader("📊 배치 결과")
        c1, c2 = st.columns(2)
        c1.metric("분석 성공", f"{report['ok']} 곳")
        c2.metric("건너뜀(실패)", f"{len(report['failed'])} 곳")

        # (2) 결과 표 — 지역명·평균변화·감소%·증가% (감소 많은 순으로 위)
        if not report["table"].empty:
            st.dataframe(report["table"], use_container_width=True, hide_index=True)
            st.info(report["summary"])

            # 표를 CSV 로 내려받기
            st.download_button(
                "결과 표 내려받기 (CSV)",
                data=report["table"].to_csv(index=False).encode("utf-8-sig"),
                file_name="batch_change_report.csv",
                mime="text/csv",
            )
        else:
            st.warning("성공한 지역이 없어요. 구름 임계값을 올리거나 기간을 넓혀 다시 시도하세요.")

        # (3) 건너뛴 지역도 숨기지 않고 남긴다(왜 빠졌는지 알 수 있게)
        if report["failed"]:
            with st.expander(f"건너뛴 지역 {len(report['failed'])} 곳 보기"):
                for r in report["failed"]:
                    st.write(f"- **{r['name']}** — {r['error']} "
                             f"(구름 임계값을 올리거나 기간을 넓혀 다시 시도)")
    else:
        st.info("위 목록을 확인하고 **[② 여러 지역 자동 분석]** 을 누르세요. "
                "한 지역이 실패해도 멈추지 않고 나머지를 계속 분석합니다.")
