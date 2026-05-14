// 도메인 엔티티 + 공유 enum/유니온. ADR-0010 데이터 모델 / DESIGN.md 출력 스펙 정합.

export type MoodTag = '행복' | '신남' | '평온' | '졸림' | '심심' | '슬픔' | '까칠';

export const MOOD_TAGS: readonly MoodTag[] = [
  '행복',
  '신남',
  '평온',
  '졸림',
  '심심',
  '슬픔',
  '까칠',
] as const;

export type Gender = 'male' | 'female' | 'unknown';

// BFF 응답에서 클라이언트가 보는 펫 모양. owner_id/deleted_at은 응답에 노출하지 않는다.
export interface Pet {
  id: string;
  name: string;        // 1~20자, trim
  species: string;     // 1~20자, 자유 입력 (cat/dog 분기는 prompt layer)
  honorific: string;   // 1~20자
  gender: Gender;
  created_at: string;  // ISO 8601
  updated_at: string;
}

// BFF 응답 일기 모양. photo_signed_url은 BFF가 호출 시점에 발급 (TTL 1h, ADR-0009).
export interface Diary {
  id: string;
  pet_id: string;
  diary_text: string;
  short_caption: string;
  mood_tag: MoodTag;
  photo_signed_url: string;
  created_at: string;
}

// 클라이언트가 supabase-js로 직접 SELECT하는 profiles row 모양 (β 패턴, ADR-0006).
export interface Profile {
  display_name: string;  // 1~24자
  updated_at: string;
}

// LLM 산출물. Gateway 응답 + BFF generate/regenerate 응답에 공통 포함.
export interface DiaryGenerationResult {
  diary_text: string;
  short_caption: string;
  mood_tag: MoodTag;
}
