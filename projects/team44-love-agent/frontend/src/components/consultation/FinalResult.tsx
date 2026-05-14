// 최종 결과 섹션 카드 목록 — 상황 정리, 쟁점, 조언, 액션 아이템, 주의사항
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { FinalResult as FinalResultType } from '@/types';
import { ResultCategoryCard } from './ResultCategoryCard';
import { resultContent } from '@/content';

interface FinalResultProps {
  result: FinalResultType;
}

export function FinalResult({ result }: FinalResultProps) {
  return (
    <div className="flex flex-col gap-4">
      {/* 상황 정리 */}
      <Card className="p-4">
        <CardHeader className="p-0 pb-2">
          <CardTitle className="text-sm font-semibold">{resultContent.situationTitle}</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <p className="text-sm text-muted-foreground">{result.situationSummary}</p>
        </CardContent>
      </Card>

      {/* 의견이 갈린 지점 + 주요 쟁점 */}
      <div className="grid grid-cols-2 gap-4">
        {result.disagreements && result.disagreements.length > 0 && (
          <ResultCategoryCard
            title={resultContent.disagreementsTitle}
            items={result.disagreements}
          />
        )}
        <ResultCategoryCard
          title={resultContent.keyConflictsTitle}
          items={result.keyConflicts}
        />
      </div>

      {/* 최종 조언 */}
      <Card className="p-4">
        <CardHeader className="p-0 pb-2">
          <CardTitle className="text-sm font-semibold">{resultContent.adviceTitle}</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <p className="text-sm leading-relaxed">{result.advice}</p>
        </CardContent>
      </Card>

      {/* 바로 해볼 수 있는 행동 */}
      <Card className="p-4">
        <CardHeader className="p-0 pb-2">
          <CardTitle className="text-sm font-semibold">{resultContent.actionItemsTitle}</CardTitle>
        </CardHeader>
        <CardContent className="p-0 flex flex-col gap-2">
          {result.actionItems.map((item, i) => (
            <div key={i} className="flex items-start gap-2">
              <span className="mt-0.5 shrink-0 rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-primary">
                {item.timing === 'immediate' ? '즉시' : item.timing === 'short_term' ? '단기' : '장기'}
              </span>
              <div className="flex flex-col">
                <span className="text-xs font-semibold">{item.title}</span>
                <span className="text-xs text-muted-foreground">{item.detail}</span>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* 기억하면 좋은 점 */}
      {result.caveats && result.caveats.length > 0 && (
        <Card className="p-4">
          <CardHeader className="p-0 pb-2">
            <CardTitle className="text-sm font-semibold">{resultContent.caveatsTitle}</CardTitle>
          </CardHeader>
          <CardContent className="p-0 flex flex-col gap-1.5">
            {result.caveats.map((c, i) => (
              <p key={i} className="text-xs text-muted-foreground">• {c}</p>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
