import { useState, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { RefreshCw } from 'lucide-react';
import {
  fetchAccount,
  fetchTickerPrice,
  fetchBookTicker,
  fetchKlines,
} from '../../api/testnet';
import { useStreamStatus } from '../../hooks';
import {
  DEFAULT_SYMBOLS,
  DEFAULT_SYMBOL,
  DEFAULT_INTERVAL,
  type KlineInterval,
  type Symbol,
} from '../../constants/symbols';
import { Button } from '../../components/common';
import { BalanceCard } from '../../components/domain/BalanceCard';
import { PriceCard } from '../../components/domain/PriceCard';
import { OrderBookCard } from '../../components/domain/OrderBookCard';
import { KlineChart } from '../../components/domain/KlineChart';
import { StreamStatusCard } from '../../components/domain/StreamStatusCard';
import styles from './DashboardPage.module.css';

export function DashboardPage() {
  const [symbol, setSymbol] = useState<Symbol>(DEFAULT_SYMBOL);
  const [interval, setInterval] = useState<KlineInterval>(DEFAULT_INTERVAL);

  const accountQuery = useQuery({
    queryKey: ['account'],
    queryFn: fetchAccount,
    staleTime: 30_000,
  });

  const priceQuery = useQuery({
    queryKey: ['tickerPrice', symbol],
    queryFn: () => fetchTickerPrice(symbol),
    staleTime: 10_000,
  });

  const bookQuery = useQuery({
    queryKey: ['bookTicker', symbol],
    queryFn: () => fetchBookTicker(symbol),
    staleTime: 10_000,
  });

  const klineQuery = useQuery({
    queryKey: ['klines', symbol, interval],
    queryFn: () => fetchKlines(symbol, interval),
    staleTime: 30_000,
  });

  const stream = useStreamStatus();

  const refreshAll = useCallback(() => {
    accountQuery.refetch();
    priceQuery.refetch();
    bookQuery.refetch();
    klineQuery.refetch();
    stream.refetch();
  }, [accountQuery, priceQuery, bookQuery, klineQuery, stream]);

  const isAnyRefetching =
    accountQuery.isRefetching ||
    priceQuery.isRefetching ||
    bookQuery.isRefetching ||
    klineQuery.isRefetching ||
    stream.isRefetching;

  const handleSymbolChange = (newSymbol: Symbol) => {
    setSymbol(newSymbol);
  };

  const getErrorMessage = (error: unknown): string | undefined => {
    if (error instanceof Error) return error.message;
    return undefined;
  };

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <h1 className={styles.heading}>대시보드</h1>
          <p className={styles.description}>
            Binance Spot Testnet 실시간 시장 데이터를 조회합니다.
          </p>
        </div>

        <div className={styles.headerActions}>
          <div className={styles.symbolSelector}>
            {DEFAULT_SYMBOLS.map((s) => (
              <button
                key={s}
                type="button"
                className={`${styles.symbolButton} ${s === symbol ? styles.symbolButtonActive : ''}`}
                onClick={() => handleSymbolChange(s)}
              >
                {s}
              </button>
            ))}
          </div>

          <Button
            variant="primary"
            size="sm"
            icon={<RefreshCw size={14} />}
            onClick={refreshAll}
            loading={isAnyRefetching}
          >
            전체 조회
          </Button>
        </div>
      </div>

      <KlineChart
        items={klineQuery.data?.items}
        isLoading={klineQuery.isLoading && klineQuery.isFetching}
        isError={klineQuery.isError}
        errorMessage={getErrorMessage(klineQuery.error)}
        interval={interval}
        onIntervalChange={setInterval}
        onRefresh={() => klineQuery.refetch()}
        isRefetching={klineQuery.isRefetching}
      />

      <div className={styles.infoGrid}>
        <PriceCard
          ticker={priceQuery.data}
          isLoading={priceQuery.isLoading && priceQuery.isFetching}
          isError={priceQuery.isError}
          errorMessage={getErrorMessage(priceQuery.error)}
          onRefresh={() => priceQuery.refetch()}
          isRefetching={priceQuery.isRefetching}
        />
        <StreamStatusCard
          streamStatus={stream.streamStatus}
          isLoading={stream.isLoading}
          isError={stream.isError}
          onRefresh={() => stream.refetch()}
          isRefetching={stream.isRefetching}
        />
        <OrderBookCard
          bookTicker={bookQuery.data}
          isLoading={bookQuery.isLoading && bookQuery.isFetching}
          isError={bookQuery.isError}
          errorMessage={getErrorMessage(bookQuery.error)}
          onRefresh={() => bookQuery.refetch()}
          isRefetching={bookQuery.isRefetching}
        />
        <BalanceCard
          balances={accountQuery.data?.balances}
          isLoading={accountQuery.isLoading && accountQuery.isFetching}
          isError={accountQuery.isError}
          errorMessage={getErrorMessage(accountQuery.error)}
          onRefresh={() => accountQuery.refetch()}
          isRefetching={accountQuery.isRefetching}
        />
      </div>
    </div>
  );
}
