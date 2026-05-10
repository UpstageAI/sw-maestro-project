import type { HoldReason, ReportPayload } from './agent';

export interface Balance {
  asset: string;
  free: string;
  locked: string;
}

export interface BalanceSnapshot {
  balances: Balance[];
}

export interface TickerPrice {
  symbol: string;
  price: string;
}

export interface DepthEntry {
  price: string;
  quantity: string;
}

export interface DepthSnapshot {
  lastUpdateId: number;
  bids: [string, string][];
  asks: [string, string][];
}

export interface BookTicker {
  symbol: string;
  bidPrice: string;
  bidQty: string;
  askPrice: string;
  askQty: string;
  depth: DepthSnapshot;
}

export interface KlineItem {
  openTime: number;
  open: string;
  high: string;
  low: string;
  close: string;
  volume: string;
}

export interface KlineResponse {
  symbol: string;
  interval: string;
  items: KlineItem[];
}

export type OrderSide = 'BUY' | 'SELL';
export type OrderType = 'MARKET' | 'LIMIT';
export type TimeInForce = 'GTC' | 'IOC' | 'FOK';

export type OrderStatus =
  | 'NEW'
  | 'PARTIALLY_FILLED'
  | 'FILLED'
  | 'CANCELED'
  | 'REJECTED'
  | 'EXPIRED';

export type OrderRunLifecycleStatus =
  | 'HOLD'
  | 'NO_ORDER'
  | 'BE_REJECTED'
  | 'REPORT_READY';

export interface SpotOrderRequest {
  symbol: string;
  side: OrderSide;
  type: OrderType;
  quantity?: string;
  quoteOrderQty?: string;
  price?: string;
  timeInForce?: TimeInForce;
}

export interface OrderRunResponse {
  runId: string;
  lifecycleStatus: OrderRunLifecycleStatus;
  holdReason?: HoldReason | null;
  orderId?: number | null;
  symbol?: string | null;
  status?: OrderStatus | null;
  type?: OrderType | null;
  side?: OrderSide | null;
  reasonCodes: string[];
}

export interface RunReportResponse {
  runId: string;
  report: ReportPayload;
}

export interface ResumeCommandPayload {
  runId: string;
  resumeReason: string;
  patchFields: Record<string, unknown>;
}

export interface OrderStatusResponse {
  orderId: number;
  symbol: string;
  status: OrderStatus;
  executedQty: string;
}

export interface CancelOrderResponse {
  orderId: number;
  symbol: string;
  status: OrderStatus;
}

export interface ErrorResponse {
  error_code: string;
  message: string;
  detail?: string;
  request_id?: string;
  timestamp: string;
}

export interface TickerEvent {
  e: string;
  s: string;
  c: string;
  o: string;
  h: string;
  l: string;
  v: string;
  q: string;
}

export interface StreamStatus {
  connected: boolean;
  streamName: string | null;
  lastEvent: TickerEvent | null;
}
