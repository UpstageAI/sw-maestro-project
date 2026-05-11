import { useQuery } from '@tanstack/react-query';
import { fetchRunReportCadence } from '../api/testnet';
import type { ReportCadenceEvent } from '../types/agent';

function normalizeCadenceEvents(
  events: Awaited<ReturnType<typeof fetchRunReportCadence>>['events'] | undefined,
): ReportCadenceEvent[] {
  if (!events) {
    return [];
  }

  return events.map((event) => ({
    run_id: event.runId,
    event_type: event.eventType,
    lifecycle_status: event.lifecycleStatus,
    created_at: event.createdAt,
  }));
}

export function useRunReportCadence(runId: string) {
  const normalizedRunId = runId.trim();

  const query = useQuery({
    queryKey: ['runReportCadence', normalizedRunId],
    queryFn: () => fetchRunReportCadence(normalizedRunId),
    enabled: normalizedRunId.length > 0,
    staleTime: 30_000,
  });

  return {
    runId: query.data?.runId ?? normalizedRunId,
    events: normalizeCadenceEvents(query.data?.events),
    error: query.error,
    isLoading: query.isLoading && query.isFetching,
    isError: query.isError,
    refetch: query.refetch,
    isRefetching: query.isRefetching,
  };
}
