# 설치 가이드

실습에 필요한 도구를 준비합니다. **막히면 그 에러 메시지를 그대로 Claude Code에게 물어보세요** — 이것도 바이브 코딩의 일부입니다.

순서대로 따라 하면 됩니다. (Windows 기준, macOS/Linux도 거의 같습니다)

---

## 1. Claude Code

AI 개발 파트너입니다. 일상 언어를 코드로 바꿔줍니다.

- 설치/로그인: [claude.com/claude-code](https://claude.com/claude-code) 안내를 따릅니다.
- 설치 확인: 터미널에서 `claude --version`

## 2. Obsidian (교재 읽기)

이 교재의 본문을 읽는 곳입니다.

1. [obsidian.md](https://obsidian.md) 에서 설치
2. **"Open folder as vault"** → 이 저장소의 `vault/` 폴더 선택
3. `00-home.md` 노트를 열면 시작입니다

## 3. Python + Streamlit (웹앱 실습)

이 교재의 실습은 매 장 **브라우저로 열리는 웹앱**을 만듭니다. 그 도구를 준비합니다.

```bash
# 1) 파이썬 가상환경 (권장)
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# 2) 필요한 패키지 — 웹앱(streamlit) + 위성영상(geemap, earthengine)
pip install streamlit geemap earthengine-api
```

> 설치 명령이 기억나지 않아도 됩니다. Claude Code에게 *"Streamlit + geemap 웹앱 실습 환경을 만들고 싶어, 필요한 설치 명령을 알려줘"* 라고 물으면 됩니다.

## 4. Google Earth Engine 계정

전 세계 위성영상 창고에 들어가는 열쇠입니다.

1. [code.earthengine.google.com](https://code.earthengine.google.com) 접속 → Google 계정으로 가입 신청
   - 연구/교육 용도는 보통 승인됩니다. 승인까지 시간이 걸릴 수 있습니다.
2. Cloud 프로젝트 연결이 필요할 수 있습니다 (안내에 따라 무료로 생성).
3. 첫 실습에서 `earthengine authenticate` 로 인증합니다 — 0장에서 함께 합니다.

---

## 잘 됐는지 확인

먼저 Earth Engine 인증을 한 번 합니다 (브라우저 로그인):

```bash
earthengine authenticate
```

그다음 0장에서 첫 웹앱(`datawa_study00/app.py`)을 실행해 봅니다:

```bash
streamlit run app.py
```

브라우저가 열리고 지도에 위성영상이 보이면 준비 완료입니다. (0장에서 처음부터 함께 만듭니다)

> 에러가 나면 그 메시지를 복사해 Claude Code에게 그대로 물어보세요. "이게 무슨 뜻이고 어떻게 고쳐?" 한 줄이면 충분합니다.
