# 온라인 위키 (Quartz → GitHub Pages)

`vault/`(Obsidian 교재)를 **웹사이트로 공개**하는 설정입니다. 수강생은 Obsidian 설치 없이 브라우저 링크로 교재를 읽을 수 있습니다.

## 어떻게 동작하나
- `vault/`의 마크다운 노트를 [Quartz](https://quartz.jzhao.xyz)(v4.5.2)가 위키링크·콜아웃·그래프·검색이 되는 정적 사이트로 변환합니다.
- 빌드·배포는 **GitHub Actions(클라우드)**가 합니다 → 내 PC에 Node 설치 불필요.
- `main`에 `vault/**`가 바뀌어 푸시되면 자동으로 다시 배포됩니다.

## 최초 1회 설정 (사람이 클릭해야 하는 단 하나)
GitHub 저장소에서:
1. **Settings → Pages**
2. **Build and deployment → Source** 를 **`GitHub Actions`** 로 선택
3. 끝. 다음 푸시(또는 Actions 탭에서 `Deploy Wiki` 수동 실행)부터 사이트가 만들어집니다.

## 주소
```
https://dkccccc.github.io/dkccgeoaigeeharness/
```
첫 화면은 `00-홈`(메인 지도)입니다.

## 구성 파일
- `wiki/quartz.config.ts` — 사이트 제목·주소·언어·테마 (빌드 시 Quartz 루트로 복사됨)
- `.github/workflows/deploy-wiki.yml` — 클라우드 빌드·배포 워크플로

## 수정하고 싶을 때
- 제목/색/주소 → `wiki/quartz.config.ts`
- 교재 내용 → `vault/`의 노트 (바뀌면 자동 재배포)
