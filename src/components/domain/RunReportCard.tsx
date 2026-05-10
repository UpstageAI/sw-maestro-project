import { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { Badge } from '../common';
import { DecisionTraceSteps } from './DecisionTraceSteps';
import type { PublishedRunLifecycleStatus, PublishedRunReport } from '../../types/api';
import styles from './RunReportCard.module.css';

interface RunReportCardProps {
  runId: string;
  report: PublishedRunReport;
}

function getLifecycleVariant(status: PublishedRunLifecycleStatus) {
  switch (status) {
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

export function RunReportCard({ runId, report }: RunReportCardProps) {
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
        <span className={styles.runId}>{runId}</span>
        <div className={styles.badges}>
          <Badge
            label={report.lifecycleStatus}
            variant={getLifecycleVariant(report.lifecycleStatus)}
          />
          {report.holdReason && <Badge label={report.holdReason} variant="warning" />}
        </div>
        <ChevronDown
          size={18}
          className={`${styles.chevron} ${expanded ? styles.chevronOpen : ''}`}
        />
      </div>

      <div className={styles.summary}>
        {report.userSummary}
      </div>

      {expanded && (
        <div className={styles.expandedContent}>
          {report.decisionTrace && (
            <div className={styles.traceSection}>
              <DecisionTraceSteps trace={report.decisionTrace} />
            </div>
          )}
          <div className={styles.debugArea}>
            run_id: {runId}
          </div>
        </div>
      )}
    </div>
  );
}
