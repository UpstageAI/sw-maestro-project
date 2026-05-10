import { useQuery } from '@tanstack/react-query';
import { fetchRunReport } from '../api/testnet';

export function useRunReport(runId: string) {
  const normalizedRunId = runId.trim();

  const query = useQuery({
    queryKey: ['runReport', normalizedRunId],
    queryFn: () => fetchRunReport(normalizedRunId),
    enabled: normalizedRunId.length > 0,
    staleTime: 30_000,
  });

  return {
    runReport: query.data,
    runId: query.data?.runId ?? normalizedRunId,
    report: query.data?.report,
    error: query.error,
    isLoading: query.isLoading && query.isFetching,
    isError: query.isError,
    refetch: query.refetch,
    isRefetching: query.isRefetching,
  };
}
