import { ClipboardList } from 'lucide-react';
import { Badge, EmptyState } from '../common';
import { ORDER_STATUS_LABELS } from '../../constants/symbols';
import type { OrderRunLifecycleStatus, OrderRunResponse, OrderStatus } from '../../types/api';
import styles from './OrderLogList.module.css';

const STATUS_VARIANT_MAP: Record<OrderStatus, 'info' | 'success' | 'warning' | 'danger' | 'default'> = {
  NEW: 'info',
  PARTIALLY_FILLED: 'info',
  FILLED: 'success',
  CANCELED: 'warning',
  REJECTED: 'danger',
  EXPIRED: 'warning',
};

const LIFECYCLE_VARIANT_MAP: Record<
  OrderRunLifecycleStatus,
  'info' | 'success' | 'warning' | 'danger' | 'default'
> = {
  HOLD: 'warning',
  NO_ORDER: 'default',
  BE_REJECTED: 'danger',
  REPORT_READY: 'success',
};

interface OrderLogEntry {
  timestamp: number;
  response: OrderRunResponse;
}

interface OrderLogListProps {
  entries: OrderLogEntry[];
}

function formatTime(ts: number): string {
  const d = new Date(ts);
  return d.toLocaleString('ko-KR', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

export type { OrderLogEntry };

export function OrderLogList({ entries }: OrderLogListProps) {
  if (entries.length === 0) {
    return (
      <EmptyState
        icon={<ClipboardList size={32} />}
        title="주문 기록 없음"
        description="Testnet 주문 테스트를 실행하면 여기에 결과가 표시됩니다."
      />
    );
  }

  const sorted = [...entries].sort((a, b) => b.timestamp - a.timestamp);

  return (
    <div className={styles.container}>
      <div className={styles.list}>
        {sorted.map((entry) => {
          const { response } = entry;
          const statusLabel = response.status
            ? ORDER_STATUS_LABELS[response.status] ?? response.status
            : null;

          return (
            <div key={`${response.runId}-${entry.timestamp}`} className={styles.entry}>
              <span className={styles.timestamp}>{formatTime(entry.timestamp)}</span>
              <span className={styles.symbol}>{response.symbol ?? response.runId}</span>
              <span
                className={
                  response.side === 'BUY'
                    ? styles.sideBuy
                    : response.side === 'SELL'
                      ? styles.sideSell
                      : styles.type
                }
              >
                {response.side ?? 'RUN'}
              </span>
              <Badge
                label={response.lifecycleStatus}
                variant={LIFECYCLE_VARIANT_MAP[response.lifecycleStatus]}
              />
              <span className={styles.type}>{response.type ?? response.holdReason ?? '-'}</span>
              {statusLabel && response.status ? (
                <Badge
                  label={statusLabel}
                  variant={STATUS_VARIANT_MAP[response.status] ?? 'default'}
                />
              ) : null}
              <span className={styles.orderId}>#{response.orderId ?? response.runId}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
