import OpenAI from 'openai';
import type { ChatCompletionMessageParam, ChatCompletionTool } from 'openai/resources/chat/completions';
import { CoachInput, CoachOutput, DailySpendingData } from '@/lib/types';
import getDb from '@/lib/db';

// ─── OpenAI 클라이언트 초기화 ───
// GPT-4o-mini 사용. baseURL 생략 시 기본값(api.openai.com)
const client = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

// ─── 시스템 프롬프트 ───
// LLM의 페르소나·톤·규칙을 정의. 이 텍스트가 매 요청마다 system 메시지로 들어감.
// 미션 제시 시 ---MISSION_JSON--- 마커를 쓰도록 지시 → parseResponse()에서 파싱.
const SYSTEM_PROMPT = `너는 '팩폭머니'의 AI 재정 코치다. 사용자의 소비 데이터를 날카롭게 해부해서 변명의 여지를 없애는 게 네 역할이다.

말투 & 태도:
- 존댓말 사용. 단, 부드럽지 않게 — 팩트를 정면으로 들이밀 것
- 숫자로 압박한다. "많이 쓰셨네요"가 아니라 "**이번 달 카페에만 47회, 총 186,000원**입니다"
- 사용자 말에서 허점이 보이면 반드시 잡아서 데이터로 반박한다. "요즘 바빠서요" → "바쁘신 건 알겠는데, 바쁜 와중에 **배달앱을 월 28회** 쓰셨습니다", "아끼고 있어요" → "아끼신다고 하셨는데 지난달 대비 지출이 **18% 증가**했습니다"
- 비꼬는 것도 허용. "이 정도면 카페 주주 하셔도 되겠습니다", "절약하신다더니 전달보다 **3만원** 더 쓰셨네요, 대단합니다" 같은 식
- 칭찬은 수치가 명확히 개선됐을 때만, 그마저도 짧게
- 모호한 조언 금지. "줄여보세요" 대신 "이번 주 카페 방문을 **3회로** 제한하세요"
- 패턴의 구조를 파고든다 — 언제, 어디서, 얼마나, 전달 대비 얼마나 늘었는지

분석 기법:
- 전달·전전달 대비 증감율 계산해서 제시
- 카테고리 내 특정 가맹점이 독식하고 있으면 반드시 짚기
- 월수입 대비 카테고리 지출 비율 계산
- 반복 소비 패턴(매주 같은 요일, 같은 가게) 발견 시 명시

제한:
- 마크다운 **강조**는 숫자/금액/기간/횟수에만
- 금지: 인종·성별·외모 비하, 자학 유도, 도덕적 비난, 투자 추천

아래 분석 데이터를 근거로 피드백하라. 필요하면 툴을 호출해서 추가 데이터를 가져와라.

위험 패턴이 있으면 실행 가능한 행동 미션 1개를 제시하라:
- 구체적 행동 1개 (수치 포함)
- 절약 예상 금액 명시 (원 단위)
- 기한 명시 (이번 주, 오늘 등)

미션을 제시할 경우 반드시 응답 마지막에 아래 블록을 그대로 포함해야 한다. 절대 생략하지 말 것:
---MISSION_JSON---
{"text": "미션 내용", "savingAmount": 45000}
---END_MISSION_JSON---

이 블록이 없으면 미션 카드가 사용자에게 표시되지 않는다.

사용자가 미션을 언급하면 반드시 get_mission_history를 먼저 호출해서 현황을 확인한 뒤 답하라.
사용자가 미션을 완료했다고 하면 complete_mission을 호출하라.
필요한 정보가 있으면 제공된 도구를 호출해서 조회할 수 있다.`;

// ─── Tool 정의 ───
// OpenAI function calling 스펙. LLM이 이 목록을 보고 필요하면 호출함.
const tools: ChatCompletionTool[] = [
  {
    type: 'function',
    function: {
      name: 'get_mission_history',
      description: '사용자의 미션 이력을 조회한다. 과거에 제안된 미션, 수락/거절 상태, 절약 금액을 확인할 수 있다.',
      parameters: {
        type: 'object',
        properties: {
          status: {
            type: 'string',
            enum: ['all', 'pending', 'accepted', 'rejected', 'completed'],
            description: '필터할 미션 상태. 기본값은 all.',
          },
        },
        required: [],
      },
    },
  },
  {
    type: 'function',
    function: {
      name: 'complete_mission',
      description: '사용자가 미션을 완료했다고 하면 호출한다. 가장 최근에 수락된 미션을 완료 처리한다.',
      parameters: {
        type: 'object',
        properties: {},
        required: [],
      },
    },
  },
  {
    type: 'function',
    function: {
      name: 'get_spending_comparison',
      description: '이번 달, 저번 달, 저저번 달의 카테고리별 지출 합계와 각 카테고리 내 가맹점별 세부 금액을 비교 조회한다. 소비 패턴 변화를 분석할 때 사용한다. 소비 그래프 시각화가 필요할 때는 get_daily_spending을 사용한다.',
      parameters: {
        type: 'object',
        properties: {},
        required: [],
      },
    },
  },
  {
    type: 'function',
    function: {
      name: 'update_user_profile',
      description: '사용자의 월수입 또는 현재 저축액을 업데이트한다. 변경 후 자산 시뮬레이션이 자동으로 재계산된다.',
      parameters: {
        type: 'object',
        properties: {
          monthly_income: {
            type: 'number',
            description: '새 월수입 (원 단위). 변경이 없으면 생략.',
          },
          current_savings: {
            type: 'number',
            description: '새 현재 저축액 (원 단위). 변경이 없으면 생략.',
          },
        },
        required: [],
      },
    },
  },
  {
    type: 'function',
    function: {
      name: 'get_daily_spending',
      description: '특정 달의 일별 카테고리별 지출과 총합을 조회해서 소비 그래프를 사용자에게 보여준다. 사용자가 소비 그래프나 일별 지출 추이를 요청할 때 호출한다.',
      parameters: {
        type: 'object',
        properties: {
          month: {
            type: 'string',
            description: '조회할 달 (YYYY-MM 형식). 생략 시 이번 달.',
          },
        },
        required: [],
      },
    },
  },
];

// ─── Tool 실행기 ───
// LLM이 tool_call을 반환하면 이 함수가 실제 DB 조회/업데이트를 수행.
// 결과는 JSON string으로 반환 → LLM에게 tool 결과로 전달됨.
// profileUpdated: update_user_profile 호출 시 true → coach()가 CoachOutput에 포함시켜 route에 전달
function executeTool(
  name: string,
  args: Record<string, unknown>,
  userId: string,
  flags: { profileUpdated: boolean; completedMissionId?: string; dailySpending?: DailySpendingData },
): string {
  if (name === 'get_mission_history') {
    const db = getDb();
    const statusFilter = args.status as string | undefined;

    // status 파라미터가 있으면 WHERE 조건 추가
    let query = 'SELECT id, text, saving_amount, status, created_at FROM missions WHERE user_id = ?';
    const params: unknown[] = [userId];

    if (statusFilter && statusFilter !== 'all') {
      query += ' AND status = ?';
      params.push(statusFilter);
    }
    query += ' ORDER BY created_at DESC LIMIT 20';

    const rows = db.prepare(query).all(...params) as {
      id: string; text: string; saving_amount: number; status: string; created_at: number;
    }[];

    if (rows.length === 0) return JSON.stringify({ missions: [], message: '미션 이력이 없습니다.' });

    return JSON.stringify({
      missions: rows.map(r => ({
        text: r.text,
        savingAmount: r.saving_amount,
        status: r.status,
        createdAt: new Date(r.created_at).toISOString(),
      })),
    });
  }

  if (name === 'complete_mission') {
    const db = getDb();
    const mission = db
      .prepare('SELECT id, text, saving_amount FROM missions WHERE user_id = ? AND status = ? ORDER BY created_at DESC LIMIT 1')
      .get(userId, 'accepted') as { id: string; text: string; saving_amount: number } | undefined;

    if (!mission) {
      return JSON.stringify({ error: '수락된 미션이 없습니다.' });
    }

    db.prepare('UPDATE missions SET status = ? WHERE id = ?').run('completed', mission.id);
    flags.completedMissionId = mission.id;
    return JSON.stringify({
      ok: true,
      completed: { text: mission.text, savingAmount: mission.saving_amount },
      message: '미션 완료 처리됐습니다.',
    });
  }

  if (name === 'update_user_profile') {
    const db = getDb();
    const { monthly_income, current_savings } = args as {
      monthly_income?: number;
      current_savings?: number;
    };

    if (!monthly_income && !current_savings) {
      return JSON.stringify({ error: '변경할 값이 없습니다.' });
    }

    // 변경 항목만 SET 절에 포함
    const sets: string[] = [];
    const params: unknown[] = [];
    if (monthly_income) { sets.push('monthly_income = ?'); params.push(monthly_income); }
    if (current_savings) { sets.push('current_savings = ?'); params.push(current_savings); }
    params.push(userId);

    db.prepare(`UPDATE users SET ${sets.join(', ')} WHERE id = ?`).run(...params);
    flags.profileUpdated = true; // route.ts에서 simulation 재실행 트리거

    return JSON.stringify({
      ok: true,
      updated: { monthly_income, current_savings },
      message: '프로필이 업데이트됐습니다. 시뮬레이션을 다시 계산합니다.',
    });
  }

  if (name === 'get_daily_spending') {
    const db = getDb();
    const month = (args.month as string) || new Date().toISOString().slice(0, 7);

    const rows = db
      .prepare(
        `SELECT date, category, SUM(amount) AS total
         FROM transactions
         WHERE user_id = ? AND strftime('%Y-%m', date) = ?
         GROUP BY date, category
         ORDER BY date`,
      )
      .all(userId, month) as { date: string; category: string; total: number }[];

    if (rows.length === 0) {
      return JSON.stringify({ message: '해당 월의 거래 데이터가 없습니다.' });
    }

    // 카테고리 목록 (총합 제외)
    const categories = [...new Set(rows.map((r) => r.category))];

    // 날짜별로 카테고리 지출 + 총합 집계
    const byDate: Record<string, Record<string, number>> = {};
    for (const row of rows) {
      if (!byDate[row.date]) byDate[row.date] = {};
      byDate[row.date][row.category] = row.total;
    }
    const points = Object.entries(byDate).map(([date, cats]) => ({
      date,
      total: Object.values(cats).reduce((s, v) => s + v, 0),
      ...cats,
    }));

    // flags에 저장 → coach()가 CoachOutput에 포함시켜 route로 전달
    flags.dailySpending = { month, points, categories };

    return JSON.stringify({ ok: true, month, days: points.length });
  }

  if (name === 'get_spending_comparison') {
    const db = getDb();

    // 이번 달 / 저번 달 / 저저번 달의 YYYY-MM 문자열 생성
    const now = new Date();
    const months = [0, 1, 2].map((offset) => {
      const d = new Date(now.getFullYear(), now.getMonth() - offset, 1);
      return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
    });

    // 월별 · 카테고리별 합계
    const categoryRows = db
      .prepare(
        `SELECT strftime('%Y-%m', date) AS month, category, SUM(amount) AS total
         FROM transactions
         WHERE user_id = ? AND strftime('%Y-%m', date) IN (?, ?, ?)
         GROUP BY month, category
         ORDER BY month DESC, total DESC`,
      )
      .all(userId, months[0], months[1], months[2]) as {
        month: string; category: string; total: number;
      }[];

    if (categoryRows.length === 0) {
      return JSON.stringify({ message: '거래 데이터가 없습니다.' });
    }

    // 월별 · 카테고리별 · 가맹점별 합계
    const merchantRows = db
      .prepare(
        `SELECT strftime('%Y-%m', date) AS month, category, merchant, SUM(amount) AS total
         FROM transactions
         WHERE user_id = ? AND strftime('%Y-%m', date) IN (?, ?, ?)
         GROUP BY month, category, merchant
         ORDER BY month DESC, category, total DESC`,
      )
      .all(userId, months[0], months[1], months[2]) as {
        month: string; category: string; merchant: string; total: number;
      }[];

    const labels: Record<string, string> = {
      [months[0]]: '이번달',
      [months[1]]: '저번달',
      [months[2]]: '저저번달',
    };

    // 월별로 묶고, 카테고리 안에 가맹점 목록 중첩
    const result: Record<string, unknown> = {};
    for (const m of months) {
      result[labels[m]] = {
        month: m,
        categories: categoryRows
          .filter((r) => r.month === m)
          .map((r) => ({
            category: r.category,
            total: r.total,
            merchants: merchantRows
              .filter((mr) => mr.month === m && mr.category === r.category)
              .map((mr) => ({ name: mr.merchant, total: mr.total })),
          })),
      };
    }

    return JSON.stringify(result);
  }

  return JSON.stringify({ error: '알 수 없는 도구입니다.' });
}

const MAX_RETRIES = 3; // 429(rate limit) 시 최대 재시도 횟수

// ─── 메인 함수: coach() ───
// chat route에서 호출됨. 분석 데이터 + 시뮬레이션 + 대화 이력을 받아서
// LLM에게 보내고, tool call이 있으면 루프 돌면서 처리한 뒤 최종 텍스트를 반환.
export async function coach(input: CoachInput): Promise<CoachOutput> {
  const { analysis, simulation, userMessage, chatHistory, userId } = input;

  // ── messages 조립 ──
  // [system] 시스템 프롬프트 + 분석/시뮬레이션 데이터
  // [user/assistant ...] 과거 대화 이력 (최근 20건, DB에서 가져옴)
  // [user] 현재 사용자 메시지
  const today = new Date().toISOString().slice(0, 10);
  const messages: ChatCompletionMessageParam[] = [
    {
      role: 'system',
      content: SYSTEM_PROMPT
        + `\n\n오늘 날짜: ${today}`
        + '\n\n[분석 데이터]\n' + JSON.stringify(analysis)
        + '\n\n[시뮬레이션]\n' + JSON.stringify(simulation),
    },
    ...chatHistory.map(h => ({
      role: (h.role === 'ai' ? 'assistant' : 'user') as 'assistant' | 'user',
      content: h.content,
    })),
    {
      role: 'user',
      content: userMessage || '처음 방문한 사용자입니다. 전체 소비 요약을 해주세요.',
    },
  ];

  // ── 1차 LLM 호출 ──
  const response = await callWithRetry(messages);

  // ── Tool Call 루프 ──
  // LLM 응답에 tool_calls가 있으면:
  //   1. assistant 메시지(tool_calls 포함)를 messages에 추가
  //   2. 각 tool_call을 executeTool()로 실행
  //   3. 결과를 role:'tool' 메시지로 messages에 추가
  //   4. LLM을 다시 호출 → 또 tool_call이면 반복, 텍스트면 종료
  const flags: { profileUpdated: boolean; completedMissionId?: string; dailySpending?: DailySpendingData } = { profileUpdated: false };
  let msg = response.choices[0]?.message;
  while (msg?.tool_calls && msg.tool_calls.length > 0) {
    console.log(`[coach] tool call ${msg.tool_calls.length}건 수신`);
    messages.push(msg);
    for (const tc of msg.tool_calls) {
      if (tc.type !== 'function') continue;
      const fn = tc.function;
      const args = JSON.parse(fn.arguments || '{}') ?? {};
      console.log(`[coach] → ${fn.name}(${JSON.stringify(args)})`);
      const result = executeTool(fn.name, args, userId, flags);
      console.log(`[coach] ← ${result.slice(0, 200)}`);
      messages.push({
        role: 'tool',
        tool_call_id: tc.id,
        content: result,
      });
    }
    // tool 결과를 포함해서 LLM 재호출
    const next = await callWithRetry(messages);
    msg = next.choices[0]?.message;
  }

  // ── 최종 응답 파싱 ──
  const rawContent = msg?.content ?? '';
  console.log(`[coach] raw 응답:\n${rawContent}`);
  return { ...parseResponse(rawContent), profileUpdated: flags.profileUpdated, completedMissionId: flags.completedMissionId, dailySpending: flags.dailySpending };
}

// ─── LLM 호출 + 429 재시도 ───
// 429(rate limit) 발생 시 지수 백오프(1s → 2s → 4s)로 재시도.
// 그 외 에러는 즉시 throw.
async function callWithRetry(
  messages: ChatCompletionMessageParam[],
): Promise<OpenAI.Chat.Completions.ChatCompletion> {
  for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
    try {
      return await client.chat.completions.create({
        model: 'gpt-4o-mini',
        messages,
        tools, // LLM에게 사용 가능한 tool 목록 전달
      });
    } catch (err: unknown) {
      const isRateLimit =
        err instanceof Error && 'status' in err && (err as { status: number }).status === 429;

      if (isRateLimit && attempt < MAX_RETRIES - 1) {
        const delay = Math.pow(2, attempt) * 1000; // 1s → 2s → 4s
        await sleep(delay);
        continue;
      }
      throw err;
    }
  }

  throw new Error('LLM 호출 최대 재시도 횟수 초과');
}

// ─── 응답 파싱 ───
// LLM 응답에서 본문(content)과 미션(mission)을 분리.
// ---MISSION_JSON--- 마커가 있으면 그 앞이 본문, 안의 JSON이 미션.
// 마커가 없거나 JSON 파싱 실패 시 전체를 본문으로, 미션은 null.
function parseResponse(raw: string): CoachOutput {
  const missionMarker = '---MISSION_JSON---';
  const endMarker = '---END_MISSION_JSON---';

  const markerIdx = raw.indexOf(missionMarker);
  if (markerIdx === -1) {
    return { content: raw.trim(), mission: null };
  }

  const content = raw.slice(0, markerIdx).trim(); // 마커 앞 = 본문
  const jsonStart = markerIdx + missionMarker.length;
  const jsonEnd = raw.indexOf(endMarker, jsonStart);
  const jsonStr = raw.slice(jsonStart, jsonEnd === -1 ? undefined : jsonEnd).trim();

  try {
    const parsed = JSON.parse(jsonStr) as { text: string; savingAmount: number };
    return {
      content,
      mission: { text: parsed.text, savingAmount: parsed.savingAmount },
    };
  } catch {
    // JSON 파싱 실패 시 미션 없이 전체를 본문으로
    return { content: raw.trim(), mission: null };
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}
