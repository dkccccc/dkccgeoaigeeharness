# datawa_study04 · 변화탐지 서비스 웹앱

4장의 결과물. 3장(변화탐지)을 **남이 가져다 쓸 수 있는 서비스**로 키운 누적 Streamlit 웹앱입니다.
사이드바에서 지역·이전/이후 기간·**구름 임계값**을 고르면, 두 시점을 비교해 식생이 어디서 늘고 줄었는지를 지도로 보여주고, **요약 통계를 카드로** 띄우며, 결과를 **GeoJSON/CSV 파일로 내려받게** 합니다.

## 누적된 것 (0~3장 → 4장)

- **make_roi** (1장) · **ndvi_for_roi** (2장) · **ndvi_change** (3장) — 그대로 들어 있습니다.
- 보기 모드(자연색 / NDVI / 변화), 이전·이후 기간, 사이드바 — 이어집니다.
- **추가(4장):** 구름 임계값 슬라이더, `run_change_detection` 서비스 함수, st.metric 요약 카드, 셀 단위 GeoJSON/CSV 다운로드.

## 만든 방법 (뼈대 → 기능 → 점검)

[PROMPTS.md](../PROMPTS.md)의 프롬프트 **4-1 → 4-2 → 4-3** 순서로 Claude Code에게 시켜 단계별로 키웠습니다.

- **4-1 뼈대** — 3장 변화탐지를 `run_change_detection(roi, before, after, cloud_pct)` 로 감싸 **변화 이미지 + 요약 통계 dict**를 반환하게 하고, 구름 임계값 슬라이더와 st.metric 카드를 붙였습니다.
- **4-2 기능** — 영역을 격자(셀)로 나눠 셀별 평균 변화량을 계산하고, `st.download_button` 으로 **GeoJSON/CSV**를 내려받게 했습니다.
- **4-3 점검** — 내려받은 파일을 다시 열어 셀 개수·변화량 범위가 상식과 맞는지 확인합니다.

## 실행

```bash
pip install -r requirements.txt
earthengine authenticate     # 처음 한 번만 (브라우저 로그인)
streamlit run app.py
```

실행하면 **브라우저가 자동으로 열립니다.** 왼쪽 사이드바에서 지역·기간·구름 임계값을 고르고 **[분석 / 보기]**를 누르세요.

## 주요 함수

- `run_change_detection(roi, before, after, cloud_pct=20)` → **변화 이미지 + 요약 통계를 담은 dict**를 반환. dict에는 `image`·`mean_change`·`decrease_ratio`·`increase_ratio`·`area_km2` 가 들어 있습니다. **5장 에이전트 팀이 이 함수를 여러 지역(AOI)에 반복 호출합니다.**
- `build_grid_table(result, roi, grid_km=2)` → 영역을 격자로 나눠 셀별 평균 변화량 표(리스트)를 만든다.
- `rows_to_csv` / `rows_to_geojson` → 셀 표를 CSV·GeoJSON 텍스트로 변환해 `st.download_button` 에 넘긴다.

## 확인 (이게 보이면 성공)

- 사이드바에서 지역·기간·구름값을 고르고 누르면, 평균 변화량·감소/증가 면적·영역 넓이가 **카드 4개**로 뜬다.
- 보기 모드를 바꾸면 지도가 변화 히트맵 / NDVI / 자연색으로 바뀐다.
- **CSV 내려받기 / GeoJSON 내려받기** 버튼이 보이고, 누르면 `change_20230101_to_20240101.csv` 같은 파일이 다운로드된다.
- 그 파일을 엑셀·QGIS로 열면 셀별 변화량이 표/지도로 보이고, 변화량이 대략 **-0.5 ~ +0.5** 사이다.

## 막히면

- `Please authorize access...` / `ee.Initialize` 오류 → 터미널에서 `earthengine authenticate` 를 한 번 실행.
- **모든 카드가 안 뜨고 "맑은 영상이 없어요"** → 그 기간에 구름 임계값 미만 영상이 없는 것. **구름 임계값 슬라이더**를 30~40으로 올리거나 기간을 넓히세요.
- **변화량이 ±1을 넘게 큼** → 이전/이후가 계절이 다른 영상일 수 있음. 두 기간을 같은 계절(예: 둘 다 여름)로 맞추세요.
- **셀이 수백 개로 폭증 / 느림** → 반경이 큰 것. **격자 크기**를 5~10km로 키워 셀 수를 줄이세요.
- `streamlit: command not found` → `pip install -r requirements.txt` 후 다시.
- 그 외 에러는 메시지를 복사해 Claude Code에게 물어보세요. (프롬프트 0-2 패턴)

> 코드 검증 메모: 셀 단위 익스포트(영역을 격자로 나눠 셀별 통계 → GeoJSON/CSV)와 구름 임계값·기간 선택은 참고 프로젝트 `dkchangedetection` PRD의 실제 설계(셀 단위 CSV/GeoJSON 익스포트, 격자, 구름 마스킹 후 맑은 관측만 사용)에 근거합니다. `coveringGrid`·`reduceRegions` 인자명은 EE 버전에 따라 다를 수 있어, 안 되면 위 막히면 항목을 보세요.
