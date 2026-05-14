import { ENDPOINTS } from '../constants/endpoints';
import type {
  AutoSessionStartRequest,
  AutoTradingSessionResponse,
  BalanceSnapshot,
  BookTicker,
  CancelOrderResponse,
  KlineResponse,
  OrderRunResponse,
  RunReportCadenceResponse,
  RunReportResponse,
  OrderStatusResponse,
  ResumeCommandPayload,
  SpotOrderRequest,
  StreamStatus,
  TestnetConfig,
  TickerPrice,
} from '../types/api';
import { del, get, post } from './client';

export function fetchAccount(): Promise<BalanceSnapshot> {
  return get<BalanceSnapshot>(ENDPOINTS.account);
}

export function fetchTestnetConfig(): Promise<TestnetConfig> {
  return get<TestnetConfig>(ENDPOINTS.config);
}

export function fetchTickerPrice(symbol: string): Promise<TickerPrice> {
  return get<TickerPrice>(ENDPOINTS.tickerPrice, { symbol });
}

export function fetchBookTicker(symbol: string): Promise<BookTicker> {
  return get<BookTicker>(ENDPOINTS.tickerBook, { symbol });
}

export function fetchKlines(
  symbol: string,
  interval: string,
  limit = '30',
): Promise<KlineResponse> {
  return get<KlineResponse>(ENDPOINTS.klines, { symbol, interval, limit });
}

export function placeOrder(
  order: SpotOrderRequest,
): Promise<OrderRunResponse> {
  return post<OrderRunResponse>(ENDPOINTS.orders, order);
}

export function startAutoTradingSession(
  payload: AutoSessionStartRequest,
): Promise<AutoTradingSessionResponse> {
  return post<AutoTradingSessionResponse>(ENDPOINTS.ordersAutoSessionStart, payload);
}

export function stopAutoTradingSession(): Promise<AutoTradingSessionResponse> {
  return post<AutoTradingSessionResponse>(ENDPOINTS.ordersAutoSessionStop, undefined);
}

export function fetchAutoTradingSession(): Promise<AutoTradingSessionResponse> {
  return get<AutoTradingSessionResponse>(ENDPOINTS.ordersAutoSession);
}

export function resumeOrder(
  payload: ResumeCommandPayload,
): Promise<OrderRunResponse> {
  return post<OrderRunResponse>(ENDPOINTS.ordersResume, payload);
}

export function fetchRunReport(runId: string): Promise<RunReportResponse> {
  return get<RunReportResponse>(ENDPOINTS.ordersReport, { runId });
}

export function fetchRunReportCadence(
  runId: string,
): Promise<RunReportCadenceResponse> {
  return get<RunReportCadenceResponse>(ENDPOINTS.ordersReportCadence, { runId });
}

export function fetchOrderStatus(
  symbol: string,
  identifier: { orderId?: string; origClientOrderId?: string },
): Promise<OrderStatusResponse> {
  return get<OrderStatusResponse>(ENDPOINTS.orderStatus, {
    symbol,
    ...(identifier.orderId ? { orderId: identifier.orderId } : {}),
    ...(identifier.origClientOrderId
      ? { origClientOrderId: identifier.origClientOrderId }
      : {}),
  });
}

export function cancelOrder(
  symbol: string,
  identifier: { orderId?: number; origClientOrderId?: string },
): Promise<CancelOrderResponse> {
  return del<CancelOrderResponse>(ENDPOINTS.orders, {
    symbol,
    ...identifier,
  });
}

export function fetchStreamStatus(): Promise<StreamStatus> {
  return get<StreamStatus>(ENDPOINTS.streamStatus);
}
