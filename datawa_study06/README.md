# datawa_study06 · 배포 (Streamlit 웹앱)

6장의 결과물. 지금까지 노트북에서 셀로 돌리던 변화탐지를 **남이 브라우저에서 클릭해 쓰는 웹앱**으로 바꿉니다.
4장에서 만든 `run_change_detection` 을 그대로 가져다 **화면(Streamlit)으로 감쌌을** 뿐입니다 — 분석 로직은 4장과 동일합니다.

## 만든 방법 (뼈대 → 기능 → 점검)

[PROMPTS.md](../PROMPTS.md)의 프롬프트 **6-1 → 6-2 → 6-3** 순서로 Claude Code에게 시켜 단계별로 키웠습니다.

- **6-1 뼈대** — 지역·기간·구름값 **입력칸** + **[분석 실행]** 버튼 + 결과(지도·통계) 표시. (`app.py`)
- **6-2 배포** — 이 앱을 **Streamlit Community Cloud**(무료)에 올려 **링크 하나로 공유**.
- **6-3 점검(맛보기)** — **MCP**가 무엇이고 왜 유용한지 + 아주 작은 연결 예. 배포가 실제로 도는지 확인.

## 설치

```bash
pip install streamlit geemap earthengine-api
```

(2장 환경이 있다면 `streamlit` 만 추가로 깔면 됩니다.)

## 로컬에서 실행

먼저 Earth Engine 인증을 **터미널에서 한 번** 해 둡니다. (웹앱은 브라우저 인증 창을 띄울 수 없어서, 미리 토큰을 만들어 둡니다.)

```bash
earthengine authenticate     # 처음 한 번 (브라우저가 열리며 로그인)
streamlit run app.py         # 앱 실행
```

실행하면 터미널에 `Local URL: http://localhost:8501` 이 뜨고, 브라우저가 자동으로 열립니다.
왼쪽에서 지역·기간·구름값을 정하고 **[② 분석 실행]** 을 누르면 변화 지도와 요약 카드가 나옵니다.

## 사용법

1. 왼쪽 사이드바에서 **중심 위도·경도**와 **반경(km)** 으로 분석할 네모 영역을 정한다.
2. **이전 기간 / 이후 기간**(두 시점)을 고른다. (비워 두면 2023 → 2024 가 기본값)
3. **구름 임계값**을 조정한다. (결과가 비면 올린다)
4. **[② 분석 실행]** 을 누른다 → 요약 카드(면적·평균 변화·감소/증가 비율) + 변화 지도가 뜬다.
5. **[결과 통계 내려받기 (JSON)]** 로 숫자를 저장한다.

## 배포 — 링크로 공유하기 (Streamlit Community Cloud, 무료)

1. 이 폴더(`app.py` + `requirements.txt`)를 **GitHub 공개 저장소**에 올린다.
   - `requirements.txt` 에 `streamlit`, `geemap`, `earthengine-api` 세 줄을 적는다.
2. [share.streamlit.io](https://share.streamlit.io) 에 GitHub 계정으로 로그인한다.
3. **New app** → 저장소·브랜치·`app.py` 를 고르고 **Deploy**.
4. 1~2분 뒤 `https://...streamlit.app` 형태의 **공개 링크**가 생긴다. 이 링크를 동료에게 보내면 끝.

> **클라우드 인증 주의:** 클라우드에는 `earthengine authenticate` 의 브라우저 창이 없습니다.
> 그래서 **서비스 계정(Service Account)** 토큰을 Streamlit 의 **Secrets**(앱 설정 → Secrets)에 넣어
> `ee.Initialize()` 가 그 토큰으로 조용히 인증하게 합니다. (자세한 절차는 lab 노트 6-2 와 막히면 항목 참고)
> 처음에는 **로컬 `streamlit run` 으로 충분히 확인**한 뒤, 공유가 필요할 때 클라우드로 올리세요.

## 막히면

- **지도가 빈 회색** → `geemap.foliumap` 이 아니라 일반 `geemap` 을 import 한 경우. 웹앱에서는 `import geemap.foliumap as geemap` 이어야 지도가 뜹니다.
- **`EEException: not initialized` / 인증 오류** → 로컬이면 `earthengine authenticate` 를 안 한 것. 터미널에서 먼저 인증하세요. 클라우드면 위 Secrets(서비스 계정)를 설정하세요.
- **`streamlit: command not found`** → 설치가 안 된 것. `pip install streamlit` 후 다시.
- **분석이 영원히 도는 것 같음 / 결과 비어 있음** → 그 기간에 맑은 영상이 없는 것. 구름 임계값을 30~40으로 올리거나 반경을 줄여보세요.
- **클라우드 배포가 `ModuleNotFoundError`** → `requirements.txt` 에 패키지를 빠뜨린 것. 세 패키지를 모두 적었는지 확인하세요.
- 그 외 에러는 메시지를 복사해 Claude Code에게 물어보세요. (프롬프트 0-2 패턴)

> 코드 검증 메모: 변화탐지 로직(`run_change_detection`)은 4장 `datawa_study04/service.py` 와 동일합니다. Streamlit 안에서 EE 지도를 임베드할 때 `geemap.foliumap` + `Map.to_streamlit()` 을 쓰는 것은 geemap 공식 streamlit 예제의 표준 패턴입니다.
