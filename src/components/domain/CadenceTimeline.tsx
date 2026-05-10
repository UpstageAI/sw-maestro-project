import { Badge } from '../common';
import type { ReportCadenceEvent, LifecycleStatus } from '../../types/agent';
import styles from './CadenceTimeline.module.css';

interface CadenceTimelineProps {
  events: ReportCadenceEvent[];
}

const EVENT_TYPE_LABELS: Record<string, string> = {
  request_accepted: '요청 접수',
  policy_retrieval_complete: '정책 조회 완료',
  policy_complete: '정책 판단 완료',
  risk_gate_complete: '리스크 게이트 완료',
  evaluator_complete: '평가자 판단 완료',
  be_revalidation_complete: 'BE 재검증 완료',
  final_report_ready: '최종 리포트 준비 완료',
};

function getDotClass(status: LifecycleStatus, isLast: boolean) {
  if (status === 'HOLD') return styles.dotHold;
  if (status === 'FAILED') return styles.dotFailed;
  if (status === 'REPORT_READY') return styles.dotCompleted;
  if (isLast) return styles.dotActive;
  return styles.dotCompleted;
}

function getStatusVariant(status: LifecycleStatus) {
  switch (status) {
    case 'REPORT_READY':
      return 'success' as const;
    case 'HOLD':
      return 'warning' as const;
    case 'FAILED':
    case 'NO_ORDER':
      return 'danger' as const;
    default:
      return 'info' as const;
  }
}

function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleString('ko-KR', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

export function CadenceTimeline({ events }: CadenceTimelineProps) {
  const sorted = [...events].sort(
    (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
  );

  return (
    <div className={styles.container}>
      <div className={styles.line} />
      {sorted.map((event, idx) => {
        const isHold = event.lifecycle_status === 'HOLD';
        const previousEvent = sorted[idx - 1];
        const isResumeAfterHold = previousEvent?.lifecycle_status === 'HOLD' && !isHold;
        const isLast = idx === sorted.length - 1;
        const dotClass = getDotClass(event.lifecycle_status, isLast);

        return (
          <div
            key={`${event.run_id}-${event.created_at}-${idx}`}
            className={`${styles.event} ${isHold ? styles.holdEvent : ''}`}
          >
            <div className={`${styles.dot} ${dotClass}`} />
            <div className={styles.eventContent}>
              {isResumeAfterHold && (
                <span className={styles.resumeLabel}>▶ HOLD 해제 후 재개</span>
              )}
              <span className={styles.eventType}>
                {EVENT_TYPE_LABELS[event.event_type] ?? event.event_type}
              </span>
              <div className={styles.eventMeta}>
                <span className={styles.timestamp}>
                  {formatTimestamp(event.created_at)}
                </span>
                <span className={styles.statusBadge}>
                  <Badge
                    label={event.lifecycle_status}
                    variant={getStatusVariant(event.lifecycle_status)}
                  />
                </span>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
