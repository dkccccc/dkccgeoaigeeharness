# dkccgeoaigeeharness

원격탐사 초급 연구자를 위한 **Claude Code + GeoAI + GEE + Harness** 강의 교재 제작 프로젝트. (참고: `RFP.md`)

## 하네스: 강의 교재 제작 (Courseware)

**목표:** 원격탐사 변화탐지 프로젝트를 관통 실습으로 삼아 GEE → GeoAI → Claude Code → Harness 4개 주제를 그 프로젝트를 만들며 배우는 교재를, **Obsidian LLM 위키**(마크다운 + 위키링크)로 제작한다. 실습 위주, 초급자 대상.

**트리거:** 교재·강의자료·실습 노트·커리큘럼·개념 노트·Obsidian 볼트의 생성/수정/보완/재실행 등 교재 제작 관련 작업 요청 시 `courseware-orchestrator` 스킬을 사용하라. 단순 질문은 직접 응답 가능.

**구성:** 에이전트 팀(5명) — curriculum-architect, content-author, lab-builder, tech-validator, obsidian-curator. 상세는 `.claude/agents/`·`.claude/skills/`·오케스트레이터 스킬 참조.

**변경 이력:**
| 날짜 | 변경 내용 | 대상 | 사유 |
|------|----------|------|------|
| 2026-06-18 | 초기 구성 (에이전트 5 + 스킬 5 + 오케스트레이터) | 전체 | 신규 하네스 구축 |
