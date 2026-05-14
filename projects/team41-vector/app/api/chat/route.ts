import { NextResponse } from 'next/server';
import crypto from 'crypto';
import getDb from '@/lib/db';
import { analyze } from '@/lib/agents/analyzer';
import { simulate } from '@/lib/agents/simulator';
import { coach } from '@/lib/agents/coach';
import type { Transaction, AnalysisResult, SimulationResult } from '@/lib/types';

// ─── POST /api/chat ───
// 프론트에서 채팅 메시지를 보내면 이 핸들러가 처리.
// 전체 흐름: 거래 로드 → Analyzer → Simulator → Coach(LLM) → 응답 조립
export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { message, userId } = body as { message: string; userId: string };

    if (!userId) {
      return NextResponse.json({ error: 'userId가 필요합니다.' }, { status: 400 });
    }

    const db = getDb();

    // ── user 자동 생성 ──
    // 프론트에서 crypto.randomUUID()로 생성한 userId가 DB에 없으면 기본값으로 INSERT.
    // chat_history에 FK 걸려있어서 user가 없으면 INSERT 실패함.
    const existingUser = db.prepare('SELECT id FROM users WHERE id = ?').get(userId);
    if (!existingUser) {
      db.prepare(
        'INSERT INTO users (id, name, monthly_income, current_savings, created_at) VALUES (?, ?, ?, ?, ?)',
      ).run(userId, '사용자', 2800000, 5000000, Date.now());
    }

    // ── Step 1: 거래 데이터 로드 ──
    // CSV 업로드 시 /api/upload에서 transactions 테이블에 저장됨.
    // 여기서는 해당 유저의 전체 거래를 가져옴.
    const rows = db
      .prepare('SELECT date, category, merchant, amount FROM transactions WHERE user_id = ?')
      .all(userId) as Transaction[];

    const hasTransactions = rows.length > 0;

    // ── Step 2: user 메시지를 chat_history에 저장 ──
    // LLM에게 대화 맥락을 제공하기 위해 DB에 보관.
    const userContent = message || '[CSV 업로드 후 자동 분석 요청]';
    db.prepare(
      'INSERT INTO chat_history (id, user_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)',
    ).run(crypto.randomUUID(), userId, 'user', userContent, Date.now());

    // 초기 분석 모드: message가 비어있으면 CSV 업로드 직후 자동 분석 요청
    const isInitialAnalysis = message === '' || message === undefined || message === null;

    let coachContent: string;
    let mission: { text: string; savingAmount: number } | null = null;
    let simulationResult: SimulationResult | undefined;
    let categoryBreakdown: Record<string, number> | undefined;
    let completedMissionId: string | undefined;
    let dailySpending: import('@/lib/types').DailySpendingData | undefined;

    if (!hasTransactions) {
      // ── 거래 데이터 없음: CSV 업로드 유도 ──
      // Analyzer/Simulator 건너뛰고 빈 데이터로 Coach만 호출.
      const chatHistory = db
        .prepare('SELECT role, content FROM chat_history WHERE user_id = ? ORDER BY created_at DESC LIMIT 20')
        .all(userId) as { role: 'user' | 'ai'; content: string }[];
      chatHistory.reverse(); // DB는 DESC로 가져오니까 시간순으로 뒤집기

      const emptyAnalysis: AnalysisResult = {
        totalSpending: 0,
        byCategory: {},
        riskPatterns: [],
        topMerchants: [],
        period: { from: '', to: '' },
      };
      const emptySimulation: SimulationResult = {
        currentPattern: { monthlySaving: 0, projections: [] },
        optimizedPattern: { monthlySaving: 0, projections: [] },
      };

      const coachOutput = await coach({
        analysis: emptyAnalysis,
        simulation: emptySimulation,
        userMessage: '사용자가 아직 CSV를 업로드하지 않았습니다. CSV 업로드를 유도해주세요.',
        chatHistory,
        userId,
      });

      coachContent = coachOutput.content;
      mission = coachOutput.mission;
      completedMissionId = coachOutput.completedMissionId;
    } else {
      // ── 거래 데이터 있음: 전체 파이프라인 실행 ──

      // Step 3: Analyzer — 순수 JS. 카테고리별 합산, 위험 패턴 탐지 등.
      const analysis = analyze(rows);

      // Step 4: Simulator — 순수 JS. 현재 vs 최적화 패턴으로 1/3/5년 자산 시뮬레이션.
      const user = db.prepare('SELECT monthly_income, current_savings FROM users WHERE id = ?').get(userId) as
        | { monthly_income: number; current_savings: number }
        | undefined;

      const monthlyIncome = user?.monthly_income ?? 2800000;
      const currentSavings = user?.current_savings ?? 5000000;

      simulationResult = simulate({
        monthlyIncome,
        totalSpending: analysis.totalSpending,
        currentSavings,
        riskPatternSavings: analysis.riskPatterns.reduce((s, p) => s + p.amount, 0),
      });

      // Step 5: Coach — LLM 호출. 분석+시뮬레이션+대화이력을 넘겨서 팩폭 피드백 생성.
      const chatHistory = db
        .prepare('SELECT role, content FROM chat_history WHERE user_id = ? ORDER BY created_at DESC LIMIT 20')
        .all(userId) as { role: 'user' | 'ai'; content: string }[];
      chatHistory.reverse();

      const coachOutput = await coach({
        analysis,
        simulation: simulationResult,
        userMessage: message || '처음 방문한 사용자입니다. 전체 소비 요약을 해주세요.',
        chatHistory,
        userId,
      });

      // Step 6: Coach 응답에서 content(본문)와 mission(미션)이 분리되어 나옴
      coachContent = coachOutput.content;
      mission = coachOutput.mission;
      completedMissionId = coachOutput.completedMissionId;
      dailySpending = coachOutput.dailySpending;

      // Step 7: 초기 분석 모드일 때만 카테고리별 지출 차트 데이터 생성
      // 상위 5개 카테고리를 금액 내림차순으로 뽑음. 프론트에서 CategoryBreakdown 컴포넌트로 렌더링.
      if (isInitialAnalysis) {
        categoryBreakdown = Object.fromEntries(
          Object.entries(analysis.byCategory)
            .sort((a, b) => b[1].total - a[1].total)
            .slice(0, 5)
            .map(([k, v]) => [k, v.total]),
        );
      }
    }

    // ── Step 8: 미션 DB 저장 ──
    // Coach가 미션을 제시했으면 missions 테이블에 저장. status는 기본 'pending'.
    // 프론트에서 수락/거절 시 PATCH /api/missions로 상태 업데이트.
    let missionId: string | undefined;
    if (mission) {
      missionId = crypto.randomUUID();
      db.prepare(
        'INSERT INTO missions (id, user_id, text, saving_amount, created_at) VALUES (?, ?, ?, ?, ?)',
      ).run(missionId, userId, mission.text, mission.savingAmount, Date.now());
    }

    // ── Step 9: AI 응답을 chat_history에 저장 ──
    // 다음 대화에서 맥락으로 사용됨 (최근 20건 로드).
    db.prepare(
      'INSERT INTO chat_history (id, user_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)',
    ).run(crypto.randomUUID(), userId, 'ai', coachContent, Date.now());

    // ── Step 10: 프론트에 보낼 응답 조립 ──
    // content: AI 텍스트, simulation: 차트 데이터, mission: 미션 카드, categoryBreakdown: 카테고리 바 차트
    // simulation/categoryBreakdown은 초기 분석 시에만 내려줌 (매 응답마다 차트 노출 방지)
    const response = {
      id: crypto.randomUUID(),
      role: 'ai' as const,
      content: coachContent,
      createdAt: Date.now(),
      simulation: isInitialAnalysis ? simulationResult : undefined,
      mission: mission && missionId ? { id: missionId, text: mission.text, savingAmount: mission.savingAmount } : undefined,
      categoryBreakdown: isInitialAnalysis ? categoryBreakdown : undefined,
      completedMissionId,
      dailySpending,
    };

    return NextResponse.json(response);
  } catch (error) {
    console.error('[chat] error:', error);
    return NextResponse.json(
      { error: '채팅 처리 중 오류가 발생했습니다.' },
      { status: 500 },
    );
  }
}
