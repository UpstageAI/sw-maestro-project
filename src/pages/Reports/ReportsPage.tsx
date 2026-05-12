import { FileText } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import { Banner, Card, EmptyState, Skeleton } from '../../components/common';
import { CadenceTimeline } from '../../components/domain/CadenceTimeline';
import { RunReportCard } from '../../components/domain/RunReportCard';
import { useRunReport, useRunReportCadence } from '../../hooks';
import { getErrorMessage } from '../../utils/error';
import styles from './ReportsPage.module.css';

export function ReportsPage() {
  const [searchParams] = useSearchParams();
  const runId = searchParams.get('runId')?.trim() ?? '';
  const reportQuery = useRunReport(runId);
  const cadenceQuery = useRunReportCadence(runId);

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

        {!runId && (
          <Card title="runId가 필요합니다" subtitle="케이던스도 같은 run 기준으로 조회됩니다.">
            <p className={styles.placeholderText}>
              리포트와 동일하게 <code className={styles.inlineCode}>runId</code> 를 지정해야
              단계별 케이던스를 불러올 수 있습니다.
            </p>
          </Card>
        )}

        {runId && cadenceQuery.isLoading && (
          <Card title="케이던스를 불러오는 중" subtitle={`runId: ${runId}`}>
            <div className={styles.loadingState}>
              <Skeleton height="16px" />
              <Skeleton height="16px" width="92%" />
              <Skeleton height="16px" width="84%" />
            </div>
          </Card>
        )}

        {runId && cadenceQuery.isError && (
          <Card title="케이던스를 불러오지 못했습니다" subtitle={`runId: ${runId}`}>
            <Banner variant="danger">{getErrorMessage(cadenceQuery.error)}</Banner>
          </Card>
        )}

        {runId && !cadenceQuery.isLoading && !cadenceQuery.isError && cadenceQuery.events.length > 0 && (
          <Card title="실행 케이던스" subtitle={`runId: ${cadenceQuery.runId}`}>
            <CadenceTimeline events={cadenceQuery.events} />
          </Card>
        )}

        {runId && !cadenceQuery.isLoading && !cadenceQuery.isError && cadenceQuery.events.length === 0 && (
          <Card title="케이던스 데이터가 없습니다" subtitle={`runId: ${runId}`}>
            <p className={styles.placeholderText}>
              현재 run에 대해 표시할 단계별 케이던스 이벤트가 없습니다.
            </p>
          </Card>
        )}
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
