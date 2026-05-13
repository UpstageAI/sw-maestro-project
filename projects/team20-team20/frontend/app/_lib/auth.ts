export type User = {
  name: string
  email: string
  department: string
  grade: string
}

export type PendingSignup = {
  name: string
  email: string
  password: string
  department: string
  grade: string
}

export function getPendingSignup(): PendingSignup | null {
  if (typeof window === 'undefined') return null
  const data = localStorage.getItem('pendingSignup')
  return data ? JSON.parse(data) : null
}

export function setPendingSignup(data: PendingSignup): void {
  localStorage.setItem('pendingSignup', JSON.stringify(data))
}

export function clearPendingSignup(): void {
  localStorage.removeItem('pendingSignup')
}

export function getUser(): User | null {
  if (typeof window === 'undefined') return null
  const data = localStorage.getItem('user')
  return data ? JSON.parse(data) : null
}

export function setUser(user: User): void {
  localStorage.setItem('user', JSON.stringify(user))
}

export function isLoggedIn(): boolean {
  if (typeof window === 'undefined') return false
  return localStorage.getItem('isLoggedIn') === 'true'
}

export function getUserId(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem('userId')
}

export function setUserId(uid: string): void {
  localStorage.setItem('userId', uid)
}

export function login(): void {
  localStorage.setItem('isLoggedIn', 'true')
}

export function logout(): void {
  localStorage.removeItem('isLoggedIn')
  localStorage.removeItem('userId')
}

export function isOnboarded(): boolean {
  if (typeof window === 'undefined') return false
  return localStorage.getItem('onboardingComplete') === 'true'
}

export function setOnboarded(): void {
  localStorage.setItem('onboardingComplete', 'true')
}
