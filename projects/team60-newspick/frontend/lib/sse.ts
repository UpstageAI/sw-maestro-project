type SseHandlers<T> = {
  onEvent: (event: string, data: T) => void;
  onDone?: () => void;
  onError?: (event: Event) => void;
};

const eventNames = ["progress", "step", "warn", "token", "done", "error"];

export function subscribeSse<T>(url: string, handlers: SseHandlers<T>) {
  const eventSource = new EventSource(url);

  eventNames.forEach((name) => {
    eventSource.addEventListener(name, (event) => {
      const rawData = (event as MessageEvent<string>).data;
      try {
        const data = parseSseData<T>(rawData, name);
        handlers.onEvent(name, data);

        if (name === "done") {
          handlers.onDone?.();
          eventSource.close();
        }

        if (name === "error") {
          eventSource.close();
        }
      } catch {
        handlers.onError?.(event);
        eventSource.close();
      }
    });
  });

  eventSource.onerror = (event) => {
    handlers.onError?.(event);
    eventSource.close();
  };

  return () => eventSource.close();
}

function parseSseData<T>(rawData: string, eventName: string): T {
  try {
    return JSON.parse(rawData) as T;
  } catch (error) {
    if (eventName === "error") {
      return {
        code: "SSE_ERROR",
        message: rawData || "SSE error",
      } as T;
    }
    throw error;
  }
}
