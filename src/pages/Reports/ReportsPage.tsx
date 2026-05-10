import { FileText } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import { Banner, Card, EmptyState, Skeleton } from '../../components/common';
import { RunReportCard } from '../../components/domain/RunReportCard';
import { useRunReport } from '../../hooks';
import styles from './ReportsPage.module.css';

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }

  return '리포트를 불러오는 중 알 수 없는 오류가 발생했습니다.';
}

export function ReportsPage() {
  const [searchParams] = useSearchParams();
  const runId = searchParams.get('runId')?.trim() ?? '';
  const reportQuery = useRunReport(runId);

  return (
    <div className={styles.page}>
      <h1 className={styles.heading}>에이전트 리포트</h1>
      <p className={styles.description}>
        URL 쿼리 파라미터 <code className={styles.inlineCode}>runId</code> 기준으로
        단일 실행 리포트를 조회합니다.
      </p>

      <div className={styles.section}>
        <h2 className={styles.sectionTitle}>실행 리포트</h2>

        {!runId && (
          <EmptyState
            icon={<FileText size={40} />}
            title="runId가 필요합니다"
            description="예: /reports?runId=run_report_001 형태로 접근하면 해당 실행 리포트를 불러옵니다."
          />
        )}

        {runId && reportQuery.isLoading && (
          <Card title="리포트를 불러오는 중" subtitle={`runId: ${runId}`}>
            <div className={styles.loadingState}>
              <Skeleton height="20px" width="220px" />
              <Skeleton height="16px" />
              <Skeleton height="16px" width="88%" />
              <Skeleton height="16px" width="72%" />
            </div>
          </Card>
        )}

        {runId && reportQuery.isError && (
          <Card title="리포트를 불러오지 못했습니다" subtitle={`runId: ${runId}`}>
            <Banner variant="danger">
              {getErrorMessage(reportQuery.error)}
            </Banner>
          </Card>
        )}

        {runId && reportQuery.report && !reportQuery.isLoading && !reportQuery.isError && (
          <div className={styles.reportList}>
            <RunReportCard runId={reportQuery.runId} report={reportQuery.report} />
          </div>
        )}
      </div>

      <div className={styles.section}>
        <h2 className={styles.sectionTitle}>실행 케이던스</h2>
        <Card title="아직 지원되지 않습니다" subtitle="Cadence event API 미연동">
          <p className={styles.placeholderText}>
            현재 Reports 페이지는 최종 실행 리포트만 실시간 조회합니다. 단계별 케이던스
            타임라인은 전용 API가 준비되면 연결할 예정입니다.
          </p>
        </Card>
      </div>

      <div className={styles.section}>
        <h2 className={styles.sectionTitle}>리포트 히스토리</h2>
        <Card title="아직 지원되지 않습니다" subtitle="과거 run 목록 API 미연동">
          <p className={styles.placeholderText}>
            여러 run의 이력 목록과 비교 보기는 아직 제공되지 않습니다. 현재는
            <code className={styles.inlineCode}>runId</code> 를 직접 지정한 단일 리포트 조회만 지원합니다.
          </p>
        </Card>
      </div>
    </div>
  );
}
