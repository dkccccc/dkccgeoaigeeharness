# datawa_study05 · 여러 지역 자동 분석

5장의 결과물. **여러 관심지역(AOI)을 한 번에 분석해, 결과를 한 장의 보고서로 모으는 앱**입니다.
4장까지는 지역 한 곳을 손으로 한 번씩 돌렸습니다. 5장은 지역 목록만 주면 **알아서 전부 분석하고 표 보고서로 묶어줍니다** — 자동화의 출발점입니다.

## 만든 방법 (뼈대 → 기능 → 점검)

[PROMPTS.md](../PROMPTS.md)의 프롬프트 **5-1 → 5-2 → 5-3** 순서로 Claude Code에게 시켜 단계별로 키웠습니다.

- **5-1 뼈대** — 4장 `run_change_detection` 을 지역 목록에 차례로 호출하는 `batch_change_detection` 부터. 보고서는 아직.
- **5-2 기능** — 모인 결과를 지역명·평균변화·감소%·증가% 표(마크다운)로 묶어 파일로 저장(`build_report`).
- **5-3 점검** — 표의 숫자가 상식 범위인지 교차 확인(`check_report`).

## 혼자(loop) vs 팀(에이전트 팀)

이 파일은 **혼자 차례로 도는 loop 방식**입니다 — 가장 단순하고 확실합니다.
같은 일을 **Claude Code에게 "여러 지역을 나눠 동시에 분석시키는"** 에이전트 팀 방식으로도 할 수 있습니다. 그 프롬프트는 실습 노트 `lab-05` 와 PROMPTS 5-1을 보세요. (이 교재 자체가 5인 에이전트 팀이 만든 결과물입니다.)

## 실행 (주피터/코랩 권장)

```bash
pip install geemap earthengine-api jupyter
jupyter notebook   # 또는 Colab에 batch.py 내용을 붙여넣기
```

`batch.py` 의 코드를 노트북 셀에 붙여넣고 실행합니다. (4장과 같은 환경이면 추가 설치는 필요 없습니다.)

## 사용법

1. 분석할 지역 목록을 만든다 — 이름과 중심 좌표만 적으면 됩니다(구글지도에서 우클릭하면 좌표가 보입니다).
   ```python
   aoi_list = [
       aoi_from_point("서울숲",   127.0375, 37.5444),
       aoi_from_point("세종신도시", 127.2890, 36.4800),
       aoi_from_point("송도",     126.6490, 37.3830),
   ]
   ```
2. 두 기간(이전/이후)을 정한다. 모든 지역에 같은 기간을 씁니다.
3. `results = batch_change_detection(aoi_list, before, after)` 로 전부 분석한다.
4. `print(build_report(results))` 로 표 보고서를 만들고 `change_report.md` 파일로 저장한다.
5. (점검) `check_report(results)` 로 값이 상식 범위인지 확인한다.

## 주요 함수

- `aoi_from_point(name, lon, lat, half_km=5)` → **이름+중심좌표로 사각형 AOI 하나**를 만든다. `{"name", "roi"}` 딕셔너리 반환.
- `batch_change_detection(aoi_list, before, after, cloud_pct=20)` → **여러 지역을 차례로 분석**해 지역별 통계 dict의 목록을 반환한다. 4장 `run_change_detection` 을 지역마다 한 번씩 호출. 한 지역이 실패해도 멈추지 않고 다음으로 넘어간다.
- `build_report(results, out_path="change_report.md")` → 결과 목록을 **지역명·평균변화·감소%·증가% 마크다운 표**로 묶어 문자열 반환 + 파일 저장. 가장 많이 감소한 지역을 위로 정렬.
- `check_report(results)` → 표 값이 상식 범위(평균 -0.5~+0.5)인지 교차 확인.

## 확인 (이게 보이면 성공)

- 배치 분석 중 `(1/3) 서울숲 분석 중 ... 완료 (평균 -0.012)` 처럼 지역마다 한 줄씩 진행이 찍힌다.
- `change_report.md` 파일이 생기고, 그 안에 지역별 행이 있는 마크다운 표가 들어 있다.
- `check_report` 가 "모든 지역 값이 상식 범위입니다"를 출력한다(또는 의심 지역을 짚어준다).

## 막히면

- **한 지역만 "건너뜀"** → 그 기간에 맑은 영상이 없는 것. `cloud_pct` 를 30~40으로 올리거나 기간을 넓히세요. 다른 지역은 정상 처리됩니다.
- **모든 지역 "건너뜀"** → 기간 형식(`("2023-01-01", "2023-12-31")`)이나 인증을 먼저 확인하세요.
- **평균 변화량이 ±1을 넘게 큼** → `before` / `after` 가 계절이 다른 영상일 수 있음. 두 기간을 같은 계절로 맞추세요.
- **느림** → 지역이 많거나 `half_km` 가 큰 것. 지역 수를 줄이거나 `aoi_from_point(..., half_km=3)` 으로 영역을 줄이세요.
- 그 외 에러는 메시지를 복사해 Claude Code에게 물어보세요. (프롬프트 0-2 패턴)

> 코드 검증 메모: `run_change_detection` 의 시그니처·반환 dict(`mean_change`, `decrease_ratio`, `increase_ratio`, `area_km2`)는 4장 `datawa_study04/service.py` 와 동일합니다. 5장은 이 함수를 여러 지역에 반복 호출만 합니다(경계면 일치). `aoi_from_point` 의 위경도→km 환산은 위도 1도≈111km, 경도는 cos 보정의 표준 근사입니다.
