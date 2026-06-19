# datawa_study04 · 변화탐지 서비스

4장의 결과물. 3장에서 만든 변화탐지를 **기간·지역·구름 임계값을 마음대로 바꿀 수 있는 서비스**로 감싸고, 결과를 **GeoJSON/CSV 파일로 내보냅니다**.
"한 번 보여주는 코드"에서 나아가, 다른 지역·기간으로 **반복해서 돌릴 수 있는** 도구가 됩니다.

## 만든 방법 (뼈대 → 기능 → 점검)

[PROMPTS.md](../PROMPTS.md)의 프롬프트 **4-1 → 4-2 → 4-3** 순서로 Claude Code에게 시켜 단계별로 키웠습니다.

- **4-1 뼈대** — 3장 변화탐지를 `run_change_detection(roi, before, after, cloud_pct)` 로 감쌉니다. 기간·지역·구름값을 변수로 받아 **변화 이미지 + 요약 통계 dict**를 반환합니다.
- **4-2 기능** — 결과를 영역 격자(셀)로 나눠 셀별 평균 변화량을 계산하고, `export_result(...)` 로 **GeoJSON/CSV 파일**로 내보냅니다.
- **4-3 점검** — 내보낸 파일을 다시 열어(`check_export`) 셀 개수와 변화량 범위가 상식과 맞는지 사람 눈으로 확인합니다.

## 실행 (주피터/코랩 권장)

```bash
pip install geemap earthengine-api jupyter
jupyter notebook   # 또는 Colab에 service.py 내용을 붙여넣기
```

`service.py` 의 코드를 노트북 셀에 붙여넣고 실행하면 됩니다. (2·3장과 같은 환경이면 추가 설치는 필요 없습니다.)

## 사용법 (이 네 줄만 바꾸면 됩니다)

```python
roi    = m.user_roi                          # 지역: 지도에서 그린 영역
before = ("2023-01-01", "2023-12-31")        # 이전 기간
after  = ("2024-01-01", "2024-12-31")        # 이후 기간
result = run_change_detection(roi, before, after, cloud_pct=20)  # 구름 임계값
path   = export_result(result, fmt="csv")    # csv 또는 geojson 으로 내보내기
check_export(path)                           # 내보낸 파일 점검
```

## 주요 함수

- `run_change_detection(roi, before, after, cloud_pct=20)` → **변화 이미지 + 요약 통계를 담은 dict 를 반환**한다. dict에는 `image`(변화 이미지), `mean_change`(평균 변화량), `decrease_ratio`/`increase_ratio`(감소·증가 면적 비율 %), `area_km2` 등이 들어 있다. **5장 에이전트 팀이 이 함수를 여러 지역(AOI)에 반복 호출합니다.**
- `export_result(result, fmt="geojson"|"csv", grid_km=2)` → 영역을 격자로 나눠 셀별 평균 변화량을 파일로 내보낸다.
- `check_export(path)` → 내보낸 파일을 열어 셀 개수·변화량 범위를 출력해 검증.
- `show_change(result)` → (보너스) 변화 이미지를 빨강~파랑 히트맵으로 지도에 올린다.

`ndvi_for_roi`(2장)·`ndvi_change`(3장)는 이 스크립트만으로 돌아가도록 파일 안에 다시 넣어 두었습니다. "[3장에서 만든 것]" 주석 블록이 그것입니다.

## 확인 (이게 보이면 성공)

- `run_change_detection` 이 평균 변화량·감소/증가 면적 비율을 한 줄로 출력한다.
- `export_result` 가 `change_20230101_to_20240101.csv`(또는 `.geojson`) 같은 파일을 만든다.
- 그 파일을 엑셀·QGIS로 열면 셀별 변화량이 표/지도로 보인다.
- `check_export` 의 변화량 범위가 대략 **-0.5 ~ +0.5** 사이다.

## 막히면

- `roi` 가 `None` → 아직 영역을 안 그렸거나, 그린 뒤 셀을 다시 실행하지 않은 경우.
- **`cell_change` 가 전부 비어 있음** → 기간에 맑은 영상이 없을 수 있음. `cloud_pct` 를 30~40으로 올리거나 기간을 넓혀보세요. → [[구름-필터]]
- **변화량이 비정상으로 큼(±1 이상)** → before/after 가 계절이 다른 영상일 수 있음. 두 기간을 같은 계절로 맞추세요. (예: 둘 다 여름)
- `coveringGrid` / `reduceRegions` 에러 → 영역이 너무 크면 셀이 폭증합니다. `grid_km` 을 5~10으로 키워 셀 수를 줄이세요.
- `ee_to_geojson` 가 없다는 에러 → geemap 버전이 낮은 경우. `pip install -U geemap` 로 올려보세요.
- 그 외 에러는 메시지를 복사해 Claude Code에게 물어보세요. (프롬프트 0-2 패턴)

> 코드 검증 메모: 셀 단위 익스포트(영역을 격자로 나눠 셀별 통계 → GeoJSON/CSV)와 구름 임계값·기간 선택은 참고 프로젝트 `dkchangedetection` PRD의 실제 설계(`셀 단위 CSV/GeoJSON 익스포트`, `cell_key` 격자, 구름 마스킹 후 맑은 관측만 사용)에 근거합니다. `coveringGrid`·`reduceRegions`·`ee_to_geojson` 인자명은 EE/geemap 버전에 따라 다를 수 있어, 안 되면 위 막히면 항목을 보세요.
