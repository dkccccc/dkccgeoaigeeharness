"""
datawa_study06 · 배포 (Streamlit 웹앱)
====================================================================
이 교재의 '최종 결과물'. 5장까지 키운 변화탐지를 '남이 클릭해서 쓰고, 링크로 공유되는'
배포 가능한 웹앱으로 마무리합니다. 기능은 5장과 같되(여러 지역 분석 포함),
인증만 '클라우드에서도 도는' 방식(서비스 계정)으로 바꿨습니다.

만든 순서: 프롬프트 6-1(배포 준비: requirements·서비스계정 secrets)
        → 6-2(Streamlit Cloud 에 배포해 링크 공유) → 6-3(MCP 맛보기·배포 확인)

[경계면 — 4장 service.py + 5장 batch 를 그대로 재사용합니다]
  · 한 지역 분석    : run_change_detection(roi, before, after, cloud_pct)   ← 4장
  · 여러 지역 분석   : batch_change_detection(aoi_list, before, after, ...)  ← 5장
이 파일은 그 두 함수를 'Streamlit 화면'으로 감쌌을 뿐입니다. 분석 로직은 4·5장 그대로입니다.

로컬 실행:
    pip install -r requirements.txt
    earthengine authenticate        # 처음 한 번 (브라우저 로그인)
    streamlit run app.py
배포(클라우드) 실행은 README 의 'Streamlit Cloud 배포 + 서비스 계정 Secrets' 참고.
"""

import json
import math

import ee
import geemap.foliumap as geemap   # streamlit 안에서는 folium 백엔드를 써야 지도가 뜸
import streamlit as st


# =====================================================================
# [0] Earth Engine 초기화 — '로컬'과 '배포(클라우드)' 둘 다 되게
# ---------------------------------------------------------------------
# 노트북/로컬에서는 미리 'earthengine authenticate' 해 둔 토큰으로 초기화됩니다.
# 하지만 배포된 클라우드 서버에는 '브라우저 로그인 창'이 없습니다. 그래서 사람이
# 로그인하는 대신, '서비스 계정(robot 계정)' 의 열쇠(JSON)로 조용히 인증합니다.
#
# 분기 규칙:
#   · st.secrets 에 서비스 계정 JSON 이 들어 있으면  → 그걸로 ServiceAccountCredentials 인증 (배포용)
#   · 없으면                                        → 그냥 ee.Initialize() (로컬, 미리 인증해 둔 토큰 사용)
# Streamlit Cloud 에서는 앱 설정 → Secrets 에 서비스 계정 JSON 을 넣으면 됩니다(README 참고).
# =====================================================================

@st.cache_resource   # 초기화는 앱 수명 동안 '한 번만' (매번 다시 인증하지 않게)
def init_ee():
    # (1) 배포용 — Secrets 에 서비스 계정 정보가 있으면 그걸로 인증
    if "gee_service_account" in st.secrets:
        sa = st.secrets["gee_service_account"]
        # secrets 에는 [gee_service_account] 표 아래에 서비스 계정 JSON 의 키들이 들어 있습니다.
        # (client_email, private_key, project_id ...) — README 의 Secrets 예시 참고.
        key_data = json.dumps(dict(sa))            # secrets 표 → JSON 문자열
        credentials = ee.ServiceAccountCredentials(
            sa["client_email"], key_data=key_data,
        )
        ee.Initialize(credentials, project=sa.get("project_id"))
        return

    # (2) 로컬용 — 미리 'earthengine authenticate' 한 토큰으로 초기화
    try:
        ee.Initialize()
    except Exception:
        # 토큰이 아직 없으면(첫 실행) 브라우저 인증을 한 번 시도한다. (로컬에서만 동작)
        ee.Authenticate()
        ee.Initialize()


# =====================================================================
# [4장에서 만든 것] — service.py 의 핵심 3함수를 그대로 가져왔습니다.
# (이 한 파일만으로 배포되도록 여기에 다시 넣어 두었습니다. 로직은 4장과 동일.)
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
    """변화탐지 서비스 한 번 실행. 변화 이미지 + 요약 통계를 dict로 반환한다. (4장 함수)"""
    if roi is None:
        return None

    change = ndvi_change(roi, before, after, cloud_pct)

    mean_stat = change.reduceRegion(
        reducer=ee.Reducer.mean(), geometry=roi, scale=10, maxPixels=1e9,
    )
    mean_change = mean_stat.get("NDVI_change").getInfo()
    if mean_change is None:
        return None   # 그 기간에 맑은 영상이 없으면 None (배치가 멈추지 않게)

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
    decrease_m2 = area_m2(decreased)
    increase_m2 = area_m2(increased)
    decrease_ratio = decrease_m2 / total_m2 * 100 if total_m2 else 0.0
    increase_ratio = increase_m2 / total_m2 * 100 if total_m2 else 0.0

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
# [5장에서 만든 것] — 여러 지역(AOI) 목록을 차례로 분석한다 (batch).
# 4장 run_change_detection 을 지역마다 한 번씩 호출하고 결과를 모읍니다.
# =====================================================================

def aoi_from_point(name, lon, lat, half_km=5):
    """중심 좌표 둘레로 사각형 AOI 하나를 만든다. {"name", "roi"} 를 반환. (5장 함수)"""
    dlat = half_km / 111.0
    dlon = half_km / (111.0 * math.cos(math.radians(lat)))
    roi = ee.Geometry.Rectangle([lon - dlon, lat - dlat, lon + dlon, lat + dlat])
    return {"name": name, "roi": roi}


def batch_change_detection(aoi_list, before, after, cloud_pct=20, progress=None):
    """여러 지역을 차례로 분석해, 지역별 통계 dict 의 목록을 반환한다. (5장 함수)

      progress: Streamlit 진행바(st.progress)를 넘기면 한 지역 끝낼 때마다 갱신합니다.
    """
    results = []
    total = len(aoi_list)
    for i, aoi in enumerate(aoi_list, start=1):
        name, roi = aoi["name"], aoi["roi"]
        try:
            stat = run_change_detection(roi, before, after, cloud_pct)
            if stat is None:
                raise ValueError("그 기간에 맑은 영상이 없음")
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
        if progress is not None:
            progress.progress(i / total, text=f"({i}/{total}) {name} 분석 완료")
    return results


# =====================================================================
# [6-1] 화면 — 4·5장 함수를 입력칸·버튼·결과로 감쌉니다.
# Streamlit 은 위에서 아래로 코드를 읽으며 화면을 그립니다.
# st.xxx 한 줄이 화면의 한 요소(제목·입력칸·버튼·지도)가 됩니다.
# =====================================================================

# --- 페이지 기본 설정 (가장 위에 한 번) ---
st.set_page_config(page_title="변화탐지 웹앱", page_icon="🛰️", layout="wide")
init_ee()

st.title("🛰️ 위성영상 변화탐지 웹앱")
st.caption("지역과 두 기간을 정하면, 식생이 줄거나 는 곳을 지도로 보여줍니다. (NDVI 변화)")

# --- 변화 이미지를 지도에 칠하는 색 규칙 (3·4장과 동일) ---
VIS = {
    "min": -0.3, "max": 0.3,
    "palette": ["#d73027", "#ffffff", "#1a9850"],  # 감소(빨강) → 흰 → 증가(초록)
}


def make_roi(lon, lat, radius_km):
    """중심 좌표와 반경(km)으로 네모 영역(ee.Geometry)을 만든다."""
    point = ee.Geometry.Point([lon, lat])
    return point.buffer(radius_km * 1000).bounds()


# --- 왼쪽 사이드바: 공통 입력값 (기간·구름값) ---
with st.sidebar:
    st.header("① 기간 · 구름")
    before = (
        str(st.date_input("이전 시작", value=None, key="b0", format="YYYY-MM-DD")
            or "2023-01-01"),
        str(st.date_input("이전 끝", value=None, key="b1", format="YYYY-MM-DD")
            or "2023-12-31"),
    )
    after = (
        str(st.date_input("이후 시작", value=None, key="a0", format="YYYY-MM-DD")
            or "2024-01-01"),
        str(st.date_input("이후 끝", value=None, key="a1", format="YYYY-MM-DD")
            or "2024-12-31"),
    )
    cloud_pct = st.slider("구름 임계값 (%)", min_value=5, max_value=60, value=20,
                          help="낮출수록 맑은 영상만. 결과가 비면 높여보세요.")


# --- 두 가지 모드: 한 지역 자세히 / 여러 지역 비교 (5장 batch 가 여기 들어옵니다) ---
tab_one, tab_many = st.tabs(["🔍 한 지역 자세히", "🗂️ 여러 지역 비교"])


# ===== 모드 1: 한 지역 — 변화 지도 + 요약 카드 (4장) =====
with tab_one:
    c_lat, c_lon, c_r = st.columns(3)
    lat = c_lat.number_input("중심 위도", value=37.50, format="%.4f")
    lon = c_lon.number_input("중심 경도", value=127.00, format="%.4f")
    radius_km = c_r.slider("반경 (km)", min_value=1, max_value=15, value=3)
    run_one = st.button("② 이 지역 분석", type="primary", use_container_width=True)

    if run_one:
        with st.spinner("위성영상을 모아 변화를 계산하는 중... (10~40초)"):
            roi = make_roi(lon, lat, radius_km)
            result = run_change_detection(roi, before, after, cloud_pct)

        if result is None:
            st.error("그 기간에 맑은 영상이 없어요. 구름 임계값을 올리거나 기간을 넓혀보세요.")
        else:
            # (1) 요약 통계를 숫자 카드로
            st.subheader("📊 요약")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("분석 면적", f"{result['area_km2']:.1f} km²")
            m2.metric("평균 변화량", f"{result['mean_change']:+.3f}", help="+ 증가 / - 감소")
            m3.metric("식생 감소", f"{result['decrease_ratio']:.1f} %",
                      delta="-개발·벌채 의심", delta_color="inverse")
            m4.metric("식생 증가", f"{result['increase_ratio']:.1f} %", delta="+회복·생장")

            # (2) 변화 지도 — geemap.foliumap 으로 그려야 streamlit 안에 임베드됩니다.
            st.subheader("🗺️ 변화 지도  (빨강=감소 · 초록=증가)")
            m = geemap.Map()
            m.add_layer(result["image"], VIS, "NDVI 변화")
            m.center_object(result["roi"])
            m.add_colorbar(VIS, label="NDVI 변화량 (- 감소 / + 증가)")
            m.to_streamlit(height=520)

            # (3) 결과 통계 내려받기 (이미지는 빼고 통계만)
            stats = {k: v for k, v in result.items() if k not in ("image", "roi")}
            st.download_button(
                "결과 통계 내려받기 (JSON)",
                data=json.dumps(stats, ensure_ascii=False, indent=2),
                file_name="change_result.json", mime="application/json",
            )
    else:
        st.info("위에서 중심 좌표·반경을 정하고 **[② 이 지역 분석]** 을 누르세요.")


# ===== 모드 2: 여러 지역 — 이름+좌표 목록을 한 번에 (5장 batch) =====
with tab_many:
    st.caption("이름, 경도, 위도를 한 줄에 하나씩. (구글지도에서 우클릭하면 좌표가 보입니다)")
    default_text = (
        "서울숲, 127.0375, 37.5444\n"
        "세종신도시, 127.2890, 36.4800\n"
        "송도, 126.6490, 37.3830"
    )
    raw = st.text_area("지역 목록 (이름, 경도, 위도)", value=default_text, height=130)
    half_km = st.slider("각 지역 반경 (km)", min_value=2, max_value=15, value=5,
                        key="half_km")
    run_many = st.button("② 여러 지역 분석", type="primary", use_container_width=True)

    if run_many:
        # 입력 텍스트 → aoi_list 로 파싱 (5장 aoi_from_point 사용)
        aoi_list = []
        for line in raw.strip().splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) != 3:
                continue
            name, lon_s, lat_s = parts
            try:
                aoi_list.append(aoi_from_point(name, float(lon_s), float(lat_s), half_km))
            except ValueError:
                st.warning(f"좌표를 못 읽었어요(숫자가 아님): {line}")

        if not aoi_list:
            st.error("읽을 수 있는 지역이 없어요. '이름, 경도, 위도' 형식인지 확인하세요.")
        else:
            bar = st.progress(0.0, text="분석 시작...")
            results = batch_change_detection(aoi_list, before, after, cloud_pct,
                                             progress=bar)
            bar.empty()

            ok_rows = [r for r in results if "error" not in r]
            bad_rows = [r for r in results if "error" in r]
            st.success(f"분석 끝 — {len(ok_rows)}/{len(results)} 곳 성공")

            # (1) 표 — 평균 변화량이 가장 많이 '감소'한 순(개발·벌채 의심이 위로)
            if ok_rows:
                table = sorted(ok_rows, key=lambda x: x["mean_change"])
                st.subheader("📋 지역별 변화 (감소 큰 순)")
                st.dataframe(
                    [{
                        "지역": r["name"],
                        "평균 변화량": round(r["mean_change"], 3),
                        "식생 감소 %": round(r["decrease_ratio"], 1),
                        "식생 증가 %": round(r["increase_ratio"], 1),
                        "면적 km²": round(r["area_km2"], 1),
                    } for r in table],
                    use_container_width=True, hide_index=True,
                )
                worst = table[0]
                st.info(f"가장 많이 식생이 줄어든 곳: **{worst['name']}** "
                        f"(평균 {worst['mean_change']:+.3f}). 개발·벌채를 의심해 우선 살펴보세요.")

            # (2) 분석 못 한 지역도 숨기지 않고 남긴다
            for r in bad_rows:
                st.warning(f"{r['name']} — {r['error']} (구름 임계값을 올리거나 기간을 넓혀 다시)")

            # (3) 보고서 내려받기 (JSON)
            st.download_button(
                "보고서 내려받기 (JSON)",
                data=json.dumps(results, ensure_ascii=False, indent=2),
                file_name="change_report.json", mime="application/json",
            )
    else:
        st.info("지역 목록을 정하고 **[② 여러 지역 분석]** 을 누르세요. (여러 곳을 한 번에)")
