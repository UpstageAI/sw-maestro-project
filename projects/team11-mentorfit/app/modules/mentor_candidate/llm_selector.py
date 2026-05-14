from __future__ import annotations

import json
import logging

from app.core.upstage import upstage_client
from pydantic import TypeAdapter
from app.modules.mentor_candidate.schemas import CandidateResult, CandidateResultInternal, Mentor, TeamProfile

logger = logging.getLogger(__name__)

async def select_candidates(
    team_profile: TeamProfile,
    mentors: list[Mentor],
    top_k: int = 5,
) -> list[CandidateResult]:
    """
    LLM을 사용하여 팀 프로필에 가장 적합한 멘토 K명을 선택합니다.
    """
    
    # Lost in the Middle 문제 완화: U-shaped re-ranking
    # retriever에서 코사인 유사도 순(가장 적합한 순서)으로 정렬되어 들어왔음.
    # LLM은 프롬프트의 처음과 끝을 가장 잘 기억하므로, 가장 중요한 멘토들을 양 끝에 배치.
    # 목표 순서 예시 (1~6등): [1등, 3등, 5등, 6등, 4등, 2등]
    if len(mentors) > 1:
        left = []
        right = []
        for i, m in enumerate(mentors):
            if i % 2 == 0:
                left.append(m)  # 0, 2, 4... 인덱스 (1등, 3등, 5등...)
            else:
                right.append(m) # 1, 3, 5... 인덱스 (2등, 4등, 6등...)
        right.reverse() # 짝수 등수를 역순으로 만듦
        reordered_mentors = left + right
    else:
        reordered_mentors = mentors

    # 멘토 정보 포맷팅
    mentors_info = ""
    for m in reordered_mentors:
        # 주요 특징을 강조하기 위한 뱃지 텍스트 생성
        badges = []
        # SW마에스트로 도메인 지식 반영: 인증 여부는 멘토 자격이 아니라 과거 멘토링 팀의 최종 인증(우수자) 배출 여부를 의미함
        if m.is_certificated:
            badges.append("[🏆 소마 인증자 배출 경험 보유]")
        else:
            badges.append("[🌱 소마 인증자 배출 경험 없음]")

        if m.is_overseas:
            badges.append("[🌍 해외 멘토]")
        if m.is_new_mentor:
            badges.append("[✨ 올해 신규 합류 멘토]")
        if m.can_plan:
            badges.append("[💡 기획 멘토링 가능]")

        mentors_info += f"### 멘토 ID: {m.mentor_id} (이름: {m.name})\n"
        mentors_info += f"- 특징: {' '.join(badges)}\n"
        mentors_info += f"- 기술스택: {', '.join(m.stacks)}\n"
        mentors_info += f"- 도메인: {', '.join(m.domains)}\n"
        mentors_info += f"- 멘토링 목표: {m.target}\n"
        mentors_info += f"- 관심사/취미: {m.hobbie}\n"
        mentors_info += f"- 미팅 선호 방식: {m.meeting_mode_preference}\n"

        career_str = ", ".join([f"{c[0]}({c[1]}년)" for c in m.career])
        mentors_info += f"- 경력: {career_str}\n"
        mentors_info += "\n"

    # 팀 프로필 포맷팅
    team_info = f"""
- 기술 스택: {team_profile.skills}
- R&R: {team_profile.members_rnr}
- 프로젝트 계획 및 기술적 목표: {team_profile.project_plan_tech_goals}
- 소마 과정 목표: {team_profile.maestro_program_goals}
- 멘토링 니즈: {team_profile.mentoring_needs}
- 선호 조건: {team_profile.fit_conditions}
"""

    system_prompt = """당신은 SW마에스트로(소마) 과정의 팀과 멘토를 매칭해주는 엄격하고 전문적인 운영진입니다.
제공된 팀 프로필과 가용한 멘토들의 정보를 분석하여, 해당 팀에 가장 도움이 될 만한 멘토 후보들을 선정해주세요.

[SW마에스트로 도메인 지식 및 지시사항]
1. '소마 인증자 배출 경험(is_certificated)'이란 과거에 지도했던 멘티 팀이 우수한 성적으로 최종 '인증'을 받았는지를 의미합니다.
2. SW마에스트로는 자기 주도적인 심화 프로젝트를 수행하는 약 6개월간의 고밀도 과정입니다. 단순한 코딩 교육이 아니며, 팀워크, 아키텍처 설계, 비즈니스 모델 등 실무적인 피드백이 매우 중요합니다.
3. [핵심 평가 기준] 멘토를 평가할 때 절대 '기술 스택'에만 매몰되지 마십시오. 팀의 '프로젝트 계획 및 기술적 목표', '소마 과정 목표(인증/창업/취업)', '멘토링 니즈', '선호 조건(미팅 방식, 출신 경력 등)'을 모두 종합적으로 분석해야 합니다.

[🚨 최고 수준의 경고: 데이터 정합성 및 UX/파이프라인 작성 규칙 🚨]
당신은 멘토를 팀에 맞추기 위해 '거짓말'을 하거나, 시스템 내부 ID를 노출하거나, 필드의 목적을 섞어서는 안 됩니다.

1. `reasoning_process` 필드: [내부용] 멘토의 팩트를 나열하고 팀의 요구사항과 매칭하는 사고 과정. 반드시 3가지 관점(기술, 목표, 핏)에서 솔직하게 분석하십시오.
   - 반드시 "현재 분석 중인 멘토: [ID: {mentor_id}, 이름: {name}]" 로 시작하십시오.

2. `reason` 필드 (추천 근거): [사용자 노출용] 고급 헤드헌터의 추천서처럼 작성하십시오.
   - **필수 규칙**: 반드시 '{name} 멘토님은...' 처럼 성함을 사용하십시오. '멘토 ID', 'ID 12' 등은 절대 금지입니다.
   - **순수 긍정**: 이 필드에는 오직 멘토의 강점과 팀에 기여할 가치만 적으십시오. **"하지만", "다만", "~는 없으나" 같은 부정적인 내용은 1글자도 적지 마십시오.** (그 내용은 weak_point의 몫입니다.)
   - **팩트 기반**: 없는 기술을 지어내지 마십시오. 실제 스택이 다르다면 "기초 기술력"이나 "아키텍처 역량" 등 본질적인 강점을 포장하십시오.

3. `weak_point` 필드 (보완점): [사용자 및 파이프라인 연계용] 냉철한 전략 분석가처럼 작성하십시오.
   - **순수 부정**: 팀의 요구사항 대비 부족한 점(스택 부재, 도메인 불일치 등)만 명확하게 적으십시오. **"그럼에도 불구하고", "대신 ~는 가능" 같은 변명이나 강점 언급은 절대 금지입니다.**
   - **문장 형식**: 단답형 키워드 나열을 금지하고, 정중하고 완성된 문장으로 작성하십시오.
   - **ID 노출 금지**: 여기서도 성함을 사용하거나 주어를 생략하십시오. ID 언급은 절대 금지입니다.

조건에 완벽히 부합하지 않더라도 요청받은 멘토 인원수를 반드시 꽉 채워서 출력해야 하며, 중복 추천은 금지됩니다.
"""

    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "mentor_candidates",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "candidates": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "mentor_id": {
                                    "type": "integer",
                                    "description": "선정된 멘토의 고유 ID"
                                },
                                "rank": {
                                    "type": "integer",
                                    "description": "추천 순위 (1부터 시작)"
                                },
                                "extracted_facts": {
                                    "type": "string",
                                    "description": "반드시 프롬프트 원문에서 이 ID에 해당하는 멘토의 실제 이름, 스택, 도메인, 경력을 정확하게 발췌하여 작성 (조작/혼합 금지)"
                                },
                                "reasoning_process": {
                                    "type": "string",
                                    "description": "[사고 과정] 1.기술/프로젝트, 2.목표(인증/창업 등), 3.팀 핏(선호조건)의 3가지 차원에서 왜 이 멘토가 적합한지/부족한지 Step-by-Step으로 분석한 내부 사고 과정"
                                },
                                "reason": {
                                    "type": "string",
                                    "description": "reasoning_process를 바탕으로 기술 스택뿐만 아니라 팀의 목표와 멘토링 니즈에 어떻게 부합하는지 종합적으로 설명하는 구체적인 추천 이유 (한국어)"
                                },
                                "weak_point": {
                                    "type": "string",
                                    "description": "reasoning_process를 바탕으로 작성된 명확한 한계 및 아쉬운 점 (한국어)"
                                }
                            },
                            "required": ["mentor_id", "rank", "extracted_facts", "reasoning_process", "reason", "weak_point"],
                            "additionalProperties": False
                        }
                    }
                },
                "required": ["candidates"],
                "additionalProperties": False
            }
        }
    }

    valid_mentor_ids = {m.mentor_id for m in mentors}
    max_retries = 3
    accumulated_candidates: list[CandidateResult] = []
    seen_ids = set()

    for attempt in range(max_retries):
        missing_count = top_k - len(accumulated_candidates)
        
        if len(accumulated_candidates) > 0:
            already_selected_ids = [str(c.mentor_id) for c in accumulated_candidates]
            dynamic_instruction = f"다음 팀에게 가장 적합한 서로 다른 멘토를 반드시 '정확히 {missing_count}명' 추가로 선정해주세요. (결과 배열의 크기가 무조건 {missing_count}이어야 합니다)\n[경고] 이미 멘토 ID [{', '.join(already_selected_ids)}]가 선정되었습니다. 이들을 절대 중복해서 추천하지 마세요."
        else:
            dynamic_instruction = f"다음 팀에게 가장 적합한 서로 다른 멘토를 반드시 '정확히 {top_k}명' 선정해주세요. (결과 배열의 크기가 무조건 {top_k}이어야 하고, 중복된 멘토가 없어야 합니다)"

        user_prompt = f"""{dynamic_instruction}

[팀 프로필]
{team_info}

[멘토 목록]
{mentors_info}
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        try:
            logger.info(f"   🤖 [Attempt {attempt+1}] LLM 멘토 선정 요청 (목표: {top_k}명)")
            response_text = await upstage_client.get_chat_completion(
                messages=messages, 
                model="solar-pro3",
                response_format=response_format
            )
            
            # JSON Schema를 {"candidates": [...]} 형태의 객체로 받았으므로 파싱 시에도 꺼내어 사용
            data = json.loads(response_text)
            candidates_list = data.get("candidates", [])
            
            # Pydantic TypeAdapter를 이용한 내부 스키마 검증 (reasoning_process 포함)
            adapter = TypeAdapter(list[CandidateResultInternal])
            parsed_candidates_internal = adapter.validate_python(candidates_list)
            
            # 내부 스키마에서 외부 공개용 스키마(CandidateResult)로 매핑
            # 상속 구조이므로 reasoning_process만 제외하고 동적으로 매핑하여 일관성 유지
            parsed_candidates = [
                CandidateResult(**c.model_dump(exclude={"reasoning_process", "extracted_facts"})) 
                for c in parsed_candidates_internal
            ]
            
            # 검증 로직: 중복 ID 제거 및 유효한 ID인지 확인하여 누적
            new_finds = 0
            for c in parsed_candidates:
                if c.mentor_id not in seen_ids and c.mentor_id in valid_mentor_ids:
                    accumulated_candidates.append(c)
                    seen_ids.add(c.mentor_id)
                    new_finds += 1
                else:
                    logger.debug(f"     ⚠️ 무효하거나 중복된 멘토 ID 무시됨: {c.mentor_id}")

            logger.info(f"     ✅ 파싱 성공: 새로 유효하게 추가된 멘토 {new_finds}명 (현재 총 {len(accumulated_candidates)}/{top_k}명)")
            
            # 요구한 인원수를 다 채웠는지 확인
            if len(accumulated_candidates) >= top_k:
                final_candidates = accumulated_candidates[:top_k]
                # 순위 재정렬
                for i, c in enumerate(final_candidates):
                    c.rank = i + 1
                return final_candidates
            else:
                logger.warning(f"   [Attempt {attempt+1}] 부족한 인원수 ({len(accumulated_candidates)}/{top_k}명 확보됨). 재시도 요청을 보냅니다.")
                
        except Exception as e:
            logger.error(f"   ❌ [Attempt {attempt+1}] LLM 파싱/검증 오류: {e}")
            messages.append({"role": "user", "content": "JSON 형식이 잘못되었거나 파싱 오류가 발생했습니다. 할루시네이션(거짓 정보) 없이 프롬프트 규칙에 맞춰 다시 시도해주세요."})
            
    # [무조건 보장 로직] 모든 재시도 후에도 top_k명을 못 채웠을 경우
    missing_count = top_k - len(accumulated_candidates)
    if missing_count > 0:
        logger.critical(f"   🚨 [Fallback 발동] LLM이 {missing_count}명을 채우지 못했습니다. 가용 풀에서 강제 할당합니다.")
        remaining_mentors = [m for m in mentors if m.mentor_id not in seen_ids]
        
        for m in remaining_mentors[:missing_count]:
            fallback_candidate = CandidateResult(
                mentor_id=m.mentor_id,
                rank=len(accumulated_candidates) + 1,
                reason=f"{m.name} 멘토님은 {', '.join(m.stacks)} 등 팀의 기술 스택 전반에 걸친 폭넓은 지식을 바탕으로 프로젝트의 안정성을 높여줄 수 있는 전문가입니다.",
                weak_point="직접적인 도메인 경험이나 상세한 적합도 분석은 다소 부족할 수 있습니다."
            )
            accumulated_candidates.append(fallback_candidate)
            seen_ids.add(m.mentor_id)

    # 최종 결과물이 top_k개를 넘는 경우 자르기
    final_candidates = accumulated_candidates[:top_k]
    
    # 최종 순위 재정렬
    for i, c in enumerate(final_candidates):
        c.rank = i + 1
        
    return final_candidates
