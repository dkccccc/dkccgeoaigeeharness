# datawa_study02 · NDVI 식생지도 앱

2장의 결과물. **그린 영역의 식생 상태(NDVI)를 갈색~초록 색지도로 보여주는 앱**입니다.
1장 뷰어에서 "영상을 보는" 데서 나아가, 그 영상에서 **식생을 읽어냅니다**.

## 만든 방법 (뼈대 → 기능 → 점검)

[PROMPTS.md](../PROMPTS.md)의 프롬프트 **2-1 → 2-2 → 2-3** 순서로 Claude Code에게 시켜 단계별로 키웠습니다.

- **2-1 뼈대** — 그린 영역의 NDVI를 계산하는 함수(`ndvi_for_roi`)부터. 색은 아직 안 칠합니다.
- **2-2 기능** — 그 NDVI를 갈색→흰→초록 색지도로 지도에 올리고 범례를 붙입니다.
- **2-3 점검** — 물(낮음) vs 숲(높음) NDVI를 비교해 값이 상식과 맞는지 확인합니다.

## 실행 (주피터/코랩 권장)

```bash
pip install geemap earthengine-api jupyter
jupyter notebook   # 또는 Colab에 ndvi_map.py 내용을 붙여넣기
```

`ndvi_map.py` 의 코드를 노트북 셀에 붙여넣고 실행하면 지도가 뜹니다. (1장과 같은 환경이면 추가 설치는 필요 없습니다.)

## 사용법

1. 지도 왼쪽의 사각형 그리기 도구로 관심 영역을 그린다. (1장과 동일)
2. `show_ndvi(m.user_roi)` 를 실행한다.
3. 영역이 갈색~초록 색지도로 칠해지고, 색-값 범례가 함께 뜬다.
4. (점검) 영역 안의 강·숲 좌표를 정해 `compare_ndvi(m.user_roi, water, forest)` 로 값을 확인한다.

## 주요 함수

- `ndvi_for_roi(roi, start, end)` → **NDVI 이미지(`ee.Image`, 밴드 "NDVI")를 반환**한다. 구름 적은 가장 맑은 Sentinel-2 한 장면에서 `normalizedDifference(["B8", "B4"])` 로 계산. **3장 변화탐지가 이 함수를 두 시점에 호출해 재사용합니다.**
- `show_ndvi(roi, ...)` → 위 이미지를 색지도+범례로 지도에 올린다.
- `compare_ndvi(roi, water_point, forest_point, ...)` → 두 지점 NDVI 평균을 출력해 검증.

## 확인 (이게 보이면 성공)

- 그린 영역이 갈색~초록 색지도로 칠해지고, 범례(colorbar)가 보인다.
- 식생이 많은 곳(숲·논)이 초록, 적은 곳(물·맨땅·도시)이 갈색으로 구분된다.
- `compare_ndvi` 에서 **물은 0 근처/음수, 숲은 0.6~0.9** 로 나온다.

## 막히면

- `user_roi` 가 `None` → 아직 영역을 안 그렸거나, 그린 뒤 셀을 다시 실행하지 않은 경우.
- **온통 한 색** → `min`/`max` 범위(`-0.2`~`0.8`)가 영역과 안 맞을 수 있음. 범위를 좁혀보세요.
- **물이 높고 숲이 낮음** → 밴드 순서가 바뀐 것. `normalizedDifference(["B8", "B4"])`(B8=근적외선, B4=빨강)가 맞습니다.
- 영역에 색이 안 뜸 → 기간(`start`/`end`)에 맑은 영상이 없을 수 있음. 기간을 넓혀보세요.
- `add_colorbar` 가 없다는 에러 → geemap 버전이 낮은 경우. `pip install -U geemap` 로 올려보세요. (대체로 최신 geemap에 포함되어 있습니다.)
- 그 외 에러는 메시지를 복사해 Claude Code에게 물어보세요. (프롬프트 0-2 패턴)

> 코드 검증 메모: NDVI 식(`normalizedDifference(["B8","B4"])`)과 팔레트·min/max는 참고 프로젝트 `dkidi/collector/ee_ndvi.py`·`ee_download.py`의 실제 패턴(`min=-0.2, max=0.9, palette=["brown","yellow","green"]`)에 근거합니다. `add_colorbar` 의 인자명은 geemap 버전에 따라 다를 수 있어, 안 되면 위 막히면 항목을 보세요.
