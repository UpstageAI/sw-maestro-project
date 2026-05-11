import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Card, Banner, Button, Skeleton } from '../../components/common';
import { resumeOrder } from '../../api/testnet';
import { AgentStatusDisplay } from '../../components/domain/AgentStatusDisplay';
import { OrderForm } from '../../components/domain/OrderForm';
import { OrderStatusPanel } from '../../components/domain/OrderStatusPanel';
import { CancelOrderPanel } from '../../components/domain/CancelOrderPanel';
import { OrderLogList } from '../../components/domain/OrderLogList';
import { RunReportCard } from '../../components/domain/RunReportCard';
import type { OrderLogEntry } from '../../components/domain/OrderLogList';
import { useRunReport } from '../../hooks';
import type { AgentRunState } from '../../types/agent';
import type { ErrorResponse, OrderRunResponse, SpotOrderRequest } from '../../types/api';
import styles from './OrdersPage.module.css';

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }

  return '리포트를 불러오는 중 알 수 없는 오류가 발생했습니다.';
}

export function OrdersPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [orderLog, setOrderLog] = useState<OrderLogEntry[]>([]);
  const [latestRun, setLatestRun] = useState<OrderRunResponse | null>(null);
  const [latestOrderRequest, setLatestOrderRequest] = useState<SpotOrderRequest | null>(null);
  const [resumeError, setResumeError] = useState<string | null>(null);
  const latestReportQuery = useRunReport(latestRun?.runId ?? '');

  const resumeMutation = useMutation({
    mutationFn: resumeOrder,
    onSuccess: async (response) => {
      setLatestRun(response);
      setResumeError(null);
      setOrderLog((prev) => [...prev, { timestamp: Date.now(), response }]);
      await queryClient.invalidateQueries({
        queryKey: ['runReport', response.runId],
      });
    },
    onError: (err: unknown) => {
      const apiError = err as ErrorResponse;
      setResumeError(apiError?.message ?? '주문 재개 요청에 실패했습니다.');
    },
  });

  function handleOrderSuccess(response: OrderRunResponse) {
    setLatestRun(response);
    setResumeError(null);
    setOrderLog((prev) => [
      ...prev,
      { timestamp: Date.now(), response },
    ]);
  }

  function toAgentRunState(response: OrderRunResponse): AgentRunState {
    return {
      run_id: response.runId,
      lifecycle_status: response.lifecycleStatus,
      request_type: 'PLACE_ORDER_TEST',
      final_action: response.lifecycleStatus,
      hold_reason: response.holdReason ?? undefined,
    };
  }

  function handleApproveResume() {
    if (!latestRun) return;
    setResumeError(null);
    resumeMutation.mutate({
      runId: latestRun.runId,
      resumeReason: 'USER_APPROVED_ORDER',
      patchFields: {
        approval: {
          approved: true,
        },
      },
    });
  }

  function handleRetryResume() {
    if (!latestRun) return;
    setResumeError(null);
    resumeMutation.mutate({
      runId: latestRun.runId,
      resumeReason: 'USER_REQUESTED_RETRY',
      patchFields: {
        supplemental_user_input: {
          ...(latestOrderRequest ?? {}),
          market_snapshot_fresh: true,
        },
      },
    });
  }

  function handleOpenReport(runId: string) {
    navigate({
      pathname: '/reports',
      search: `?${new URLSearchParams({ runId }).toString()}`,
    });
  }

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>주문 테스트</h1>
      <Banner variant="warning">
        Binance Spot Testnet 가상 자금 기반 주문 테스트입니다. 실제 자금이
        사용되지 않습니다.
      </Banner>

      <div className={styles.grid}>
        <Card title="주문 생성" subtitle="Spot 현물 주문 테스트">
          <OrderForm
            onOrderSuccess={handleOrderSuccess}
            onOrderSubmitted={setLatestOrderRequest}
          />
          {latestRun?.lifecycleStatus === 'HOLD' && (
            <div className={styles.logSection}>
              <AgentStatusDisplay
                state={toAgentRunState(latestRun)}
                reasonCodes={latestRun.reasonCodes}
                description={resumeError ?? undefined}
                onApprove={
                  latestRun.holdReason === 'HOLD_REVIEW_REQUIRED'
                    ? handleApproveResume
                    : undefined
                }
                onRefetch={
                  latestRun.holdReason === 'HOLD_DATA_INSUFFICIENT'
                    ? handleRetryResume
                    : undefined
                }
              />
            </div>
          )}
        </Card>
        <Card title="주문 상태 조회" subtitle="orderId 또는 clientOrderId로 조회">
          <OrderStatusPanel />
        </Card>
        <Card title="주문 취소" subtitle="미체결 주문 취소">
          <CancelOrderPanel />
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
              AI 리포트는 참고 정보이며 최종 주문 실행과 재검증 권한은 백엔드에 있습니다.
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

      <div className={styles.logSection}>
        <Card title="최근 주문 테스트 기록">
          <OrderLogList entries={orderLog} />
        </Card>
      </div>
    </div>
  );
}
