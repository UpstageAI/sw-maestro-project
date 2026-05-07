import { Shield, AlertTriangle, CheckCircle, Cpu, FileText } from 'lucide-react';
import { Badge } from '../common';
import type { DecisionTrace, AgentDecisionTrace, FinalAction } from '../../types/agent';
import styles from './DecisionTraceSteps.module.css';

interface DecisionTraceStepsProps {
  trace: DecisionTrace;
}

function getFinalActionVariant(action: FinalAction) {
  switch (action) {
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
  trace: AgentDecisionTrace;
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
        ) : (
          <Badge label={trace.final_action} variant={getFinalActionVariant(trace.final_action)} />
        )}
      </div>
      {trace.notes && <p className={styles.notes}>{trace.notes}</p>}
      {trace.reason_codes.length > 0 && (
        <div className={styles.reasonCodes}>
          {trace.reason_codes.map((code) => (
            <span key={code} className={styles.reasonCode}>
              {code}
            </span>
          ))}
        </div>
      )}
      {trace.evidence_refs && trace.evidence_refs.length > 0 && (
        <div className={styles.evidenceRefs}>
          {trace.evidence_refs.map((ref) => (
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
          showPassPending={trace.risk.final_action === 'READY_FOR_BE'}
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
      {trace.run_summary && (
        <div className={styles.step}>
          <div className={styles.stepHeader}>
            <span className={styles.stepIcon}><FileText size={16} /></span>
            <span className={styles.stepLabel}>Run Summary</span>
          </div>
          <div className={styles.finalActionRow}>
            <Badge
              label={trace.run_summary.final_action}
              variant={getFinalActionVariant(trace.run_summary.final_action)}
            />
            {trace.run_summary.be_override && (
              <span className={styles.beOverrideTag}>BE Override</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
