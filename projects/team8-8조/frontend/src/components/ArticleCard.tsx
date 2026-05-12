import type { NewsArticle } from '../types';

interface Props {
  article: NewsArticle;
}

export default function ArticleCard({ article }: Props) {
  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-4 flex flex-col gap-3 hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200 group">
      <div>
        <h3 className="font-bold text-slate-800 text-sm leading-snug line-clamp-2 group-hover:text-indigo-600 transition-colors">
          {article.title}
        </h3>
      </div>

      {article.summary && (
        <p className="text-slate-500 text-xs leading-relaxed line-clamp-3">
          {article.summary}
        </p>
      )}

      <div className="text-xs flex flex-wrap gap-1 items-center">
        <span className="font-semibold text-slate-600">{article.source}</span>
        {article.published_at && (
          <>
            <span className="text-slate-300">·</span>
            <span className="text-slate-400">{article.published_at}</span>
          </>
        )}
      </div>

      {article.tags.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {article.tags.map((tag) => (
            <span key={tag} className="bg-indigo-50 text-indigo-500 text-xs px-2 py-0.5 rounded-full font-medium">
              #{tag}
            </span>
          ))}
        </div>
      )}

      <a
        href={article.link}
        target="_blank"
        rel="noopener noreferrer"
        className="mt-auto text-center text-xs font-semibold text-indigo-600 bg-indigo-50 rounded-xl py-2 hover:bg-indigo-100 transition-colors"
      >
        원문 보기 →
      </a>
    </div>
  );
}
