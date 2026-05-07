import { useState } from 'react';
import { Card, Banner } from '../../components/common';
import { OrderForm } from '../../components/domain/OrderForm';
import { OrderStatusPanel } from '../../components/domain/OrderStatusPanel';
import { CancelOrderPanel } from '../../components/domain/CancelOrderPanel';
import { OrderLogList } from '../../components/domain/OrderLogList';
import type { OrderLogEntry } from '../../components/domain/OrderLogList';
import type { SpotOrderResponse } from '../../types/api';
import styles from './OrdersPage.module.css';

export function OrdersPage() {
  const [orderLog, setOrderLog] = useState<OrderLogEntry[]>([]);

  function handleOrderSuccess(response: SpotOrderResponse) {
    setOrderLog((prev) => [
      ...prev,
      { timestamp: Date.now(), response },
    ]);
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
          <OrderForm onOrderSuccess={handleOrderSuccess} />
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
