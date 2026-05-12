import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Search } from 'lucide-react';
import { fetchOrderStatus } from '../../api/testnet';
import { ApiError } from '../../api/client';
import { Button, Badge } from '../common';
import { DEFAULT_SYMBOLS, DEFAULT_SYMBOL, ORDER_STATUS_LABELS } from '../../constants/symbols';
import type { OrderStatus, OrderStatusResponse } from '../../types/api';
import styles from './OrderStatusPanel.module.css';

const STATUS_VARIANT_MAP: Record<OrderStatus, 'info' | 'success' | 'warning' | 'danger' | 'default'> = {
  NEW: 'info',
  PARTIALLY_FILLED: 'info',
  FILLED: 'success',
  CANCELED: 'warning',
  REJECTED: 'danger',
  EXPIRED: 'warning',
};

export function OrderStatusPanel() {
  const [symbol, setSymbol] = useState<string>(DEFAULT_SYMBOL);
  const [orderId, setOrderId] = useState('');
  const [clientOrderId, setClientOrderId] = useState('');
  const [result, setResult] = useState<OrderStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () =>
      fetchOrderStatus(symbol, {
        ...(orderId ? { orderId } : {}),
        ...(clientOrderId ? { origClientOrderId: clientOrderId } : {}),
      }),
    onSuccess: (data) => {
      setResult(data);
      setError(null);
    },
    onError: (err: unknown) => {
      const message =
        err instanceof ApiError
          ? err.errorResponse?.message ?? err.message
          : '주문 상태 조회에 실패했습니다.';
      setError(message);
      setResult(null);
    },
  });

  const canQuery = orderId.trim() !== '' || clientOrderId.trim() !== '';

  return (
    <div className={styles.container}>
      <div className={styles.fieldGroup}>
        <span className={styles.label}>심볼</span>
        <select
          className={styles.select}
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
        >
          {DEFAULT_SYMBOLS.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>

      <div className={styles.fieldGroup}>
        <span className={styles.label}>Order ID</span>
        <input
          className={styles.input}
          type="text"
          placeholder="숫자 Order ID"
          value={orderId}
          onChange={(e) => setOrderId(e.target.value)}
        />
      </div>

      <div className={styles.fieldGroup}>
        <span className={styles.label}>Client Order ID (선택)</span>
        <input
          className={styles.input}
          type="text"
          placeholder="origClientOrderId"
          value={clientOrderId}
          onChange={(e) => setClientOrderId(e.target.value)}
        />
      </div>

      <Button
        variant="secondary"
        icon={<Search size={16} />}
        disabled={!canQuery}
        loading={mutation.isPending}
        onClick={() => mutation.mutate()}
      >
        주문 상태 조회
      </Button>

      {error && <div className={styles.errorMessage}>{error}</div>}

      {result && (
        <div className={styles.resultCard}>
          <div className={styles.resultRow}>
            <span className={styles.resultLabel}>Order ID</span>
            <span className={styles.resultValue}>{result.orderId}</span>
          </div>
          <div className={styles.resultRow}>
            <span className={styles.resultLabel}>심볼</span>
            <span className={styles.resultValue}>{result.symbol}</span>
          </div>
          <div className={styles.resultRow}>
            <span className={styles.resultLabel}>상태</span>
            <Badge
              label={ORDER_STATUS_LABELS[result.status] ?? result.status}
              variant={STATUS_VARIANT_MAP[result.status] ?? 'default'}
            />
          </div>
          <div className={styles.resultRow}>
            <span className={styles.resultLabel}>체결 수량</span>
            <span className={styles.resultValue}>{result.executedQty}</span>
          </div>
        </div>
      )}
    </div>
  );
}
