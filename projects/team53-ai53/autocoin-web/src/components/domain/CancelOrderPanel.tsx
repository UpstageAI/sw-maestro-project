import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { XCircle } from 'lucide-react';
import { cancelOrder } from '../../api/testnet';
import { ApiError } from '../../api/client';
import { Button, Badge } from '../common';
import { DEFAULT_SYMBOLS, DEFAULT_SYMBOL, ORDER_STATUS_LABELS } from '../../constants/symbols';
import type { CancelOrderResponse } from '../../types/api';
import styles from './CancelOrderPanel.module.css';

export function CancelOrderPanel() {
  const [symbol, setSymbol] = useState<string>(DEFAULT_SYMBOL);
  const [orderId, setOrderId] = useState('');
  const [clientOrderId, setClientOrderId] = useState('');
  const [showConfirm, setShowConfirm] = useState(false);
  const [result, setResult] = useState<CancelOrderResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () =>
      cancelOrder(symbol, {
        ...(orderId ? { orderId: Number(orderId) } : {}),
        ...(clientOrderId ? { origClientOrderId: clientOrderId } : {}),
      }),
    onSuccess: (data) => {
      setResult(data);
      setError(null);
      setShowConfirm(false);
    },
    onError: (err: unknown) => {
      const message =
        err instanceof ApiError
          ? err.errorResponse?.message ?? err.message
          : '주문 취소에 실패했습니다.';
      setError(message);
      setResult(null);
      setShowConfirm(false);
    },
  });

  const canCancel = orderId.trim() !== '' || clientOrderId.trim() !== '';

  function handleCancelClick() {
    setShowConfirm(true);
  }

  function handleConfirm() {
    mutation.mutate();
  }

  function handleDismiss() {
    setShowConfirm(false);
  }

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
        variant="danger"
        icon={<XCircle size={16} />}
        disabled={!canCancel}
        loading={mutation.isPending}
        onClick={handleCancelClick}
      >
        주문 취소
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
              variant="warning"
            />
          </div>
        </div>
      )}

      {showConfirm && (
        <div className={styles.confirmOverlay} onClick={handleDismiss}>
          <div
            className={styles.confirmDialog}
            onClick={(e) => e.stopPropagation()}
          >
            <h4 className={styles.confirmTitle}>주문 취소 확인</h4>
            <p className={styles.confirmMessage}>
              정말로 이 주문을 취소하시겠습니까? 이 작업은 되돌릴 수 없습니다.
            </p>
            <div className={styles.confirmActions}>
              <Button variant="ghost" onClick={handleDismiss}>
                돌아가기
              </Button>
              <Button
                variant="danger"
                loading={mutation.isPending}
                onClick={handleConfirm}
              >
                취소 확인
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
