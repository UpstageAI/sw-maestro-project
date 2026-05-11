import type { HoldReason } from './agent';

export interface Balance {
  asset: string;
  free: string;
  locked: string;
}

export interface BalanceSnapshot {
  balances: Balance[];
}

export interface TestnetConfig {
  restBaseUrl: string;
  wsStreamUrl: string;
  wsApiUrl: string;
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

export interface AutoOrderRequest {
  rawText: string;
}

export interface AutoSessionStartRequest {
  rawText: string;
}

export type JsonPrimitive = string | number | boolean | null;
export type JsonValue = JsonPrimitive | JsonValue[] | { [key: string]: JsonValue };

export interface NormalizedOrderIntent {
  symbol?: string | null;
  side?: OrderSide | null;
  type?: OrderType | null;
  quantity?: string | null;
  quoteOrderQty?: string | null;
  price?: string | null;
  timeInForce?: TimeInForce | null;
  [key: string]: JsonValue | undefined;
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

export interface AutoOrderRunResponse extends OrderRunResponse {
  normalizedOrderIntent?: NormalizedOrderIntent | null;
  traderId?: string | null;
  inferredPersona?: string | null;
}

export type AutoTradingSessionStatus = 'IDLE' | 'ACTIVE' | 'STOPPING' | 'STOPPED';

export interface AutoTradingSessionResponse {
  sessionId?: string | null;
  sessionStatus: AutoTradingSessionStatus;
  stopRequested: boolean;
  selectedTickIntervalSeconds?: number | null;
  rawText?: string | null;
  selectedTraderId?: string | null;
  tickCount: number;
  startedAt?: string | null;
  stoppedAt?: string | null;
  lastTickStartedAt?: string | null;
  lastTickCompletedAt?: string | null;
  stopReason?: string | null;
  latestError?: string | null;
  latestRun?: AutoOrderRunResponse | null;
}

export type PublishedRunLifecycleStatus = OrderRunLifecycleStatus | 'FAILED';

export interface RunDecisionTraceStage {
  reasonCodes: string[];
  evidenceRefs: string[];
  finalAction: string | null;
  notes: string | null;
}

export interface PublishedRunDecisionTrace {
  policy: RunDecisionTraceStage | null;
  risk: RunDecisionTraceStage | null;
  evaluator: RunDecisionTraceStage | null;
  execution: RunDecisionTraceStage | null;
  runSummary: RunDecisionTraceStage | null;
}

export interface PublishedOrderOutcome {
  orderId: number | null;
  symbol: string | null;
  status: OrderStatus | null;
  type: OrderType | null;
  side: OrderSide | null;
}

export interface PublishedRunReport {
  lifecycleStatus: PublishedRunLifecycleStatus;
  holdReason: HoldReason | null;
  reasonCodes: string[];
  userSummary: string | null;
  decisionTrace: PublishedRunDecisionTrace | null;
  order: PublishedOrderOutcome | null;
}

export interface RunReportResponse {
  runId: string;
  report: PublishedRunReport;
}

export interface ReportCadenceEventResponse {
  runId: string;
  eventType: string;
  lifecycleStatus: PublishedRunLifecycleStatus;
  createdAt: string;
}

export interface RunReportCadenceResponse {
  runId: string;
  events: ReportCadenceEventResponse[];
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
