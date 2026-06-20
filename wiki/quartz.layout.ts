import { PageLayout, SharedLayout } from "./quartz/cfg"
import * as Component from "./quartz/components"

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
    Component.Explorer(),
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
    Component.Explorer(),
    Component.Graph(),
  ],
  right: [],
}
