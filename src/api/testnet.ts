import { ENDPOINTS } from '../constants/endpoints';
import type {
  BalanceSnapshot,
  BookTicker,
  CancelOrderResponse,
  KlineResponse,
  OrderStatusResponse,
  SpotOrderRequest,
  SpotOrderResponse,
  StreamStatus,
  TickerPrice,
} from '../types/api';
import { del, get, post } from './client';

export function fetchAccount(): Promise<BalanceSnapshot> {
  return get<BalanceSnapshot>(ENDPOINTS.account);
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
): Promise<SpotOrderResponse> {
  return post<SpotOrderResponse>(ENDPOINTS.orders, order);
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
