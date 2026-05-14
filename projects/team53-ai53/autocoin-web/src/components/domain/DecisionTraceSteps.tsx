import { Shield, AlertTriangle, CheckCircle, Cpu, FileText } from 'lucide-react';
import { Badge } from '../common';
import type { PublishedRunDecisionTrace, RunDecisionTraceStage } from '../../types/api';
import styles from './DecisionTraceSteps.module.css';

interface DecisionTraceStepsProps {
  trace: PublishedRunDecisionTrace;
}

function getFinalActionVariant(action: string | null) {
  switch (action) {
    case 'PASS':
    case 'READY_FOR_BE':
    case 'REPORT_READY':
      return 'success' as const;
    case 'HOLD':
      return 'warning' as const;
    case 'NO_ORDER':
    case 'BE_REJECTED':
    case 'FAILED':
      return 'danger' as const;
  }
}

function TraceStepCard({
  label,
  icon,
  trace,
  showPassPending = false,
}: {
  label: string;
  icon: React.ReactNode;
  trace: RunDecisionTraceStage;
  showPassPending?: boolean;
}) {
  return (
    <div className={styles.step}>
      <div className={styles.stepHeader}>
        <span className={styles.stepIcon}>{icon}</span>
        <span className={styles.stepLabel}>{label}</span>
        {showPassPending ? (
          <div className={styles.passWithPending}>
            <Badge label="PASS" variant="success" />
            <span className={styles.pendingLabel}>BE 재검증 대기</span>
          </div>
        ) : trace.finalAction ? (
          <Badge label={trace.finalAction} variant={getFinalActionVariant(trace.finalAction)} />
        ) : null}
      </div>
      {trace.notes && <p className={styles.notes}>{trace.notes}</p>}
      {trace.reasonCodes.length > 0 && (
        <div className={styles.reasonCodes}>
          {trace.reasonCodes.map((code) => (
            <span key={code} className={styles.reasonCode}>
              {code}
            </span>
          ))}
        </div>
      )}
      {trace.evidenceRefs.length > 0 && (
        <div className={styles.evidenceRefs}>
          {trace.evidenceRefs.map((ref) => (
            <span key={ref} className={styles.evidenceRef}>
              {ref}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

export function DecisionTraceSteps({ trace }: DecisionTraceStepsProps) {
  return (
    <div className={styles.container}>
      {trace.policy && (
        <TraceStepCard
          label="Policy 조회"
          icon={<Shield size={16} />}
          trace={trace.policy}
        />
      )}
      {trace.risk && (
        <TraceStepCard
          label="Risk 검증"
          icon={<AlertTriangle size={16} />}
          trace={trace.risk}
          showPassPending={trace.risk.finalAction === 'PASS'}
        />
      )}
      {trace.evaluator && (
        <TraceStepCard
          label="Evaluator 평가"
          icon={<CheckCircle size={16} />}
          trace={trace.evaluator}
        />
      )}
      {trace.execution && (
        <TraceStepCard
          label="Execution 실행"
          icon={<Cpu size={16} />}
          trace={trace.execution}
        />
      )}
      {trace.runSummary && (
        <TraceStepCard
          label="Run Summary"
          icon={<FileText size={16} />}
          trace={trace.runSummary}
        />
      )}
    </div>
  );
}
