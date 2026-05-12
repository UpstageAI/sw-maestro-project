import { Wallet } from 'lucide-react';
import type { Balance } from '../../types/api';
import { Card, Skeleton, Banner, EmptyState, Button } from '../common';
import styles from './BalanceCard.module.css';

interface BalanceCardProps {
  balances: Balance[] | undefined;
  isLoading: boolean;
  isError: boolean;
  errorMessage?: string;
  onRefresh: () => void;
  isRefetching: boolean;
}

export function BalanceCard({
  balances,
  isLoading,
  isError,
  errorMessage,
  onRefresh,
  isRefetching,
}: BalanceCardProps) {
  const renderContent = () => {
    if (isLoading) {
      return (
        <div className={styles.skeletonRows}>
          <Skeleton height="20px" />
          <Skeleton height="20px" />
          <Skeleton height="20px" />
          <Skeleton height="20px" />
        </div>
      );
    }

    if (isError) {
      return (
        <Banner variant="danger">
          잔고 조회에 실패했습니다. {errorMessage ?? '네트워크 연결을 확인해 주세요.'}
        </Banner>
      );
    }

    if (!balances || balances.length === 0) {
      return (
        <EmptyState
          icon={<Wallet size={32} />}
          title="잔고 없음"
          description="Testnet 계정에 잔고가 없습니다."
        />
      );
    }

    return (
      <div className={styles.tableWrapper}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>자산</th>
              <th className={styles.numeric}>사용 가능</th>
              <th className={styles.numeric}>잠금</th>
            </tr>
          </thead>
          <tbody>
            {balances.map((b) => (
              <tr key={b.asset}>
                <td className={styles.asset}>{b.asset}</td>
                <td className={styles.numeric}>{b.free}</td>
                <td className={styles.numeric}>{b.locked}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  return (
    <Card
      title="잔고"
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
