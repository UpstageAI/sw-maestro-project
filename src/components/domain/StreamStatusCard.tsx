import { Radio } from 'lucide-react';
import { Card, Badge, Button, Banner, Skeleton } from '../common';
import type { StreamStatus } from '../../types/api';
import styles from './StreamStatusCard.module.css';

type ConnectionState = 'connected' | 'disconnected' | 'reconnecting';

interface StreamStatusCardProps {
  streamStatus: StreamStatus | undefined;
  isLoading: boolean;
  isError: boolean;
  onRefresh: () => void;
  isRefetching: boolean;
}

const CONNECTION_LABELS: Record<ConnectionState, string> = {
  connected: '수신 중',
  disconnected: '연결 끊김',
  reconnecting: '재연결 중',
};

const CONNECTION_BADGE_VARIANT: Record<ConnectionState, 'success' | 'danger' | 'warning'> = {
  connected: 'success',
  disconnected: 'danger',
  reconnecting: 'warning',
};

function getConnectionState(status: StreamStatus | undefined): ConnectionState {
  if (!status) return 'disconnected';
  return status.connected ? 'connected' : 'disconnected';
}

function getDotClass(state: ConnectionState): string {
  const map: Record<ConnectionState, string> = {
    connected: styles.dotConnected,
    disconnected: styles.dotDisconnected,
    reconnecting: styles.dotReconnecting,
  };
  return map[state];
}

export function StreamStatusCard({
  streamStatus,
  isLoading,
  isError,
  onRefresh,
  isRefetching,
}: StreamStatusCardProps) {
  const connectionState = getConnectionState(streamStatus);

  const renderContent = () => {
    if (isLoading) {
      return (
        <div className={styles.statusList}>
          <Skeleton height="20px" />
          <Skeleton height="20px" />
          <Skeleton height="20px" />
        </div>
      );
    }

    if (isError) {
      return (
        <Banner variant="danger">
          스트림 상태 조회에 실패했습니다. 네트워크 연결을 확인해 주세요.
        </Banner>
      );
    }

    if (!streamStatus) {
      return (
        <div className={styles.placeholder}>
          <Radio size={20} />
          <span>
            WebSocket 시세 스트림 상태를 불러오는 중입니다.
          </span>
        </div>
      );
    }

    const lastEvent = streamStatus.lastEvent;

    return (
      <div className={styles.statusList}>
        <div className={styles.statusRow}>
          <span className={styles.label}>연결 상태</span>
          <div className={styles.statusIndicator}>
            <span className={`${styles.dot} ${getDotClass(connectionState)}`} />
            <Badge
              label={CONNECTION_LABELS[connectionState]}
              variant={CONNECTION_BADGE_VARIANT[connectionState]}
            />
          </div>
        </div>

        <div className={styles.statusRow}>
          <span className={styles.label}>스트림</span>
          <span className={styles.streamName}>
            {streamStatus.streamName ?? '—'}
          </span>
        </div>

        {lastEvent && (
          <>
            <div className={styles.statusRow}>
              <span className={styles.label}>현재가</span>
              <span className={styles.value}>{lastEvent.c}</span>
            </div>
            <div className={styles.statusRow}>
              <span className={styles.label}>24h 고가 / 저가</span>
              <span className={styles.value}>
                {lastEvent.h} / {lastEvent.l}
              </span>
            </div>
            <div className={styles.statusRow}>
              <span className={styles.label}>24h 거래량</span>
              <span className={styles.value}>{lastEvent.v}</span>
            </div>
          </>
        )}

        {!lastEvent && streamStatus.connected && (
          <div className={styles.statusRow}>
            <span className={styles.label}>최근 이벤트</span>
            <span className={styles.value}>수신 대기 중…</span>
          </div>
        )}
      </div>
    );
  };

  return (
    <Card
      title="시세 스트림"
      subtitle="WebSocket 상태"
      actions={
        <Button
          variant="ghost"
          size="sm"
          onClick={onRefresh}
          loading={isRefetching}
        >
          새로고침
        </Button>
      }
    >
      {renderContent()}
    </Card>
  );
}
