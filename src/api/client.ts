import { API_BASE_URL } from '../constants/endpoints';
import type { ErrorResponse } from '../types/api';

export class ApiError extends Error {
  status: number;
  errorResponse?: ErrorResponse;

  constructor(
    status: number,
    errorResponse?: ErrorResponse,
  ) {
    super(errorResponse?.message ?? `API 요청 실패 (${status})`);
    this.name = 'ApiError';
    this.status = status;
    this.errorResponse = errorResponse;
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorResponse: ErrorResponse | undefined;
    try {
      errorResponse = await response.json();
    } catch {
      /* empty */
    }
    throw new ApiError(response.status, errorResponse);
  }
  return response.json();
}

function buildUrl(path: string, params?: Record<string, string>): string {
  const url = new URL(path, API_BASE_URL);
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value) url.searchParams.set(key, value);
    });
  }
  return url.toString();
}

export async function get<T>(
  path: string,
  params?: Record<string, string>,
): Promise<T> {
  const response = await fetch(buildUrl(path, params), {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });
  return handleResponse<T>(response);
}

export async function post<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(buildUrl(path), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return handleResponse<T>(response);
}

export async function del<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(buildUrl(path), {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  return handleResponse<T>(response);
}
