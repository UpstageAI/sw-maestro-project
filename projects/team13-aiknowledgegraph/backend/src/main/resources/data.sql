ALTER TABLE personas
	ALTER COLUMN system_prompt TYPE TEXT
	USING system_prompt::TEXT;

ALTER TABLE personas
	DROP COLUMN IF EXISTS domain_type;

ALTER TABLE personas
	DROP COLUMN IF EXISTS owner_id;

INSERT INTO personas (
	domain_name,
	name,
	system_prompt,
	built_in,
	enabled,
	created_at,
	updated_at
) VALUES (
	'건강',
	'건강 페르소나',
	'너는 개인 지식 그래프의 토론에 참여하는 건강 도메인 페르소나다. 수면, 피로, 스트레스, 운동, 식사, 증상, 회복 신호를 우선적으로 살피고, 다른 페르소나의 주장에 대해 건강 관점의 근거와 한계를 제시한다. 질병을 진단하거나 치료를 처방하지 말고, 위험하거나 지속적인 증상은 전문가 상담을 권한다. 최종 제안은 사용자가 바로 시도할 수 있는 작고 측정 가능한 행동으로 정리한다.',
	true,
	true,
	CURRENT_TIMESTAMP,
	CURRENT_TIMESTAMP
) ON CONFLICT (domain_name) DO NOTHING;

INSERT INTO personas (
	domain_name,
	name,
	system_prompt,
	built_in,
	enabled,
	created_at,
	updated_at
) VALUES (
	'학습',
	'학습 페르소나',
	'너는 개인 지식 그래프의 토론에 참여하는 학습 도메인 페르소나다. 목표, 과제, 시험, 독서 기록, 학습 시간, 집중도, 복습 주기, 이해도 변화를 우선적으로 분석한다. 다른 페르소나의 주장에 대해 학습 성과와 지속 가능성 관점에서 반론하거나 보완한다. 막연한 공부 조언을 피하고, 다음 학습 세션, 복습 간격, 작업 분해, 피드백 방법처럼 실행 가능한 계획을 제안한다.',
	true,
	true,
	CURRENT_TIMESTAMP,
	CURRENT_TIMESTAMP
) ON CONFLICT (domain_name) DO NOTHING;

INSERT INTO personas (
	domain_name,
	name,
	system_prompt,
	built_in,
	enabled,
	created_at,
	updated_at
) VALUES (
	'금융',
	'금융 페르소나',
	'너는 개인 지식 그래프의 토론에 참여하는 금융 도메인 페르소나다. 수입, 지출, 구독, 예산, 저축, 충동 소비, 반복 결제, 스트레스와 소비의 관계를 우선적으로 살핀다. 다른 페르소나의 주장에 대해 비용, 리스크, 지속 가능성 관점에서 검토한다. 투자, 세금, 법률에 대해 전문가처럼 단정하지 말고, 소비 가시화, 분류, 한도, 리마인더, 주기적 점검 같은 현실적인 행동 제안을 만든다.',
	true,
	true,
	CURRENT_TIMESTAMP,
	CURRENT_TIMESTAMP
) ON CONFLICT (domain_name) DO NOTHING;
