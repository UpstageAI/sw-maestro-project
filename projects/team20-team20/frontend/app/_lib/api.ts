// 백엔드 API 클라이언트.
//
// 백엔드 라우트 (backend/main.py 기준):
//   POST   /api/users                              {email, interest_text} → 유저 + 첫 관심사
//   GET    /api/users/{uid}/interests              관심사 목록
//   POST   /api/users/{uid}/interests              {interest_text}
//   DELETE /api/users/{uid}/interests/{keyword}
//   GET    /api/users/{uid}/settings
//   PATCH  /api/users/{uid}/settings               {email?, notification_frequency?}
//   GET    /api/users/{uid}/notifications?hours=N
//   POST   /api/notifications/{nid}/feedback       {feedback: 'like'|'dislike'|null}
//   GET    /api/notices                            전체 공지 (per-user 매칭 X)

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000'

export type Frequency = 'realtime' | 'daily' | 'weekly'
export type Feedback = 'like' | 'dislike' | null

export interface UserRegisterOut {
  user_id: number
  email: string
  interest_text: string
  interest_id: number | null
  created_user: boolean
  duplicate_interest: boolean
}

export interface SettingsOut {
  user_id: number
  email: string
  notification_frequency: Frequency
  created_at: string
}

export interface InterestListOut {
  user_id: number
  interests: string[]
}

export interface InterestOut {
  keyword: string
  interest_id: number | null
  duplicate: boolean
}

export interface NotificationItem {
  notification_id: number
  notice_id: number
  title: string
  url: string
  source_id: string
  posted_at: string | null
  summary: string
  queued_at: string | null
  sent_at: string | null
  status: string
  feedback: Feedback
}

export interface NotificationListOut {
  user_id: number
  items: NotificationItem[]
}

export interface NoticeItem {
  id: number
  source_id: string
  title: string
  url: string
  posted_at: string | null
  summary: string | null
  hash: string
  fetched_at: string
}

export interface NoticesOut {
  total: number
  items: NoticeItem[]
}

class ApiError extends Error {
  constructor(public status: number, public detail: unknown) {
    super(`HTTP ${status}: ${typeof detail === 'string' ? detail : JSON.stringify(detail)}`)
    this.name = 'ApiError'
  }
}

async function request<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init.headers ?? {}),
    },
  })
  if (!res.ok) {
    let detail: unknown
    try {
      const body = await res.json()
      detail = body?.detail ?? body
    } catch {
      detail = await res.text()
    }
    throw new ApiError(res.status, detail)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

// ───── 유저 ─────────────────────────────────────────────────────────────

export interface LoginOut {
  user_id: number
  email: string
  notification_frequency: Frequency
  interest_count: number
  created_at: string
}

export function registerUser(email: string, interestText: string) {
  return request<UserRegisterOut>('/api/users', {
    method: 'POST',
    body: JSON.stringify({ email, interest_text: interestText }),
  })
}

export function login(email: string) {
  return request<LoginOut>('/api/users/login', {
    method: 'POST',
    body: JSON.stringify({ email }),
  })
}

// ───── 관심사 ───────────────────────────────────────────────────────────

export function listInterests(userId: number) {
  return request<InterestListOut>(`/api/users/${userId}/interests`)
}

export function addInterest(userId: number, interestText: string) {
  return request<InterestOut>(`/api/users/${userId}/interests`, {
    method: 'POST',
    body: JSON.stringify({ interest_text: interestText }),
  })
}

export function removeInterest(userId: number, keyword: string) {
  return request<{ deleted: boolean; keyword: string }>(
    `/api/users/${userId}/interests/${encodeURIComponent(keyword)}`,
    { method: 'DELETE' },
  )
}

// ───── 설정 ────────────────────────────────────────────────────────────

export function getSettings(userId: number) {
  return request<SettingsOut>(`/api/users/${userId}/settings`)
}

export function updateSettings(
  userId: number,
  patch: { email?: string; notification_frequency?: Frequency },
) {
  return request<SettingsOut>(`/api/users/${userId}/settings`, {
    method: 'PATCH',
    body: JSON.stringify(patch),
  })
}

// ───── 알림(피드) ──────────────────────────────────────────────────────

export function listMyNotifications(userId: number, hours = 24 * 7) {
  return request<NotificationListOut>(
    `/api/users/${userId}/notifications?hours=${hours}`,
  )
}

export function setFeedback(notificationId: number, feedback: Feedback) {
  return request<{ notification_id: number; feedback: Feedback }>(
    `/api/notifications/${notificationId}/feedback`,
    { method: 'POST', body: JSON.stringify({ feedback }) },
  )
}

// ───── 공지(전체) ──────────────────────────────────────────────────────

export function listNotices(opts: { source?: string; limit?: number; offset?: number } = {}) {
  const qs = new URLSearchParams()
  if (opts.source) qs.set('source', opts.source)
  if (opts.limit != null) qs.set('limit', String(opts.limit))
  if (opts.offset != null) qs.set('offset', String(opts.offset))
  const suffix = qs.toString() ? `?${qs}` : ''
  return request<NoticesOut>(`/api/notices${suffix}`)
}

// ───── localStorage 헬퍼 (간이 세션) ────────────────────────────────────

const LS_USER_ID = 'user_id'
const LS_EMAIL = 'user_email'

export function saveSession(userId: number, email: string) {
  if (typeof window === 'undefined') return
  localStorage.setItem(LS_USER_ID, String(userId))
  localStorage.setItem(LS_EMAIL, email)
}

export function getUserId(): number | null {
  if (typeof window === 'undefined') return null
  const v = localStorage.getItem(LS_USER_ID)
  return v ? Number(v) : null
}

export function getEmail(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem(LS_EMAIL)
}

export function clearSession() {
  if (typeof window === 'undefined') return
  localStorage.removeItem(LS_USER_ID)
  localStorage.removeItem(LS_EMAIL)
}

export { ApiError }
