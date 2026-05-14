import { useQuery } from '@tanstack/react-query';
import { fetchStreamStatus } from '../api/testnet';

const POLL_INTERVAL = 5_000;

export function useStreamStatus() {
  const query = useQuery({
    queryKey: ['streamStatus'],
    queryFn: fetchStreamStatus,
    refetchInterval: POLL_INTERVAL,
    staleTime: POLL_INTERVAL - 1_000,
  });

  return {
    streamStatus: query.data,
    isLoading: query.isLoading && query.isFetching,
    isError: query.isError,
    refetch: query.refetch,
    isRefetching: query.isRefetching,
  };
}
