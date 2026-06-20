import { PageLayout, SharedLayout } from "./quartz/cfg"
import * as Component from "./quartz/components"

// 목차(사이드바) 정렬 순서: 메인 지도 → 시작하기 → 사전 셋팅 → 0~6장 → 마무리
const tocOrder = [
  "00-home",
  "00-getting-started",
  "claude-code-setup",
  "0-first-vibe-coding",
  "1-prompts",
  "2-ndvi-map",
  "3-change-detection",
  "4-service",
  "5-agent-team",
  "6-deploy",
  "wrap-up",
]
const tocSort = (a: any, b: any) => {
  const rank = (n: any) => {
    const i = tocOrder.indexOf(n.slugSegment)
    return i === -1 ? 999 : i
  }
  return rank(a) - rank(b)
}

const explorer = Component.Explorer({
  title: "목차",
  folderDefaultState: "open",
  sortFn: tocSort,
})

// 모든 페이지 공통
export const sharedPageComponents: SharedLayout = {
  head: Component.Head(),
  header: [Component.PageTitle()], // ① 사이트 제목을 상단(헤더)으로
  afterBody: [],
  footer: Component.Footer({
    links: {
      GitHub: "https://github.com/dkccccc/dkccgeoaigeeharness",
    },
  }),
}

// 단일 노트 페이지
export const defaultContentPageLayout: PageLayout = {
  beforeBody: [
    Component.ConditionalRender({
      component: Component.Breadcrumbs(),
      condition: (page) => page.fileData.slug !== "index",
    }),
    Component.ArticleTitle(),
    Component.ContentMeta(),
    Component.TagList(),
  ],
  left: [
    Component.MobileOnly(Component.Spacer()),
    Component.Flex({
      components: [
        { Component: Component.Search(), grow: true },
        { Component: Component.Darkmode() },
        { Component: Component.ReaderMode() },
      ],
    }),
    explorer,
    Component.Graph(), // ③ 그래프 뷰를 왼쪽 사이드바 아래로
  ],
  right: [], // ② 오른쪽 섹션(목차·백링크 등) 전부 제거
}

// 목록(태그·폴더) 페이지
export const defaultListPageLayout: PageLayout = {
  beforeBody: [Component.Breadcrumbs(), Component.ArticleTitle(), Component.ContentMeta()],
  left: [
    Component.MobileOnly(Component.Spacer()),
    Component.Flex({
      components: [
        { Component: Component.Search(), grow: true },
        { Component: Component.Darkmode() },
      ],
    }),
    explorer,
    Component.Graph(),
  ],
  right: [],
}
