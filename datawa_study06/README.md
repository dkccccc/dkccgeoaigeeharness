# datawa_study06 · 배포 (Streamlit 웹앱)

이 교재의 **최종 결과물**. 5장까지 키운 변화탐지를 **남이 브라우저에서 클릭해 쓰고, 링크 하나로 공유되는** 배포 가능한 웹앱으로 마무리합니다.
기능은 5장과 같고(한 지역 자세히 보기 + 여러 지역 비교), **인증만 클라우드에서도 도는 방식(서비스 계정)** 으로 바꿨습니다 — 4·5장의 분석 로직은 그대로입니다.

## 만든 방법 (배포 준비 → 배포 → 점검)

[PROMPTS.md](../PROMPTS.md)의 프롬프트 **6-1 → 6-2 → 6-3** 순서로 Claude Code에게 시켜 단계별로 마무리했습니다.

- **6-1 배포 준비** — `requirements.txt` + 서비스 계정 인증 분기(`st.secrets` 가 있으면 그걸로, 없으면 로컬).
- **6-2 배포** — 이 폴더를 **GitHub**에 올리고 **Streamlit Community Cloud**(무료)에 연결 → **링크 공유**.
- **6-3 점검(맛보기)** — **MCP**가 무엇이고 왜 유용한지 + 배포된 링크가 실제로 도는지 확인.

## 들어 있는 것

| 파일 | 내용 |
|------|------|
| `app.py` | 배포용 최종 앱 (한 지역 + 여러 지역 + 내보내기, 서비스 계정 대응) |
| `requirements.txt` | 클라우드가 설치할 패키지 세 줄 |
| `README.md` | 이 문서 |

## 1. 로컬에서 실행 (먼저 여기서 확인하세요)

```bash
pip install -r requirements.txt
earthengine authenticate     # 처음 한 번 (브라우저가 열리며 로그인)
streamlit run app.py         # 앱 실행
```

실행하면 터미널에 `Local URL: http://localhost:8501` 이 뜨고 브라우저가 자동으로 열립니다.

- **🔍 한 지역 자세히** 탭 — 중심 좌표·반경을 정하고 분석하면 요약 카드 + 변화 지도가 뜹니다.
- **🗂️ 여러 지역 비교** 탭 — `이름, 경도, 위도` 를 한 줄에 하나씩 적고 분석하면 지역별 표가 나옵니다. (5장 batch 가 화면으로 들어온 것)
- 사이드바에서 **기간 / 구름 임계값**을 정합니다. (결과가 비면 구름값을 올리세요)

## 2. Streamlit Community Cloud 에 배포 (무료, 링크 공유)

> 클라우드에는 `earthengine authenticate` 의 **브라우저 인증 창이 없습니다.** 그래서 사람이 로그인하는 대신 **서비스 계정(robot 계정)** 의 열쇠(JSON)를 **Secrets** 에 넣어 인증합니다. 아래 3·4단계가 그 부분입니다.

1. **GitHub 공개 저장소에 올린다** — 최소한 `app.py` 와 `requirements.txt` 두 파일.

2. **[share.streamlit.io](https://share.streamlit.io)** 에 GitHub 계정으로 로그인 → **New app** → 저장소·브랜치·`app.py` 선택 → **Deploy**. 1~2분 뒤 `https://<앱이름>.streamlit.app` 링크가 생깁니다.

3. **서비스 계정 키를 발급한다** (한 번만)
   - [Google Cloud Console](https://console.cloud.google.com) → 프로젝트 선택 → **IAM 및 관리자 → 서비스 계정 → 만들기**.
   - 만든 서비스 계정에서 **키 → 키 추가 → JSON** → `.json` 파일이 내려받아집니다.
   - 그 서비스 계정 이메일(`...@....iam.gserviceaccount.com`)을 [Earth Engine](https://code.earthengine.google.com) 프로젝트에 **사용자로 등록**합니다. (Earth Engine 이 그 robot 계정을 허락하도록)

4. **그 JSON 을 Streamlit Secrets 에 넣는다**
   - 배포된 앱 화면 오른쪽 아래 **⋮ → Settings → Secrets**.
   - 아래처럼 `[gee_service_account]` 표 아래에 JSON 키들을 그대로 붙여넣습니다. (`app.py` 가 이 이름을 찾습니다)

   ```toml
   [gee_service_account]
   type = "service_account"
   project_id = "내-프로젝트-아이디"
   private_key_id = "..."
   private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
   client_email = "내서비스계정@내-프로젝트.iam.gserviceaccount.com"
   client_id = "..."
   token_uri = "https://oauth2.googleapis.com/token"
   ```

   - `private_key` 의 줄바꿈은 `\n` 그대로 둡니다(여러 줄로 풀지 마세요).
   - 저장하면 앱이 자동으로 다시 떠서, 이번엔 서비스 계정으로 조용히 인증합니다.

5. **링크를 공유한다** — `https://<앱이름>.streamlit.app` 을 동료에게 보내면, 설치도 코딩도 없이 브라우저에서 바로 씁니다.

> **인증이 어떻게 갈리나** — `app.py` 의 `init_ee()` 는 `st.secrets` 에 `gee_service_account` 가 있으면 `ee.ServiceAccountCredentials` 로 인증하고(배포), 없으면 로컬 `ee.Initialize()` 로 인증합니다. 그래서 **같은 코드가 로컬에서도 클라우드에서도** 돕니다.

## 막히면

- **지도가 빈 회색** → `import geemap.foliumap as geemap` 인지 확인. 웹앱에서는 folium 백엔드 + `m.to_streamlit()` 이어야 지도가 뜹니다.
- **로컬에서 `EEException: not initialized`** → `earthengine authenticate` 를 안 한 것. 터미널에서 먼저 인증하세요.
- **`streamlit: command not found`** → 설치가 안 된 것. `pip install -r requirements.txt` 후 다시.
- **클라우드에서 인증 오류 / 결과가 안 뜸** → Secrets 의 서비스 계정이 빠졌거나, 그 서비스 계정 이메일이 Earth Engine 에 **사용자로 등록되지 않은** 것. 4단계와 3단계 마지막 항목을 확인하세요. `private_key` 의 `\n` 이 풀려 있어도 실패합니다.
- **클라우드 배포가 `ModuleNotFoundError`** → `requirements.txt` 에 패키지를 빠뜨린 것. `streamlit`·`geemap`·`earthengine-api` 세 줄을 확인하세요.
- **결과가 계속 비어 있음** → 그 기간에 맑은 영상이 없는 것. 구름 임계값을 30~40 으로 올리거나 반경을 줄이세요.
- 그 외 에러는 메시지를 복사해 Claude Code에게 물어보세요. (프롬프트 0-2 패턴)

> 코드 검증 메모: 분석 로직(`run_change_detection` · `batch_change_detection`)은 4장 `datawa_study04/service.py` · 5장 `datawa_study05/batch.py` 와 동일합니다. Streamlit 안 EE 지도 임베드(`geemap.foliumap` + `Map.to_streamlit()`)와 서비스 계정 인증(`ee.ServiceAccountCredentials`)은 geemap·Earth Engine 공식 배포 패턴입니다.
