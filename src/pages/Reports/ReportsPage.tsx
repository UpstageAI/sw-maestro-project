import { FileText } from 'lucide-react';
import { EmptyState } from '../../components/common';
import { RunReportCard } from '../../components/domain/RunReportCard';
import { AgentStatusDisplay } from '../../components/domain/AgentStatusDisplay';
import { CadenceTimeline } from '../../components/domain/CadenceTimeline';
import type { ReportPayload, ReportCadenceEvent, AgentRunState } from '../../types/agent';
import styles from './ReportsPage.module.css';

const MOCK_REPORTS: ReportPayload[] = [
  {
    run_id: 'run_20260508_001',
    gate_decision: 'PASS',
    final_action: 'READY_FOR_BE',
    user_summary: 'BTC/USDT 매수 주문: 정책 통과, 리스크 게이트 PASS 판정. BE 재검증 대기 상태입니다.',
    decision_trace: {
      policy: {
        reason_codes: ['POLICY_SPOT_ALLOWED', 'POLICY_AMOUNT_OK'],
        evidence_refs: ['policy_v2.3_spot_rules'],
        final_action: 'READY_FOR_BE',
        notes: '스팟 매수 정책 조건 충족',
      },
      risk: {
        reason_codes: ['RISK_VOL_NORMAL', 'RISK_BALANCE_OK'],
        evidence_refs: ['vol_check_20260508'],
        final_action: 'READY_FOR_BE',
        notes: '변동성 정상 범위, 잔고 충분',
      },
      evaluator: {
        reason_codes: ['EVAL_CONFIDENCE_HIGH'],
        final_action: 'READY_FOR_BE',
        notes: '평가 신뢰도 92%',
      },
      run_summary: {
        final_action: 'READY_FOR_BE',
        be_override: false,
      },
    },
  },
  {
    run_id: 'run_20260508_002',
    gate_decision: 'HOLD',
    final_action: 'HOLD',
    user_summary: 'ETH/USDT 매수 주문: 리스크 게이트에서 HOLD 판정. 사용자 승인이 필요합니다.',
    decision_trace: {
      policy: {
        reason_codes: ['POLICY_SPOT_ALLOWED'],
        final_action: 'HOLD',
        notes: '정책 통과, 다음 단계 리스크 검증으로 이동',
      },
      risk: {
        reason_codes: ['RISK_VOL_HIGH', 'RISK_AMOUNT_LARGE'],
        final_action: 'HOLD',
        notes: '변동성 높음 + 대량 주문으로 인해 사용자 확인 필요',
      },
      run_summary: {
        final_action: 'HOLD',
        be_override: false,
      },
    },
  },
  {
    run_id: 'run_20260507_003',
    gate_decision: 'REJECT',
    final_action: 'NO_ORDER',
    user_summary: 'SOL/USDT 매도 주문: 정책 위반으로 주문 차단됨.',
    decision_trace: {
      policy: {
        reason_codes: ['POLICY_COOLDOWN_ACTIVE', 'POLICY_DAILY_LIMIT_EXCEEDED'],
        final_action: 'NO_ORDER',
        notes: '쿨다운 기간 활성 + 일일 거래 한도 초과',
      },
      run_summary: {
        final_action: 'NO_ORDER',
        be_override: false,
      },
    },
  },
];

const MOCK_CADENCE_EVENTS: ReportCadenceEvent[] = [
  { run_id: 'run_20260508_001', event_type: 'request_accepted', lifecycle_status: 'RECEIVED', created_at: '2026-05-08T09:00:00Z' },
  { run_id: 'run_20260508_001', event_type: 'policy_retrieval_complete', lifecycle_status: 'NORMALIZING', created_at: '2026-05-08T09:00:02Z' },
  { run_id: 'run_20260508_001', event_type: 'policy_complete', lifecycle_status: 'RISK_REVIEW', created_at: '2026-05-08T09:00:05Z' },
  { run_id: 'run_20260508_001', event_type: 'risk_gate_complete', lifecycle_status: 'READY_FOR_BE', created_at: '2026-05-08T09:00:08Z' },
  { run_id: 'run_20260508_001', event_type: 'evaluator_complete', lifecycle_status: 'READY_FOR_BE', created_at: '2026-05-08T09:00:10Z' },
  { run_id: 'run_20260508_001', event_type: 'be_revalidation_complete', lifecycle_status: 'EXECUTING', created_at: '2026-05-08T09:00:12Z' },
  { run_id: 'run_20260508_001', event_type: 'final_report_ready', lifecycle_status: 'REPORT_READY', created_at: '2026-05-08T09:00:15Z' },
];

const MOCK_HOLD_EVENTS: ReportCadenceEvent[] = [
  { run_id: 'run_20260508_002', event_type: 'request_accepted', lifecycle_status: 'RECEIVED', created_at: '2026-05-08T10:00:00Z' },
  { run_id: 'run_20260508_002', event_type: 'policy_complete', lifecycle_status: 'RISK_REVIEW', created_at: '2026-05-08T10:00:04Z' },
  { run_id: 'run_20260508_002', event_type: 'risk_gate_complete', lifecycle_status: 'HOLD', created_at: '2026-05-08T10:00:07Z' },
  { run_id: 'run_20260508_002', event_type: 'evaluator_complete', lifecycle_status: 'READY_FOR_BE', created_at: '2026-05-08T10:05:30Z' },
  { run_id: 'run_20260508_002', event_type: 'be_revalidation_complete', lifecycle_status: 'EXECUTING', created_at: '2026-05-08T10:05:35Z' },
];

const MOCK_AGENT_STATE_HOLD_REVIEW: AgentRunState = {
  run_id: 'run_20260508_002',
  lifecycle_status: 'HOLD',
  request_type: 'SPOT_BUY',
  final_action: 'HOLD',
  hold_reason: 'HOLD_REVIEW_REQUIRED',
};

const MOCK_AGENT_STATE_HOLD_DATA: AgentRunState = {
  run_id: 'run_20260508_004',
  lifecycle_status: 'HOLD',
  request_type: 'SPOT_BUY',
  final_action: 'HOLD',
  hold_reason: 'HOLD_DATA_INSUFFICIENT',
};

export function ReportsPage() {
  const reports = MOCK_REPORTS;

  if (reports.length === 0) {
    return (
      <div className={styles.page}>
        <h1 className={styles.heading}>에이전트 리포트</h1>
        <EmptyState
          icon={<FileText size={40} />}
          title="아직 리포트가 없습니다"
          description="에이전트가 실행을 완료하면 여기에 리포트가 표시됩니다."
        />
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <h1 className={styles.heading}>에이전트 리포트</h1>
      <p className={styles.description}>
        AI 에이전트의 실행 결과와 의사결정 과정을 확인합니다.
      </p>

      <div className={styles.reportList}>
        {reports.map((report) => (
          <RunReportCard key={report.run_id} report={report} />
        ))}
      </div>

      <div className={styles.section}>
        <h2 className={styles.sectionTitle}>실행 타임라인</h2>
        <div className={styles.columns}>
          <div>
            <CadenceTimeline events={MOCK_CADENCE_EVENTS} />
          </div>
          <div>
            <CadenceTimeline events={MOCK_HOLD_EVENTS} />
          </div>
        </div>
      </div>

      <div className={styles.section}>
        <h2 className={styles.sectionTitle}>에이전트 상태 알림</h2>
        <div className={styles.reportList}>
          <AgentStatusDisplay
            state={MOCK_AGENT_STATE_HOLD_REVIEW}
            reasonCodes={['RISK_VOL_HIGH', 'RISK_AMOUNT_LARGE']}
          />
          <AgentStatusDisplay
            state={MOCK_AGENT_STATE_HOLD_DATA}
            reasonCodes={['DATA_MISSING_ORDERBOOK']}
          />
          <AgentStatusDisplay
            state={{
              run_id: 'run_20260507_005',
              lifecycle_status: 'BE_REJECTED',
              request_type: 'SPOT_BUY',
              final_action: 'BE_REJECTED',
            }}
          />
          <AgentStatusDisplay
            state={{
              run_id: 'run_20260507_006',
              lifecycle_status: 'FAILED',
              request_type: 'SPOT_SELL',
              final_action: 'FAILED',
            }}
            description="WebSocket 연결 실패로 에이전트 실행이 중단되었습니다."
          />
          <AgentStatusDisplay
            state={{
              run_id: 'run_20260507_007',
              lifecycle_status: 'NO_ORDER',
              request_type: 'SPOT_BUY',
              final_action: 'NO_ORDER',
            }}
            reasonCodes={['POLICY_COOLDOWN_ACTIVE', 'POLICY_DAILY_LIMIT_EXCEEDED']}
          />
        </div>
      </div>
    </div>
  );
}
