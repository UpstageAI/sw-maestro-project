const DEFAULT_API_BASE_URL =
  typeof window !== 'undefined'
    ? `http://${window.location.hostname}:8000`
    : 'http://localhost:8000';

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL;

export const ENDPOINTS = {
  account: '/api/v1/testnet/account',
  tickerPrice: '/api/v1/testnet/ticker/price',
  tickerBook: '/api/v1/testnet/ticker/book',
  klines: '/api/v1/testnet/klines',
  orders: '/api/v1/testnet/orders',
  ordersReport: '/api/v1/testnet/orders/report',
  ordersResume: '/api/v1/testnet/orders/resume',
  orderStatus: '/api/v1/testnet/orders/status',
  streamStatus: '/api/v1/testnet/stream/status',
} as const;

