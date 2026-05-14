import type { ConsultationSession } from '@/types';

export const MOCK_CONSULTATION: ConsultationSession = {
  userInput: '요즘 썸남이 답장이 늦는데 밀당인지 관심이 식은 건지 모르겠어.',

  opinions: [
    {
      agentId: 'playboy',
      advice:
        '에휴, 이런 거 100번은 봤다. 매달리지 말고 한 발만 빼봐. 따라오면 게임이고 안 따라오면 다음 카드.',
      rationale: '매달릴수록 가치가 떨어진다. 거리감이 권력이다.',
      stance: 'pause',
    },
    {
      agentId: 'ice',
      advice:
        '감정 변수 제거. 2주간 답장 빈도·길이·주제 데이터 수집 필요. 표본 부족 상태의 결론은 통계적 의미 없음.',
      rationale: '현재 정보 표본 크기 추정 1~2. 결론 도출 불가.',
      stance: 'mixed',
    },
    {
      agentId: 'confessor',
      advice:
        '지금 바로 고백해!!! 답장 늦는 거 신경 쓸 시간에 마음 던져버려! 차여도 데이터 하나 추가야!! 고고고!',
      rationale: '고민 시간 = 손해. 거절도 데이터, 수락은 보너스.',
      stance: 'proceed',
    },
    {
      agentId: 'bestie',
      advice: '야 ㅋㅋ 그냥 "오늘 뭐해?" 보내봐. 너무 어렵게 만들지 말자 우리.',
      rationale: '친구 시점에서 답 빤한데 본인이 자꾸 머리 굴리는 거임.',
      stance: 'clarify',
    },
  ],

  rounds: [
    {
      roundNumber: 1,
      messages: [
        {
          agentId: 'ice',
          content:
            '바람둥이의 "거리두기"는 표본 1의 일화 기반. 일반화 불가. 변수 통제 후 데이터 수집이 선결.',
          messageType: 'rebuttal',
          replyToAgentId: 'playboy',
        },
        {
          agentId: 'playboy',
          content:
            '데이터 데이터 노래 부르네. 연애는 통계가 아니라 타이밍이야. 차가운 분석은 사람 잃기 딱 좋아.',
          messageType: 'rebuttal',
          replyToAgentId: 'ice',
        },
        {
          agentId: 'confessor',
          content:
            '둘 다 멈춰있는 게 문제! 데이터고 거리두기고 일단 메시지 보내고 데이터 만들어!! 행동이 답이야!',
          messageType: 'rebuttal',
          replyToAgentId: 'ice',
        },
        {
          agentId: 'bestie',
          content:
            '솔직히 셋 다 너무 진지하다 ㅋㅋ 그냥 "잘 지내?" 톡 한 줄이면 끝나는 일임. 머리 굴리지 말자.',
          messageType: 'rebuttal',
          replyToAgentId: 'confessor',
        },
      ],
    },
    {
      roundNumber: 2,
      messages: [
        {
          agentId: 'ice',
          content:
            '재평가: 행동 우선 가설과 데이터 수집 가설의 절충안 가능. "한 번의 메시지" 자체가 추가 데이터 포인트가 됨. 비용 대비 정보량 적절.',
          messageType: 'deepdive',
        },
        {
          agentId: 'playboy',
          content:
            '인정. 한 번은 보내봐. 단, 매달리는 톤은 절대 금지. 가볍게, 답이 늦어도 신경 안 쓰는 척.',
          messageType: 'deepdive',
        },
        {
          agentId: 'confessor',
          content:
            '거봐!! 결국 다 행동하는 거야! 너무 늦지 마, 오늘이나 내일!!!',
          messageType: 'deepdive',
        },
        {
          agentId: 'bestie',
          content: '맞아, 가볍게 톡 한 줄. 그게 다임. 답 오면 좋고, 안 와도 그건 그것대로 답.',
          messageType: 'deepdive',
        },
      ],
    },
  ],

  finalResult: {
    situationSummary:
      '썸 상태에서 상대의 답장이 느려져 사용자가 다음 행동을 결정 못 하고 있는 상황. 정보가 부족해 의도 단정은 어렵고, 결정 지연 자체가 사용자의 불안을 키우는 구조.',
    keyConflicts: [
      '바람둥이 vs 연쇄고백마: 거리두기로 가치 유지 vs 즉시 행동으로 정보 확보',
      '얼음 분석가 vs 찐친: 표본 수집 후 판단 vs 메시지 하나로 종결',
    ],
    disagreements: [
      '거리두기로 상대를 끌어당기는 게 우선인지, 즉시 행동으로 정보를 얻는 게 우선인지',
      '데이터를 충분히 모은 뒤 판단할지, 일단 한 번 부딪혀볼지',
    ],
    advice:
      '가벼운 톤으로 한 번 메시지를 보내 상대의 반응을 데이터로 만들되, 매달리거나 의도 분석을 시도하지는 마세요. 답이 빠르면 관계 가능성 ↑, 늦거나 없으면 그 자체가 명확한 신호입니다.',
    actionItems: [
      {
        title: '가벼운 톡 한 줄',
        detail: '"오늘 뭐해?" 정도의 부담 없는 한 문장을 오늘 안에 보낸다.',
        timing: 'immediate',
      },
      {
        title: '24시간 관찰',
        detail: '답장 시간과 분위기를 기록하되, 그 사이엔 본인 일에 집중한다.',
        timing: 'short_term',
      },
      {
        title: '다음 카드 준비',
        detail: '답이 미지근하면 이 관계에 시간 더 쓸지 결정한다.',
        timing: 'long_term',
      },
    ],
    caveats: [
      '이 조언은 일반 패턴이고 개별 상황은 다를 수 있어요.',
      '메시지 한 통의 결과로 모든 걸 단정하지는 마세요.',
    ],
  },
};
