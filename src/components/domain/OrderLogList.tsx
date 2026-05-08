import { ClipboardList } from 'lucide-react';
import { Badge, EmptyState } from '../common';
import { ORDER_STATUS_LABELS } from '../../constants/symbols';
import type { OrderStatus, SpotOrderResponse } from '../../types/api';
import styles from './OrderLogList.module.css';

const STATUS_VARIANT_MAP: Record<OrderStatus, 'info' | 'success' | 'warning' | 'danger' | 'default'> = {
  NEW: 'info',
  PARTIALLY_FILLED: 'info',
  FILLED: 'success',
  CANCELED: 'warning',
  REJECTED: 'danger',
  EXPIRED: 'warning',
};

interface OrderLogEntry {
  timestamp: number;
  response: SpotOrderResponse;
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
          return (
            <div key={`${response.orderId}-${entry.timestamp}`} className={styles.entry}>
              <span className={styles.timestamp}>{formatTime(entry.timestamp)}</span>
              <span className={styles.symbol}>{response.symbol}</span>
              <span className={response.side === 'BUY' ? styles.sideBuy : styles.sideSell}>
                {response.side}
              </span>
              <span className={styles.type}>{response.type}</span>
              <Badge
                label={ORDER_STATUS_LABELS[response.status] ?? response.status}
                variant={STATUS_VARIANT_MAP[response.status] ?? 'default'}
              />
              <span className={styles.orderId}>#{response.orderId}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
