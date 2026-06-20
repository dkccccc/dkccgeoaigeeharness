# datawa_study00 · 위성영상 한 장 띄우는 웹앱

0장의 결과물. **Claude Code에게 말해서** 만든, 위성영상 한 장을 브라우저에 띄우는 가장 작은 **Streamlit 웹앱**.

## 만든 방법

처음부터 손으로 짠 게 아닙니다. [PROMPTS.md](../PROMPTS.md)의 프롬프트 **0-1**을 Claude Code에게 건네서 받은 결과를, 실행하고 확인하며 다듬은 것입니다.

## 실행

```bash
pip install -r requirements.txt
earthengine authenticate     # 처음 한 번만 (브라우저 로그인)
streamlit run app.py
```

실행하면 **브라우저가 자동으로 열리고** 지도가 보입니다.

## 확인 (이게 보이면 성공)

- 브라우저에 지도가 뜨고, 서울 부근에 위성영상(자연색)이 보인다. 🎉

## 막히면

에러 메시지를 복사해 Claude Code에게 *"이게 무슨 뜻이고 어떻게 고쳐?"* 라고 물어보세요. 자주 나는 것:
- `Please authorize access...` / `ee.Initialize` 오류 → 터미널에서 `earthengine authenticate` 를 한 번 실행
- `not been used in project ... before` → Cloud 프로젝트 연결 필요 (설치가이드 4번)
- `streamlit: command not found` → `pip install streamlit` 후 다시
