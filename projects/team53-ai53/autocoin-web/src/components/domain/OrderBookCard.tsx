import { BookOpen } from 'lucide-react';
import type { BookTicker } from '../../types/api';
import { Card, Skeleton, Banner, EmptyState, Button } from '../common';
import styles from './OrderBookCard.module.css';

interface OrderBookCardProps {
  bookTicker: BookTicker | undefined;
  isLoading: boolean;
  isError: boolean;
  errorMessage?: string;
  onRefresh: () => void;
  isRefetching: boolean;
}

export function OrderBookCard({
  bookTicker,
  isLoading,
  isError,
  errorMessage,
  onRefresh,
  isRefetching,
}: OrderBookCardProps) {
  const renderContent = () => {
    if (isLoading) {
      return (
        <div className={styles.skeletonBlock}>
          <Skeleton height="16px" />
          <Skeleton height="16px" />
          <Skeleton height="16px" />
          <Skeleton height="16px" />
          <Skeleton height="16px" />
        </div>
      );
    }

    if (isError) {
      return (
        <Banner variant="danger">
          호가 조회에 실패했습니다. {errorMessage ?? '네트워크 연결을 확인해 주세요.'}
        </Banner>
      );
    }

    if (!bookTicker) {
      return (
        <EmptyState
          icon={<BookOpen size={32} />}
          title="호가 정보 없음"
          description="심볼을 선택한 뒤 조회해 주세요."
        />
      );
    }

    const { depth } = bookTicker;
    const bids = depth.bids.slice(0, 10);
    const asks = depth.asks.slice(0, 10);

    return (
      <div className={styles.container}>
        <div className={styles.columns}>
          <div className={styles.column}>
            <span className={`${styles.columnTitle} ${styles.bidsTitle}`}>
              매수 (Bids)
            </span>
            <div className={styles.headerRow}>
              <span>가격</span>
              <span className={styles.quantity}>수량</span>
            </div>
            {bids.map(([price, qty], i) => (
              <div className={styles.row} key={`bid-${i}`}>
                <span className={styles.bidPrice}>{price}</span>
                <span className={styles.quantity}>{qty}</span>
              </div>
            ))}
          </div>

          <div className={styles.column}>
            <span className={`${styles.columnTitle} ${styles.asksTitle}`}>
              매도 (Asks)
            </span>
            <div className={styles.headerRow}>
              <span>가격</span>
              <span className={styles.quantity}>수량</span>
            </div>
            {asks.map(([price, qty], i) => (
              <div className={styles.row} key={`ask-${i}`}>
                <span className={styles.askPrice}>{price}</span>
                <span className={styles.quantity}>{qty}</span>
              </div>
            ))}
          </div>
        </div>

        <span className={styles.meta}>
          lastUpdateId: {depth.lastUpdateId}
        </span>
      </div>
    );
  };

  return (
    <Card
      title="호가"
      subtitle="Binance Spot Testnet"
      actions={
        <Button
          variant="ghost"
          size="sm"
          onClick={onRefresh}
          loading={isRefetching}
        >
          새로고침
        </Button>
      }
    >
      {renderContent()}
    </Card>
  );
}
