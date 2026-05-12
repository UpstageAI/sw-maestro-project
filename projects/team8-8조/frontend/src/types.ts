export interface NewsArticle {
  title: string;
  summary: string;
  link: string;
  source: string;
  published_at: string;
  keyword: string;
  tags: string[];
}

export interface CollectionResult {
  interest: string;
  keywords: string[];
  collected_articles: NewsArticle[];
  collected_count: number;
  stored_count: number;
  skipped_existing_count: number;
  errors: string[];
}

export interface BriefingResult {
  interest: string;
  keywords: string[];
  collected_count: number;
  stored_count: number;
  skipped_existing_count: number;
  selected_articles: NewsArticle[];
  briefing_markdown: string;
  errors: string[];
}

export interface AppSettings {
  ai_mode: 'Demo' | 'Upstage';
  news_source: 'Naver(한글) + Google' | 'Google only';
  chroma_path: string;
  collection_name: string;
  per_keyword_limit: number;
  top_k: number;
  email_to_default: string;
}
