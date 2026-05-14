import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Card, Banner } from '../../components/common';
import { resumeOrder } from '../../api/testnet';
import { AgentStatusDisplay } from '../../components/domain/AgentStatusDisplay';
import { OrderForm } from '../../components/domain/OrderForm';
import { OrderStatusPanel } from '../../components/domain/OrderStatusPanel';
import { CancelOrderPanel } from '../../components/domain/CancelOrderPanel';
import { OrderLogList } from '../../components/domain/OrderLogList';
import type { OrderLogEntry } from '../../components/domain/OrderLogList';
import type { AgentRunState } from '../../types/agent';
import type { ErrorResponse, OrderRunResponse, SpotOrderRequest } from '../../types/api';
import styles from './OrdersPage.module.css';

export function OrdersPage() {
  const [orderLog, setOrderLog] = useState<OrderLogEntry[]>([]);
  const [latestRun, setLatestRun] = useState<OrderRunResponse | null>(null);
  const [latestOrderRequest, setLatestOrderRequest] = useState<SpotOrderRequest | null>(null);
  const [resumeError, setResumeError] = useState<string | null>(null);

  const resumeMutation = useMutation({
    mutationFn: resumeOrder,
    onSuccess: (response) => {
      setLatestRun(response);
      setResumeError(null);
      setOrderLog((prev) => [...prev, { timestamp: Date.now(), response }]);
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

      <div className={styles.logSection}>
        <Card title="최근 주문 테스트 기록">
          <OrderLogList entries={orderLog} />
        </Card>
      </div>
    </div>
  );
}
