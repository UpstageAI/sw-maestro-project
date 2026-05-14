// ADR-0008 BFF API 표면 11 endpoint의 request / response 계약.
// 4xx/5xx 응답은 ./error의 ErrorBody.

import type { Pet, Diary, MoodTag, Gender, Profile } from './domain';

// ============================================================
// diaries
// ============================================================

// POST /api/diaries/generate — 첫 생성. BFF가 새 session_id 발급.
export interface GenerateRequest {
  pet_id: string;
  photo_path: string;   // Storage path (클라이언트가 supabase-js로 업로드 후 BFF에 전달, ADR-0009)
  keywords: string;     // 1~1000자
}
export interface GenerateResponse {
  session_id: string;            // UUID, 클라이언트 메모리 보관 (ADR-0008)
  generation_id: string;
  diary_text: string;
  short_caption: string;
  mood_tag: MoodTag;
  regenerate_remaining: number;  // 0~3
  today_new_remaining: number;   // 0~5
}

// POST /api/diaries/regenerate — 재생성. seq는 BFF가 결정.
export interface RegenerateRequest {
  session_id: string;
  pet_id: string;
  photo_path: string;
  keywords: string;
  feedback?: string;    // 1~500자, NULL 허용
}
export interface RegenerateResponse {
  generation_id: string;
  diary_text: string;
  short_caption: string;
  mood_tag: MoodTag;
  regenerate_remaining: number;
}

// POST /api/diaries — generation 채택. diaries INSERT.
export interface AdoptDiaryRequest {
  source_generation_id: string;
}
export interface AdoptDiaryResponse {
  diary_id: string;
}

// DELETE /api/diaries/:id — 일기 hard delete + same-session generations + storage object 동반.
// path param: id. 성공 시 204 No Content (응답 body 없음).

// GET /api/diaries — 펫별 피드 (cursor pagination).
export interface ListDiariesQuery {
  petId: string;
  cursor?: string;       // opaque (BFF 발급, 클라이언트는 그대로 echo)
  limit?: number;        // 기본 20, max 50
}
export interface ListDiariesResponse {
  items: Diary[];
  next_cursor: string | null;
}

// ============================================================
// pets
// ============================================================

// POST /api/pets — 펫 등록.
export interface CreatePetRequest {
  name: string;          // 1~20자
  species: string;       // 1~20자
  honorific: string;     // 1~20자
  gender: Gender;
}
export type CreatePetResponse = Pet;

// GET /api/pets — alive만 (deleted_at IS NULL).
export interface ListPetsResponse {
  items: Pet[];
}

// PATCH /api/pets/:id — 부분 수정. 응답은 갱신된 Pet.
export interface UpdatePetRequest {
  name?: string;
  species?: string;
  honorific?: string;
  gender?: Gender;
}
export type UpdatePetResponse = Pet;

// DELETE /api/pets/:id — soft delete (deleted_at = now()). 자식 일기 보존.
// path param: id. 성공 시 204 No Content.

// ============================================================
// profile
// ============================================================

// PATCH /api/profile — 닉네임 변경.
export interface UpdateProfileRequest {
  display_name: string;  // 1~24자
}
export type UpdateProfileResponse = Profile;

// ============================================================
// usage
// ============================================================

// GET /api/usage/today — 오늘 신규 잔여 횟수.
export interface UsageTodayResponse {
  new_remaining: number;  // 0~5
}
