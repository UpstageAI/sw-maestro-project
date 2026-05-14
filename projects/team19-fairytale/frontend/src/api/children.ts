import { authHeaders, request } from "./client";

export type Child = {
  id: string;
  user_id: string;
  name: string;
  age: number;
  personality: string;
  favorite_character: string;
  favorite_toy: string;
  family_relationship: string;
  created_at: string;
  updated_at: string;
};

export type ChildCreatePayload = {
  name: string;
  age: number;
  personality: string;
  favorite_character: string;
  favorite_toy?: string;
  family_relationship?: string;
};

export type ChildUpdatePayload = Partial<ChildCreatePayload>;

export type Experience = {
  id: string;
  child_id: string;
  content: string;
  experienced_at: string;
  created_at: string;
};

export type ExperienceCreatePayload = {
  content: string;
  experienced_at?: string | null;
};

export function createChild(
  payload: ChildCreatePayload,
  token: string
): Promise<Child> {
  return request<Child>("/children", {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(payload)
  });
}

export function listChildren(token: string): Promise<Child[]> {
  return request<Child[]>("/children", {
    headers: authHeaders(token)
  });
}

export function getChild(childId: string, token: string): Promise<Child> {
  return request<Child>(`/children/${childId}`, {
    headers: authHeaders(token)
  });
}

export function updateChild(
  childId: string,
  payload: ChildUpdatePayload,
  token: string
): Promise<Child> {
  return request<Child>(`/children/${childId}`, {
    method: "PUT",
    headers: authHeaders(token),
    body: JSON.stringify(payload)
  });
}

export function deleteChild(childId: string, token: string): Promise<void> {
  return request<void>(`/children/${childId}`, {
    method: "DELETE",
    headers: authHeaders(token)
  });
}

export function createExperience(
  childId: string,
  payload: ExperienceCreatePayload,
  token: string
): Promise<Experience> {
  return request<Experience>(`/children/${childId}/experiences`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(payload)
  });
}

export function listExperiences(
  childId: string,
  token: string
): Promise<Experience[]> {
  return request<Experience[]>(`/children/${childId}/experiences`, {
    headers: authHeaders(token)
  });
}
