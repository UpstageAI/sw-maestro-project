export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export const ENDPOINTS = {
  account: '/api/v1/testnet/account',
  tickerPrice: '/api/v1/testnet/ticker/price',
  tickerBook: '/api/v1/testnet/ticker/book',
  klines: '/api/v1/testnet/klines',
  orders: '/api/v1/testnet/orders',
  orderStatus: '/api/v1/testnet/orders/status',
  streamStatus: '/api/v1/testnet/stream/status',
} as const;

