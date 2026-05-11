import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { ApiError } from '../../api/client';
import {
  startAutoTradingSession,
  stopAutoTradingSession,
} from '../../api/testnet';
import { Banner, Badge, Button, Card, Skeleton } from '../../components/common';
import { AgentStatusDisplay } from '../../components/domain/AgentStatusDisplay';
import { RunReportCard } from '../../components/domain/RunReportCard';
import { useAutoTradingSession, useRunReport } from '../../hooks';
import type { AgentRunState } from '../../types/agent';
import type {
  AutoOrderRunResponse,
  AutoTradingSessionStatus,
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

function getSessionVariant(status: AutoTradingSessionStatus) {
  switch (status) {
    case 'ACTIVE':
      return 'success' as const;
    case 'STOPPING':
      return 'warning' as const;
    case 'STOPPED':
      return 'default' as const;
    case 'IDLE':
      return 'info' as const;
  }
}

function getSessionDescription(status: AutoTradingSessionStatus) {
  switch (status) {
    case 'ACTIVE':
      return '백엔드가 주기 tick을 계속 실행하며 최신 run 상태를 갱신합니다.';
    case 'STOPPING':
      return '중지 요청이 전달되었고, 백엔드가 현재 세션을 안전하게 정리 중입니다.';
    case 'STOPPED':
      return '직전 세션이 종료되었으며 최신 결과는 표시 전용으로 유지됩니다.';
    case 'IDLE':
      return '현재 실행 중인 자동매매 세션이 없습니다.';
  }
}

function getAmbiguityGuidance(rawText: string, holdReason?: string | null) {
  if (holdReason !== 'HOLD_INPUT_AMBIGUOUS') {
    return null;
  }

  return {
    title: '입력 모호성 개선 팁',
    message:
      '심볼, 방향, 금액, 조건을 한 문장에 함께 넣으면 보류를 줄일 수 있습니다. 예: BTCUSDT를 50 USDT만큼 시장가 매수해줘.',
    traderHint: rawText.includes('워뇨띠') || rawText.toLowerCase().includes('wonyotti')
      ? '현재 지시문에는 trader 키워드가 포함되어 있습니다.'
      : '워뇨띠 / BNF / 매억남 / 리버모어 같은 trader 이름을 명시하지 않으면 기본 trader가 사용되거나 첫 tick 전까지 미선택으로 보일 수 있습니다.',
  };
}

function formatTickInterval(seconds?: number | null) {
  if (!seconds) {
    return '미선택';
  }

  if (seconds % 60 === 0) {
    return `${seconds / 60}분 (${seconds}초)`;
  }

  return `${seconds}초`;
}

function formatTimestamp(value?: string | null) {
  if (!value) {
    return '—';
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString('ko-KR');
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
  const queryClient = useQueryClient();
  const [rawText, setRawText] = useState('');
  const sessionQuery = useAutoTradingSession();
  const session = sessionQuery.session;
  const latestRun = session?.latestRun ?? null;
  const latestReportQuery = useRunReport(latestRun?.runId ?? '');

  const startSessionMutation = useMutation({
    mutationFn: startAutoTradingSession,
    onSuccess: (response, variables) => {
      queryClient.setQueryData(['autoTradingSession'], response);
      setRawText(response.rawText ?? variables.rawText.trim());
    },
  });

  const stopSessionMutation = useMutation({
    mutationFn: stopAutoTradingSession,
    onSuccess: (response) => {
      queryClient.setQueryData(['autoTradingSession'], response);
    },
  });

  const intentEntries = toIntentEntries(latestRun?.normalizedOrderIntent);
  const mutationError = startSessionMutation.isError
    ? getSubmissionError(startSessionMutation.error)
    : stopSessionMutation.isError
      ? getSubmissionError(stopSessionMutation.error)
      : null;
  const isSessionRunning = session?.sessionStatus === 'ACTIVE' || session?.sessionStatus === 'STOPPING';
  const sessionStatus = session?.sessionStatus ?? 'IDLE';
  const sessionSubtitle = session?.sessionId
    ? `sessionId: ${session.sessionId}`
    : '백엔드 세션 상태 폴링';
  const ambiguityGuidance = getAmbiguityGuidance(session?.rawText ?? '', latestRun?.holdReason);

  function handleSubmit() {
    const trimmedRawText = rawText.trim();

    if (trimmedRawText.length === 0) {
      return;
    }

    startSessionMutation.mutate({ rawText: trimmedRawText });
  }

  function handleStop() {
    stopSessionMutation.mutate();
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
            자연어 지시문으로 백엔드 연속 자동매매 세션을 시작·중지하고, 최신 run 및
            리포트 상태를 폴링으로 확인합니다.
          </p>
        </div>
      </div>

      <Banner variant="warning">
        AI 해석과 리포트는 참고 정보입니다. 최종 주문 실행과 재검증 권한은 항상 백엔드에
        있으며, 이 화면은 Binance Spot Testnet 세션 제어 전용입니다.
      </Banner>

      <div className={styles.contentGrid}>
        <Card title="자동매매 세션 시작" subtitle="클라이언트는 로컬 루프를 소유하지 않습니다">
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
                placeholder="예: BTC를 계속 관찰하면서 5분 간격으로 상황을 평가하고, 조건이 불명확하면 주문하지 말아줘."
                rows={8}
              />
              <p className={styles.inputHint}>
                현재 텍스트만 백엔드 세션 시작 요청으로 전달되며, 이후 tick 루프와 최종
                실행 판단은 모두 백엔드가 소유합니다.
              </p>
            </div>

            {mutationError && (
              <Banner variant="danger">
                <div className={styles.errorContent}>
                  <span>{mutationError.message}</span>
                  {mutationError.code && (
                    <code className={styles.errorCode}>Error code: {mutationError.code}</code>
                  )}
                </div>
              </Banner>
            )}

            <div className={styles.actionRow}>
              <Button
                type="button"
                variant="primary"
                size="lg"
                loading={startSessionMutation.isPending}
                disabled={rawText.trim().length === 0 || isSessionRunning}
                onClick={handleSubmit}
              >
                연속 세션 시작
              </Button>

              <Button
                type="button"
                variant="danger"
                size="lg"
                loading={stopSessionMutation.isPending}
                disabled={!isSessionRunning}
                onClick={handleStop}
              >
                세션 중지 요청
              </Button>
            </div>
          </div>
        </Card>

        <Card title="현재 세션 상태" subtitle={sessionSubtitle}>
          {sessionQuery.isLoading && (
            <div className={styles.reportLoading}>
              <Skeleton height="20px" width="220px" />
              <Skeleton height="16px" />
              <Skeleton height="16px" width="88%" />
              <Skeleton height="16px" width="72%" />
            </div>
          )}

          {sessionQuery.isError && (
            <Banner variant="danger">
              {getErrorMessage(sessionQuery.error)}
            </Banner>
          )}

          {session && !sessionQuery.isLoading && !sessionQuery.isError && (
            <div className={styles.resultStack}>
              <div className={styles.summaryGridFour}>
                <div className={styles.summaryItem}>
                  <span className={styles.summaryLabel}>Session</span>
                  <div className={styles.summaryBadges}>
                    <Badge label={sessionStatus} variant={getSessionVariant(sessionStatus)} />
                    {session.stopRequested && (
                      <Badge label="STOP_REQUESTED" variant="warning" />
                    )}
                  </div>
                  <span className={styles.summaryMeta}>{getSessionDescription(sessionStatus)}</span>
                </div>

                <div className={styles.summaryItem}>
                  <span className={styles.summaryLabel}>Tick Interval</span>
                  <span className={styles.summaryValue}>
                    {formatTickInterval(session.selectedTickIntervalSeconds)}
                  </span>
                </div>

                <div className={styles.summaryItem}>
                  <span className={styles.summaryLabel}>Tick Count</span>
                  <span className={styles.summaryValue}>{session.tickCount}</span>
                </div>

                <div className={styles.summaryItem}>
                  <span className={styles.summaryLabel}>Selected Trader ID</span>
                  <span className={styles.summaryValue}>{session.selectedTraderId ?? '미선택'}</span>
                </div>
              </div>

              <div className={styles.section}>
                <h2 className={styles.sectionTitle}>현재 세션 지시문</h2>
                <div className={styles.rawTextPanel}>
                  {session.rawText?.trim() ? (
                    <p className={styles.rawTextValue}>{session.rawText}</p>
                  ) : (
                    <p className={styles.placeholder}>
                      백엔드에 등록된 자동매매 지시문이 아직 없습니다.
                    </p>
                  )}
                </div>
              </div>

              <div className={styles.section}>
                <h2 className={styles.sectionTitle}>세션 타임라인</h2>
                <div className={styles.metaGrid}>
                  <div className={styles.metaItem}>
                    <span className={styles.summaryLabel}>Started At</span>
                    <span className={styles.summaryValue}>{formatTimestamp(session.startedAt)}</span>
                  </div>
                  <div className={styles.metaItem}>
                    <span className={styles.summaryLabel}>Stopped At</span>
                    <span className={styles.summaryValue}>{formatTimestamp(session.stoppedAt)}</span>
                  </div>
                  <div className={styles.metaItem}>
                    <span className={styles.summaryLabel}>Last Tick Started</span>
                    <span className={styles.summaryValue}>{formatTimestamp(session.lastTickStartedAt)}</span>
                  </div>
                  <div className={styles.metaItem}>
                    <span className={styles.summaryLabel}>Last Tick Completed</span>
                    <span className={styles.summaryValue}>{formatTimestamp(session.lastTickCompletedAt)}</span>
                  </div>
                </div>
              </div>

              {(session.stopReason || session.latestError) && (
                <div className={styles.section}>
                  <h2 className={styles.sectionTitle}>중지 / 오류 정보</h2>
                  <div className={styles.feedbackStack}>
                    {session.stopReason && (
                      <Banner variant="warning">
                        <div className={styles.errorContent}>
                          <span>Stop reason: {session.stopReason}</span>
                        </div>
                      </Banner>
                    )}
                    {session.latestError && (
                      <Banner variant="danger">
                        <div className={styles.errorContent}>
                          <span>{session.latestError}</span>
                        </div>
                      </Banner>
                    )}
                  </div>
                </div>
              )}

              {ambiguityGuidance && (
                <div className={styles.section}>
                  <h2 className={styles.sectionTitle}>{ambiguityGuidance.title}</h2>
                  <div className={styles.feedbackStack}>
                    <Banner variant="info">
                      <div className={styles.errorContent}>
                        <span>{ambiguityGuidance.message}</span>
                        <span>{ambiguityGuidance.traderHint}</span>
                      </div>
                    </Banner>
                  </div>
                </div>
              )}

              <div className={styles.section}>
                <h2 className={styles.sectionTitle}>최신 실행 정보</h2>
                {!latestRun && (
                  <p className={styles.placeholder}>
                    세션이 tick을 실행하면 여기에서 lifecycle 상태, 정규화된 주문 의도,
                    최신 run 정보를 확인할 수 있습니다.
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
                        <span className={styles.summaryLabel}>Run ID</span>
                        <span className={styles.summaryValue}>{latestRun.runId}</span>
                      </div>

                      <div className={styles.summaryItem}>
                        <span className={styles.summaryLabel}>Trader ID</span>
                        <span className={styles.summaryValue}>
                          {latestRun.traderId ?? '미제공'}
                        </span>
                        {!latestRun.traderId && (
                          <span className={styles.summaryMeta}>
                            trader 명시가 없거나 첫 tick 전이면 값이 비어 있을 수 있습니다.
                          </span>
                        )}
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
              </div>
            </div>
          )}
        </Card>
      </div>

      {latestRun?.runId && (
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
