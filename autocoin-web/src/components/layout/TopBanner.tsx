import { AlertTriangle } from 'lucide-react';
import styles from './TopBanner.module.css';

export function TopBanner() {
  return (
    <div className={styles.banner} role="alert">
      <AlertTriangle size={16} aria-hidden="true" />
      <span className={styles.label}>Binance Spot Testnet</span>
      <span className={styles.separator}>|</span>
      <span>
        모의투자 전용 환경입니다. 실거래가 아니며 가상 자금으로만 테스트합니다.
      </span>
    </div>
  );
}
