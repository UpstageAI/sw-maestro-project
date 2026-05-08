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

export interface SpotOrderRequest {
  symbol: string;
  side: OrderSide;
  type: OrderType;
  quantity?: string;
  quoteOrderQty?: string;
  price?: string;
  timeInForce?: TimeInForce;
}

export interface SpotOrderResponse {
  orderId: number;
  symbol: string;
  clientOrderId: string;
  transactTime: number;
  price: string;
  origQty: string;
  executedQty: string;
  cummulativeQuoteQty: string;
  status: OrderStatus;
  timeInForce: TimeInForce;
  type: OrderType;
  side: OrderSide;
}

export interface OrderStatusResponse {
  orderId: number;
  symbol: string;
  clientOrderId: string;
  price: string;
  origQty: string;
  executedQty: string;
  cummulativeQuoteQty: string;
  status: OrderStatus;
  type: OrderType;
  side: OrderSide;
  time: number;
  updateTime: number;
}

export interface CancelOrderResponse {
  orderId: number;
  symbol: string;
  origClientOrderId: string;
  status: 'CANCELED';
  clientOrderId: string;
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
