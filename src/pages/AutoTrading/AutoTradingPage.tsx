import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { ApiError } from '../../api/client';
import { placeAutoOrder } from '../../api/testnet';
import { Banner, Badge, Button, Card, Skeleton } from '../../components/common';
import { AgentStatusDisplay } from '../../components/domain/AgentStatusDisplay';
import { RunReportCard } from '../../components/domain/RunReportCard';
import { useRunReport } from '../../hooks';
import type { AgentRunState } from '../../types/agent';
import type {
  AutoOrderRunResponse,
  JsonValue,
  NormalizedOrderIntent,
  OrderRunLifecycleStatus,
} from '../../types/api';
import styles from './AutoTradingPage.module.css';

const INTENT_LABELS: Record<string, string> = {
  symbol: '심볼',
  side: '주문 방향',
  type: '주문 유형',
  quantity: '수량',
  quoteOrderQty: '주문 금액',
  price: '지정 가격',
  timeInForce: 'Time in Force',
};

function getLifecycleVariant(status: OrderRunLifecycleStatus) {
  switch (status) {
    case 'REPORT_READY':
      return 'success' as const;
    case 'HOLD':
      return 'warning' as const;
    case 'NO_ORDER':
    case 'BE_REJECTED':
      return 'danger' as const;
  }
}

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }

  return '리포트를 불러오는 중 알 수 없는 오류가 발생했습니다.';
}

function getSubmissionError(error: unknown): { message: string; code?: string } {
  if (error instanceof ApiError) {
    return {
      message: error.errorResponse?.message ?? error.message,
      code: error.errorResponse?.error_code,
    };
  }

  if (error instanceof Error) {
    return { message: error.message };
  }

  return { message: '자연어 주문 요청에 실패했습니다.' };
}

function toAgentRunState(response: AutoOrderRunResponse): AgentRunState {
  return {
    run_id: response.runId,
    lifecycle_status: response.lifecycleStatus,
    request_type: 'AUTO_ORDER_TEST',
    final_action: response.lifecycleStatus,
    hold_reason: response.holdReason ?? undefined,
  };
}

function toIntentEntries(intent?: NormalizedOrderIntent | null) {
  if (!intent) {
    return [];
  }

  return Object.entries(intent).flatMap(([key, value]) => {
    if (value === undefined || value === null) {
      return [];
    }

    return [{ key, value }];
  });
}

function formatIntentLabel(key: string) {
  if (INTENT_LABELS[key]) {
    return INTENT_LABELS[key];
  }

  return key
    .replace(/([A-Z])/g, ' $1')
    .replace(/_/g, ' ')
    .trim();
}

function formatIntentValue(value: JsonValue): string {
  if (Array.isArray(value) || (typeof value === 'object' && value !== null)) {
    return JSON.stringify(value);
  }

  return String(value);
}

export function AutoTradingPage() {
  const navigate = useNavigate();
  const [rawText, setRawText] = useState('');
  const [latestRun, setLatestRun] = useState<AutoOrderRunResponse | null>(null);
  const latestReportQuery = useRunReport(latestRun?.runId ?? '');

  const autoOrderMutation = useMutation({
    mutationFn: placeAutoOrder,
    onSuccess: (response) => {
      setLatestRun(response);
    },
  });

  const intentEntries = toIntentEntries(latestRun?.normalizedOrderIntent);
  const submissionError = autoOrderMutation.isError
    ? getSubmissionError(autoOrderMutation.error)
    : null;

  function handleSubmit() {
    const trimmedRawText = rawText.trim();

    if (trimmedRawText.length === 0) {
      return;
    }

    autoOrderMutation.mutate({ rawText: trimmedRawText });
  }

  function handleOpenReport(runId: string) {
    navigate({
      pathname: '/reports',
      search: `?${new URLSearchParams({ runId }).toString()}`,
    });
  }

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <div className={styles.headerText}>
          <h1 className={styles.heading}>자연어 자동매매</h1>
          <p className={styles.description}>
            자연어 지시를 AI 주문 해석 엔드포인트로 전달하고, 백엔드가 정규화한 의도와
            실행 결과를 확인합니다.
          </p>
        </div>
      </div>

      <Banner variant="warning">
        AI 해석 결과는 참고 정보입니다. 최종 주문 실행과 재검증 권한은 항상 백엔드에
        있으며, 이 화면은 Binance Spot Testnet 전용입니다.
      </Banner>

      <div className={styles.contentGrid}>
        <Card title="자연어 주문 요청" subtitle="단건 실행 지시문 입력">
          <div className={styles.form}>
            <div className={styles.fieldGroup}>
              <label className={styles.label} htmlFor="auto-trading-raw-text">
                지시문
              </label>
              <textarea
                id="auto-trading-raw-text"
                className={styles.textarea}
                value={rawText}
                onChange={(event) => setRawText(event.target.value)}
                placeholder="예: BTCUSDT를 68000 아래에서 0.002 BTC만큼 분할 매수하되, 조건이 불분명하면 주문하지 마."
                rows={8}
              />
              <p className={styles.inputHint}>
                스트리밍이나 대화 이력 없이 현재 텍스트 한 건만 백엔드에 전달합니다.
              </p>
            </div>

            {submissionError && (
              <Banner variant="danger">
                <div className={styles.errorContent}>
                  <span>{submissionError.message}</span>
                  {submissionError.code && (
                    <code className={styles.errorCode}>Error code: {submissionError.code}</code>
                  )}
                </div>
              </Banner>
            )}

            <Button
              type="button"
              variant="primary"
              size="lg"
              loading={autoOrderMutation.isPending}
              disabled={rawText.trim().length === 0}
              onClick={handleSubmit}
            >
              자연어 주문 실행 요청 보내기
            </Button>
          </div>
        </Card>

        <Card
          title="최신 실행 결과"
          subtitle={latestRun ? `runId: ${latestRun.runId}` : '응답 대기'}
        >
          {!latestRun && (
            <p className={styles.placeholder}>
              자연어 주문 요청을 제출하면 여기에서 lifecycle 상태, 정규화된 주문 의도,
              최신 실행 리포트를 확인할 수 있습니다.
            </p>
          )}

          {latestRun && (
            <div className={styles.resultStack}>
              <div className={styles.summaryGrid}>
                <div className={styles.summaryItem}>
                  <span className={styles.summaryLabel}>Lifecycle</span>
                  <div className={styles.summaryBadges}>
                    <Badge
                      label={latestRun.lifecycleStatus}
                      variant={getLifecycleVariant(latestRun.lifecycleStatus)}
                    />
                    {latestRun.holdReason && (
                      <Badge label={latestRun.holdReason} variant="warning" />
                    )}
                  </div>
                </div>

                <div className={styles.summaryItem}>
                  <span className={styles.summaryLabel}>Trader ID</span>
                  <span className={styles.summaryValue}>
                    {latestRun.traderId ?? '미제공'}
                  </span>
                </div>

                <div className={styles.summaryItem}>
                  <span className={styles.summaryLabel}>추론 Persona</span>
                  <span className={styles.summaryValue}>
                    {latestRun.inferredPersona ?? '미제공'}
                  </span>
                </div>
              </div>

              <div className={styles.section}>
                <h2 className={styles.sectionTitle}>Reason Codes</h2>
                {latestRun.reasonCodes.length > 0 ? (
                  <div className={styles.reasonCodes}>
                    {latestRun.reasonCodes.map((code) => (
                      <Badge key={code} label={code} variant="default" />
                    ))}
                  </div>
                ) : (
                  <p className={styles.placeholder}>현재 응답에 reason code가 없습니다.</p>
                )}
              </div>

              <div className={styles.section}>
                <h2 className={styles.sectionTitle}>정규화된 주문 의도</h2>
                {intentEntries.length > 0 ? (
                  <div className={styles.intentGrid}>
                    {intentEntries.map(({ key, value }) => (
                      <div key={key} className={styles.intentItem}>
                        <span className={styles.intentLabel}>{formatIntentLabel(key)}</span>
                        <code className={styles.intentValue}>{formatIntentValue(value)}</code>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className={styles.placeholder}>
                    백엔드가 정규화된 주문 의도를 아직 반환하지 않았습니다.
                  </p>
                )}
              </div>

              {latestRun.lifecycleStatus !== 'REPORT_READY' && (
                <div className={styles.section}>
                  <h2 className={styles.sectionTitle}>현재 상태</h2>
                  <AgentStatusDisplay
                    state={toAgentRunState(latestRun)}
                    reasonCodes={latestRun.reasonCodes}
                    description="AI 판단 결과는 참고용이며, 최종 주문 실행 권한은 백엔드에 있습니다."
                  />
                </div>
              )}
            </div>
          )}
        </Card>
      </div>

      {latestRun && (
        <div className={styles.reportSection}>
          <Card
            title="최신 AI 실행 리포트"
            subtitle={`runId: ${latestRun.runId}`}
            actions={(
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => handleOpenReport(latestRun.runId)}
              >
                Reports에서 열기
              </Button>
            )}
          >
            <p className={styles.reportHint}>
              이 리포트는 AI 해석과 백엔드 실행 결과를 설명하기 위한 표시용 정보입니다.
            </p>

            {latestReportQuery.isLoading && (
              <div className={styles.reportLoading}>
                <Skeleton height="20px" width="220px" />
                <Skeleton height="16px" />
                <Skeleton height="16px" width="88%" />
                <Skeleton height="16px" width="72%" />
              </div>
            )}

            {latestReportQuery.isError && (
              <Banner variant="danger">
                {getErrorMessage(latestReportQuery.error)}
              </Banner>
            )}

            {latestReportQuery.report && !latestReportQuery.isLoading && !latestReportQuery.isError && (
              <RunReportCard
                runId={latestReportQuery.runId}
                report={latestReportQuery.report}
              />
            )}
          </Card>
        </div>
      )}
    </div>
  );
}
