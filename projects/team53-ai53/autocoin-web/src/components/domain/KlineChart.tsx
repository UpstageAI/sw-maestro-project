import { useEffect, useRef, useCallback } from 'react';
import { createChart, type IChartApi, ColorType, CandlestickSeries } from 'lightweight-charts';
import { CandlestickChart } from 'lucide-react';
import type { KlineItem } from '../../types/api';
import { KLINE_INTERVALS, type KlineInterval } from '../../constants/symbols';
import { Card, Skeleton, Banner, EmptyState, Button } from '../common';
import styles from './KlineChart.module.css';

interface KlineChartProps {
  items: KlineItem[] | undefined;
  isLoading: boolean;
  isError: boolean;
  errorMessage?: string;
  interval: KlineInterval;
  onIntervalChange: (interval: KlineInterval) => void;
  onRefresh: () => void;
  isRefetching: boolean;
}

export function KlineChart({
  items,
  isLoading,
  isError,
  errorMessage,
  interval,
  onIntervalChange,
  onRefresh,
  isRefetching,
}: KlineChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  const buildChart = useCallback(() => {
    const container = chartContainerRef.current;
    if (!container || !items || items.length === 0) return;

    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
    }

    const chart = createChart(container, {
      width: container.clientWidth,
      height: 400,
      layout: {
        background: { type: ColorType.Solid, color: '#ffffff' },
        textColor: '#111827',
        fontFamily: "'Inter', sans-serif",
      },
      grid: {
        vertLines: { color: '#e5e7eb' },
        horzLines: { color: '#e5e7eb' },
      },
      timeScale: {
        borderColor: '#e5e7eb',
        timeVisible: true,
        secondsVisible: false,
      },
      rightPriceScale: {
        borderColor: '#e5e7eb',
      },
    });

    const candlestickSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#16a34a',
      downColor: '#dc2626',
      borderDownColor: '#dc2626',
      borderUpColor: '#16a34a',
      wickDownColor: '#dc2626',
      wickUpColor: '#16a34a',
    });

    const localOffsetSec = -(new Date().getTimezoneOffset() * 60);
    const data = items.map((k) => ({
      time: (k.openTime / 1000 + localOffsetSec) as import('lightweight-charts').UTCTimestamp,
      open: parseFloat(k.open),
      high: parseFloat(k.high),
      low: parseFloat(k.low),
      close: parseFloat(k.close),
    }));

    candlestickSeries.setData(data);
    chart.timeScale().fitContent();
    chartRef.current = chart;
  }, [items]);

  useEffect(() => {
    buildChart();

    return () => {
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }
    };
  }, [buildChart]);

  useEffect(() => {
    const container = chartContainerRef.current;
    const chart = chartRef.current;
    if (!container || !chart) return;

    const handleResize = () => {
      chart.applyOptions({ width: container.clientWidth });
    };

    const observer = new ResizeObserver(handleResize);
    observer.observe(container);

    return () => observer.disconnect();
  }, [items]);

  const renderContent = () => {
    if (isLoading) {
      return (
        <div className={styles.skeletonBlock}>
          <Skeleton height="16px" width="120px" />
          <Skeleton height="400px" />
        </div>
      );
    }

    if (isError) {
      return (
        <Banner variant="danger">
          캔들 데이터 조회에 실패했습니다. {errorMessage ?? '네트워크 연결을 확인해 주세요.'}
        </Banner>
      );
    }

    if (!items || items.length === 0) {
      return (
        <EmptyState
          icon={<CandlestickChart size={32} />}
          title="캔들 데이터 없음"
          description="심볼과 인터벌을 선택한 뒤 조회해 주세요."
        />
      );
    }

    return <div ref={chartContainerRef} className={styles.chartWrapper} />;
  };

  return (
    <Card
      title="캔들 차트"
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
      <div className={styles.container}>
        <div className={styles.controls}>
          <div className={styles.intervalSelector}>
            {KLINE_INTERVALS.map((iv) => (
              <button
                key={iv}
                type="button"
                className={`${styles.intervalButton} ${iv === interval ? styles.intervalButtonActive : ''}`}
                onClick={() => onIntervalChange(iv)}
              >
                {iv}
              </button>
            ))}
          </div>
        </div>
        {renderContent()}
      </div>
    </Card>
  );
}
