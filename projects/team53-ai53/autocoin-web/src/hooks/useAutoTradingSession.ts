import { useQuery } from '@tanstack/react-query';
import { fetchAutoTradingSession } from '../api/testnet';

const ACTIVE_POLL_INTERVAL = 5_000;
const IDLE_POLL_INTERVAL = 15_000;

export function useAutoTradingSession() {
  const query = useQuery({
    queryKey: ['autoTradingSession'],
    queryFn: fetchAutoTradingSession,
    refetchInterval: (queryState) => {
      const sessionStatus = queryState.state.data?.sessionStatus;

      if (sessionStatus === 'ACTIVE' || sessionStatus === 'STOPPING') {
        return ACTIVE_POLL_INTERVAL;
      }

      return IDLE_POLL_INTERVAL;
    },
    staleTime: ACTIVE_POLL_INTERVAL - 1_000,
  });

  return {
    session: query.data,
    error: query.error,
    isLoading: query.isLoading && query.isFetching,
    isError: query.isError,
    refetch: query.refetch,
    isRefetching: query.isRefetching,
  };
}
