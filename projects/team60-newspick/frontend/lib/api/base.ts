const DEFAULT_API_PORT = "8080";

type ApiLocation = Pick<Location, "hostname" | "protocol">;

export function defaultApiBaseForLocation(location: ApiLocation) {
  return `${location.protocol}//${location.hostname}:${DEFAULT_API_PORT}`;
}

export function apiBase() {
  const configured =
    process.env.NEXT_PUBLIC_API_BASE?.trim() || process.env.NEXT_PUBLIC_API_URL?.trim();

  if (configured) {
    return configured.replace(/\/$/, "");
  }

  if (typeof window === "undefined") {
    return `http://localhost:${DEFAULT_API_PORT}`;
  }

  return defaultApiBaseForLocation(window.location);
}

export function apiUrl(path: string) {
  return `${apiBase()}${path.startsWith("/") ? path : `/${path}`}`;
}
