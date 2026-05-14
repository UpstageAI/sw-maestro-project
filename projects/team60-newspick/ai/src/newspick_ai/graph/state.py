from typing import NotRequired, TypedDict


class ArticleState(TypedDict, total=False):
    id: str
    url: str
    title: str
    source: NotRequired[str]
    category: NotRequired[str]
    publishedAt: NotRequired[str]
    description: NotRequired[str]
    status: NotRequired[str]


class RefreshEvent(TypedDict):
    stage: str
    message: str
    articleIds: list[str]
    count: NotRequired[int]


class RefreshState(TypedDict):
    articles: list[ArticleState]
    events: list[RefreshEvent]
    categoryIds: NotRequired[list[str]]
    persistedArticleIds: NotRequired[list[str]]
    reportDate: NotRequired[str]
