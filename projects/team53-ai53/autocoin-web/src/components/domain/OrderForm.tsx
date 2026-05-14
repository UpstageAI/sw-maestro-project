import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { placeOrder } from '../../api/testnet';
import { Button } from '../common';
import { DEFAULT_SYMBOLS, DEFAULT_SYMBOL } from '../../constants/symbols';
import type {
  OrderSide,
  OrderType,
  OrderRunResponse,
  SpotOrderRequest,
  TimeInForce,
  ErrorResponse,
} from '../../types/api';
import styles from './OrderForm.module.css';

interface OrderFormProps {
  onOrderSuccess: (response: OrderRunResponse) => void;
  onOrderSubmitted?: (order: SpotOrderRequest) => void;
}

export function OrderForm({ onOrderSuccess, onOrderSubmitted }: OrderFormProps) {
  const [symbol, setSymbol] = useState<string>(DEFAULT_SYMBOL);
  const [side, setSide] = useState<OrderSide>('BUY');
  const [orderType, setOrderType] = useState<OrderType>('MARKET');
  const [quantity, setQuantity] = useState('');
  const [quoteOrderQty, setQuoteOrderQty] = useState('');
  const [price, setPrice] = useState('');
  const [timeInForce, setTimeInForce] = useState<TimeInForce>('GTC');
  const [error, setError] = useState<{ message: string; code?: string } | null>(
    null,
  );

  const mutation = useMutation({
    mutationFn: placeOrder,
    onSuccess: (data) => {
      onOrderSuccess(data);
      setError(null);
      resetInputs();
    },
    onError: (err: unknown) => {
      const apiError = err as ErrorResponse;
      setError({
        message: apiError?.message ?? '주문 요청에 실패했습니다.',
        code: apiError?.error_code,
      });
    },
  });

  function resetInputs() {
    setQuantity('');
    setQuoteOrderQty('');
    setPrice('');
  }

  function isFormValid(): boolean {
    if (orderType === 'MARKET') {
      if (side === 'BUY') return quoteOrderQty.trim() !== '';
      return quantity.trim() !== '';
    }
    return quantity.trim() !== '' && price.trim() !== '';
  }

  function handleSubmit() {
    const order: SpotOrderRequest = {
      symbol,
      side,
      type: orderType,
    };

    if (orderType === 'MARKET') {
      if (side === 'BUY') {
        order.quoteOrderQty = quoteOrderQty;
      } else {
        order.quantity = quantity;
      }
    } else {
      order.quantity = quantity;
      order.price = price;
      order.timeInForce = timeInForce;
    }

    setError(null);
    onOrderSubmitted?.(order);
    mutation.mutate(order);
  }

  const buttonText =
    side === 'BUY' ? 'Testnet 매수 주문 테스트' : 'Testnet 매도 주문 테스트';

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
        <span className={styles.label}>주문 방향</span>
        <div className={styles.selectorRow}>
          <button
            type="button"
            className={`${styles.buyButton} ${side === 'BUY' ? styles.active : ''}`}
            onClick={() => setSide('BUY')}
          >
            BUY (매수)
          </button>
          <button
            type="button"
            className={`${styles.sellButton} ${side === 'SELL' ? styles.active : ''}`}
            onClick={() => setSide('SELL')}
          >
            SELL (매도)
          </button>
        </div>
      </div>

      <div className={styles.fieldGroup}>
        <span className={styles.label}>주문 유형</span>
        <div className={styles.selectorRow}>
          <button
            type="button"
            className={`${styles.selectorButton} ${orderType === 'MARKET' ? styles.active : ''}`}
            onClick={() => setOrderType('MARKET')}
          >
            MARKET (시장가)
          </button>
          <button
            type="button"
            className={`${styles.selectorButton} ${orderType === 'LIMIT' ? styles.active : ''}`}
            onClick={() => setOrderType('LIMIT')}
          >
            LIMIT (지정가)
          </button>
        </div>
      </div>

      {orderType === 'MARKET' && side === 'BUY' && (
        <div className={styles.fieldGroup}>
          <span className={styles.label}>주문 금액 (Quote)</span>
          <input
            className={styles.input}
            type="text"
            inputMode="decimal"
            placeholder="예: 100 (USDT 기준 금액)"
            value={quoteOrderQty}
            onChange={(e) => setQuoteOrderQty(e.target.value)}
          />
          <span className={styles.inputHint}>
            USDT 기준으로 매수할 금액을 입력하세요
          </span>
        </div>
      )}

      {orderType === 'MARKET' && side === 'SELL' && (
        <div className={styles.fieldGroup}>
          <span className={styles.label}>수량</span>
          <input
            className={styles.input}
            type="text"
            inputMode="decimal"
            placeholder="예: 0.001"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
          />
          <span className={styles.inputHint}>매도할 수량을 입력하세요</span>
        </div>
      )}

      {orderType === 'LIMIT' && (
        <>
          <div className={styles.fieldGroup}>
            <span className={styles.label}>가격</span>
            <input
              className={styles.input}
              type="text"
              inputMode="decimal"
              placeholder="예: 65000.00"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
            />
          </div>
          <div className={styles.fieldGroup}>
            <span className={styles.label}>수량</span>
            <input
              className={styles.input}
              type="text"
              inputMode="decimal"
              placeholder="예: 0.001"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
            />
          </div>
          <div className={styles.fieldGroup}>
            <span className={styles.label}>Time in Force</span>
            <select
              className={styles.select}
              value={timeInForce}
              onChange={(e) => setTimeInForce(e.target.value as TimeInForce)}
            >
              <option value="GTC">GTC (Good Till Cancel)</option>
              <option value="IOC">IOC (Immediate or Cancel)</option>
              <option value="FOK">FOK (Fill or Kill)</option>
            </select>
          </div>
        </>
      )}

      {error && (
        <div className={styles.errorMessage}>
          <div>{error.message}</div>
          {error.code && (
            <div className={styles.errorCode}>Error code: {error.code}</div>
          )}
        </div>
      )}

      <Button
        variant="primary"
        size="lg"
        disabled={!isFormValid()}
        loading={mutation.isPending}
        onClick={handleSubmit}
      >
        {buttonText}
      </Button>
    </div>
  );
}
