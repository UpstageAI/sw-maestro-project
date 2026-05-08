import { Ban, Clock, ShieldAlert, XCircle, AlertTriangle } from 'lucide-react';
import { Badge, Button } from '../common';
import type { AgentRunState } from '../../types/agent';
import styles from './AgentStatusDisplay.module.css';

interface AgentStatusDisplayProps {
  state: AgentRunState;
  reasonCodes?: string[];
  description?: string;
  onApprove?: () => void;
  onReject?: () => void;
  onEditInput?: () => void;
  onRetry?: () => void;
  onViewDetails?: () => void;
  onRefetch?: () => void;
}

export function AgentStatusDisplay({
  state,
  reasonCodes = [],
  description,
  onApprove,
  onReject,
  onEditInput,
  onRetry,
  onViewDetails,
  onRefetch,
}: AgentStatusDisplayProps) {
  if (state.lifecycle_status === 'NO_ORDER') {
    return (
      <div className={`${styles.container} ${styles.noOrder}`}>
        <div className={styles.header}>
          <span className={`${styles.statusIcon} ${styles.iconWarning}`}>
            <Ban size={20} />
          </span>
          <span className={styles.title}>주문 불가</span>
        </div>
        <p className={styles.description}>
          {description ?? '정책 또는 리스크 조건에 의해 주문이 차단되었습니다.'}
        </p>
        {reasonCodes.length > 0 && (
          <div className={styles.reasonCodes}>
            {reasonCodes.map((code) => (
              <span key={code} className={styles.reasonCode}>{code}</span>
            ))}
          </div>
        )}
        <div className={styles.actions}>
          <Button variant="secondary" size="sm" onClick={onEditInput}>
            입력 수정
          </Button>
        </div>
      </div>
    );
  }

  if (state.lifecycle_status === 'HOLD' && state.hold_reason === 'HOLD_REVIEW_REQUIRED') {
    return (
      <div className={`${styles.container} ${styles.holdReview}`}>
        <div className={styles.header}>
          <span className={`${styles.statusIcon} ${styles.iconPrimary}`}>
            <Clock size={20} />
          </span>
          <span className={styles.title}>사용자 승인 대기</span>
          <Badge label="승인 필요" variant="warning" />
        </div>
        <p className={styles.description}>
          {description ?? 'AI 에이전트가 실행을 보류했습니다. 계속 진행하려면 승인이 필요합니다.'}
        </p>
        {reasonCodes.length > 0 && (
          <div className={styles.reasonCodes}>
            {reasonCodes.map((code) => (
              <span key={code} className={styles.reasonCode}>{code}</span>
            ))}
          </div>
        )}
        <div className={styles.actions}>
          <Button variant="primary" size="sm" onClick={onApprove}>
            승인
          </Button>
          <Button variant="danger" size="sm" onClick={onReject}>
            거부
          </Button>
        </div>
      </div>
    );
  }

  if (state.lifecycle_status === 'HOLD' && state.hold_reason === 'HOLD_DATA_INSUFFICIENT') {
    return (
      <div className={`${styles.container} ${styles.holdData}`}>
        <div className={styles.header}>
          <span className={`${styles.statusIcon} ${styles.iconWarning}`}>
            <AlertTriangle size={20} />
          </span>
          <span className={styles.title}>데이터 부족</span>
          <Badge label="추가 입력 필요" variant="info" />
        </div>
        <p className={styles.description}>
          {description ?? '판단에 필요한 데이터가 충분하지 않습니다. 추가 정보를 입력하거나 재조회해 주세요.'}
        </p>
        {reasonCodes.length > 0 && (
          <div className={styles.reasonCodes}>
            {reasonCodes.map((code) => (
              <span key={code} className={styles.reasonCode}>{code}</span>
            ))}
          </div>
        )}
        <div className={styles.actions}>
          <Button variant="secondary" size="sm" onClick={onRefetch}>
            재조회/재입력
          </Button>
        </div>
      </div>
    );
  }

  if (state.lifecycle_status === 'BE_REJECTED') {
    return (
      <div className={`${styles.container} ${styles.beRejected}`}>
        <div className={styles.header}>
          <span className={`${styles.statusIcon} ${styles.iconDanger}`}>
            <ShieldAlert size={20} />
          </span>
          <span className={styles.title}>BE 검증 거부</span>
          <Badge label="BE_REJECTED" variant="danger" />
        </div>
        <p className={styles.description}>
          {description ?? 'AI 에이전트는 통과 판단을 내렸으나, 백엔드 재검증에서 거부되었습니다.'}
        </p>
        <div className={styles.actions}>
          <button className={styles.detailLink} onClick={onViewDetails}>
            상세 사유 보기
          </button>
        </div>
      </div>
    );
  }

  if (state.lifecycle_status === 'FAILED') {
    return (
      <div className={`${styles.container} ${styles.failed}`}>
        <div className={styles.header}>
          <span className={`${styles.statusIcon} ${styles.iconMuted}`}>
            <XCircle size={20} />
          </span>
          <span className={styles.title}>실행 실패</span>
          <Badge label="FAILED" variant="default" />
        </div>
        <p className={styles.description}>
          {description ?? '기술적 오류로 에이전트 실행이 실패했습니다.'}
        </p>
        <div className={styles.failedMeta}>
          run_id: {state.run_id}
        </div>
        <div className={styles.actions}>
          <Button variant="secondary" size="sm" onClick={onRetry}>
            재시도
          </Button>
        </div>
      </div>
    );
  }

  return null;
}
