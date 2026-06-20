---
title: "사전 셋팅 · Claude Code 설치"
tags: [유형/실습, 주제/claude-code, 난이도/입문]
---

# 🧰 사전 셋팅 · Claude Code 설치와 로그인

> [!info] 이 자료를 마치면
> Claude Code가 설치·로그인되어, 터미널에서 `claude`를 띄울 수 있다. 약 15~20분.

**Claude Code**는 터미널에서 AI와 대화하며 코딩하는 도구입니다. 이 교재의 모든 실습은 여기에 **일상 언어로 말해서** 만듭니다. 그러니 가장 먼저 이걸 준비합니다.

> [!warning] 먼저 확인 — 유료 구독이 필요해요
> Claude Code는 **무료 claude.ai 계정으로는 쓸 수 없습니다.** 다음 중 하나가 필요합니다:
> - **Claude Pro 또는 Max 구독** (권장, 가장 간단) — [claude.com/pricing](https://claude.com/pricing)
> - 또는 **Anthropic Console**(console.anthropic.com)의 크레딧 충전 계정
>
> 시작하기 전에 구독을 먼저 준비하세요.

---

## 1. 설치

### Windows (권장)

1. 시작 버튼 → **`PowerShell`** 검색 → 열기
2. 아래를 복사해 붙여넣고 **Enter**:
   ```powershell
   irm https://claude.ai/install.ps1 | iex
   ```
3. `successfully installed` 메시지가 보이면, **PowerShell 창을 닫았다가 새로 엽니다.**

> [!tip] Git도 함께 설치해두면 좋아요 (선택)
> 일부 실습에서 편리합니다. [git-scm.com/downloads/win](https://git-scm.com/downloads/win) 에서 받아 설치 화면은 전부 기본값(Next)으로 진행하면 됩니다.

### macOS / Linux

터미널에서:
```bash
curl -fsSL https://claude.ai/install.sh | bash
```
(Homebrew를 쓰면 `brew install --cask claude-code` 도 가능합니다.)

> [!note] Node.js 같은 건 필요 없나요?
> 네, 필요 없습니다. Claude Code는 독립 실행 파일이라 위 명령 하나로 끝납니다.

---

## 2. 로그인

터미널(PowerShell)에 입력:
```bash
claude
```

그러면 **브라우저가 자동으로 열려 로그인 화면**이 뜹니다. 준비한 **Claude 계정(Pro/Max)**으로 로그인하면 됩니다.

> [!tip] 브라우저가 안 열리면
> 터미널에 표시된 로그인 링크를 직접 복사해 브라우저 주소창에 붙여넣으세요.

---

## 3. 잘 됐는지 확인

```bash
claude --version
```
버전 번호가 나오면 설치 성공입니다.

문제가 있는지 종합 점검하려면:
```bash
claude doctor
```

> [!success] 확인
> `claude` 를 실행했을 때 입력창(프롬프트)이 뜨고, 무언가 한국어로 물어봤을 때 답이 오면 준비 완료입니다. 🎉

---

## 4. 터미널 기초 (Windows 초보자용)

Claude Code는 터미널에서 씁니다. 딱 이만큼만 알면 됩니다.

**터미널(PowerShell) 여는 법**: `Windows 키 + X` → "터미널" 또는 "Windows PowerShell" 클릭.

| 명령어 | 뜻 |
|--------|-----|
| `cd C:\dev\my-project` | 그 폴더로 이동 |
| `cd ..` | 상위 폴더로 |
| `ls` (또는 `dir`) | 현재 폴더의 파일 목록 |
| `mkdir my-project` | 새 폴더 만들기 |
| `exit` | 터미널 닫기 |

**작업 폴더에서 시작하기** — 보통 프로젝트 폴더로 이동한 뒤 `claude`를 켭니다:
```bash
cd C:\dev\my-project
claude
```

---

## 5. 자주 막히는 점

> [!warning] 흔한 오류와 해결
> - **`irm ... is not recognized`** → CMD가 아니라 **PowerShell**에서 실행하세요.
> - **`command not found: claude`** → 설치 후 터미널을 **닫았다 새로 여세요**(경로 갱신).
> - **SSL/TLS 오류 (Windows)** → 먼저 `[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12` 실행 후 설치 명령 재시도.
> - **로그인이 안 됨** → ① [claude.com/settings](https://claude.com/settings) 에서 구독이 활성인지 확인, ② 세션에서 `/logout` 후 다시 로그인, ③ PC 시간이 정확한지 확인.
>
> 그래도 막히면, 그 에러 메시지를 복사해 **Claude Code(또는 claude.ai)에게 "이게 무슨 뜻이고 어떻게 고쳐?"** 라고 물어보세요. 이것도 바이브 코딩입니다.

---

## (선택) VS Code와 함께 쓰기

코드 화면을 같이 보고 싶다면 [VS Code](https://code.visualstudio.com/Download)를 설치한 뒤, 확장(Extensions, `Ctrl+Shift+X`)에서 **"Claude Code"**를 검색해 설치하면 됩니다. 물론 **터미널만으로도** 이 교재의 모든 실습이 가능합니다.

---

## 다음

준비가 끝났다면 → [[00-getting-started|시작하기]] 로 가서 나머지 도구(Obsidian·GEE)를 준비하고, [[chapters/0-first-vibe-coding|0장]]에서 첫 실습을 시작하세요.

> 공식 문서: [code.claude.com/docs](https://code.claude.com/docs)
