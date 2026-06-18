---
name: courseware-orchestrator
description: 원격탐사 초급자용 'Claude Code+GeoAI+GEE+Harness' 통합 프로젝트형 강의 교재를 Obsidian LLM 위키로 제작하는 에이전트 팀을 조율한다. 교재/강의자료/실습 노트/커리큘럼/볼트 생성·제작 요청 시 사용. 후속 작업: 교재 수정·보완·업데이트·재실행, 특정 챕터/실습/개념만 다시, 이전 결과 기반 개선, QA 재검증, 볼트 재조립 요청 시에도 반드시 이 스킬을 사용.
---

# Courseware Orchestrator (교재 제작 오케스트레이터)

원격탐사 변화탐지 프로젝트를 관통 실습으로 삼아 GEE → GeoAI → Claude Code → Harness를 가르치는 강의 교재를, Obsidian LLM 위키 형태로 제작하는 에이전트 팀을 조율한다.

## 실행 모드: 에이전트 팀

생성-검증 + 파이프라인 혼합. 한 팀(5명)이 SendMessage·공유 작업 목록으로 자체 조율하며, tech-validator가 모듈 완성 즉시 점진적으로 검증한다.

## 에이전트 구성

| 팀원 | 타입 | 역할 | 스킬 | 출력 |
|------|------|------|------|------|
| curriculum-architect | general-purpose | 학습 경로 + 볼트 골격 + 노트 매니페스트 | curriculum-design | `_workspace/01_curriculum/` |
| content-author | general-purpose | 개념 노트(초급자용, 위키링크) | concept-authoring | `_workspace/02_concepts/` |
| lab-builder | general-purpose | 단계별 실습 노트(복붙 가능) | lab-authoring | `_workspace/03_labs/` |
| tech-validator | general-purpose | 코드 실행·기술 정확성·경계면 정합성 QA | courseware-qa | `_workspace/04_qa/` |
| obsidian-curator | general-purpose | 볼트 조립·링크 무결성·MOC·최종 내보내기 | obsidian-vault | `vault/` (최종) |

모든 팀원은 `model: "opus"`.

## 워크플로우

### Phase 0: 컨텍스트 확인 (후속 작업 지원)

1. `_workspace/` 존재 여부 확인.
2. 실행 모드 결정:
   - **미존재** → 초기 실행. Phase 1로.
   - **존재 + 부분 수정 요청**("3챕터 실습만 다시", "정사보정 개념 보완") → **부분 재실행**. 해당 팀원만 호출하고, 그 팀원에게 기존 산출물 경로를 줘서 읽고 피드백만 반영하게 한다. 이후 tech-validator 재검증 + obsidian-curator 재조립.
   - **존재 + 새 입력**(새 RFP/범위) → **새 실행**. 기존 `_workspace/`를 `_workspace_{YYYYMMDD_HHMMSS}/`로 이동 후 Phase 1.

### Phase 1: 준비
1. 사용자 요청 분석 — 범위·강조 주제·산출 경로 파악. 미지정 항목은 RFP 기본값 사용(대상: 원격탐사 초급자, 형식: Obsidian 볼트, 구성: 통합 프로젝트형).
2. `_workspace/` 생성(또는 새 실행 시 기존 보관 후 재생성).
3. 참고 소스를 `_workspace/00_input/`에 메모: `RFP.md`, `C:\dev\dkchangedetection`, `C:\dev\dkidi`, `https://github.com/taehojo/vibecoding`.

### Phase 2: 팀 구성
1. `TeamCreate(team_name: "courseware-team", members: [...])` — 위 5명, 각 `model: "opus"`, prompt에 역할·담당 스킬·산출 경로 명시.
2. `TaskCreate`로 작업 등록(의존성 포함):
   - T1 설계: curriculum-architect — 매니페스트 작성 (선행 없음)
   - T2 개념 작성: content-author — `depends_on: [T1]`
   - T3 실습 작성: lab-builder — `depends_on: [T1]`
   - T4 점진 QA: tech-validator — T2/T3 모듈 완성분부터 검사 (T2·T3와 병행)
   - T5 볼트 조립: obsidian-curator — `depends_on: [T2, T3, T4]`

### Phase 3: 설계 (게이트)
**실행 방식:** curriculum-architect 단독 → 팀 공유.
- architect가 `00_outline.md`·`01_vault-structure.md`·`02_note-manifest.md`를 만들고 리더+팀에 SendMessage로 공유.
- 매니페스트가 content-author·lab-builder의 작업 명세이자 위키링크 파일명의 단일 출처다. 이 게이트를 통과해야 작성 단계로 간다.

### Phase 4: 작성 + 점진 검증 (병렬)
**실행 방식:** 팀원 자체 조율.
- content-author와 lab-builder가 매니페스트에서 자기 노트를 claim해 병렬 작성.
- 두 사람은 개념↔실습 위키링크 파일명을 SendMessage로 맞춘다(깨진 링크 예방).
- **모듈이 하나 완성될 때마다** lab-builder/content-author가 tech-validator에 알리고, validator는 즉시 그 모듈과 인접 모듈의 경계면을 검사한다(전체 완성을 기다리지 않음).
- validator의 발견은 해당 작성자에게 SendMessage로 라우팅 → 수정 → regression check.

**산출물 경로:**
| 팀원 | 경로 |
|------|------|
| content-author | `_workspace/02_concepts/{매니페스트 경로}` |
| lab-builder | `_workspace/03_labs/{매니페스트 경로}` (+ `assets/`) |
| tech-validator | `_workspace/04_qa/qa-report.md` |

### Phase 5: 조립 + 내보내기
**실행 방식:** obsidian-curator 주도.
- QA 통과분으로 볼트를 조립, MOC 작성, 링크 무결성 검사(깨진 링크 0·고아 노트 0), 태그 일관화.
- 최종 볼트를 사용자 지정 경로(미지정 시 `vault/`)로 내보내고 `_workspace/05_curation/link-audit.md` 작성.

### Phase 6: 정리 + 피드백
1. 팀원에게 종료 요청, `TeamDelete`.
2. `_workspace/` 보존(감사 추적).
3. 사용자에게 결과 요약(생성 챕터/노트 수, QA 결과, 볼트 경로) 보고.
4. **피드백 요청**: "개선할 부분이나 바꾸고 싶은 팀 구성/워크플로우가 있나요?" — 있으면 Phase 0 부분 재실행으로 반영, CLAUDE.md 변경 이력 갱신.

## 데이터 흐름

```
[리더] TeamCreate + TaskCreate
   │
architect ─ 매니페스트 ─→ ┌ content-author ─ 개념노트 ┐
                         └ lab-builder ──── 실습노트 ┘
                                 │ (모듈 완성마다)
                          tech-validator ── qa-report (라우팅·재검증)
                                 ↓ (QA 통과)
                          obsidian-curator ── 볼트 조립·MOC·링크검사
                                 ↓
                          vault/ (최종 산출물)
```

데이터 전달: **태스크 기반**(조율) + **파일 기반**(`_workspace/` 산출물) + **메시지 기반**(위키링크 파일명·QA 라우팅 실시간 소통).

## 에러 핸들링

| 상황 | 전략 |
|------|------|
| 팀원 1명 실패/중지 | 리더 감지 → SendMessage 상태 확인 → 재시작 또는 작업 재할당 |
| 팀원 과반 실패 | 사용자에게 알리고 진행 여부 확인 |
| 코드 검증 불가(환경 제약) | tech-validator가 참고 프로젝트로 대조 판정, 근거 명시 (추측 금지) |
| 깨진 위키링크 | curator가 매니페스트 대조 후 수정 또는 작성자에 요청, 삭제 안 함 |
| 개념↔실습 용어 충돌 | 출처 병기, 삭제하지 않고 작성자에 라우팅 |
| 타임아웃 | 완성·QA통과 모듈만으로 볼트 조립, 미완성 노트는 `검수중` 표시 |

## 테스트 시나리오

### 정상 흐름
1. 사용자: "교재 만들어줘". Phase 1에서 범위·경로 확정(기본값 적용).
2. Phase 2에서 5명 팀 + 5개 작업(의존성) 등록.
3. Phase 3에서 architect가 매니페스트 게이트 통과.
4. Phase 4에서 author/lab이 병렬 작성, validator가 모듈마다 점진 QA·라우팅.
5. Phase 5에서 curator가 볼트 조립·링크 검사.
6. 예상 결과: `vault/`에 MOC + 개념/실습 노트, 깨진 링크 0, `_workspace/` 보존.

### 에러 흐름
1. Phase 4에서 lab-builder의 GEE 코드가 다음 실습 입력과 산출물명 불일치(경계면 버그).
2. tech-validator가 점진 QA에서 감지 → lab-builder에 SendMessage 라우팅.
3. lab-builder가 산출물명 통일 수정 → validator regression check 통과.
4. curator가 정합화된 노트로 볼트 조립.
5. 최종 보고서에 해당 수정 이력 기록.

## 후속 작업 시 동작
- 부분 수정 요청("4챕터 Harness 실습만 보강") → Phase 0에서 부분 재실행 판정 → lab-builder만 호출(기존 산출물 읽고 개선) → tech-validator 재검증 → curator 재조립. architect/content-author는 건너뜀.
