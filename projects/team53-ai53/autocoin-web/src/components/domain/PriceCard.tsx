import { TrendingUp } from 'lucide-react';
import type { TickerPrice } from '../../types/api';
import { Card, Skeleton, Banner, EmptyState, Button } from '../common';
import styles from './PriceCard.module.css';

interface PriceCardProps {
  ticker: TickerPrice | undefined;
  isLoading: boolean;
  isError: boolean;
  errorMessage?: string;
  onRefresh: () => void;
  isRefetching: boolean;
}

export function PriceCard({
  ticker,
  isLoading,
  isError,
  errorMessage,
  onRefresh,
  isRefetching,
}: PriceCardProps) {
  const renderContent = () => {
    if (isLoading) {
      return (
        <div className={styles.skeletonBlock}>
          <Skeleton width="80px" height="16px" />
          <Skeleton width="200px" height="40px" />
        </div>
      );
    }

    if (isError) {
      return (
        <Banner variant="danger">
          가격 조회에 실패했습니다. {errorMessage ?? '네트워크 연결을 확인해 주세요.'}
        </Banner>
      );
    }

    if (!ticker) {
      return (
        <EmptyState
          icon={<TrendingUp size={32} />}
          title="가격 정보 없음"
          description="심볼을 선택한 뒤 조회해 주세요."
        />
      );
    }

    return (
      <div className={styles.priceDisplay}>
        <span className={styles.symbol}>{ticker.symbol}</span>
        <span className={styles.price}>{ticker.price}</span>
        <span className={styles.unit}>USDT</span>
      </div>
    );
  };

  return (
    <Card
      title="현재가"
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
