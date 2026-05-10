export const DEFAULT_SYMBOLS = ['BTCUSDT', 'ETHUSDT'] as const;
export type Symbol = (typeof DEFAULT_SYMBOLS)[number];
export const DEFAULT_SYMBOL: Symbol = 'BTCUSDT';

export const KLINE_INTERVALS = [
  '1m',
  '3m',
  '5m',
  '15m',
  '30m',
  '1h',
  '4h',
  '1d',
] as const;
export type KlineInterval = (typeof KLINE_INTERVALS)[number];
export const DEFAULT_INTERVAL: KlineInterval = '1m';

export const ORDER_STATUS_LABELS: Record<string, string> = {
  NEW: '신규',
  PARTIALLY_FILLED: '부분 체결',
  FILLED: '체결 완료',
  CANCELED: '취소됨',
  REJECTED: '거부됨',
  EXPIRED: '만료됨',
};
