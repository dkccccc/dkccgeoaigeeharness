# datawa_study02 · NDVI 식생지도 웹앱

2장의 결과물. **1장 뷰어(사이드바로 지역 골라 영상 보기)에 'NDVI 식생지도'를 더한 누적 웹앱**입니다.
사이드바에서 보기 모드를 고르면 같은 영역을 자연색(RGB) 또는 NDVI 색지도로 볼 수 있습니다.

## 만든 방법 (뼈대 → 기능 → 점검)

Claude Code에게 **프롬프트 2-1 → 2-2 → 2-3** 순서로 시켜 1장 앱을 단계별로 키웠습니다.
한꺼번에 만들지 않고 한 번에 하나씩 — 그래야 어디가 잘못됐는지 보입니다.

- **2-1 뼈대** — 영역의 NDVI를 계산하는 함수(`ndvi_for_roi`)부터. 색은 아직 안 칠합니다.
- **2-2 기능** — 보기 모드를 추가해 그 NDVI를 갈색→흰→초록 색지도+범례로 지도에 올립니다.
- **2-3 점검** — 물(낮음) vs 숲(높음) NDVI를 비교해 값이 상식과 맞는지 확인합니다.

## 실행

```bash
pip install -r requirements.txt
earthengine authenticate   # 처음 한 번만 (브라우저 인증)
streamlit run app.py       # 브라우저가 열립니다
```

## 사용법

1. 브라우저가 열리면 **왼쪽 사이드바**에서 경도·위도·반경으로 관심 지역을 고른다.
2. **보기 모드**를 `자연색`으로 두면 1장처럼 맑은 위성영상이, `NDVI`로 바꾸면 식생 색지도가 보인다.
3. `NDVI` 모드에서는 갈색~초록 색지도와 색-값 **범례(colorbar)**가 함께 뜬다.

## 주요 함수

- `make_roi(lon, lat, radius_km)` → 중심 좌표·반경으로 사각형 관심 영역(ROI)을 만든다. (1장 누적)
- `clearest_s2(roi, start, end)` → 구름 20% 미만, 가장 맑은 Sentinel-2 한 장을 반환한다. (1장 누적)
- `ndvi_for_roi(roi, start, end)` → **NDVI 이미지(`ee.Image`, 밴드 "NDVI")를 반환**한다. `normalizedDifference(["B8", "B4"])`(B8=근적외선, B4=빨강)로 계산. **3장 변화탐지가 이 함수를 두 시점에 호출해 재사용합니다.**

## 확인 (이게 보이면 성공)

- `자연색` 모드에서 1장과 똑같이 맑은 위성영상이 영역에 또렷이 보인다.
- `NDVI` 모드로 바꾸면 영역이 갈색~초록 색지도로 칠해지고, 범례(colorbar)가 보인다.
- 식생이 많은 곳(숲·논)이 초록, 적은 곳(물·맨땅·도시)이 갈색으로 구분된다.

## 막히면

- **`earthengine authenticate` 안 했다** → 첫 실행 전 터미널에서 한 번 인증해야 합니다.
- **온통 한 색** → `min`/`max` 범위(`-0.2`~`0.8`)가 영역과 안 맞을 수 있음. 범위를 좁혀보세요.
- **물이 높고 숲이 낮음** → 밴드 순서가 바뀐 것. `normalizedDifference(["B8", "B4"])`(B8=근적외선, B4=빨강)가 맞습니다.
- **영역에 색이 안 뜸** → 기간(`시작일`/`종료일`)에 맑은 영상이 없을 수 있음. 기간을 넓혀보세요.
- **범례(컬러바)가 안 보임** → `pip install folium streamlit-folium` 확인 (branca는 folium에 포함).
- 그 외 에러는 메시지를 복사해 Claude Code에게 물어보세요.

> 코드 검증 메모: NDVI 식(`normalizedDifference(["B8","B4"])`)과 팔레트·min/max는 참고 프로젝트 `dkidi/collector/ee_ndvi.py`의 실제 패턴(`add_ndvi`에서 `normalizedDifference(["B8","B4"]).rename("NDVI")`)에 근거합니다.
