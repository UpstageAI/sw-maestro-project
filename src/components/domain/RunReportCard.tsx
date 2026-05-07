import { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { Badge } from '../common';
import { DecisionTraceSteps } from './DecisionTraceSteps';
import type { ReportPayload, GateDecisionType, FinalAction } from '../../types/agent';
import styles from './RunReportCard.module.css';

interface RunReportCardProps {
  report: ReportPayload;
}

function getGateVariant(decision: GateDecisionType) {
  switch (decision) {
    case 'PASS':
      return 'success' as const;
    case 'HOLD':
      return 'warning' as const;
    case 'REJECT':
      return 'danger' as const;
  }
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

export function RunReportCard({ report }: RunReportCardProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className={styles.card}>
      <div
        className={styles.header}
        onClick={() => setExpanded((prev) => !prev)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            setExpanded((prev) => !prev);
          }
        }}
      >
        <span className={styles.runId}>{report.run_id}</span>
        <div className={styles.badges}>
          <Badge label={report.final_action} variant={getFinalActionVariant(report.final_action)} />
          <Badge label={report.gate_decision} variant={getGateVariant(report.gate_decision)} />
        </div>
        <ChevronDown
          size={18}
          className={`${styles.chevron} ${expanded ? styles.chevronOpen : ''}`}
        />
      </div>

      <div className={styles.summary}>
        {report.user_summary}
      </div>

      {expanded && (
        <div className={styles.expandedContent}>
          <div className={styles.traceSection}>
            <DecisionTraceSteps trace={report.decision_trace} />
          </div>
          <div className={styles.debugArea}>
            run_id: {report.run_id}
          </div>
        </div>
      )}
    </div>
  );
}
