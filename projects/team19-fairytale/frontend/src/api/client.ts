type ApiErrorBody = {
  detail?: unknown;
};

const API_BASE_URL = "/api/v1";

async function parseApiError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as ApiErrorBody;

    if (typeof body.detail === "string") {
      return body.detail;
    }

    if (Array.isArray(body.detail)) {
      return body.detail
        .map((item) =>
          typeof item === "object" && item !== null && "msg" in item
            ? String(item.msg)
            : JSON.stringify(item)
        )
        .filter(Boolean)
        .join(", ");
    }

    if (body.detail !== undefined) {
      return JSON.stringify(body.detail);
    }
  } catch {
    // Fall through to the generic status message.
  }

  return `Request failed with ${response.status}`;
}

export function authHeaders(token: string): Record<string, string> {
  return {
    Authorization: `Bearer ${token}`
  };
}

export async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const { headers, ...requestOptions } = options;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...requestOptions,
    headers: {
      "Content-Type": "application/json",
      ...headers
    }
  });

  if (!response.ok) {
    throw new Error(await parseApiError(response));
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}
