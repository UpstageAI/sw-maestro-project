// ─── PATCH /api/missions ───
// 미션 카드에서 수락/거절 버튼을 누르거나, Coach가 complete_mission 툴로
// 완료 처리할 때 호출된다. missions 테이블의 status 컬럼 하나만 바꾼다.
//
// 허용 status: accepted | rejected | completed
// - accepted:  사용자가 미션 수락 버튼 클릭
// - rejected:  사용자가 미션 거절 버튼 클릭
// - completed: Coach의 complete_mission 툴 호출 (대화로 완료 보고)

import { NextResponse } from 'next/server';
import getDb from '@/lib/db';

export async function PATCH(req: Request) {
  try {
    const { missionId, status } = (await req.json()) as {
      missionId: string;
      status: 'accepted' | 'rejected' | 'completed';
    };

    // 필수 값 누락 or 허용되지 않은 status 차단
    if (!missionId || !['accepted', 'rejected', 'completed'].includes(status)) {
      return NextResponse.json({ error: '잘못된 요청입니다.' }, { status: 400 });
    }

    const db = getDb();
    const result = db
      .prepare('UPDATE missions SET status = ? WHERE id = ?')
      .run(status, missionId);

    // 해당 id 미션이 없으면 changes = 0
    if (result.changes === 0) {
      return NextResponse.json({ error: '미션을 찾을 수 없습니다.' }, { status: 404 });
    }

    return NextResponse.json({ ok: true, missionId, status });
  } catch (error) {
    console.error('[missions] error:', error);
    return NextResponse.json({ error: '미션 업데이트 중 오류가 발생했습니다.' }, { status: 500 });
  }
}
