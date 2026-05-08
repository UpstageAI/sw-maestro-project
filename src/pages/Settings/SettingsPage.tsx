import { Card, Banner, Spinner } from '../../components/common';
import { API_BASE_URL } from '../../constants';
import styles from './SettingsPage.module.css';

/**
 * Testnet 엔드포인트 정보는 BE 설정 API에서 조회한다.
 * FE는 Binance URL을 직접 보유하지 않으며, BE가 반환한 값을 읽기 전용으로 표시한다.
 * BE 미구현 시 "BE 연결 후 표시" placeholder를 보여준다.
 */

interface TestnetConfig {
  rest_base_url: string;
  ws_stream_url: string;
  ws_api_url: string;
}

function useTestnetConfig(): {
  config: TestnetConfig | null;
  isLoading: boolean;
  error: string | null;
} {
  // TODO: BE 구현 후 GET /api/v1/testnet/config 등으로 교체
  return { config: null, isLoading: false, error: null };
}

export function SettingsPage() {
  const { config, isLoading } = useTestnetConfig();

  return (
    <div className={styles.page}>
      <h1 className={styles.heading}>환경 설정</h1>
      <p className={styles.description}>
        Binance Spot Testnet 환경 변수 설정 상태를 확인합니다.
      </p>

      <Banner variant="warning">
        이 시스템은 Binance Spot Testnet 전용입니다. 실거래 URL이나 실거래 API
        Key는 사용하지 않습니다.
      </Banner>

      <Card title="연결 정보" subtitle="읽기 전용" className={styles.card}>
        <div className={styles.configList}>
          <ConfigRow label="Backend API" value={API_BASE_URL} />
        </div>
      </Card>

      <Card
        title="Testnet 엔드포인트"
        subtitle="BE 서버에서 조회"
        className={styles.card}
      >
        {isLoading ? (
          <Spinner size="sm" />
        ) : config ? (
          <div className={styles.configList}>
            <ConfigRow label="REST Base URL" value={config.rest_base_url} />
            <ConfigRow label="WebSocket Streams" value={config.ws_stream_url} />
            <ConfigRow label="WebSocket API" value={config.ws_api_url} />
          </div>
        ) : (
          <p className={styles.hint}>
            BE 서버 연결 후 Testnet 엔드포인트 정보가 표시됩니다.
          </p>
        )}
      </Card>

      <Card title="API Key 설정 상태" className={styles.card}>
        <div className={styles.configList}>
          <ConfigRow
            label="BINANCE_TESTNET_API_KEY"
            value="서버 환경 변수로 관리됩니다"
            masked
          />
          <ConfigRow
            label="BINANCE_TESTNET_SECRET_KEY"
            value="서버 환경 변수로 관리됩니다"
            masked
          />
        </div>
        <p className={styles.hint}>
          API Key와 Secret은 서버 측 환경 변수에만 저장되며, 브라우저에서
          입력하거나 확인할 수 없습니다.
        </p>
      </Card>
    </div>
  );
}

function ConfigRow({
  label,
  value,
  masked = false,
}: {
  label: string;
  value: string;
  masked?: boolean;
}) {
  return (
    <div className={styles.configRow}>
      <span className={styles.configLabel}>{label}</span>
      <code className={`${styles.configValue} ${masked ? styles.masked : ''}`}>
        {value}
      </code>
    </div>
  );
}
