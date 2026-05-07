import { Card, Banner } from '../../components/common';
import { TESTNET_REST_BASE_URL, TESTNET_WS_STREAM_URL, TESTNET_WS_API_URL } from '../../constants';
import styles from './SettingsPage.module.css';

export function SettingsPage() {
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

      <Card title="Testnet 엔드포인트" subtitle="읽기 전용" className={styles.card}>
        <div className={styles.configList}>
          <ConfigRow label="REST Base URL" value={TESTNET_REST_BASE_URL} />
          <ConfigRow label="WebSocket Streams" value={TESTNET_WS_STREAM_URL} />
          <ConfigRow label="WebSocket API" value={TESTNET_WS_API_URL} />
        </div>
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
